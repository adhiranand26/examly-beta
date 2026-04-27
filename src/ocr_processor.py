"""
OCR processing module.
Extracts and cleans text from screenshot images.
Optimized for screen captures (high-DPI, colored backgrounds).
"""

import platform
import re
import shutil
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

from src.config import OCRConfig


class OCRProcessor:
    """Tesseract-based OCR with preprocessing for screen captures."""

    def __init__(self, config: OCRConfig) -> None:
        self.config = config
        self._configure_tesseract()

    # ── Public API ─────────────────────────────────────────────────────
    def extract_text(self, image_path: Path) -> str:
        """Run OCR on an image file, return cleaned text."""
        if not self.config.enabled:
            return ""

        # Cloud OCR
        if self.config.provider == "ocr.space" and self.config.api_key:
            return self._run_ocr_space(image_path)

        # Local Tesseract OCR
        img = Image.open(image_path)

        # Try multiple preprocessing strategies, pick best result
        results = []

        # Strategy 1: Direct (no preprocessing — works great on clean screens)
        raw1 = self._run_ocr(img)
        results.append(raw1)

        # Strategy 2: Grayscale + high contrast
        img2 = self._preprocess_contrast(img)
        raw2 = self._run_ocr(img2)
        results.append(raw2)

        # Strategy 3: Inverted (for dark mode / dark backgrounds)
        img3 = ImageOps.invert(img.convert("RGB"))
        raw3 = self._run_ocr(img3)
        results.append(raw3)

        # Pick the result with the most text
        best = max(results, key=len)
        return self._clean(best)

    def _run_ocr_space(self, image_path: Path) -> str:
        """Use the OCR.space API."""
        try:
            import httpx
            with open(image_path, 'rb') as f:
                r = httpx.post(
                    'https://api.ocr.space/parse/image',
                    files={'file': (image_path.name, f, 'image/png')},
                    data={
                        'apikey': self.config.api_key,
                        'language': self.config.language,
                        'OCREngine': '2',  # Engine 2 is better for math/special chars
                    },
                    timeout=15.0
                )
            r.raise_for_status()
            data = r.json()
            if data.get('IsErroredOnProcessing'):
                print(f"[ocr.space] Error: {data.get('ErrorMessage')}")
                return ""
            
            # Combine all parsed text
            parsed = data.get('ParsedResults', [])
            text = "\n".join([p.get('ParsedText', '') for p in parsed])
            return self._clean(text)
        except Exception as e:
            print(f"[ocr.space] Exception: {e}")
            return ""

    def _run_ocr(self, img: Image.Image) -> str:
        """Run Tesseract with optimal settings for screen text."""
        try:
            return pytesseract.image_to_string(
                img,
                lang=self.config.language,
                config="--psm 3 --oem 3",  # fully automatic page segmentation + LSTM
            )
        except Exception as e:
            print(f"[ocr] error: {e}")
            return ""

    # ── Preprocessing ──────────────────────────────────────────────────
    @staticmethod
    def _preprocess_contrast(img: Image.Image) -> Image.Image:
        """Grayscale + contrast boost — good for light backgrounds."""
        img = img.convert("L")
        img = ImageEnhance.Contrast(img).enhance(2.5)
        img = img.filter(ImageFilter.SHARPEN)
        # Binarize with threshold
        img = img.point(lambda x: 0 if x < 140 else 255, '1')
        return img

    # ── Text cleanup ───────────────────────────────────────────────────
    @staticmethod
    def _clean(text: str) -> str:
        """Remove OCR artefacts and normalise whitespace."""
        # Collapse multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip per line
        lines = [line.strip() for line in text.splitlines()]
        # Remove lines that are only punctuation/noise (1-2 char noise)
        lines = [l for l in lines if len(l) > 1 or l.isalnum()]
        return "\n".join(lines).strip()

    # ── Setup ──────────────────────────────────────────────────────────
    def _configure_tesseract(self) -> None:
        """Set Tesseract binary path."""
        if self.config.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.config.tesseract_path
            return

        if platform.system() == "Darwin":
            for p in ["/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"]:
                if Path(p).exists():
                    pytesseract.pytesseract.tesseract_cmd = p
                    return
        elif platform.system() == "Windows":
            prog = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
            if prog.exists():
                pytesseract.pytesseract.tesseract_cmd = str(prog)
                return

        found = shutil.which("tesseract")
        if found:
            pytesseract.pytesseract.tesseract_cmd = found

    @staticmethod
    def is_available() -> bool:
        return shutil.which("tesseract") is not None
