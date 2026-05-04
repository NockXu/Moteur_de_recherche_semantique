import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QFileDialog, QLabel, QFrame,
    QGridLayout, QProgressBar, QApplication, QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QEvent
from PyQt6.QtGui import QFont, QColor, QResizeEvent
from pathlib import Path

from common.ImageInfo import ImageInfo, ProcessingStatus
from ui.ImportTool.ImportToolModel import ImportToolModel
from ui.ImportTool.ImageWidget import ImageWidget
from ui.ImportTool.widget.ConnectionVerificator import create_connection_verificator
from typing import List, Dict


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de style
# ─────────────────────────────────────────────────────────────────────────────

def _shadow(widget: QWidget, radius: int = 12, alpha: int = 30):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(radius)
    eff.setOffset(0, 2)
    eff.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(eff)


_CARD_STYLE = "QFrame { border-radius: 8px; }"

_BTN_PRIMARY = """
    QPushButton {{
        background-color: {bg};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
    }}
    QPushButton:hover    {{ background-color: {hover};   }}
    QPushButton:pressed  {{ background-color: {pressed}; }}
    QPushButton:disabled {{ background-color: #adb5bd; color: #f8f9fa; }}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Vue principale
# ─────────────────────────────────────────────────────────────────────────────

class ImportToolView(QWidget):
    """
    Vue principale de l'outil d'import.

    Chargement virtuel des widgets :
    - Seule la première page (PAGE_SIZE images) est rendue au démarrage.
    - Quand l'utilisateur approche du bas du scroll (seuil = 80 %),
      la page suivante est ajoutée automatiquement.
    - Chaque ajout de page est différé via QTimer pour ne jamais bloquer l'UI.
    """

    folder_selected            = pyqtSignal(str)
    start_processing_requested = pyqtSignal()
    stop_processing_requested  = pyqtSignal()
    image_clicked              = pyqtSignal(ImageInfo)

    _CARD_W   = ImageWidget.CARD_WIDTH
    _CARD_H   = ImageWidget.CARD_HEIGHT
    _GRID_GAP = 12

    # Seuil de scroll (0–1) à partir duquel on charge la page suivante
    _SCROLL_THRESHOLD = 0.80

    def __init__(self, parent=None, ollama_base_url: str = None):
        super().__init__(parent)
        self.model = ImportToolModel()
        self.image_widgets: Dict[str, ImageWidget] = {}
        self.status_labels: Dict[ProcessingStatus, QLabel] = {}
        self._current_cols  = 1
        self._loaded_page   = -1       # dernière page rendue
        self._all_images: List[ImageInfo] = []   # référence complète courante
        self._loading_page  = False    # garde contre les appels simultanés

        self.connection_verificator = create_connection_verificator(
            base_url=ollama_base_url
        )

        self._setup_ui()
        self._update_progress_display()

    # ─────────────────────────────────────────────────────────────────────────
    # Construction UI
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)
        self._build_header(root)
        self._build_image_area(root)
        self._build_footer(root)

    def _build_header(self, parent):
        card = QFrame()
        card.setStyleSheet(_CARD_STYLE)
        _shadow(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        folder_icon = QLabel("📁")
        folder_icon.setFont(QFont("Segoe UI", 14))
        folder_row.addWidget(folder_icon)
        self.folder_label = QLabel("Aucun dossier sélectionné")
        self.folder_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.folder_label.setWordWrap(True)
        folder_row.addWidget(self.folder_label, 1)
        lay.addLayout(folder_row)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        self.select_folder_btn = QPushButton("📁 Parcourir")
        self.select_folder_btn.setFont(QFont("Segoe UI", 10))
        self.select_folder_btn.setStyleSheet(_BTN_PRIMARY.format(bg="#009688", hover="#00796b", pressed="#00695c"))
        self.select_folder_btn.setFixedHeight(38)
        self.select_folder_btn.clicked.connect(self._on_select_folder)
        buttons_row.addWidget(self.select_folder_btn)

        self.process_btn = QPushButton("▶")
        self.process_btn.setFont(QFont("Segoe UI", 10))
        self.process_btn.setStyleSheet(_BTN_PRIMARY.format(bg="#009688", hover="#00796b", pressed="#00695c"))
        self.process_btn.setFixedHeight(38)
        self.process_btn.clicked.connect(self._on_process_clicked)
        buttons_row.addWidget(self.process_btn)

        self.reset_btn = QPushButton("🔄 Réinitialiser")
        self.reset_btn.setFont(QFont("Segoe UI", 10))
        self.reset_btn.setStyleSheet(_BTN_PRIMARY.format(bg="#757575", hover="#616161", pressed="#424242"))
        self.reset_btn.setFixedHeight(38)
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        buttons_row.addWidget(self.reset_btn)

        lay.addLayout(buttons_row)
        parent.addWidget(card)

    def _build_image_area(self, parent):
        area_card   = QFrame()
        area_layout = QVBoxLayout(area_card)
        area_layout.setContentsMargins(0, 0, 0, 0)
        area_layout.setSpacing(0)

        # En-tête de section
        section_header = QWidget()
        sh_lay = QHBoxLayout(section_header)
        sh_lay.setContentsMargins(16, 10, 16, 10)
        section_title = QLabel("Images importées")
        section_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        sh_lay.addWidget(section_title)
        sh_lay.addStretch()
        self.image_count_label = QLabel("0 image")
        self.image_count_label.setFont(QFont("Segoe UI", 10))
        self.image_count_label.setStyleSheet("font-weight: bold;")
        sh_lay.addWidget(self.image_count_label)
        area_layout.addWidget(section_header)

        # ScrollArea
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollBar:vertical { width: 6px; margin: 4px 2px; }
            QScrollBar::handle:vertical { background: #ced4da; border-radius: 3px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #adb5bd; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        # Écouter le scroll pour le lazy-load
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.scroll_area.viewport().installEventFilter(self)

        # Container grille
        self.image_container = QWidget()
        self.image_layout = QGridLayout(self.image_container)
        self.image_layout.setSpacing(self._GRID_GAP)
        self.image_layout.setContentsMargins(4, 4, 4, 4)
        self.image_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.image_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Placeholder vide
        self._empty_label = QLabel("Sélectionnez un dossier pour charger les images")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setFont(QFont("Segoe UI", 11))
        self._empty_label.setStyleSheet("padding: 60px;")
        self.image_layout.addWidget(self._empty_label, 0, 0)

        self.scroll_area.setWidget(self.image_container)
        area_layout.addWidget(self.scroll_area, 1)

        parent.addWidget(area_card, 1)

    def _build_footer(self, parent):
        status_row = QHBoxLayout()
        status_row.setSpacing(12)

        self.status_labels = {}
        for status, text in [
            (ProcessingStatus.NOT_STARTED, "En attente"),
            (ProcessingStatus.IN_PROGRESS, "En cours"),
            (ProcessingStatus.COMPLETED,   "Terminé"),
            (ProcessingStatus.ERROR,       "Erreur"),
        ]:
            label = QLabel(f"{text}: 0")
            label.setFont(QFont("Segoe UI", 9))
            label.setStyleSheet("padding: 2px 6px;")
            status_row.addWidget(label)
            self.status_labels[status] = label

        progress_connexion_row = QHBoxLayout()
        progress_connexion_row.setSpacing(12)

        progress_container = QWidget()
        progress_layout = QHBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)

        self.progress_counter = QLabel("0 / 0")
        self.progress_counter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        progress_layout.addWidget(self.progress_counter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar::chunk { background-color: #009688; border-radius: 4px; }
        """)
        progress_layout.addWidget(self.progress_bar, 1)
        progress_connexion_row.addWidget(progress_container, 1)
        progress_connexion_row.addWidget(self.connection_verificator.get_view())

        parent.addLayout(status_row)
        lay = QHBoxLayout()
        lay.addLayout(progress_connexion_row)
        parent.addLayout(lay)

    # ─────────────────────────────────────────────────────────────────────────
    # Grille responsive
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_cols(self) -> int:
        vp_width  = self.scroll_area.viewport().width()
        # Prendre en compte les marges du layout (4px de chaque côté)
        layout_margins = 8  # 4px gauche + 4px droite
        available = max(vp_width - layout_margins, self._CARD_W)
        # Forcer un maximum de 2 colonnes pour éviter les lignes de 3+
        max_cols = 2
        calculated = max(1, available // (self._CARD_W + self._GRID_GAP))
        return min(calculated, max_cols)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._check_reflow()

    def eventFilter(self, obj, event):
        if obj is self.scroll_area.viewport() and event.type() == QEvent.Type.Resize:
            self._check_reflow()
        return super().eventFilter(obj, event)

    def _check_reflow(self):
        new_cols = self._compute_cols()
        if new_cols != self._current_cols and self.image_widgets:
            self._current_cols = new_cols
            QTimer.singleShot(40, self._reflow_grid)

    def _reflow_grid(self):
        cols = self._current_cols
        for i, w in enumerate(self.image_widgets.values()):
            w.setFixedSize(w.CARD_WIDTH, w.CARD_HEIGHT)
            self.image_layout.addWidget(w, i // cols, i % cols)

    # ─────────────────────────────────────────────────────────────────────────
    # Virtual scroll — lazy loading par page
    # ─────────────────────────────────────────────────────────────────────────

    def _on_scroll(self, value: int):
        """Déclenche le chargement de la page suivante quand on approche du bas."""
        sb   = self.scroll_area.verticalScrollBar()
        maxi = sb.maximum()
        if maxi <= 0:
            return
        ratio = value / maxi
        if ratio >= self._SCROLL_THRESHOLD:
            self._load_next_page()

    def _load_next_page(self):
        """Charge et affiche la page suivante de widgets (différé pour ne pas freezer)."""
        if self._loading_page:
            return

        next_page  = self._loaded_page + 1
        page_count = self.model.get_page_count()
        if next_page >= page_count:
            return   # tout est déjà affiché

        self._loading_page = True

        def _do_load():
            images = self.model.get_page(next_page)
            if not images:
                self._loading_page = False
                return

            cols        = self._current_cols
            base_index  = len(self.image_widgets)

            for j, image_info in enumerate(images):
                i = base_index + j
                widget = self._make_widget(image_info)
                self.image_widgets[str(image_info.path)] = widget
                self.image_layout.addWidget(widget, i // cols, i % cols)

            self._loaded_page  = next_page
            self._loading_page = False

        # Différer légèrement pour laisser Qt respirer
        QTimer.singleShot(0, _do_load)

    def _make_widget(self, image_info: ImageInfo) -> ImageWidget:
        widget = ImageWidget(str(image_info.path), image_info.status)
        # Utiliser une référence faible pour éviter les fuites de mémoire
        def create_click_handler(img_info):
            def handler():
                self.image_clicked.emit(img_info)
            return handler
        
        widget.image_clicked.connect(create_click_handler(image_info))
        widget.setFixedSize(widget.CARD_WIDTH, widget.CARD_HEIGHT)
        return widget

    # ─────────────────────────────────────────────────────────────────────────
    # Handlers UI
    # ─────────────────────────────────────────────────────────────────────────

    def _on_select_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Sélectionner un dossier d'images",
            str(Path.home()), QFileDialog.Option.ShowDirsOnly,
        )
        if path:
            self.folder_selected.emit(path)

    def _on_process_clicked(self):
        if "▶" in self.process_btn.text() or "Commencer" in self.process_btn.text():
            self.start_processing_requested.emit()
        else:
            self.stop_processing_requested.emit()

    def _on_reset_clicked(self):
        self.model.reset_all_status()
        self._refresh_image_display()
        self._update_progress_display()
        self.process_btn.setText("▶  Commencer le traitement")
        self._set_process_btn_style("start")

    def _set_process_btn_style(self, mode: str):
        styles = {
            "start":    ("#009688", "#00796b", "#00695c"),
            "stop":     ("#e63946", "#cc2f3b", "#b52730"),
            "disabled": ("#757575", "#616161", "#424242"),
        }
        bg, hover, pressed = styles.get(mode, styles["start"])
        self.process_btn.setStyleSheet(_BTN_PRIMARY.format(bg=bg, hover=hover, pressed=pressed))

    # ─────────────────────────────────────────────────────────────────────────
    # API publique (appelée par le Controller)
    # ─────────────────────────────────────────────────────────────────────────

    def set_folder(self, folder_path: str, success: bool):
        if success:
            self.folder_label.setText(Path(folder_path).name)
            self.select_folder_btn.setText("  Changer de dossier")
            self.process_btn.setEnabled(True)
            self.reset_btn.setEnabled(True)
        else:
            self.folder_label.setText("Erreur lors de la sélection")
            self.process_btn.setEnabled(False)
            self.reset_btn.setEnabled(False)

    def load_images(self, images: List[ImageInfo]):
        """
        Point d'entrée principal — appelé par le Controller après set_folder.
        N'affiche que la première page ; le reste se charge au scroll.
        """
        self._clear_image_display()
        self._empty_label.hide()
        self._all_images    = images
        self._loaded_page   = -1
        self._loading_page  = False
        self._current_cols  = self._compute_cols()

        # Charger immédiatement la première page
        self._load_next_page()

        n = self.model.get_images_count()
        self.image_count_label.setText(f"{n} image{'s' if n > 1 else ''}")
        self._update_progress_display()

    def _clear_image_display(self):
        for i in reversed(range(self.image_layout.count())):
            item = self.image_layout.itemAt(i)
            if item:
                w = item.widget()
                if w and w is not self._empty_label:
                    # Annuler le chargement asynchrone avant destruction
                    if hasattr(w, 'cancel_load'):
                        w = None
                    else :
                        w.setParent(None)
                        w.deleteLater()
        self.image_widgets.clear()
        self._loaded_page  = -1
        self._loading_page = False

    def _refresh_image_display(self):
        self._clear_image_display()
        self._empty_label.hide()
        self._loaded_page  = -1
        self._loading_page = False
        self._load_next_page()

    def update_image_status(self, image_path: str, status: ProcessingStatus):
        if image_path in self.image_widgets:
            self.image_widgets[image_path].set_status(status)
        self._update_progress_display()

    def _update_progress_display(self):
        counts    = self.model.get_images_by_status()
        total     = self.model.get_images_count()
        processed = self.model.get_processed_count()

        labels_cfg = {
            ProcessingStatus.NOT_STARTED: "En attente",
            ProcessingStatus.IN_PROGRESS: "En cours",
            ProcessingStatus.COMPLETED:   "Terminé",
            ProcessingStatus.ERROR:       "Erreur",
        }
        for status, text in labels_cfg.items():
            count = counts.get(status, 0)
            self.status_labels[status].setText(f"{text}: {count}")

        self.progress_counter.setText(f"{processed} / {total}")
        self.progress_bar.setValue(
            int((processed / total) * 100) if total > 0 else 0
        )

    def set_processing_mode(self, is_processing: bool):
        if is_processing:
            self.process_btn.setText("⏹  Arrêter le traitement")
            self._set_process_btn_style("stop")
            self.process_btn.setEnabled(True)
            self.select_folder_btn.setEnabled(False)
        else:
            self.process_btn.setText("▶  Commencer le traitement")
            self._set_process_btn_style("start")
            self.process_btn.setEnabled(True)
            self.select_folder_btn.setEnabled(True)

    def set_stop_requested(self):
        self.process_btn.setText("Arrêt en cours…")
        self._set_process_btn_style("disabled")
        self.process_btn.setEnabled(False)

    def get_model(self) -> ImportToolModel:
        return self.model

    def get_connection_verificator(self):
        return self.connection_verificator

    def cleanup(self):
        """Nettoie toutes les ressources et détruit les widgets."""
        # Annuler tous les chargements en cours
        for widget in self.image_widgets.values():
            if hasattr(widget, 'cancel_load'):
                widget.cancel_load()
        
        # Nettoyer l'affichage
        self._clear_image_display()
        
        # Nettoyer le vérificateur de connexion
        if hasattr(self, "connection_verificator"):
            self.connection_verificator.cleanup()
        
        # Déconnecter les signaux
        try:
            self.folder_selected.disconnect()
            self.start_processing_requested.disconnect()
            self.stop_processing_requested.disconnect()
            self.image_clicked.disconnect()
        except:
            pass