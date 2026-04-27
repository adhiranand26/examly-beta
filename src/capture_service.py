import io
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QImage
from PySide6.QtCore import Qt, QRect, Signal
from PIL import Image, ImageGrab

class SnippingTool(QWidget):
    on_capture = Signal(object)  # Emits PIL Image
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # Prevent Memory Leaks
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Grab image using PIL (fixes mixed DPI multi-monitor bugs on Windows natively)
        # Convert to RGBA so tobytes() returns uniform 4-channel data for QImage
        pil_image = ImageGrab.grab(all_screens=True).convert("RGBA")
        self.pil_image = pil_image
        
        # Convert PIL Image to QPixmap
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
        self.original_pixmap = QPixmap.fromImage(qimage)
        
        # Geometry must align with virtual desktop coordinate space
        # Windows can have negative coordinates if Monitor 2 is to the left of Monitor 1
        # The top-left of the virtual_geometry precisely maps to the (0,0) of ImageGrab.grab(all_screens=True)
        virtual_geometry = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(virtual_geometry)
        
        # Calculate the actual scaling between PIL (device pixels) and Qt (logical pixels)
        # This handles Windows Display Scaling (125%, 150%, etc.)
        self.scale_x = self.pil_image.width / virtual_geometry.width()
        self.scale_y = self.pil_image.height / virtual_geometry.height()
        
        self.begin = None
        self.end = None

    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw the pixmap stretched to the logical size of the widget
        painter.drawPixmap(self.rect(), self.original_pixmap)
        
        # Draw translucent black overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        if self.begin and self.end:
            rect = QRect(self.begin, self.end).normalized()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, QColor(0, 0, 0, 0))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        self.begin = event.position().toPoint()
        self.end = self.begin
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, event):
        rect = QRect(self.begin, self.end).normalized()
        self.hide()
        
        if rect.width() > 10 and rect.height() > 10:
            # Map logical selection coordinates back to device pixels in the PIL image
            crop_x1 = int(rect.x() * self.scale_x)
            crop_y1 = int(rect.y() * self.scale_y)
            crop_x2 = int((rect.x() + rect.width()) * self.scale_x)
            crop_y2 = int((rect.y() + rect.height()) * self.scale_y)
            
            cropped = self.pil_image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            self.on_capture.emit(cropped)
        else:
            self.on_capture.emit(None)
            
        self.deleteLater()  # Critical to release RAM immediately


class CaptureService:
    @staticmethod
    def capture_full_screen() -> Image.Image:
        return ImageGrab.grab(all_screens=True)

    @staticmethod
    def capture_region(callback):
        snipper = SnippingTool()
        snipper.on_capture.connect(callback)
        snipper.show()
        return snipper
