from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QComboBox, QSlider, QFormLayout, QLabel, QCheckBox,
    QScrollArea, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QCursor
import os
import sys

STYLESHEET = """
    QWidget#SettingsCard {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #1e1e2e, stop:1 #181825);
        border-radius: 16px;
        border: 1px solid #313244;
    }
    QLabel {
        color: #cdd6f4;
        font-size: 12px;
        background: transparent;
        border: none;
    }
    QLineEdit {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
    }
    QLineEdit:focus {
        border: 1px solid #cba6f7;
    }
    QComboBox {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
    }
    QComboBox::drop-down {
        border: none;
    }
    QSlider::groove:horizontal {
        background: #313244;
        height: 6px;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #cba6f7;
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }
    QSlider::sub-page:horizontal {
        background: #cba6f7;
        border-radius: 3px;
    }
    QCheckBox {
        color: #cdd6f4;
        font-size: 12px;
        spacing: 8px;
        background: transparent;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid #45475a;
        background: #313244;
    }
    QCheckBox::indicator:checked {
        background: #cba6f7;
        border: 2px solid #cba6f7;
    }
"""

class SettingsUI(QWidget):
    def __init__(self, config_manager, hotkey_service, overlay):
        super().__init__()
        self.config_manager = config_manager
        self.hotkey_service = hotkey_service
        self.overlay = overlay
        self.answer_history = []
        
        self.setWindowTitle("Examly Settings")
        self.setFixedSize(440, 620)
        self.setStyleSheet("background-color: #11111b;")
        
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        
        # ── Title ──
        title = QLabel("⚡ Examly")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #cba6f7; background: transparent; border: none;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(title)
        
        subtitle = QLabel("Stealth Exam Assistant")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #6c7086; background: transparent; border: none;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(subtitle)
        root_layout.addSpacing(8)
        
        # ── Main Card ──
        card = QWidget()
        card.setObjectName("SettingsCard")
        card.setStyleSheet(STYLESHEET)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(10)
        
        form = QFormLayout()
        form.setSpacing(8)
        
        # ── AI Provider ──
        self.provider = QComboBox()
        self.provider.addItems(["inceptionlabs", "openai", "gemini", "mistral", "ollama"])
        self.provider.setCurrentText(self.config_manager.config.ai.provider)
        form.addRow("AI Provider", self.provider)
        
        # ── API Key ──
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setText(self.config_manager.get_api_key())
        self.api_key.setPlaceholderText("sk_xxxxx or leave blank for Ollama")
        form.addRow("API Key", self.api_key)
        
        # ── Opacity ──
        opacity_row = QHBoxLayout()
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(10, 100)
        self.opacity.setValue(int(self.config_manager.config.overlay_opacity * 100))
        self.opacity.valueChanged.connect(self.update_opacity_live)
        self.opacity_label = QLabel(f"{int(self.config_manager.config.overlay_opacity * 100)}%")
        self.opacity_label.setFixedWidth(35)
        opacity_row.addWidget(self.opacity)
        opacity_row.addWidget(self.opacity_label)
        form.addRow("Opacity", opacity_row)
        
        # ── Auto-Hide ──
        auto_hide_row = QHBoxLayout()
        self.auto_hide = QSlider(Qt.Orientation.Horizontal)
        self.auto_hide.setRange(0, 30)
        self.auto_hide.setValue(self.config_manager.config.auto_hide_seconds)
        self.auto_hide.valueChanged.connect(lambda v: self.auto_hide_label.setText(f"{v}s" if v > 0 else "Off"))
        self.auto_hide_label = QLabel(f"{self.config_manager.config.auto_hide_seconds}s")
        self.auto_hide_label.setFixedWidth(35)
        auto_hide_row.addWidget(self.auto_hide)
        auto_hide_row.addWidget(self.auto_hide_label)
        form.addRow("Auto-Hide", auto_hide_row)
        
        # ── Toggles ──
        self.tooltip_mode = QCheckBox("Tooltip Mode (tiny answer near cursor)")
        self.tooltip_mode.setChecked(self.config_manager.config.tooltip_mode)
        form.addRow("", self.tooltip_mode)
        
        self.auto_copy = QCheckBox("Auto-copy answer to clipboard")
        self.auto_copy.setChecked(self.config_manager.config.auto_copy)
        form.addRow("", self.auto_copy)
        
        card_layout.addLayout(form)
        
        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #313244; border: none; max-height: 1px;")
        card_layout.addWidget(sep)
        
        # ── Hotkeys ──
        hotkey_title = QLabel("⌨️ Hotkeys")
        hotkey_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        hotkey_title.setStyleSheet("color: #89b4fa; background: transparent; border: none;")
        card_layout.addWidget(hotkey_title)
        
        hk_form = QFormLayout()
        hk_form.setSpacing(6)
        
        self.region_key = QLineEdit(self.config_manager.config.hotkey.region_capture)
        hk_form.addRow("Region Snip", self.region_key)
        
        self.full_key = QLineEdit(self.config_manager.config.hotkey.full_capture)
        hk_form.addRow("Full Screen", self.full_key)
        
        self.show_key = QLineEdit(self.config_manager.config.hotkey.show_last)
        hk_form.addRow("Show Last", self.show_key)
        
        card_layout.addLayout(hk_form)
        
        root_layout.addWidget(card)
        
        # ── Buttons ──
        btn_row = QHBoxLayout()
        
        apply_btn = QPushButton("✅ Apply")
        apply_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #a6e3a1, stop:1 #94e2d5);
                color: #1e1e2e;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 10px;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background: #94e2d5; }
        """)
        apply_btn.clicked.connect(self.apply_settings)
        apply_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        history_btn = QPushButton("📜 History")
        history_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 10px;
                font-size: 13px;
                border: 1px solid #45475a;
            }
            QPushButton:hover { background-color: #45475a; }
        """)
        history_btn.clicked.connect(self.show_history)
        history_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        btn_row.addWidget(apply_btn)
        btn_row.addWidget(history_btn)
        root_layout.addLayout(btn_row)
        
        # ── History Panel (hidden by default) ──
        self.history_panel = None
        
    def update_opacity_live(self, value):
        opacity = value / 100.0
        self.opacity_label.setText(f"{value}%")
        self.overlay.setWindowOpacity(opacity)
        if not self.overlay.isVisible():
            self.overlay.show()
            QTimer.singleShot(1500, self.overlay.hide)

    def apply_settings(self):
        self.config_manager.config.ai.provider = self.provider.currentText()
        self.config_manager.set_api_key(self.api_key.text())
        self.config_manager.config.overlay_opacity = self.opacity.value() / 100.0
        self.config_manager.config.auto_hide_seconds = self.auto_hide.value()
        self.config_manager.config.tooltip_mode = self.tooltip_mode.isChecked()
        self.config_manager.config.auto_copy = self.auto_copy.isChecked()
        self.config_manager.config.hotkey.region_capture = self.region_key.text()
        self.config_manager.config.hotkey.full_capture = self.full_key.text()
        self.config_manager.config.hotkey.show_last = self.show_key.text()
        
        self.config_manager.save()
        self.hotkey_service.start()
        self.overlay.setWindowOpacity(self.config_manager.config.overlay_opacity)

    def add_to_history(self, data: dict):
        self.answer_history.insert(0, data)
        if len(self.answer_history) > 50:
            self.answer_history = self.answer_history[:50]

    def show_history(self):
        if self.history_panel and self.history_panel.isVisible():
            self.history_panel.hide()
            return
            
        self.history_panel = QWidget()
        self.history_panel.setWindowTitle("📜 Answer History")
        self.history_panel.setFixedSize(400, 500)
        self.history_panel.setStyleSheet("background-color: #11111b;")
        
        layout = QVBoxLayout(self.history_panel)
        layout.setContentsMargins(12, 12, 12, 12)
        
        title = QLabel("📜 Answer History")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #cba6f7; background: transparent; border: none;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(8)
        
        if not self.answer_history:
            empty = QLabel("No answers yet. Take a screenshot!")
            empty.setStyleSheet("color: #6c7086; background: transparent; border: none;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scroll_layout.addWidget(empty)
        else:
            for i, entry in enumerate(self.answer_history):
                item = QWidget()
                item.setStyleSheet("""
                    background-color: #1e1e2e;
                    border-radius: 10px;
                    border: 1px solid #313244;
                    padding: 8px;
                """)
                item_layout = QVBoxLayout(item)
                item_layout.setContentsMargins(12, 8, 12, 8)
                
                ans = QLabel(str(entry.get("answer", "N/A")))
                ans.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                ans.setStyleSheet("color: #cdd6f4; background: transparent; border: none;")
                ans.setWordWrap(True)
                
                meta = QLabel(f"{entry.get('type', '').upper()}  •  {int(entry.get('confidence', 0) * 100)}%")
                meta.setStyleSheet("color: #6c7086; font-size: 10px; background: transparent; border: none;")
                
                item_layout.addWidget(ans)
                item_layout.addWidget(meta)
                scroll_layout.addWidget(item)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        self.history_panel.show()
