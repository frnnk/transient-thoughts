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

from transient_thoughts import settings as settings_module

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


def _force_foreground_windows(hwnd):
    """Bypass Windows' foreground-lock so the entry card actually grabs keyboard
    focus when summoned from a background context (global hotkey). focus_force()
    alone fails because SetForegroundWindow is blocked unless the calling thread
    owns recent input — which it doesn't when pynput's hook consumed the key.
    Attaching our thread input to the current foreground thread sidesteps the
    check; we detach immediately after."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        fg = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg, 0)
        cur_thread = kernel32.GetCurrentThreadId()
        if fg_thread and fg_thread != cur_thread:
            user32.AttachThreadInput(fg_thread, cur_thread, True)
            try:
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)
            finally:
                user32.AttachThreadInput(fg_thread, cur_thread, False)
        else:
            user32.SetForegroundWindow(hwnd)
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


def _place_window(root, w, h, placement):
    """Position a window per the user's placement setting."""
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    margin = 40
    if placement == "top-left":
        x, y = margin, margin
    elif placement == "top-right":
        x, y = sw - w - margin, margin
    elif placement == "bottom-left":
        x, y = margin, sh - h - margin
    elif placement == "bottom-right":
        x, y = sw - w - margin, sh - h - margin
    else:  # "center" or anything unrecognized
        x, y = (sw - w) // 2, (sh - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")


def show_input_window(on_submit, on_view=None, on_quit=None, on_settings=None, placement="center"):
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
        text="esc close  ·  ↵ save  ·  ↑↓ scroll  ·  ctrl+l view  ·  ctrl+s settings  ·  ctrl+q quit",
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

    def open_settings(event=None):
        root.destroy()
        if on_settings is not None:
            on_settings()
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
    if on_settings is not None:
        text_widget.bind("<Control-s>", open_settings)
        root.bind("<Control-s>", open_settings)
    if on_quit is not None:
        text_widget.bind("<Control-q>", quit_app)
        root.bind("<Control-q>", quit_app)

    # Size the window to fit its children (so the hint pins to the bottom) and place it.
    root.update_idletasks()
    w = int(540 * scale)
    h = root.winfo_reqheight()
    _place_window(root, w, h, placement)

    # Grab OS-level focus (tray-icon callbacks don't auto-focus on Windows), then
    # direct the keyboard focus to the text widget so the user can type immediately.
    def grab_focus():
        _force_foreground_windows(root.winfo_id())
        root.focus_force()
        text_widget.focus_set()
    root.after(10, grab_focus)

    root.mainloop()


def show_viewer_window(entries, on_settings=None):
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
        text="esc close  ·  drag header to move  ·  ↑↓ scroll  ·  ctrl+s settings",
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

    if on_settings is not None:
        def open_settings(event=None):
            root.destroy()
            on_settings()
            return "break"
        root.bind("<Control-s>", open_settings)

    root.mainloop()


