import sys
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea,
    QPushButton, QHBoxLayout, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from numpy import imag

from common.Image_Classes.Image import Image
from ui.ImageSearchedContainer.widget.ImageThumbnailWidget import ImageThumbnailWidget
from ui.ImageSearchedContainer.widget.SearchBar.SearchBarController import SearchBarController
from ui.utils.colored_icon import colored_icon
from ui.utils.JustifiedGalleryLayout import JustifiedGalleryLayout


# ─────────────────────────────────────────────
# Lazy wrapper
# ─────────────────────────────────────────────

class LazyImageCard:
    def __init__(self, image: Image):
        self.image = image
        self.widget: ImageThumbnailWidget | None = None
        self.is_visible = False
        self._loaded = False

    @property
    def is_loaded(self):
        return self._loaded


# ─────────────────────────────────────────────
# VIEW
# ─────────────────────────────────────────────

class ImageSearchedContainerView(QWidget):

    image_clicked = pyqtSignal(Image)
    load_more_requested = pyqtSignal()
    reload_requested = pyqtSignal()
    search_requested = pyqtSignal(str, list)
    threshold_changed = pyqtSignal(float)

    def __init__(self, parent=None, enable_lazy_loading: bool = True):
        super().__init__(parent)

        self._cards: list[LazyImageCard] = []
        self._loading = False

        # lazy config
        self._lazy_enabled = enable_lazy_loading
        self._render_queue: list[LazyImageCard] = []

        self._lazy_timer = QTimer(self)
        self._lazy_timer.timeout.connect(self._lazy_render_batch)
        self._lazy_timer.setInterval(50)

        self._max_renders_per_batch = 10
        self._total_loaded = 0

        self.search_controller = SearchBarController()

        self._setup_ui()
        self._apply_styles()

    # ─────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # HEADER
        header = QHBoxLayout()

        self.reload_button = QPushButton()
        self.reload_button.clicked.connect(self.reload_requested.emit)

        header.addWidget(self.reload_button)
        header.addStretch()

        self.search_controller.view.setMinimumWidth(300)
        header.addWidget(self.search_controller.view)

        layout.addLayout(header)

        # SCROLL
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.masonry = QWidget()
        self.gallery_layout = JustifiedGalleryLayout()
        self.masonry.setLayout(self.gallery_layout)

        self.scroll_area.setWidget(self.masonry)
        layout.addWidget(self.scroll_area)

        # FOOTER
        footer = QHBoxLayout()

        self.number_img_label = QLabel("0 image")
        self.number_img_label.setFont(QFont("Segoe UI", 10))

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(50)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)

        self.threshold_value_label = QLabel("50%")

        footer.addWidget(self.threshold_slider)
        footer.addWidget(self.threshold_value_label)
        footer.addStretch()
        footer.addWidget(self.number_img_label)

        layout.addLayout(footer)

    # ─────────────────────────────────────────────
    # SCROLL / LOAD MORE
    # ─────────────────────────────────────────────

    def _on_scroll(self, value: int):
        if self._lazy_enabled:
            self._check_visible_cards()

        if self._loading:
            return

        bar = self.scroll_area.verticalScrollBar()
        if bar.maximum() - value < 300:
            self._loading = True
            QTimer.singleShot(100, self._emit_load_more)

    def _emit_load_more(self):
        self._loading = False
        self.load_more_requested.emit()

    # ─────────────────────────────────────────────
    # LAZY CORE
    # ─────────────────────────────────────────────

    def _check_visible_cards(self):
        if not self._lazy_enabled:
            return

        viewport = self.scroll_area.viewport()
        viewport_rect = viewport.rect()

        for card in self._cards:
            if card.is_loaded or not card.widget:
                continue

            try:
                pos = card.widget.mapTo(viewport, card.widget.rect().topLeft())
                rect = card.widget.rect()
                rect.moveTo(pos)

                extended = viewport_rect.adjusted(-200, -200, 200, 200)
                visible = extended.intersects(rect)

                if visible and not card.is_visible:
                    card.is_visible = True
                    if card not in self._render_queue:
                        self._render_queue.append(card)
                elif not visible:
                    card.is_visible = False

            except RuntimeError:
                continue

        if self._render_queue and not self._lazy_timer.isActive():
            self._lazy_timer.start()

    def _lazy_render_batch(self):
        if not self._render_queue:
            self._lazy_timer.stop()
            return

        batch = self._render_queue[:self._max_renders_per_batch]
        self._render_queue = self._render_queue[self._max_renders_per_batch:]

        for card in batch:
            if not card.is_loaded:
                self._load_thumbnail(card)

        if not self._render_queue:
            self._lazy_timer.stop()

    def _load_thumbnail(self, card: LazyImageCard):
        """
        Déclenche le chargement async du widget.
        card._loaded sera mis à True via le signal image_loaded,
        PAS ici — le chargement est asynchrone.
        """
        if not card.widget:
            return

        try:
            card.widget.load_image()
            # Ne pas setter card._loaded ici : c'est le signal image_loaded qui le fait
        except Exception as e:
            print(f"[LAZY] error: {e}")

    # ─────────────────────────────────────────────
    # API
    # ─────────────────────────────────────────────

    def display_images(self, image_data: list[Image], total_count: int):
        self.number_img_label.setText(f"{total_count} image(s)")

        for image in image_data:
            lazy_card = LazyImageCard(image)

            widget = ImageThumbnailWidget(
                image=image,
                lazy=self._lazy_enabled,
            )

            widget.clicked.connect(
                lambda _, img=image: self.image_clicked.emit(img)
            )

            # image_loaded marque la card comme chargée ET met à jour le layout
            widget.image_loaded.connect(
                lambda card=lazy_card: self._on_image_loaded(card)
            )

            lazy_card.widget = widget
            self._cards.append(lazy_card)
            self.gallery_layout.addWidget(widget)

        if self._lazy_enabled:
            QTimer.singleShot(100, self._check_visible_cards)

    def _on_image_loaded(self, card: LazyImageCard):
        """
        Appelé quand le widget a vraiment fini de charger sa pixmap.
        C'est ici qu'on marque la card comme loaded.
        """
        card._loaded = True
        self._total_loaded += 1
        self.gallery_layout.update()
        self.masonry.update()

    def update_images(self, images_results: dict[str, list[dict]]):
        widgets = {
            str(c.image.path): c.widget
            for c in self._cards
            if c.widget
        }

        for path, results in images_results.items():
            w = widgets.get(str(path))
            if w:
                w.set_result(results)

    def clear_results(self, images_paths: list[str]):
        widgets = {
            str(c.image.path): c.widget
            for c in self._cards
            if c.widget
        }

        for path in images_paths:
            w = widgets.get(str(path))
            if w:
                w.clear_results()

    # ─────────────────────────────────────────────
    # CLEAR
    # ─────────────────────────────────────────────

    def clear(self):
        self._cards.clear()
        self._render_queue.clear()
        self._lazy_timer.stop()

        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

        self.number_img_label.setText("0 image")
        self._total_loaded = 0
        self._loading = False

    # ─────────────────────────────────────────────
    # CONFIG
    # ─────────────────────────────────────────────

    def set_lazy_batch_size(self, size: int):
        self._max_renders_per_batch = size

    def enable_lazy_loading(self, enabled: bool):
        self._lazy_enabled = enabled

    def _on_threshold_changed(self, value: int):
        self.threshold_value_label.setText(f"{value}%")
        self.threshold_changed.emit(value / 100.0)

    def _apply_styles(self):
        self.reload_button.setIcon(
            colored_icon("./ui/Icon/refresh.svg",
                         os.environ["QTMATERIAL_PRIMARYCOLOR"],
                         64)
        )

    def _on_theme_changed(self):
        self._apply_styles()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from database.DbService import DbService
    from common.Image_Classes.ImageRepository import ImageRepository

    db = DbService()
    repo = ImageRepository(db.sqlite, db.faiss)

    app = QApplication(sys.argv)

    view = ImageSearchedContainerView(enable_lazy_loading=True)
    view.set_lazy_batch_size(15)
    view.show()

    images = repo.get_all()
    view.display_images(images, len(images))

    sys.exit(app.exec())