"""
Tkinter windows: small input prompt for new thoughts and a viewer for past entries.

Styled after the prototype sketch (a-digital-journal.pptx, slide 4): a clean
white card with a thin tan border, Helvetica for chrome (date, hints), Georgia
italic for the thought itself.
"""

import sys
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timezone

# Palette lifted from the prototype sketch.
PANEL_BORDER = "#C9C4B8"  # tan border around the card
CARD_BG = "#FFFFFF"       # white card surface
DOT_COLOR = "#D9D4C7"     # status dot next to timestamp
MUTED_TEXT = "#8A8680"    # chrome text (dates, hints)
DARK_TEXT = "#1A1A1A"     # thought body


def _enable_windows_dpi_awareness():
    """Tell Windows we'll handle DPI ourselves so Tk fonts render sharp on hi-DPI
    displays instead of being bitmap-upscaled and blurry."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # PROCESS_PER_MONITOR_DPI_AWARE = 2 (Win 8.1+); fall back to system aware.
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _tk_dpi_scale(root):
    """Return a pixel scale factor (1.0 at 96 DPI, 1.5 at 144 DPI, etc.) and sync
    Tk's point-based font scaling to match. Call right after creating the root."""
    px_per_inch = root.winfo_fpixels("1i")
    root.tk.call("tk", "scaling", px_per_inch / 72.0)
    return px_per_inch / 96.0

FONT_HELV_META = ("Helvetica", 9)
FONT_GEORGIA_BODY = ("Georgia", 14, "italic")
FONT_GEORGIA_ENTRY = ("Georgia", 12)


def _format_now_lowercase():
    """Format current local time as 'tuesday, 2:14 pm' to match the prototype."""
    now = datetime.now()
    hour12 = now.hour % 12 or 12
    ampm = "am" if now.hour < 12 else "pm"
    day = now.strftime("%A").lower()
    return f"{day}, {hour12}:{now.minute:02d} {ampm}"


def show_input_window(on_submit, on_view=None, on_quit=None):
    _enable_windows_dpi_awareness()
    root = tk.Tk()
    scale = _tk_dpi_scale(root)
    root.title("Quick Thought")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg=CARD_BG)

    # Thin border around the white card (overrideredirect removes the WM frame).
    card = tk.Frame(
        root, bg=CARD_BG,
        highlightthickness=1,
        highlightbackground=PANEL_BORDER,
        highlightcolor=PANEL_BORDER,
    )
    card.pack(fill=tk.BOTH, expand=True)

    # Header row: small dot + lowercase Helvetica timestamp.
    header = tk.Frame(card, bg=CARD_BG)
    header.pack(side=tk.TOP, fill=tk.X, padx=18, pady=(16, 0))

    dot_px = max(8, int(10 * scale))
    dot = tk.Canvas(header, width=dot_px, height=dot_px, bg=CARD_BG, highlightthickness=0)
    dot.create_oval(1, 1, dot_px - 1, dot_px - 1, fill=DOT_COLOR, outline=DOT_COLOR)
    dot.pack(side=tk.LEFT, padx=(0, 8))

    tk.Label(
        header, text=_format_now_lowercase(),
        bg=CARD_BG, fg=MUTED_TEXT, font=FONT_HELV_META,
    ).pack(side=tk.LEFT)

    # Georgia italic multi-line text. Caps the visible area at 3 lines; arrow
    # keys scroll once content overflows. Return submits (no newline insertion).
    text_widget = tk.Text(
        card,
        height=3, width=1,            # width=1 + fill=X means width follows the card
        wrap=tk.WORD,
        font=FONT_GEORGIA_BODY,
        bg=CARD_BG, fg=DARK_TEXT,
        insertbackground=DARK_TEXT,
        relief=tk.FLAT, bd=0,
        highlightthickness=0,
    )
    text_widget.pack(side=tk.TOP, fill=tk.X, padx=18, pady=(22, 20))

    tk.Label(
        card,
        text="esc to close  ·  ↵ to save  ·  ↑↓ to scroll  ·  ctrl+l to view  ·  ctrl+q to quit",
        bg=CARD_BG, fg=MUTED_TEXT, font=FONT_HELV_META,
    ).pack(side=tk.TOP, anchor="w", padx=18, pady=(0, 16))

    def submit(event=None):
        content = text_widget.get("1.0", "end-1c").strip()
        if content:
            on_submit(content)
        root.destroy()
        return "break"  # swallow the newline so Return doesn't insert one

    def open_viewer(event=None):
        root.destroy()
        if on_view is not None:
            on_view()
        return "break"

    def quit_app(event=None):
        root.destroy()
        if on_quit is not None:
            on_quit()
        return "break"

    text_widget.bind("<Return>", submit)
    root.bind("<Escape>", lambda e: root.destroy())
    if on_view is not None:
        # Bind on both the text widget and root so the shortcut works regardless of focus.
        text_widget.bind("<Control-l>", open_viewer)
        root.bind("<Control-l>", open_viewer)
    if on_quit is not None:
        text_widget.bind("<Control-q>", quit_app)
        root.bind("<Control-q>", quit_app)

    # Size the window to fit its children (so the hint pins to the bottom) and center.
    root.update_idletasks()
    w = int(480 * scale)
    h = root.winfo_reqheight()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # Grab OS-level focus (tray-icon callbacks don't auto-focus on Windows), then
    # direct the keyboard focus to the text widget so the user can type immediately.
    def grab_focus():
        root.focus_force()
        text_widget.focus_set()
    root.after(10, grab_focus)

    root.mainloop()


