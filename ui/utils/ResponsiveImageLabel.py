from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QSizePolicy

class ResponsiveImageLabel(QLabel):
    """Custom QLabel subclass tailored to scale images dynamically.

    Listens to active canvas scale mutation ticks to maintain fixed component
    aspect profiles over highly unstable viewport resizes.
    """
    def __init__(self):
        super().__init__()
        self._pixmap = None

    def setPixmap(self, pixmap: QPixmap):
        """Override basic asset assignments to update local internal tracking models.

        Args:
            pixmap (QPixmap): Target image frame layout source to assign.

        """
        self._pixmap = pixmap
        self._update()

    def resizeEvent(self, event):
        """Intercept container resize mutation events to recalculate scale metrics."""
        super().resizeEvent(event)
        self._update()

    def _update(self):
        """Compute pixel matrices shifts to fit the source asset smoothly on screen."""
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