def show_settings_window(current_settings, on_save):
    """Form for editing user-facing settings. Theme matches the input/viewer panels."""
    _enable_windows_dpi_awareness()
    root = tk.Tk()
    scale = _tk_dpi_scale(root)
    root.title("Transient Thoughts — Settings")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg=CARD_BG)

    card = tk.Frame(
        root, bg=CARD_BG,
        highlightthickness=1,
        highlightbackground=PANEL_BORDER,
        highlightcolor=PANEL_BORDER,
    )
    card.pack(fill=tk.BOTH, expand=True)

    # Header: dot + "settings" label, doubles as drag handle.
    header = tk.Frame(card, bg=CARD_BG, cursor="fleur")
    header.pack(side=tk.TOP, fill=tk.X, padx=18, pady=(16, 0))

    dot_px = max(8, int(10 * scale))
    dot = tk.Canvas(
        header, width=dot_px, height=dot_px,
        bg=CARD_BG, highlightthickness=0, cursor="fleur",
    )
    dot.create_oval(1, 1, dot_px - 1, dot_px - 1, fill=DOT_COLOR, outline=DOT_COLOR)
    dot.pack(side=tk.LEFT, padx=(0, 8))

    title_label = tk.Label(
        header, text="settings",
        bg=CARD_BG, fg=MUTED_TEXT, font=FONT_HELV_META, cursor="fleur",
    )
    title_label.pack(side=tk.LEFT)

    # Hint footer.
    tk.Label(
        card,
        text="esc cancel  ·  ↵ save  ·  drag header to move",
        bg=CARD_BG, fg=MUTED_TEXT, font=FONT_HELV_META,
    ).pack(side=tk.BOTTOM, anchor="w", padx=18, pady=(8, 16))

    # Form body.
    form = tk.Frame(card, bg=CARD_BG)
    form.pack(side=tk.TOP, fill=tk.X, padx=18, pady=(22, 6))

    interval_var = tk.StringVar(value=str(current_settings.interval_minutes))
    enabled_var = tk.BooleanVar(value=current_settings.notifications_enabled)
    placement_var = tk.StringVar(value=current_settings.placement)
    quiet_enabled_var = tk.BooleanVar(value=current_settings.quiet_hours_enabled)
    quiet_start_var = tk.StringVar(value=str(current_settings.quiet_start_hour))
    quiet_end_var = tk.StringVar(value=str(current_settings.quiet_end_hour))
    quiet_tz_var = tk.StringVar(value=current_settings.quiet_hours_timezone)

    def make_label(parent, text):
        return tk.Label(
            parent, text=text, bg=CARD_BG, fg=MUTED_TEXT,
            font=FONT_HELV_META, width=14, anchor="w",
        )

    def georgia(parent, text):
        return tk.Label(parent, text=text, bg=CARD_BG, fg=DARK_TEXT, font=FONT_GEORGIA_ENTRY)

    def themed_spinbox(parent, var, lo, hi, width=4):
        return tk.Spinbox(
            parent, from_=lo, to=hi, textvariable=var, width=width,
            font=FONT_GEORGIA_ENTRY, bg=CARD_BG, fg=DARK_TEXT,
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=PANEL_BORDER, highlightcolor=PANEL_BORDER,
            buttonbackground=CARD_BG, justify=tk.CENTER,
            insertbackground=DARK_TEXT,
        )

    def themed_check(parent, var, text):
        return tk.Checkbutton(
            parent, text=text, variable=var,
            bg=CARD_BG, fg=DARK_TEXT, font=FONT_GEORGIA_ENTRY,
            activebackground=CARD_BG, activeforeground=DARK_TEXT,
            selectcolor=CARD_BG, anchor="w",
            relief=tk.FLAT, bd=0, highlightthickness=0,
        )

    # Row: frequency
    row = tk.Frame(form, bg=CARD_BG); row.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
    make_label(row, "frequency").pack(side=tk.LEFT)
    georgia(row, "every").pack(side=tk.LEFT)
    themed_spinbox(row, interval_var, 1, 1440, 5).pack(side=tk.LEFT, padx=(8, 8))
    georgia(row, "minutes").pack(side=tk.LEFT)

    # Row: notifications
    row = tk.Frame(form, bg=CARD_BG); row.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
    make_label(row, "notifications").pack(side=tk.LEFT)
    themed_check(row, enabled_var, "show prompts").pack(side=tk.LEFT)

    # Row: placement
    row = tk.Frame(form, bg=CARD_BG); row.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
    make_label(row, "placement").pack(side=tk.LEFT)
    placement_combo = ttk.Combobox(
        row, textvariable=placement_var,
        values=list(settings_module.PLACEMENTS),
        state="readonly", width=14, font=FONT_GEORGIA_ENTRY,
    )
    placement_combo.pack(side=tk.LEFT)

    # Row: quiet hours
    row = tk.Frame(form, bg=CARD_BG); row.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
    make_label(row, "quiet hours").pack(side=tk.LEFT)
    themed_check(row, quiet_enabled_var, "from").pack(side=tk.LEFT)
    themed_spinbox(row, quiet_start_var, 0, 23, 3).pack(side=tk.LEFT, padx=(4, 6))
    georgia(row, "to").pack(side=tk.LEFT)
    themed_spinbox(row, quiet_end_var, 0, 23, 3).pack(side=tk.LEFT, padx=(6, 0))

    # Row: timezone for the quiet-hours bounds above.
    row = tk.Frame(form, bg=CARD_BG); row.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
    make_label(row, "hours timezone").pack(side=tk.LEFT)
    tz_combo = ttk.Combobox(
        row, textvariable=quiet_tz_var,
        values=list(settings_module.TIMEZONES),
        state="readonly", width=20, font=FONT_GEORGIA_ENTRY,
    )
    tz_combo.pack(side=tk.LEFT)

    def commit(event=None):
        try:
            interval = max(1, int(interval_var.get()))
            qs = max(0, min(23, int(quiet_start_var.get())))
            qe = max(0, min(23, int(quiet_end_var.get())))
        except (TypeError, ValueError):
            return "break"
        placement = (
            placement_var.get()
            if placement_var.get() in settings_module.PLACEMENTS
            else current_settings.placement
        )
        tz_choice = (
            quiet_tz_var.get()
            if quiet_tz_var.get() in settings_module.TIMEZONES
            else current_settings.quiet_hours_timezone
        )
        new_settings = type(current_settings)(
            interval_minutes=interval,
            notifications_enabled=bool(enabled_var.get()),
            placement=placement,
            quiet_hours_enabled=bool(quiet_enabled_var.get()),
            quiet_start_hour=qs,
            quiet_end_hour=qe,
            quiet_hours_timezone=tz_choice,
        )
        on_save(new_settings)
        root.destroy()
        return "break"

    root.bind("<Return>", commit)
    root.bind("<Escape>", lambda e: root.destroy())

    # Drag from the header strip.
    drag = {"x": 0, "y": 0}
    def start_drag(e):
        drag["x"] = e.x_root - root.winfo_x()
        drag["y"] = e.y_root - root.winfo_y()
    def do_drag(e):
        root.geometry(f"+{e.x_root - drag['x']}+{e.y_root - drag['y']}")
    for widget in (header, dot, title_label):
        widget.bind("<Button-1>", start_drag)
        widget.bind("<B1-Motion>", do_drag)

    # Size and center.
    root.update_idletasks()
    w = int(520 * scale)
    h = root.winfo_reqheight()
    _place_window(root, w, h, "center")

    root.after(10, root.focus_force)

    root.mainloop()
