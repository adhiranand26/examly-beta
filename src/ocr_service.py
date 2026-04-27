"""
Production-grade OCR service with multi-pass extraction,
adaptive preprocessing, Tesseract auto-detection, and confidence scoring.
"""
import logging
import shutil
import sys
import os
import time
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

# ── Tesseract Auto-Detection ──
_TESSERACT_AVAILABLE = False

def _detect_tesseract():
    """Find tesseract.exe — checks bundled copy first, then system installs."""
    global _TESSERACT_AVAILABLE
    try:
        import pytesseract
        
        if sys.platform == "win32":
            search_paths = []
            
            # 1. Check BUNDLED copy inside PyInstaller package (highest priority)
            if getattr(sys, 'frozen', False):
                bundled = os.path.join(sys._MEIPASS, "tesseract", "tesseract.exe")
                search_paths.append(bundled)
            
            # 2. Check common system install paths
            search_paths += [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
            ]
            
            for path in search_paths:
                if os.path.isfile(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    # Set TESSDATA_PREFIX for bundled copy so it finds language files
                    tessdata = os.path.join(os.path.dirname(path), "tessdata")
                    if os.path.isdir(tessdata):
                        os.environ["TESSDATA_PREFIX"] = os.path.dirname(path)
                    _TESSERACT_AVAILABLE = True
                    logger.info(f"Tesseract found at: {path}")
                    return
        
        # macOS / Linux: check PATH
        if shutil.which("tesseract"):
            _TESSERACT_AVAILABLE = True
            logger.info("Tesseract found on PATH")
            return
        
        logger.warning("Tesseract not found. OCR will be disabled — AI will use image-only mode.")
    except ImportError:
        logger.warning("pytesseract module not installed. OCR disabled.")

_detect_tesseract()


class OCRService:
    """Multi-pass OCR with adaptive preprocessing and confidence scoring."""

    @staticmethod
    def _preprocess_standard(img: Image.Image) -> Image.Image:
        """Standard preprocessing: grayscale + high contrast."""
        img = img.convert("L")
        img = ImageEnhance.Contrast(img).enhance(2.0)
        return img

    @staticmethod
    def _preprocess_adaptive(img: Image.Image) -> Image.Image:
        """Aggressive preprocessing: denoise + sharpen + normalize."""
        img = img.convert("L")
        # Denoise with median filter
        img = img.filter(ImageFilter.MedianFilter(size=3))
        # Sharpen to recover text edges
        img = img.filter(ImageFilter.SHARPEN)
        # High contrast
        img = ImageEnhance.Contrast(img).enhance(2.5)
        # Brightness normalization
        img = ImageEnhance.Brightness(img).enhance(1.2)
        return img

    @staticmethod
    def _run_ocr_pass(img: Image.Image) -> dict:
        """Run a single OCR pass and return structured results."""
        import pytesseract
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        text_blocks = []
        total_conf = 0
        count = 0
        
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            if text and conf > 0:  # Ignore negative and zero confidence
                text_blocks.append(text)
                total_conf += conf
                count += 1
        
        avg_conf = (total_conf / count / 100.0) if count > 0 else 0.0
        full_text = " ".join(text_blocks)
        
        return {
            "text": full_text,
            "confidence": round(avg_conf, 2),
            "blocks": text_blocks,
            "word_count": count,
        }

    @staticmethod
    def extract_structured(img: Image.Image) -> dict:
        """
        Multi-pass OCR extraction with intelligent result combination.
        Returns the best result from multiple preprocessing strategies.
        Falls back to empty data (AI will use image directly) if Tesseract is missing.
        """
        start_time = time.time()
        
        if not _TESSERACT_AVAILABLE:
            logger.warning("OCR skipped — Tesseract not available. AI will analyze image directly.")
            return {
                "text": "",
                "confidence": 0.0,
                "blocks": [],
                "word_count": 0,
                "ocr_time_ms": 0,
                "ocr_available": False,
            }

        try:
            # Pass 1: Standard preprocessing
            standard_img = OCRService._preprocess_standard(img)
            result_standard = OCRService._run_ocr_pass(standard_img)
            
            # Pass 2: Adaptive preprocessing (only if Pass 1 was weak)
            if result_standard["confidence"] < 0.6 or result_standard["word_count"] < 3:
                adaptive_img = OCRService._preprocess_adaptive(img)
                result_adaptive = OCRService._run_ocr_pass(adaptive_img)
                
                # Pass 3: Raw image (sometimes preprocessing hurts clean screenshots)
                raw_gray = img.convert("L")
                result_raw = OCRService._run_ocr_pass(raw_gray)
                
                # Pick the best result by word count * confidence score
                candidates = [result_standard, result_adaptive, result_raw]
                best = max(candidates, key=lambda r: r["word_count"] * r["confidence"])
                logger.info(
                    f"OCR multi-pass: standard={result_standard['confidence']:.2f}({result_standard['word_count']}w), "
                    f"adaptive={result_adaptive['confidence']:.2f}({result_adaptive['word_count']}w), "
                    f"raw={result_raw['confidence']:.2f}({result_raw['word_count']}w) → best={best['confidence']:.2f}"
                )
            else:
                best = result_standard
                logger.info(f"OCR single-pass: conf={best['confidence']:.2f}, words={best['word_count']}")

            elapsed_ms = int((time.time() - start_time) * 1000)
            best["ocr_time_ms"] = elapsed_ms
            best["ocr_available"] = True
            
            # Warn if result is still poor
            if best["confidence"] < 0.3 or best["word_count"] < 2:
                logger.warning(f"OCR result is low quality (conf={best['confidence']:.2f}, words={best['word_count']}). AI will rely on image.")
            
            return best

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"OCR failure after {elapsed_ms}ms: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "blocks": [],
                "word_count": 0,
                "ocr_time_ms": elapsed_ms,
                "ocr_available": True,
            }
