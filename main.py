"""
Examly — Production Entry Point
- File + console logging with rotation
- Performance tracking per pipeline run
- Memory cleanup after each capture
- Crash recovery with max restarts
"""
import sys
import os
import logging
import logging.handlers
import time
import gc

# ── Logging Setup (File + Console + Rotation) ──
LOG_DIR = os.path.join(os.path.expanduser("~"), "Examly", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

# Rotating file handler (5MB max, keep 3 backups)
file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

logging.info(f"Examly starting. Logs → {LOG_FILE}")

# Fix for Qt Plugins when bundled with PyInstaller or macOS wrapper
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    qt_plugins_path = os.path.join(bundle_dir, "PySide6", "Qt", "plugins")
    if not os.path.exists(qt_plugins_path):
        qt_plugins_path = os.path.join(bundle_dir, "PySide6", "plugins")
    os.environ["QT_PLUGIN_PATH"] = qt_plugins_path
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(qt_plugins_path, "platforms")
else:
    try:
        import PySide6
        pyside_plugin_path = os.path.join(os.path.dirname(PySide6.__file__), "Qt", "plugins")
        os.environ["QT_PLUGIN_PATH"] = pyside_plugin_path
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(pyside_plugin_path, "platforms")
    except Exception:
        pass

os.environ["QT_API"] = "pyside6"

import asyncio
import qasync
import io
import base64
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

# Initialize High DPI rounding policy BEFORE QApplication is created
QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

from src.config_manager import ConfigManager
from src.capture_service import CaptureService
from src.ocr_service import OCRService
from src.ai_service import AIService
from src.hotkey_service import HotkeyService
from src.overlay_ui import OverlayUI
from src.settings_ui import SettingsUI
from src.protection import runtime_integrity_check


class ExamlyOrchestrator:
    def __init__(self):
        self.app = QApplication(sys.argv)
        # Setup Asyncio integration with Qt
        self.loop = qasync.QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)
        
        self.config = ConfigManager()
        self.ai = AIService(self.config)
        self.hotkey = HotkeyService(self.config)
        
        self.overlay = OverlayUI(self.config)
        self.settings = SettingsUI(self.config, self.hotkey, self.overlay)
        self.snipper = None
        self.last_result = {}
        self.is_capturing = False
        self.pipeline_count = 0

        self.setup_hotkeys()
        self.settings.show()
        
        # Runtime integrity check (logs warning, does not block)
        if not runtime_integrity_check():
            logging.warning("Runtime integrity check failed. App may behave differently.")
        
        logging.info("Examly initialized successfully.")

    def setup_hotkeys(self):
        self.hotkey.signals.triggered_full.connect(self.on_full_capture)
        self.hotkey.signals.triggered_region.connect(self.on_region_capture)
        self.hotkey.signals.triggered_show.connect(self.on_show_last)
        self.hotkey.start()

    def on_full_capture(self):
        logging.info("Full capture triggered")
        img = CaptureService.capture_full_screen()
        asyncio.create_task(self.process_pipeline(img))

    def on_region_capture(self):
        if self.is_capturing:
            return
        self.is_capturing = True
        logging.info("Region capture triggered")
        self.snipper = CaptureService.capture_region(self.on_region_captured)

    def on_region_captured(self, img):
        try:
            if img:
                asyncio.create_task(self.process_pipeline(img))
        finally:
            self.is_capturing = False

    def on_show_last(self):
        if self.overlay.isVisible():
            self.overlay.hide()
        else:
            self.overlay.show_result(self.last_result)

    async def process_pipeline(self, img):
        """Full processing pipeline with performance tracking and memory cleanup."""
        self.pipeline_count += 1
        pipeline_start = time.time()
        run_id = self.pipeline_count
        
        logging.info(f"[Pipeline #{run_id}] Starting...")
        
        # Show loading state
        self.overlay.show_result({
            "answer": "⏳ Processing...",
            "confidence": 0,
            "type": "",
            "explanation": "Capturing and analyzing...",
        })
        
        loop = asyncio.get_running_loop()
        
        # Helper to encode image in background
        def prep_image(i):
            buffered = io.BytesIO()
            i.save(buffered, format="PNG")
            encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
            buffered.close()
            return encoded
        
        # Parallelize OCR and Base64 Encoding
        ocr_start = time.time()
        ocr_task = loop.run_in_executor(None, OCRService.extract_structured, img)
        prep_task = loop.run_in_executor(None, prep_image, img)
        
        ocr_data, img_b64 = await asyncio.gather(ocr_task, prep_task)
        ocr_elapsed = int((time.time() - ocr_start) * 1000)
        
        logging.info(
            f"[Pipeline #{run_id}] OCR done in {ocr_elapsed}ms — "
            f"conf={ocr_data.get('confidence', 0):.2f}, words={ocr_data.get('word_count', 0)}, "
            f"text_preview={ocr_data.get('text', '')[:80]}..."
        )
        
        # Update overlay with OCR status
        if ocr_data.get("confidence", 0) < 0.3:
            self.overlay.show_result({
                "answer": "⏳ Low OCR — using image analysis...",
                "confidence": 0,
                "type": "",
                "explanation": "AI will read directly from the screenshot.",
            })
        
        # Call AI asynchronously (with multi-model fallback + retry)
        ai_start = time.time()
        ai_data = await self.ai.process_async(img_b64, ocr_data)
        ai_elapsed = int((time.time() - ai_start) * 1000)
        
        total_elapsed = int((time.time() - pipeline_start) * 1000)
        
        logging.info(
            f"[Pipeline #{run_id}] AI done in {ai_elapsed}ms — "
            f"provider={ai_data.get('provider', 'unknown')}, "
            f"answer={str(ai_data.get('answer', ''))[:60]}, "
            f"conf={ai_data.get('confidence', 0)}"
        )
        logging.info(f"[Pipeline #{run_id}] Total pipeline: {total_elapsed}ms (OCR={ocr_elapsed}ms, AI={ai_elapsed}ms)")
        
        # Add timing metadata
        ai_data["pipeline_ms"] = total_elapsed
        ai_data["ocr_ms"] = ocr_elapsed
        ai_data["ai_ms"] = ai_elapsed
        
        self.last_result = ai_data
        self.overlay.show_result(ai_data)
        
        # Save to history
        self.settings.add_to_history(ai_data)
        
        # Memory cleanup — release the large image and base64 string
        del img_b64
        del img
        gc.collect()
        logging.debug(f"[Pipeline #{run_id}] Memory cleaned.")

    def run(self):
        with self.loop:
            self.loop.run_forever()


def run_app():
    """Entry point with crash recovery."""
    orchestrator = ExamlyOrchestrator()
    orchestrator.run()


if __name__ == "__main__":
    MAX_RESTARTS = 5
    restarts = 0
    
    while restarts < MAX_RESTARTS:
        try:
            run_app()
            break  # Clean exit
        except SystemExit:
            break  # Intentional exit
        except Exception as e:
            restarts += 1
            logging.error(f"Crash #{restarts}: {e}", exc_info=True)
            if restarts >= MAX_RESTARTS:
                logging.critical("Max restarts reached. Exiting.")
                break
            logging.info(f"Auto-relaunching in 2 seconds... (attempt {restarts}/{MAX_RESTARTS})")
            time.sleep(2)
