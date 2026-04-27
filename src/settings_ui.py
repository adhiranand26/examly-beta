from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QComboBox, QSlider, QFormLayout
from PySide6.QtCore import Qt
import os
import sys

class SettingsUI(QWidget):
    def __init__(self, config_manager, hotkey_service, overlay):
        super().__init__()
        self.config_manager = config_manager
        self.hotkey_service = hotkey_service
        self.overlay = overlay
        self.setWindowTitle("Examly Settings")
        self.resize(400, 450)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.provider = QComboBox()
        self.provider.addItems(["openai", "gemini", "mistral", "inceptionlabs", "ollama"])
        self.provider.setCurrentText(self.config_manager.config.ai.provider)
        form.addRow("AI Provider:", self.provider)
        
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setText(self.config_manager.get_api_key())
        form.addRow("API Key:", self.api_key)
        
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(10, 100)
        self.opacity.setValue(int(self.config_manager.config.overlay_opacity * 100))
        self.opacity.valueChanged.connect(self.update_opacity_live)
        form.addRow("Overlay Opacity:", self.opacity)
        
        self.region_key = QLineEdit(self.config_manager.config.hotkey.region_capture)
        form.addRow("Region Snip Hotkey:", self.region_key)
        
        self.full_key = QLineEdit(self.config_manager.config.hotkey.full_capture)
        form.addRow("Full Screen Hotkey:", self.full_key)
        
        self.show_key = QLineEdit(self.config_manager.config.hotkey.show_last)
        form.addRow("Show Last Hotkey:", self.show_key)
        
        layout.addLayout(form)
        
        apply_btn = QPushButton("Apply Hotkeys & Settings")
        apply_btn.setStyleSheet("background-color: #a6e3a1; color: black; font-weight: bold; padding: 10px;")
        apply_btn.clicked.connect(self.apply_settings)
        layout.addWidget(apply_btn)

        save_btn = QPushButton("Hard Relaunch App")
        save_btn.setStyleSheet("background-color: #313244; color: white; padding: 10px; margin-top: 10px;")
        save_btn.clicked.connect(self.save_relaunch)
        layout.addWidget(save_btn)
        
    def update_opacity_live(self, value):
        opacity = value / 100.0
        self.overlay.setWindowOpacity(opacity)
        # Ensure it's visible so the user can see the change
        if not self.overlay.isVisible():
            self.overlay.show()
            # Hide it after 1 second if it wasn't already active
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, self.overlay.hide)

    def apply_settings(self):
        # Update config object
        self.config_manager.config.ai.provider = self.provider.currentText()
        self.config_manager.set_api_key(self.api_key.text())
        self.config_manager.config.overlay_opacity = self.opacity.value() / 100.0
        self.config_manager.config.hotkey.region_capture = self.region_key.text()
        self.config_manager.config.hotkey.full_capture = self.full_key.text()
        self.config_manager.config.hotkey.show_last = self.show_key.text()
        
        # Save to disk
        self.config_manager.save()
        
        # Live Remap Hotkeys
        self.hotkey_service.start()
        
        # Update Overlay
        self.overlay.setWindowOpacity(self.config_manager.config.overlay_opacity)
        
    def save_relaunch(self):
        self.apply_settings()
        os.execl(sys.executable, sys.executable, *sys.argv)
