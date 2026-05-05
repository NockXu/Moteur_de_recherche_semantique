import sys
import os

# Ajouter la racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QFileDialog, QLabel, QFrame,
    QGridLayout, QProgressBar, QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QEvent
from PyQt6.QtGui import QFont, QColor, QResizeEvent

from pathlib import Path

from common.Image_Classes.Image import Image, ProcessingStatus
from ui.ImportTool.ImageWidget import ImageWidget
from ui.ImportTool.widget.ConnectionVerificator import create_connection_verificator
from typing import List, Dict


# ─────────────────────────────────────────────
# Style helpers
# ─────────────────────────────────────────────

def _shadow(widget: QWidget, radius: int = 12, alpha: int = 30):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(radius)
    eff.setOffset(0, 2)
    eff.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(eff)


_CARD_STYLE = "QFrame { border-radius: 8px; }"

_BTN_PRIMARY = """
QPushButton {
    background-color: {bg};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-weight: 600;
}
QPushButton:hover { background-color: {hover}; }
QPushButton:pressed { background-color: {pressed}; }
QPushButton:disabled { background-color: #adb5bd; color: #f8f9fa; }
"""


# ─────────────────────────────────────────────
# VIEW
# ─────────────────────────────────────────────

class ImportToolView(QWidget):

    folder_selected = pyqtSignal(str)
    start_processing_requested = pyqtSignal()
    stop_processing_requested = pyqtSignal()
    image_clicked = pyqtSignal(Image)

    _CARD_W = ImageWidget.CARD_WIDTH
    _GRID_GAP = 12
    _SCROLL_THRESHOLD = 0.80

    def __init__(self, parent=None, ollama_base_url: str = None):
        super().__init__(parent)

        self.model = None  # ❗ injecté par controller
        self.image_widgets: Dict[str, ImageWidget] = {}

        self._loaded_page = -1
        self._loading_page = False
        self._current_cols = 1

        self._setup_ui()

        self.connection_verificator = create_connection_verificator(
            base_url=ollama_base_url
        )

    # ─────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)

        self._build_header(root)
        self._build_body(root)
        self._build_footer(root)

    def _build_header(self, parent):
        card = QFrame()
        card.setStyleSheet(_CARD_STYLE)
        _shadow(card)

        lay = QVBoxLayout(card)

        self.folder_label = QLabel("Aucun dossier")
        lay.addWidget(self.folder_label)

        self.btn_select = QPushButton("📁 Dossier")
        self.btn_select.clicked.connect(self._on_select_folder)
        lay.addWidget(self.btn_select)

        self.btn_start = QPushButton("▶ Start")
        self.btn_start.clicked.connect(lambda: self.start_processing_requested.emit())
        lay.addWidget(self.btn_start)

        parent.addWidget(card)

    def _build_body(self, parent):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.scroll.viewport().installEventFilter(self)

        self.container = QWidget()
        self.grid = QGridLayout(self.container)

        self.scroll.setWidget(self.container)
        parent.addWidget(self.scroll, 1)

    def _build_footer(self, parent):
        self.progress = QProgressBar()
        parent.addWidget(self.progress)

    # ─────────────────────────────────────────────
    # Folder
    # ─────────────────────────────────────────────

    def _on_select_folder(self):
        path = QFileDialog.getExistingDirectory(self)
        if path:
            self.folder_selected.emit(path)

    def set_folder(self, path: str, ok: bool):
        self.folder_label.setText(Path(path).name if ok else "Erreur")

    # ─────────────────────────────────────────────
    # Lazy loading
    # ─────────────────────────────────────────────

    def load_images(self, images: List[Image]):
        self._clear()

        self._all_images = images
        self._loaded_page = -1
        self._loading_page = False
        self._current_cols = self._compute_cols()

        self._load_next_page()

    def _load_next_page(self):
        if self._loading_page or not self.model:
            return

        page = self._loaded_page + 1
        if page >= self.model.get_page_count():
            return

        self._loading_page = True

        def run():
            images = self.model.get_page(page)

            base = len(self.image_widgets)

            for i, img in enumerate(images):
                w = self._make_widget(img)

                key = str(img.path.resolve())
                self.image_widgets[key] = w

                self.grid.addWidget(w, (base + i) // self._current_cols, (base + i) % self._current_cols)

            self._loaded_page = page
            self._loading_page = False

        QTimer.singleShot(0, run)

    def _make_widget(self, img: Image) -> ImageWidget:
        w = ImageWidget(str(img.path), img.status)

        w.clicked.connect(lambda _: self.image_clicked.emit(img))

        w.setFixedSize(w.CARD_WIDTH, w.CARD_HEIGHT)
        return w

    # ─────────────────────────────────────────────
    # Scroll
    # ─────────────────────────────────────────────

    def _on_scroll(self, v: int):
        bar = self.scroll.verticalScrollBar()
        if bar.maximum() == 0:
            return

        if v / bar.maximum() >= self._SCROLL_THRESHOLD:
            self._load_next_page()

    # ─────────────────────────────────────────────
    # Clear + FIX THREAD SAFE
    # ─────────────────────────────────────────────

    def _clear(self):
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            if not item:
                continue

            w = item.widget()
            if w:
                if hasattr(w, "cancel_load"):
                    w.cancel_load()

                w.setParent(None)
                w.deleteLater()

        self.image_widgets.clear()
        self._loaded_page = -1
        self._loading_page = False

    # ─────────────────────────────────────────────
    # Update status
    # ─────────────────────────────────────────────

    def update_image_status(self, path: str, status: ProcessingStatus):
        key = str(Path(path).resolve())

        if key in self.image_widgets:
            self.image_widgets[key].set_status(status)

    # ─────────────────────────────────────────────
    # Process mode
    # ─────────────────────────────────────────────

    def set_processing_mode(self, running: bool):
        self.btn_start.setText("⏹ Stop" if running else "▶ Start")

    # ─────────────────────────────────────────────
    # Model injection
    # ─────────────────────────────────────────────

    def set_model(self, model):
        self.model = model

    def get_model(self):
        return self.model

    # ─────────────────────────────────────────────
    # Resize
    # ─────────────────────────────────────────────

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)

    def eventFilter(self, obj, event):
        return super().eventFilter(obj, event)

    # ─────────────────────────────────────────────
    # Cleanup
    # ─────────────────────────────────────────────

    def cleanup(self):
        self._clear()