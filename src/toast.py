"""
Toast notification — launched as a separate process on macOS
to avoid tkinter/pynput conflicts.

Usage:
    python -m src.toast "Screenshot captured ✓"
"""

import platform
import sys
import tkinter as tk


def show_toast_window(message: str, duration_ms: int = 2000, color: str = "#00e68a"):
    """Show a brief toast notification."""
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#1a1a24")

    if platform.system() == "Darwin":
        root.attributes("-alpha", 0.92)
    else:
        root.attributes("-alpha", 0.92)

    lbl = tk.Label(
        root, text=f"  ✅  {message}  ",
        font=("Helvetica", 13, "bold"),
        fg=color, bg="#1a1a24",
        padx=16, pady=10,
    )
    lbl.pack()

    root.update_idletasks()
    w = root.winfo_reqwidth()
    sw = root.winfo_screenwidth()
    root.geometry(f"+{(sw - w) // 2}+48")

    root.after(duration_ms, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "Done"
    color = sys.argv[2] if len(sys.argv) > 2 else "#00e68a"
    show_toast_window(msg, color=color)
