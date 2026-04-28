"""
Tkinter windows: small input prompt for new thoughts and a viewer for past entries.
"""

import tkinter as tk
from datetime import datetime, timezone


def show_input_window(on_submit):
    root = tk.Tk()
    root.title("Quick Thought")
    root.geometry("420x70")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    # Center on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() - 420) // 2
    y = (root.winfo_screenheight() - 70) // 2
    root.geometry(f"+{x}+{y}")

    entry = tk.Entry(root, font=("Segoe UI", 12))
    entry.pack(fill=tk.X, padx=10, pady=15)
    entry.focus_set()

    def submit(event=None):
        text = entry.get().strip()
        if text:
            on_submit(text)
        root.destroy()

    entry.bind("<Return>", submit)
    root.bind("<Escape>", lambda e: root.destroy())

    root.mainloop()


def show_viewer_window(entries):
    root = tk.Tk()
    root.title("Transient Thoughts — All Entries")
    root.geometry("560x400")
    root.attributes("-topmost", True)

    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text = tk.Text(
        frame,
        wrap=tk.WORD,
        font=("Consolas", 10),
        yscrollcommand=scrollbar.set,
        state=tk.NORMAL,
    )
    text.pack(fill=tk.BOTH, expand=True)
    scrollbar.config(command=text.yview)

    if not entries:
        text.insert(tk.END, "No thoughts recorded yet.")
    else:
        for _id, timestamp, thought in entries:
            try:
                dt = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
                local_dt = dt.astimezone()
                display_ts = local_dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                display_ts = timestamp
            text.insert(tk.END, f"[{display_ts}]  {thought}\n")

    text.config(state=tk.DISABLED)

    root.bind("<Escape>", lambda e: root.destroy())
    root.mainloop()
