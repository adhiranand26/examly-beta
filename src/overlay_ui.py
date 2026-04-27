from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QApplication, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor, QFont, QCursor
import pyperclip

class OverlayUI(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self._last_data = {}
        
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setMouseTracking(True)
        
        self.resize(380, 180)
        self.setWindowOpacity(self.config_manager.config.overlay_opacity)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        
        # ── Main Card ──
        self.bg_widget = QWidget()
        self.bg_widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #1e1e2e, stop:1 #181825);
            border-radius: 16px;
            border: 1px solid rgba(203, 166, 247, 0.3);
        """)
        
        # Drop shadow for premium feel
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 4)
        self.bg_widget.setGraphicsEffect(shadow)
        
        self.bg_layout = QVBoxLayout(self.bg_widget)
        self.bg_layout.setContentsMargins(16, 12, 16, 12)
        self.bg_layout.setSpacing(8)
        
        # ── Header ──
        header_layout = QHBoxLayout()
        self.title = QLabel("⚡ Answer")
        self.title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.title.setStyleSheet("color: #cba6f7; border: none; background: transparent;")
        
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Segoe UI", 8))
        self.status_label.setStyleSheet("color: #6c7086; border: none; background: transparent;")
        
        self.conf_label = QLabel("--")
        self.conf_label.setFont(QFont("Segoe UI", 10))
        self.conf_label.setStyleSheet("color: #a6e3a1; border: none; background: transparent;")
        
        self.type_label = QLabel("")
        self.type_label.setFont(QFont("Segoe UI", 9))
        self.type_label.setStyleSheet("color: #89b4fa; border: none; background: transparent;")
        
        header_layout.addWidget(self.title)
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()
        header_layout.addWidget(self.type_label)
        header_layout.addWidget(self.conf_label)
        self.bg_layout.addLayout(header_layout)
        
        # ── Answer ──
        self.answer_label = QLabel("Waiting for capture...")
        self.answer_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.answer_label.setStyleSheet("color: #cdd6f4; border: none; background: transparent;")
        self.answer_label.setWordWrap(True)
        self.answer_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.bg_layout.addWidget(self.answer_label)
        
        # ── Explanation ──
        self.explain_label = QLabel("")
        self.explain_label.setFont(QFont("Segoe UI", 9))
        self.explain_label.setStyleSheet("color: #9399b2; border: none; background: transparent;")
        self.explain_label.setWordWrap(True)
        self.bg_layout.addWidget(self.explain_label)
        
        # ── Footer ──
        footer_layout = QHBoxLayout()
        
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(49, 50, 68, 0.8);
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 6px 14px;
                border-radius: 8px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #45475a; }
        """)
        copy_btn.clicked.connect(self.copy_text)
        copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        close_btn = QPushButton("✕")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(243, 139, 168, 0.2);
                color: #f38ba8;
                border: 1px solid rgba(243, 139, 168, 0.3);
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(243, 139, 168, 0.4); }
        """)
        close_btn.clicked.connect(self.hide)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        footer_layout.addStretch()
        footer_layout.addWidget(copy_btn)
        footer_layout.addWidget(close_btn)
        self.bg_layout.addLayout(footer_layout)
        
        self.layout.addWidget(self.bg_widget)
        
        self.old_pos = None
        
        # Auto-hide timer
        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide)

    def show_result(self, data: dict):
        self._last_data = data
        answer = str(data.get("answer", "No answer found."))
        self.answer_label.setText(answer)
        
        explanation = data.get("explanation", "")
        is_error = data.get("type") == "error"
        self.explain_label.setText(explanation if explanation else "")
        self.explain_label.setVisible(bool(explanation) or is_error)
        
        if is_error:
            self.explain_label.setStyleSheet("color: #f38ba8; border: none; background: transparent;")
        else:
            self.explain_label.setStyleSheet("color: #9399b2; border: none; background: transparent;")
        
        q_type = data.get("type", "")
        if q_type:
            type_badges = {"mcq": "🔘 MCQ", "math": "🔢 Math", "code": "💻 Code", "descriptive": "📝 Desc"}
            self.type_label.setText(type_badges.get(q_type, q_type.upper()))
        else:
            self.type_label.setText("")
        
        conf = data.get("confidence", 0)
        self.conf_label.setText(f"{int(conf * 100)}%")
        if conf > 0.8:
            self.conf_label.setStyleSheet("color: #a6e3a1; border: none; background: transparent; font-size: 10px;")
        elif conf > 0.5:
            self.conf_label.setStyleSheet("color: #f9e2af; border: none; background: transparent; font-size: 10px;")
        else:
            self.conf_label.setStyleSheet("color: #f38ba8; border: none; background: transparent; font-size: 10px;")
        
        # Status line: provider + latency
        provider = data.get("provider", "")
        latency = data.get("pipeline_ms", 0)
        if provider and latency:
            mode = "🟢 " + provider if provider != "ollama" else "🔵 offline"
            self.status_label.setText(f"{mode} • {latency}ms")
        elif answer.startswith("⏳"):
            self.status_label.setText("⏳ working...")
        else:
            self.status_label.setText("")
        
        # Auto-copy to clipboard (skip loading/error states)
        is_loading = answer.startswith("⏳")
        is_error = data.get("type") == "error"
        if self.config_manager.config.auto_copy and answer and not is_loading and not is_error:
            try:
                pyperclip.copy(answer)
            except Exception:
                pass
        
        # Position: check tooltip mode
        if self.config_manager.config.tooltip_mode:
            # Tiny tooltip near cursor
            self.resize(260, 50)
            self.answer_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            self.explain_label.hide()
            self.title.hide()
            self.conf_label.hide()
            self.type_label.hide()
            cursor_pos = QCursor.pos()
            self.move(cursor_pos.x() + 20, cursor_pos.y() + 20)
        else:
            # Normal overlay positioned top-right
            self.resize(380, 180)
            self.answer_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
            self.explain_label.show()
            self.title.show()
            self.conf_label.show()
            self.type_label.show()
            screen = QApplication.primaryScreen().geometry()
            self.move(screen.width() - self.width() - 20, 40)
        
        self.setWindowOpacity(self.config_manager.config.overlay_opacity)
        self.show()
        
        # Auto-hide after configured seconds
        auto_hide = self.config_manager.config.auto_hide_seconds
        if auto_hide > 0:
            self.auto_hide_timer.start(auto_hide * 1000)

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

    def enterEvent(self, event):
        """Mouse enters overlay -> fade it out for stealth"""
        self.setWindowOpacity(0.15)

    def leaveEvent(self, event):
        """Mouse leaves overlay -> restore opacity"""
        self.setWindowOpacity(self.config_manager.config.overlay_opacity)
