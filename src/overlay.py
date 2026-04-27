"""
Overlay UI — launched as a SEPARATE PROCESS.
Smaller, auto-dismisses after 5 seconds.

Usage:
    python -m src.overlay --json-file results.json
"""

import argparse
import json
import platform
import sys
import tkinter as tk

try:
    import pyperclip
except ImportError:
    pyperclip = None


# ── Colour palette ────────────────────────────────────────────────────
C = {
    "bg":      "#0f0f14",
    "surface": "#1a1a24",
    "card":    "#22223a",
    "accent":  "#7c5cfc",
    "green":   "#00e68a",
    "text":    "#e8e8f0",
    "muted":   "#8888a0",
    "border":  "#2e2e44",
    "error":   "#ff5566",
}


class OverlayWindow:
    """Compact floating result overlay — auto-dismisses after 5s."""

    def __init__(self, ocr_text: str = "", ai_text: str = "",
                 status: str = "Done ✓", auto_close_ms: int = 5000):
        self._drag_x = 0
        self._drag_y = 0

        self._root = tk.Tk()
        root = self._root
        root.title("ScreenAssist")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=C["bg"])

        from src.config import AppConfig
        opacity = AppConfig.load().overlay_opacity
        
        if platform.system() == "Darwin":
            root.attributes("-alpha", opacity)
        else:
            root.attributes("-alpha", opacity)

        # Size — top-right corner
        w, h = 260, 100
        sw = root.winfo_screenwidth()
        root.geometry(f"{w}x{h}+{sw - w - 16}+32")

        self._build(root, ocr_text, ai_text, status)
        self._make_draggable(root)

        # Auto-close after timeout
        if auto_close_ms > 0:
            root.after(auto_close_ms, root.destroy)

    def run(self):
        self._root.mainloop()

    # ── Build ──────────────────────────────────────────────────────────
    def _build(self, root, ocr_text, ai_text, status):
        pad = 8

        # Title bar (compact)
        title_bar = tk.Frame(root, bg=C["surface"], height=28)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        tk.Label(
            title_bar, text="⚡ ScreenAssist", bg=C["surface"],
            fg=C["accent"], font=("Helvetica", 11, "bold"),
        ).pack(side="left", padx=pad)

        tk.Label(
            title_bar, text=status, bg=C["surface"],
            fg=C["green"], font=("Helvetica", 10),
        ).pack(side="left", padx=4)

        # Close button
        close_btn = tk.Label(
            title_bar, text=" ✕ ", bg=C["surface"], fg=C["muted"],
            font=("Helvetica", 12), cursor="hand2",
        )
        close_btn.pack(side="right", padx=2)
        close_btn.bind("<Button-1>", lambda e: root.destroy())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg=C["error"]))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg=C["muted"]))

        # ─── AI Answer (main content) ────────────────────────────────
        ai_hdr = tk.Frame(root, bg=C["bg"])
        ai_hdr.pack(fill="x", padx=pad, pady=(6, 2))
        tk.Label(ai_hdr, text="🤖 Answer", bg=C["bg"],
                 fg=C["text"], font=("Helvetica", 11, "bold")).pack(side="left")

        copy_btn = tk.Label(ai_hdr, text=" Copy ", bg=C["card"], fg=C["muted"],
                            font=("Helvetica", 9), cursor="hand2")
        copy_btn.pack(side="right")
        copy_btn.bind("<Button-1>", lambda e: self._copy(self._ai_widget))

        ai_frame = tk.Frame(root, bg=C["border"], bd=1)
        ai_frame.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        self._ai_widget = tk.Text(
            ai_frame, bg=C["card"], fg=C["green"],
            font=("Menlo", 11), wrap="word",
            insertbackground=C["green"], relief="flat",
            padx=6, pady=4,
        )
        self._ai_widget.pack(fill="both", expand=True)
        self._ai_widget.insert("1.0", ai_text or "No answer yet")
        self._ai_widget.configure(state="disabled")

    # ── Drag ───────────────────────────────────────────────────────────
    def _make_draggable(self, w):
        w.bind("<Button-1>", self._drag_start)
        w.bind("<B1-Motion>", self._drag_motion)

    def _drag_start(self, e):
        self._drag_x = e.x
        self._drag_y = e.y

    def _drag_motion(self, e):
        x = self._root.winfo_x() + e.x - self._drag_x
        y = self._root.winfo_y() + e.y - self._drag_y
        self._root.geometry(f"+{x}+{y}")

    @staticmethod
    def _copy(widget):
        text = widget.get("1.0", "end").strip()
        if text and pyperclip:
            pyperclip.copy(text)


# ── CLI entry point ───────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ocr", default="")
    parser.add_argument("--ai", default="")
    parser.add_argument("--status", default="Done ✓")
    parser.add_argument("--json-file", default="")
    parser.add_argument("--no-auto-close", action="store_true")
    args = parser.parse_args()

    ocr = args.ocr
    ai = args.ai
    status = args.status

    if args.json_file:
        try:
            with open(args.json_file) as f:
                data = json.load(f)
            ocr = data.get("ocr", ocr)
            ai = data.get("ai", ai)
            status = data.get("status", status)
        except Exception as e:
            ai = f"[Error: {e}]"

    auto_close = 0 if args.no_auto_close else 30000
    overlay = OverlayWindow(ocr_text=ocr, ai_text=ai, status=status, auto_close_ms=auto_close)
    overlay.run()


if __name__ == "__main__":
    main()
