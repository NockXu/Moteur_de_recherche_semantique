import os
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QLabel, QHBoxLayout, QSizePolicy

from ui.widgets.ImageThumbnailWidget import ImageThumbnailWidget as BaseImageThumbnailWidget
from common.Image_Classes.Image import Image


class ImageThumbnailWidget(BaseImageThumbnailWidget):
    """Custom gallery thumbnail that adds asynchronous lazy loading and score overlays.

    Signals:
        image_loaded (pyqtSignal): Emitted when the thumbnail image asset finishes loading.

    Args:
        image (Image | None): Data entity carrying metadata, scores, and media filepaths.
        col_width (int): Target pixel column constraint for rendering. Defaults to 200.
        lazy (bool): Toggles lazy background evaluation behaviors. Defaults to False.
    """

    image_loaded = pyqtSignal()

    def __init__(
        self,
        image: Image | None,
        col_width: int = 200,
        lazy: bool = False,
    ):
        self._lazy_mode = lazy
        self._is_loaded = not lazy
        self._pixmap_ready = False
        self._image: Image = image
        self._pending_results = None

        super().__init__(
            image_path=str(self._image.path),
            title=self._image.name,
            status=None,
            col_width=col_width,
            show_status_badge=False,
            show_title=False,
        )

        if lazy:
            self.cancel_load()

        self.image_label.set_image(image)
        self._customize_title_layout()

    @property
    def aspect_ratio(self) -> float:
        """Retrieves the geometric proportions of the wrapped image object.

        Returns:
            The raw float aspect ratio calculation value.
        """
        return self._image.aspect_ratio

    @property
    def is_loaded(self) -> bool:
        """Checks if the internal graphic resource has finished processing.

        Returns:
            True if the visual representation is ready, otherwise False.
        """
        return self._is_loaded

    def load_image(self) -> None:
        """Triggers the asynchronous load routine if the asset remains uninitialized."""
        if self._is_loaded or not self._lazy_mode:
            return
        self._start_async_load()

    @pyqtSlot(QPixmap)
    def _on_pixmap_loaded(self, thumb: QPixmap) -> None:
        """Handles background worker completion results and schedules mask drawings.

        Args:
            thumb (QPixmap): Finished structural scale pixel map asset.
        """
        super()._on_pixmap_loaded(thumb)
        self._pixmap_ready = True
        self._is_loaded = True

        if self._pending_results is not None:
            # Attendre que le layout soit stabilisé avant de dessiner
            QTimer.singleShot(0, self._apply_pending_results)

        self.image_loaded.emit()

    def _apply_pending_results(self) -> None:
        """Applies stored prediction bounding boxes onto the rendered target layout."""
        if self._pending_results is not None:
            self.image_label.set_results(self._pending_results)
            self.image_label.repaint()

    def set_result(self, result: list[dict] | None) -> None:
        """Saves segmentation outputs locally and queues updates for upcoming frames.

        Args:
            result (list[dict] | None): Extracted collection layers targeting standard overlays.
        """
        if not result:
            return
        
        self._pending_results = result

        if self._pixmap_ready:
            # Même chose ici : laisser le layout se stabiliser
            QTimer.singleShot(0, self._apply_pending_results)

    def unload_image(self) -> None:
        """Purges stored pixels memory when items clear active view frames."""
        if self._is_loaded and self._lazy_mode:
            self.image_label.set_source_pixmap(QPixmap())
            self._is_loaded = False
            self._pixmap_ready = False

    @pyqtSlot()
    def _show_error(self) -> None:
        """Generates a fallback indicator icon if loading fails."""
        error_pixmap = QPixmap(200, 200)
        error_pixmap.fill(QColor(255, 200, 200))
        painter = QPainter(error_pixmap)
        painter.setPen(QColor(200, 0, 0))
        painter.drawText(error_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "❌")
        painter.end()
        self.image_label.set_source_pixmap(error_pixmap)
        self._pixmap_ready = True
        self._is_loaded = True
        self.image_loaded.emit()

    def _customize_title_layout(self) -> None:
        """Reconstructs the layout footer to show title text alongside matching weights."""
        if not hasattr(self, 'title_label'):
            return

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(8, 4, 8, 8)
        title_layout.setSpacing(4)

        title_widget = QLabel(self._image.name)
        title_widget.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_widget.setWordWrap(True)
        title_widget.setFont(QFont("Segoe UI", 9))
        title_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        score_widget = QLabel("")
        score_widget.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        score_widget.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        score_widget.setStyleSheet(
            f"color: {os.environ['QTMATERIAL_PRIMARYTEXTCOLOR']}; margin-left: 8px;"
        )
        if self._image.score > 0:
            score_widget.setText(f"{self._image.score:.2f}")

        title_layout.addWidget(title_widget)
        title_layout.addWidget(score_widget)

        parent_layout = self.title_label.parent().layout() if self.title_label.parent() else None
        if parent_layout:
            parent_layout.removeWidget(self.title_label)
            self.title_label.deleteLater()
            parent_layout.addLayout(title_layout)

    def clear_results(self) -> None:
        """Erases internal segmentation tracking data and wipes existing overlays."""
        self.image_label.clear_results()
        self._pending_results = None