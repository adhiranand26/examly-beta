import logging
import sys
from pynput import keyboard
from PySide6.QtCore import QObject, Signal

class HotkeySignals(QObject):
    triggered_region = Signal()
    triggered_full = Signal()
    triggered_show = Signal()

class HotkeyService:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.signals = HotkeySignals()
        self.listener = None

    def start(self):
        self.stop()
        
        cfg = self.config_manager.config.hotkey
        
        def parse_combo(combo_str):
            parts = combo_str.lower().split('+')
            mapped = []
            for p in parts:
                if p == 'cmd':
                    # Windows restricts the Win key globally. Fallback to Ctrl on Windows.
                    mapped.append('<ctrl>' if sys.platform == 'win32' else '<cmd>')
                elif p in ('ctrl', 'shift', 'alt'):
                    mapped.append(f'<{p}>')
                else:
                    mapped.append(p)
            return "+".join(mapped)

        mapping = {
            parse_combo(cfg.region_capture): lambda: self.signals.triggered_region.emit(),
            parse_combo(cfg.full_capture): lambda: self.signals.triggered_full.emit(),
            parse_combo(cfg.show_last): lambda: self.signals.triggered_show.emit(),
        }
        
        try:
            self.listener = keyboard.GlobalHotKeys(mapping)
            self.listener.start()
            logging.info("Hotkey listener started successfully.")
        except Exception as e:
            logging.error(f"Failed to start hotkey listener: {e}")

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
