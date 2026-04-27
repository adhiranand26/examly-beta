"""
Screenshot capture module.
Supports full-screen and region-selection capture.
"""

import io
import platform
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

import mss
import mss.tools
from PIL import Image

from src.config import TEMP_DIR, ensure_dirs


class ScreenCapture:
    """Cross-platform screenshot capture."""

    def __init__(self) -> None:
        ensure_dirs()
        self._last_path: Optional[Path] = None

    # ── Public API ─────────────────────────────────────────────────────
    def capture_full_screen(self) -> Path:
        """Capture full-screen screenshot, return path to saved PNG."""
        with mss.mss() as sct:
            # Monitor 0 is the "all-monitors" virtual screen
            monitor = sct.monitors[0]
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        return self._save(img)

    def capture_region_interactive(self) -> Optional[Path]:
        """
        Interactive region capture using native macOS screencapture crosshairs.
        Returns Path to saved image, or None if user canceled.
        """
        if platform.system() == "Darwin":
            import subprocess
            ts = int(time.time() * 1000)
            path = TEMP_DIR / f"capture_{ts}.png"
            # -i = interactive, -x = no sound
            res = subprocess.run(["/usr/sbin/screencapture", "-i", "-x", str(path)])
            if res.returncode == 0 and path.exists():
                self._last_path = path
                return path
        return None

    def capture_region(self, region: Tuple[int, int, int, int]) -> Path:
        """
        Capture a rectangular region.
        region: (left, top, width, height) in pixels.
        """
        with mss.mss() as sct:
            monitor = {"left": region[0], "top": region[1],
                        "width": region[2], "height": region[3]}
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        return self._save(img)

    def capture_to_bytes(self) -> bytes:
        """Capture full-screen and return raw PNG bytes (for in-memory use)."""
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    @property
    def last_path(self) -> Optional[Path]:
        return self._last_path

    # ── Private ────────────────────────────────────────────────────────
    def _save(self, img: Image.Image) -> Path:
        """Save image to temp directory, return Path."""
        ts = int(time.time() * 1000)
        path = TEMP_DIR / f"capture_{ts}.png"
        img.save(str(path), format="PNG", optimize=True)
        self._last_path = path
        return path

    def cleanup(self, keep_last: int = 5) -> None:
        """Remove old captures, keeping the most recent `keep_last`."""
        files = sorted(TEMP_DIR.glob("capture_*.png"), key=lambda p: p.stat().st_mtime)
        for f in files[:-keep_last]:
            f.unlink(missing_ok=True)
