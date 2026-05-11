"""
Tkinter windows: small input prompt for new thoughts and a viewer for past entries.

Styled after the prototype sketch (a-digital-journal.pptx, slide 4): a clean
white card with a thin tan border, Helvetica for chrome (date, hints), Georgia
italic for the thought itself.
"""

import sys
import tkinter as tk
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
    text_widget.focus_set()

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

    root.mainloop()


def show_viewer_window(entries):
    _enable_windows_dpi_awareness()
    root = tk.Tk()
    scale = _tk_dpi_scale(root)
    root.title("Transient Thoughts — All Entries")
    root.geometry(f"{int(640 * scale)}x{int(480 * scale)}")
    root.attributes("-topmost", True)
    root.configure(bg=CARD_BG)

    card = tk.Frame(
        root, bg=CARD_BG,
        highlightthickness=1,
        highlightbackground=PANEL_BORDER,
        highlightcolor=PANEL_BORDER,
    )
    card.pack(fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(card)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text = tk.Text(
        card,
        wrap=tk.WORD,
        bg=CARD_BG, fg=DARK_TEXT,
        font=FONT_GEORGIA_ENTRY,
        yscrollcommand=scrollbar.set,
        state=tk.NORMAL,
        relief=tk.FLAT, bd=0,
        highlightthickness=0,
        padx=20, pady=16,
        spacing1=2, spacing3=10,
    )
    text.pack(fill=tk.BOTH, expand=True)
    scrollbar.config(command=text.yview)

    text.tag_configure("ts", font=FONT_HELV_META, foreground=MUTED_TEXT, spacing1=10)
    text.tag_configure("body", font=FONT_GEORGIA_ENTRY, foreground=DARK_TEXT)

    if not entries:
        text.insert(tk.END, "No thoughts recorded yet.", "body")
    else:
        for _id, timestamp, thought in entries:
            try:
                dt = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
                display_ts = dt.astimezone().strftime("%Y-%m-%d %H:%M")
            except ValueError:
                display_ts = timestamp
            text.insert(tk.END, f"{display_ts}\n", "ts")
            text.insert(tk.END, f"{thought}\n\n", "body")

    text.config(state=tk.DISABLED)

    root.bind("<Escape>", lambda e: root.destroy())
    root.mainloop()
