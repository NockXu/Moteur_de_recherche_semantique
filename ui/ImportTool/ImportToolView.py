import os
from typing import List, Dict
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QFileDialog, QLabel, QFrame,
    QGridLayout, QProgressBar, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QColor, QResizeEvent

from common.Image_Classes.Image import Image, ProcessingStatus
from ui.ImportTool.ImageWidget import ImageWidget
from ui.ImportTool.widget.ConnectionVerificator import ConnectionVerificatorController

from ui.utils.colored_icon import colored_icon

from ui.utils.i18n import tr


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
    _GRID_GAP = 6
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

        self.folder_label = QLabel(tr("Aucun dossier"))
        lay.addWidget(self.folder_label)

        button_layout = QHBoxLayout()

        self.btn_select = QPushButton(tr("Dossier"))
        self.btn_select.clicked.connect(self._on_select_folder)
        button_layout.addWidget(self.btn_select)

        self.icon_start = colored_icon("./ui/Icon/play_arrow.svg", os.environ["QTMATERIAL_PRIMARYCOLOR"])
        self.icon_stop = colored_icon("./ui/Icon/stop.svg", os.environ["QTMATERIAL_PRIMARYCOLOR"])
        self.is_running = False

        self.btn_start = QPushButton()
        self.btn_start.setIcon(self.icon_start)
        self.btn_start.setIconSize(QSize(20, 20))
        self.btn_start.clicked.connect(self._on_start_stop_clicked)
        button_layout.addWidget(self.btn_start)

        button_layout.setStretch(0, 2)
        button_layout.setStretch(1, 1)

        lay.addLayout(button_layout)

        parent.addWidget(card)

    def _build_body(self, parent):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(self._GRID_GAP)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.scroll.setStyleSheet(f"background-color: {os.environ["QTMATERIAL_SECONDARYLIGHTCOLOR"]};")

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

        self._progress_label = QLabel(tr("En attente…"))
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
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 5px;
                background-color: #e9ecef;
            }}
            QProgressBar::chunk {{
                border-radius: 5px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {os.environ["QTMATERIAL_PRIMARYCOLOR"]},
                    stop:1 {os.environ["QTMATERIAL_PRIMARYLIGHTCOLOR"]}
                );
            }}
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
        self.folder_label.setText(Path(path).name if ok else tr("Erreur"))

    # ─────────────────────────────────────────────
    # Start / Stop
    # ─────────────────────────────────────────────

    def _on_start_stop_clicked(self):
        # FIX: un seul bouton connecté, délégation selon l'état
        if not self.is_running:
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
        return w

    def _compute_cols(self) -> int:
        """Calcule le nombre de colonnes selon la largeur disponible."""
        available = self.scroll.viewport().width()
        # Prend en compte l'espacement entre les colonnes
        effective_card_width = self._CARD_W + self._GRID_GAP
        cols = max(1, available // effective_card_width)
        return cols

    def _update_grid_layout(self):
        """Met à jour la grille quand le nombre de colonnes change."""
        new_cols = self._compute_cols()
        if new_cols != self._current_cols:
            self._current_cols = new_cols
            self._reorganize_grid()

    def _reorganize_grid(self):
        """Réorganise les widgets dans la nouvelle grille."""
        widgets = []
        # Récupérer tous les widgets dans l'ordre
        for i in range(self.grid.count()):
            item = self.grid.itemAt(i)
            if item and item.widget():
                widgets.append(item.widget())
        
        # Vider la grille
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            if item and item.widget():
                self.grid.removeWidget(item.widget())
        
        # Replacer les widgets avec le nouveau nombre de colonnes
        for i, widget in enumerate(widgets):
            self.grid.addWidget(widget, i // self._current_cols, i % self._current_cols)

    def resizeEvent(self, event: QResizeEvent):
        """Gère le redimensionnement pour ajuster les colonnes."""
        super().resizeEvent(event)
        # Utiliser un QTimer pour éviter les appels trop fréquents
        if not hasattr(self, '_resize_timer'):
            self._resize_timer = QTimer()
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self._update_grid_layout)
        
        self._resize_timer.start(100)  # Attendre 100ms avant de recalculer

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
        
        # Mettre à jour la barre de progression globale
        self._update_progress_display()

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
            self._progress_label.setText(tr("En attente…"))
        elif pct == 100:
            self._progress_label.setText(f"{tr('Terminé')} — {done} {tr('traité(s)')}, {error} {tr('erreur(s)')}")
        else:
            self._progress_label.setText(f"{pct}% — {done + error} / {total} {tr('images')}")

    # ─────────────────────────────────────────────
    # Process mode
    # ─────────────────────────────────────────────

    def set_processing_mode(self, running: bool):
        self.is_running = running
        self.btn_start.setIcon(self.icon_stop if running else self.icon_start)

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
        self.connection_verificator.cleanup()
        self._clear()

    # ─────────────────────────────────────────────
    # Cleanup
    # ─────────────────────────────────────────────

    def _on_theme_changed(self, theme: str):
        """Gère le changement de thème"""
        self.icon_start = colored_icon("./ui/Icon/play_arrow.svg", os.environ["QTMATERIAL_PRIMARYCOLOR"])
        self.icon_stop = colored_icon("./ui/Icon/stop.svg", os.environ["QTMATERIAL_PRIMARYCOLOR"])
        self.btn_start.setIcon(self.icon_stop if self.is_running else self.icon_start)
        self.scroll.setStyleSheet(f"background-color: {os.environ["QTMATERIAL_SECONDARYLIGHTCOLOR"]};")
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 5px;
                background-color: #e9ecef;
            }}
            QProgressBar::chunk {{
                border-radius: 5px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {os.environ["QTMATERIAL_PRIMARYCOLOR"]},
                    stop:1 {os.environ["QTMATERIAL_PRIMARYLIGHTCOLOR"]}
                );
            }}
        """)

    # ─────────────────────────────────────────────
    # LANGUAGE
    # ─────────────────────────────────────────────
    
    def _on_language_changed(self, lang_code: str = None):
        """Met à jour tous les textes UI de l'import tool"""

        # -----------------------------
        # HEADER
        # -----------------------------
        self.folder_label.setText(
            self.folder_label.text()
            if self.folder_label.text() not in ["", "Aucun dossier", "Erreur"]
            else tr("Aucun dossier")
        )

        self.btn_select.setText(tr("Dossier"))

        # bouton start/stop → uniquement tooltip implicite via icône
        self.btn_start.setToolTip(
            tr("Démarrer") if not self.is_running else tr("Arrêter")
        )

        # -----------------------------
        # FOOTER - PROGRESS LABEL
        # -----------------------------
        self._progress_label.setText(
            tr("En attente…")
        )

        # on force une mise à jour cohérente avec l'état actuel
        self._update_progress_display()

        # -----------------------------
        # CONNECTION WIDGET (si traduisible)
        # -----------------------------
        if hasattr(self.connection_verificator.view, "retranslate"):
            self.connection_verificator.view.retranslate()

        # -----------------------------
        # FORCE REFRESH UI
        # -----------------------------
        self.update()
            