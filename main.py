import sys
import os



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

import logging
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ExamlyOrchestrator:
    def __init__(self):
        self.app = QApplication(sys.argv)
        # Setup Asyncio integration with PyQt6
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

        self.setup_hotkeys()
        self.settings.show()

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
        self.overlay.show_result(self.last_result)

    async def process_pipeline(self, img):
        self.overlay.show_result({"answer": "Processing Image and AI...", "confidence": 0})
        
        loop = asyncio.get_running_loop()
        
        # Helper to encode image in background
        def prep_image(i):
            buffered = io.BytesIO()
            i.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # Parallelize OCR and Base64 Encoding
        ocr_task = loop.run_in_executor(None, OCRService.extract_structured, img)
        prep_task = loop.run_in_executor(None, prep_image, img)
        
        ocr_data, img_b64 = await asyncio.gather(ocr_task, prep_task)
        
        # Call AI asynchronously
        ai_data = await self.ai.process_async(img_b64, ocr_data)
        
        self.last_result = ai_data
        self.overlay.show_result(ai_data)

    def run(self):
        with self.loop:
            self.loop.run_forever()

if __name__ == "__main__":
    orchestrator = ExamlyOrchestrator()
    orchestrator.run()
