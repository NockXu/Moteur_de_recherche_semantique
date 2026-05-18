from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QSizePolicy

class ResponsiveImageLabel(QLabel):
    def __init__(self):
        super().__init__()
        self._pixmap = None

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update()

    def _update(self):
        if not self._pixmap:
            return

        w = self.width()
        h = self.height()

        # protection scroll/layout instable
        if w < 2 or h < 2:
            return

        scaled = self._pixmap.scaled(
            w,
            h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        super().setPixmap(scaled)