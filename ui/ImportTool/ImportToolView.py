import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QFileDialog, QLabel, QFrame,
    QGridLayout, QProgressBar, QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QResizeEvent

from pathlib import Path

from common.Image_Classes.Image import Image, ProcessingStatus
from ui.ImportTool.ImageWidget import ImageWidget
from ui.ImportTool.widget.ConnectionVerificator import ConnectionVerificatorController
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
    load_more_requested = pyqtSignal()

    _CARD_W = ImageWidget.CARD_WIDTH
    _GRID_GAP = 12
    _SCROLL_THRESHOLD = 0.80

    def __init__(self, parent=None, ollama_base_url: str = None):
        super().__init__(parent)

        self.model = None
        self.image_widgets: Dict[str, ImageWidget] = {}
        self._current_cols = 1

        self.connection_verificator = ConnectionVerificatorController(
            base_url=ollama_base_url
        )

        self._setup_ui()

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
        # FIX: distinguer Start et Stop selon le texte du bouton
        self.btn_start.clicked.connect(self._on_start_stop_clicked)
        lay.addWidget(self.btn_start)

        parent.addWidget(card)

    def _build_body(self, parent):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(self._GRID_GAP)

        self.scroll.setWidget(self.container)
        parent.addWidget(self.scroll, 1)

    def _build_footer(self, parent):
        footer_widget = QFrame()
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        footer_layout.setSpacing(8)

        # ── Barre de progression ───────────────────────────────
        progress_container = QWidget()
        progress_container.setStyleSheet("background: transparent;")
        progress_vlay = QVBoxLayout(progress_container)
        progress_vlay.setContentsMargins(0, 0, 0, 0)
        progress_vlay.setSpacing(4)

        self._progress_label = QLabel("En attente…")
        self._progress_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 11px;
                font-weight: 500;
                background: transparent;
            }
        """)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(5)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background-color: #e9ecef;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4361ee,
                    stop:1 #7209b7
                );
            }
        """)

        progress_vlay.addWidget(self._progress_label)
        progress_vlay.addWidget(self.progress)
        footer_layout.addWidget(progress_container)

        # ── Widget de connexion en bas à droite ─────────────────────
        connection_container = QWidget()
        connection_layout = QHBoxLayout(connection_container)
        connection_layout.setContentsMargins(0, 0, 0, 0)
        connection_layout.setSpacing(0)
        
        # Espace extensible pour pousser à droite
        connection_layout.addStretch()
        
        # Ajouter le widget de connexion
        connection_layout.addWidget(self.connection_verificator.view)

        footer_layout.addWidget(connection_container)

        parent.addWidget(footer_widget)

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
    # Start / Stop
    # ─────────────────────────────────────────────

    def _on_start_stop_clicked(self):
        # FIX: un seul bouton connecté, délégation selon l'état
        if self.btn_start.text().startswith("▶"):
            self.start_processing_requested.emit()
        else:
            self.stop_processing_requested.emit()

    # ─────────────────────────────────────────────
    # Image loading (piloté par le Controller)
    # ─────────────────────────────────────────────

    def load_images(self, images: List[Image]):
        """Remplace toute la grille par une première page d'images."""
        self._clear()
        self._current_cols = self._compute_cols()
        self._add_images_to_grid(images)

    def append_images(self, images: List[Image]):
        """Ajoute une page supplémentaire d'images à la grille existante."""
        # FIX: méthode manquante appelée par le Controller
        self._add_images_to_grid(images)

    def _add_images_to_grid(self, images: List[Image]):
        base = len(self.image_widgets)
        for i, img in enumerate(images):
            w = self._make_widget(img)
            key = str(img.path.resolve())
            self.image_widgets[key] = w
            pos = base + i
            self.grid.addWidget(w, pos // self._current_cols, pos % self._current_cols)

    def _make_widget(self, img: Image) -> ImageWidget:
        w = ImageWidget(str(img.path), img.status)
        w.clicked.connect(lambda _: self.image_clicked.emit(img))
        w.setFixedSize(w.CARD_WIDTH, w.CARD_HEIGHT)
        return w

    def _compute_cols(self) -> int:
        """Calcule le nombre de colonnes selon la largeur disponible."""
        available = self.scroll.viewport().width()
        cols = max(1, available // (self._CARD_W + self._GRID_GAP))
        return cols

    # ─────────────────────────────────────────────
    # Scroll → pagination
    # ─────────────────────────────────────────────

    def _on_scroll(self, v: int):
        bar = self.scroll.verticalScrollBar()
        if bar.maximum() == 0:
            return
        if v / bar.maximum() >= self._SCROLL_THRESHOLD:
            self.load_more_requested.emit()

    # ─────────────────────────────────────────────
    # Clear
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

    # ─────────────────────────────────────────────
    # Update status
    # ─────────────────────────────────────────────

    def update_image_status(self, path: str, status: ProcessingStatus):
        key = str(Path(path).resolve())
        if key in self.image_widgets:
            self.image_widgets[key].set_status(status)

    def _refresh_image_display(self):
        """FIX: méthode manquante — rafraîchit les badges de statut après chargement BDD."""
        if not self.model:
            return
        for img in self.model.get_loaded_images():
            self.update_image_status(str(img.path), img.status)

    def _update_progress_display(self):
        """Met à jour la barre de progression et le label associé."""
        if not self.model:
            return
        progress = self.model.get_processing_progress()
        pct = int(progress * 100)
        self.progress.setValue(pct)

        counts = self.model.get_images_by_status()
        done = counts.get(ProcessingStatus.COMPLETED, 0)
        error = counts.get(ProcessingStatus.ERROR, 0)
        total = self.model.get_images_count()

        if total == 0:
            self._progress_label.setText("En attente…")
        elif pct == 100:
            self._progress_label.setText(f"✅ Terminé — {done} traité(s), {error} erreur(s)")
        else:
            self._progress_label.setText(f"{pct}% — {done + error} / {total} images")

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
    # Cleanup
    # ─────────────────────────────────────────────

    def cleanup(self):
        self._clear()