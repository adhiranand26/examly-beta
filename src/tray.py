"""
System-tray icon for ScreenAssist.
Provides quick access to settings, quit, and status.
Uses pystray on Windows, native menu-bar on macOS (via tkinter).
"""

import platform
import threading
import tkinter as tk
from typing import Callable, Optional


class TrayIcon:
    """
    Lightweight tray/menu-bar presence.
    On macOS we use a tiny tkinter root with a menu.
    On Windows we could use pystray, but for simplicity we re-use tkinter.
    """

    def __init__(
        self,
        on_settings: Callable,
        on_quit: Callable,
    ) -> None:
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._root: Optional[tk.Tk] = None

    def run(self) -> None:
        """
        Start the tray icon — this blocks (runs tkinter mainloop).
        Should be called from the main thread.
        """
        self._root = tk.Tk()
        self._root.title("ScreenAssist")
        self._root.withdraw()  # hide the empty window

        # macOS: create a proper menu-bar app
        if platform.system() == "Darwin":
            menubar = tk.Menu(self._root)
            app_menu = tk.Menu(menubar, name="apple", tearoff=0)
            app_menu.add_command(label="Settings…", command=self._on_settings)
            app_menu.add_separator()
            app_menu.add_command(label="Quit ScreenAssist", command=self._quit)
            menubar.add_cascade(menu=app_menu)
            self._root.config(menu=menubar)
            # Keep the app "alive" for the menu bar
            self._root.createcommand("tk::mac::Quit", self._quit)
        else:
            # On Windows/Linux, keep a hidden root so we can schedule callbacks
            pass

        self._root.mainloop()

    def schedule(self, fn: Callable) -> None:
        """Thread-safe callback scheduling on the main-thread event loop."""
        if self._root:
            self._root.after(0, fn)

    def _quit(self) -> None:
        self._on_quit()
        if self._root:
            self._root.destroy()
