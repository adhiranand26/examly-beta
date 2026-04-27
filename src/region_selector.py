"""
Region-selection overlay.
Opens a transparent full-screen window where the user drags to select a rectangle.
Returns (left, top, width, height) or None if cancelled.
"""

import platform
import tkinter as tk
from typing import Optional, Tuple


class RegionSelector:
    """Full-screen transparent overlay for drag-to-select region capture."""

    def __init__(self) -> None:
        self.result: Optional[Tuple[int, int, int, int]] = None
        self._start_x = 0
        self._start_y = 0

    def select(self) -> Optional[Tuple[int, int, int, int]]:
        """Show the selector and block until the user finishes. Returns region or None."""
        root = tk.Tk()
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)

        # Platform-specific transparency
        if platform.system() == "Darwin":
            root.attributes("-transparent", True)
            root.config(bg="systemTransparent")
        else:
            root.attributes("-alpha", 0.3)
            root.config(bg="black")

        root.config(cursor="crosshair")

        canvas = tk.Canvas(root, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        if platform.system() == "Darwin":
            canvas.config(bg="systemTransparent")
        else:
            canvas.config(bg="black")

        rect_id = None

        def on_press(event: tk.Event) -> None:
            nonlocal rect_id
            self._start_x = event.x_root
            self._start_y = event.y_root
            rect_id = canvas.create_rectangle(
                event.x, event.y, event.x, event.y,
                outline="#00ff88", width=2, dash=(4, 4),
            )

        def on_drag(event: tk.Event) -> None:
            if rect_id:
                canvas.coords(
                    rect_id,
                    self._start_x - root.winfo_rootx(),
                    self._start_y - root.winfo_rooty(),
                    event.x,
                    event.y,
                )

        def on_release(event: tk.Event) -> None:
            x1, y1 = self._start_x, self._start_y
            x2, y2 = event.x_root, event.y_root
            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            if width > 10 and height > 10:
                self.result = (left, top, width, height)
            root.destroy()

        def on_escape(event: tk.Event) -> None:
            root.destroy()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        root.bind("<Escape>", on_escape)

        root.mainloop()
        return self.result
