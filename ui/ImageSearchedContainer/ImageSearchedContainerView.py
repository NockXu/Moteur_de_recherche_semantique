import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from common.Image_Classes.Image import Image
from ui.ImageSearchedContainer.widget.ImageThumbnailWidget import ImageThumbnailWidget
from ui.ImageSearchedContainer.widget.MasonryWidget import MasonryLayout


class ImageSearchedContainerView(QWidget):
    """
    Vue en mode LOAD MORE :
    - pas de pagination UI obligatoire
    - scroll → demande au controller plus d'images
    - affichage incremental
    """

    image_clicked = pyqtSignal(Image)
    load_more_requested = pyqtSignal()
    reload_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._cards = []
        self._loading = False

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

        self.header_label = QLabel("0 image")
        self.header_label.setFont(QFont("Segoe UI", 10))

        self.reload_button = QPushButton("🔄 Recharger")
        self.reload_button.clicked.connect(self.reload_requested.emit)

        header.addWidget(self.header_label)
        header.addWidget(self.reload_button)
        header.addStretch()

        layout.addLayout(header)

        # SCROLL AREA
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.masonry = MasonryLayout()
        self.scroll_area.setWidget(self.masonry)

        layout.addWidget(self.scroll_area)

    def _apply_styles(self):
        self.setStyleSheet("""
            QPushButton {
                border: none;
                padding: 5px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)

    # ─────────────────────────────────────────────
    # SCROLL → LOAD MORE
    # ─────────────────────────────────────────────

    def _on_scroll(self, value: int):
        if self._loading:
            return

        bar = self.scroll_area.verticalScrollBar()
        if bar.maximum() <= 0:
            return

        ratio = value / bar.maximum()

        # seuil identique ImportTool
        if ratio > 0.85:
            self._trigger_load_more()

    def _trigger_load_more(self):
        self._loading = True

        # petit debounce anti spam scroll
        QTimer.singleShot(100, self._emit_load_more)

    def _emit_load_more(self):
        self._loading = False
        self.load_more_requested.emit()

    # ─────────────────────────────────────────────
    # API CONTROLLER
    # ─────────────────────────────────────────────

    def display_images(self, image_data: list[Image], total_count: int):
        """
        Ajoute des images (mode append, pas replace page)
        """

        self.header_label.setText(f"{total_count} image(s)")

        new_cards = []

        for image in image_data:
            card = ImageThumbnailWidget(
                image_path=str(image.path),
                title=image.name,
            )

            # click safe (pas de closure lourde)
            card.clicked.connect(
                lambda _, img=image: self.image_clicked.emit(img)
            )

            new_cards.append(card)

        self._cards.extend(new_cards)
        self.masonry.set_cards(self._cards)

    # ─────────────────────────────────────────────
    # CLEAR
    # ─────────────────────────────────────────────

    def clear(self):
        self._cards.clear()
        self.masonry.clear()
        self.header_label.setText("0 image")
        self._loading = False