def show_viewer_window(entries):
    _enable_windows_dpi_awareness()
    root = tk.Tk()
    scale = _tk_dpi_scale(root)
    root.title("Transient Thoughts — All Entries")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg=CARD_BG)

    # White card with the same thin tan border as the input panel.
    card = tk.Frame(
        root, bg=CARD_BG,
        highlightthickness=1,
        highlightbackground=PANEL_BORDER,
        highlightcolor=PANEL_BORDER,
    )
    card.pack(fill=tk.BOTH, expand=True)

    # Header: dot + count label. Doubles as a drag handle since there's no title bar.
    header = tk.Frame(card, bg=CARD_BG, cursor="fleur")
    header.pack(side=tk.TOP, fill=tk.X, padx=18, pady=(16, 0))

    dot_px = max(8, int(10 * scale))
    dot = tk.Canvas(
        header, width=dot_px, height=dot_px,
        bg=CARD_BG, highlightthickness=0, cursor="fleur",
    )
    dot.create_oval(1, 1, dot_px - 1, dot_px - 1, fill=DOT_COLOR, outline=DOT_COLOR)
    dot.pack(side=tk.LEFT, padx=(0, 8))

    count_label = tk.Label(
        header,
        text=f"all thoughts ({len(entries)})",
        bg=CARD_BG, fg=MUTED_TEXT, font=FONT_HELV_META,
        cursor="fleur",
    )
    count_label.pack(side=tk.LEFT)

    # Hint footer (matches the input panel's chrome).
    tk.Label(
        card,
        text="esc to close  ·  drag header to move  ·  ↑↓ to scroll",
        bg=CARD_BG, fg=MUTED_TEXT, font=FONT_HELV_META,
    ).pack(side=tk.BOTTOM, anchor="w", padx=18, pady=(8, 16))

    # Body: scrollable Text with a ttk scrollbar.
    body = tk.Frame(card, bg=CARD_BG)
    body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=18, pady=(14, 10))

    scrollbar = ttk.Scrollbar(body)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text = tk.Text(
        body,
        wrap=tk.WORD,
        bg=CARD_BG, fg=DARK_TEXT,
        font=FONT_GEORGIA_ENTRY,
        yscrollcommand=scrollbar.set,
        relief=tk.FLAT, bd=0,
        highlightthickness=0,
        padx=0, pady=0,
        spacing1=2, spacing3=4,
    )
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text.yview)

    # First timestamp sits flush with the top; subsequent ones get extra spacing
    # above to separate entries visually.
    text.tag_configure("ts", font=FONT_HELV_META, foreground=MUTED_TEXT, spacing1=18, spacing3=4)
    text.tag_configure("ts_first", font=FONT_HELV_META, foreground=MUTED_TEXT, spacing1=0, spacing3=4)
    text.tag_configure("body", font=FONT_GEORGIA_ENTRY, foreground=DARK_TEXT)

    if not entries:
        text.insert(tk.END, "No thoughts recorded yet.", "body")
    else:
        for idx, (_id, timestamp, thought) in enumerate(entries):
            try:
                dt = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
                display_ts = dt.astimezone().strftime("%Y-%m-%d %H:%M")
            except ValueError:
                display_ts = timestamp
            text.insert(tk.END, f"{display_ts}\n", "ts_first" if idx == 0 else "ts")
            text.insert(tk.END, f"{thought}\n", "body")

    text.config(state=tk.DISABLED)

    # Drag-to-move from the header strip (text/scrollbar keep normal interactions).
    drag = {"x": 0, "y": 0}
    def start_drag(e):
        drag["x"] = e.x_root - root.winfo_x()
        drag["y"] = e.y_root - root.winfo_y()
    def do_drag(e):
        root.geometry(f"+{e.x_root - drag['x']}+{e.y_root - drag['y']}")
    for widget in (header, dot, count_label):
        widget.bind("<Button-1>", start_drag)
        widget.bind("<B1-Motion>", do_drag)

    # Size and center.
    w, h = int(640 * scale), int(480 * scale)
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    root.bind("<Escape>", lambda e: root.destroy())
    
    # Up/Down arrow scrolling on top of the existing wheel + scrollbar mechanics.
    root.bind("<Up>", lambda e: text.yview_scroll(-1, "units"))
    root.bind("<Down>", lambda e: text.yview_scroll(1, "units"))
    root.mainloop()
