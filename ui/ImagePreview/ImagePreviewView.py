import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea,
    QFrame, QHBoxLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from common.Image_Classes.Image import Image


class ImagePreviewView(QWidget):
    """
    Vue preview stable (type inspector panel)
    """

    image_clicked = pyqtSignal()
    reload_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    # ─────────────────────────────
    # UI
    # ─────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # HEADER
        self.title = QLabel("Aucune image sélectionnée")
        self.title.setFont(QFont("Segoe UI", 11))
        root.addWidget(self.title)

        # IMAGE INFO PANEL (scroll safe)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none;")

        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)

        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)

        # FIELDS
        self.path_label = QLabel()
        self.name_label = QLabel()
        self.status_label = QLabel()
        self.desc_label = QLabel()
        self.tags_label = QLabel()

        for w in [
            self.path_label,
            self.name_label,
            self.status_label,
            self.desc_label,
            self.tags_label,
        ]:
            w.setWordWrap(True)
            w.setStyleSheet("color: #333;")
            self.layout.addWidget(w)

        # EMPTY STATE
        self.empty = QLabel("Sélectionne une image pour afficher les détails")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.empty)

    # ─────────────────────────────
    # API
    # ─────────────────────────────

    def display_image(self, image: Image | None):
        if not image:
            self._clear()
            return

        self.empty.hide()

        self.title.setText(image.name)

        self.path_label.setText(f"📁 {image.path}")
        self.name_label.setText(f"🖼 Nom: {image.name}")

        status = getattr(image, "status", None)
        self.status_label.setText(f"📊 Status: {status.value if status else 'N/A'}")

        self.desc_label.setText(f"📝 Description:\n{image.description or 'Aucune'}")

        tags = ", ".join(image.keywords or [])
        self.tags_label.setText(f"🏷 Tags: {tags if tags else 'Aucun'}")

    def _clear(self):
        self.title.setText("Aucune image sélectionnée")

        self.path_label.clear()
        self.name_label.clear()
        self.status_label.clear()
        self.desc_label.clear()
        self.tags_label.clear()

        self.empty.show()