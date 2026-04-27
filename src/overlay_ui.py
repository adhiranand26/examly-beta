from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
import pyperclip

class OverlayUI(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        self.resize(340, 160)
        self.setWindowOpacity(self.config_manager.config.overlay_opacity)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        self.bg_widget = QWidget()
        self.bg_widget.setStyleSheet("background-color: #1e1e2e; border-radius: 12px; border: 1px solid #313244;")
        self.bg_layout = QVBoxLayout(self.bg_widget)
        
        header_layout = QHBoxLayout()
        self.title = QLabel("🤖 Examly Answer")
        self.title.setStyleSheet("color: #cba6f7; font-weight: bold; font-size: 14px;")
        
        self.conf_label = QLabel("Conf: --")
        self.conf_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        
        header_layout.addWidget(self.title)
        header_layout.addStretch()
        header_layout.addWidget(self.conf_label)
        self.bg_layout.addLayout(header_layout)
        
        self.answer_label = QLabel("Loading...")
        self.answer_label.setStyleSheet("color: #cdd6f4; font-size: 16px;")
        self.answer_label.setWordWrap(True)
        self.bg_layout.addWidget(self.answer_label)
        
        footer_layout = QHBoxLayout()
        copy_btn = QPushButton("Copy")
        copy_btn.setStyleSheet("background-color: #313244; color: white; border: none; padding: 6px; border-radius: 4px;")
        copy_btn.clicked.connect(self.copy_text)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background-color: #f38ba8; color: black; border: none; padding: 6px; border-radius: 4px;")
        close_btn.clicked.connect(self.hide)
        
        footer_layout.addStretch()
        footer_layout.addWidget(copy_btn)
        footer_layout.addWidget(close_btn)
        self.bg_layout.addLayout(footer_layout)
        
        self.layout.addWidget(self.bg_widget)
        
        self.old_pos = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.hide)

    def show_result(self, data: dict):
        self.answer_label.setText(str(data.get("answer", "No answer found.")))
        
        conf = data.get("confidence", 0)
        self.conf_label.setText(f"Conf: {int(conf * 100)}%")
        if conf > 0.8:
            self.conf_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        elif conf > 0.5:
            self.conf_label.setStyleSheet("color: #f9e2af; font-size: 11px;")
        else:
            self.conf_label.setStyleSheet("color: #f38ba8; font-size: 11px;")
            
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, 40)
        self.setWindowOpacity(self.config_manager.config.overlay_opacity)
        self.show()
        self.timer.start(20000)

    def copy_text(self):
        pyperclip.copy(self.answer_label.text())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None
