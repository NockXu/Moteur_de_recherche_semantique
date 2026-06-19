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
from ui.ImportTool.widget.ConnectionVerificator import ConnectionVerificatorController
from ui.ImportTool.ImageThumbnailWidget import ImageThumbnailWidget
from ui.utils.JustifiedGalleryLayout import JustifiedGalleryLayout

from ui.utils.colored_icon import colored_icon

from ui.utils.i18n import tr


# ─────────────────────────────────────────────
# Style helpers
# ─────────────────────────────────────────────

def _shadow(widget: QWidget, radius: int = 12, alpha: int = 30):
    """Apply a drop shadow effect to a given widget.

    Args:
        widget (QWidget):
            The widget that receives the shadow effect.
        radius (int):
            The blur radius of the shadow. Defaults to 12.
        alpha (int):
            The alpha transparency level of the shadow color (0-255). Defaults to 30.

    """
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

class LazyImageCard:
    """Wrapper class used to manage lazy-loading state for individual image components.

    Args:
        image (Image):
            The business image entity data wrapper.
        widget (ImageThumbnailWidget):
            The respective layout rendering component.

    """
    def __init__(self, image: Image, widget: ImageThumbnailWidget):
        self.image = image
        self.widget = widget
        self.loaded = False
        self.visible = False

# ─────────────────────────────────────────────
# VIEW
# ─────────────────────────────────────────────

class ImportToolView(QWidget):
    """Main view component representing the asynchronous dataset ingestion widget.

    Manages user interactions for path targeting, background batch iteration triggers,
    and a custom justified layout viewport that tracks scroll increments.

    Args:
        parent (QWidget):
            Optional parent container reference. Defaults to None.
        ollama_base_url (str):
            Optional base endpoint URL configuration parameter for connection health checks. Defaults to None.

    """

    folder_selected = pyqtSignal(str)
    start_processing_requested = pyqtSignal()
    stop_processing_requested = pyqtSignal()
    image_clicked = pyqtSignal(Image)
    load_more_requested = pyqtSignal()

    _CARD_W = 200
    _GRID_GAP = 6
    _SCROLL_MARGIN_PX = 0 * 2

    def __init__(self, parent=None, ollama_base_url: str = None):
        super().__init__(parent)

        self.connection_verificator = ConnectionVerificatorController(
            base_url=ollama_base_url
        )

        self._cards: list[LazyImageCard] = []
        self._lazy_enabled = True
        self._loading = False
        self._cols = 1
        self._total_loaded = 0

        self._render_queue = []
        self._lazy_timer = QTimer(self)
        self._lazy_timer.setInterval(16)
        self._lazy_timer.timeout.connect(self._lazy_render_batch)
        self._max_renders_per_batch = 3
        
        self._widget_map: dict[str, ImageThumbnailWidget] = {}

        self._setup_ui()
                    

    # ─────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────

    def _setup_ui(self):
        """Construct structural UI composition by stacking header, body, and footer frames."""
        root = QVBoxLayout(self)
        self._build_header(root)
        self._build_body(root)
        self._build_footer(root)

    def _build_header(self, parent):
        """Build the upper header configuration bar for selecting inputs and executing routines.

        Args:
            parent (QVBoxLayout):
                The main container layout object where the header frame is registered.

        """
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
        """Build the main content scrollable panel that dynamically holds lazy image components.

        Args:
            parent (QVBoxLayout):
                The main layout tree where the body viewport frame is registered.

        """
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.masonry = QWidget()
        self.gallery_layout = JustifiedGalleryLayout()
        self.masonry.setLayout(self.gallery_layout)

        self.scroll_area.setWidget(self.masonry)
        parent.addWidget(self.scroll_area)

    def _build_footer(self, parent):
        """Build the dashboard footer displaying background track progress and diagnostic widgets.

        Args:
            parent (QVBoxLayout):
                The global layout stack where the footer frame is registered.

        """
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
        """Prompt system directory dialog and emit the result path if selection holds valid."""
        path = QFileDialog.getExistingDirectory(self)
        if path:
            self.folder_selected.emit(path)

    def set_folder(self, path: str, ok: bool):
        """Update file tracker label according to diagnostic validation states.

        Args:
            path (str):
                Target folder absolute system path representation.
            ok (bool):
                Boolean assertion confirming execution clearance or active errors.

        """
        self.folder_label.setText(Path(path).name if ok else tr("Erreur"))

    # ─────────────────────────────────────────────
    # Start / Stop
    # ─────────────────────────────────────────────

    def _on_start_stop_clicked(self):
        """Toggle ingestion process execution states depending on active configuration values."""
        # FIX: un seul bouton connecté, délégation selon l'état
        if not self.is_running:
            self.start_processing_requested.emit()
        else:
            self.stop_processing_requested.emit()

    # ─────────────────────────────────────────────
    # Image loading (piloté par le Controller)
    # ─────────────────────────────────────────────

    

    # ─────────────────────────────────────────────
    # SCROLL / LOAD MORE
    # ─────────────────────────────────────────────

    def set_image_count(self, count: int):
        """Set numerical thresholds on internal spinbox tracker elements if applicable.

        Args:
            count (int):
                The integer amount tracking loaded entities.

        """
        self.image_count_spinbox.setValue(count)

    def _on_scroll(self, value: int):
        """Evaluate bounding box triggers during view scrolls to implement pagination offsets.

        Args:
            value (int):
                The raw vertical position offset inside the active layout structure.

        """
        if self._lazy_enabled:
            self._check_visible_cards()

        if self._loading:
            return

        bar = self.scroll_area.verticalScrollBar()

        if bar.maximum() - value < 300:
            self._loading = True
            QTimer.singleShot(100, self._emit_load_more)

    def _emit_load_more(self):
        """Dispatch a paginated request signal and clear status flags."""
        self._loading = False
        self.load_more_requested.emit()
        
    # ─────────────────────────────────────────────
    # LAZY CORE
    # ─────────────────────────────────────────────

    def _check_visible_cards(self):
        """Determine which thumbnail frames fall inside visible ranges and append to the loading queue."""
        if not self._lazy_enabled:
            return

        viewport = self.scroll_area.viewport()
        viewport_rect = viewport.rect()

        for card in self._cards:
            if card.loaded or not card.widget:
                continue

            try:
                pos = card.widget.mapTo(viewport, card.widget.rect().topLeft())
                rect = card.widget.rect()
                rect.moveTo(pos)

                extended = viewport_rect.adjusted(-200, -200, 200, 200)

                if extended.intersects(rect):
                    card.visible = True
                    if card not in self._render_queue:
                        self._render_queue.append(card)
                else:
                    card.visible = False

            except RuntimeError:
                continue

        if self._render_queue and not self._lazy_timer.isActive():
            self._lazy_timer.start()

    def _lazy_render_batch(self):
        """Iterate over queued images to extract visual properties within controlled framerate increments."""
        if not self._render_queue:
            self._lazy_timer.stop()
            return

        batch = self._render_queue[:self._max_renders_per_batch]
        self._render_queue = self._render_queue[self._max_renders_per_batch:]

        for card in batch:
            if not card.loaded:
                card.widget.load_image()

        if not self._render_queue:
            self._lazy_timer.stop()

    def _load_thumbnail(self, card: LazyImageCard):
        """Trigger the asynchronous loading of the widget thumbnail.

        The `card.loaded` property will be set to True via the `image_loaded` signal,
        NOT here — since the loading process is asynchronous.

        Args:
            card (LazyImageCard):
                The tracking structure container instance targeted for rendering update execution.

        """
        if not card.widget:
            return

        try:
            card.widget.load_image()
            # Ne pas setter card._loaded ici : c'est le signal image_loaded qui le fait
        except Exception as e:
            print(f"{tr('[LAZY] error')}: {e}")

    # ─────────────────────────────────────────────
    # API
    # ─────────────────────────────────────────────

    def display_images(self, image_data: list[Image]):
        """Render a collection of Image models onto the gallery dashboard context.

        Args:
            image_data (list[Image]):
                List containing structural business model data points.

        """
        for image in image_data:
            card = LazyImageCard(image, None)

            widget = ImageThumbnailWidget(
                image=image,
                status=image.status,
                lazy=self._lazy_enabled,
            )

            widget.clicked.connect(
                lambda checked_or_path=None, img=image: self.image_clicked.emit(img)
            )

            widget.image_loaded.connect(
                lambda c=card: self._on_image_loaded(c)
            )

            card.widget = widget
            self._cards.append(card)

            self.gallery_layout.addWidget(widget)

        if self._lazy_enabled:
            QTimer.singleShot(100, self._check_visible_cards)

    def _on_image_loaded(self, card: LazyImageCard):
        """Mark an underlying thumbnail as loaded and prompt internal layout updates.

        Args:
            card (LazyImageCard):
                The specific card structure object that has finished loading.

        """
        if card.loaded:
            return

        card.loaded = True
        self._total_loaded += 1

        self.gallery_layout.update()
        self.masonry.update()

    def update_images(self, images_results: dict[str, list[dict]]):
        """Forward diagnostic evaluation values to subcomponents based on tracking keys.

        Args:
            images_results (dict[str, list[dict]]):
                A map containing information metrics structured per dataset file path key.

        """
        widgets = {
            str(c.image.path): c.widget
            for c in self._cards
            if c.widget
        }

        for path, results in images_results.items():
            w = widgets.get(str(path))
            if w:
                w.set_result(results)
        
    def append_images(self, image_data: list[Image]):
        """Inject additional elements into the active layout framework view context.

        Args:
            image_data (list[Image]):
                List containing data properties to stack.

        """
        self.display_images(image_data)
        
    def _update_progress_display(self):
        """Recalculate and display extraction progression across data sources."""
        if not hasattr(self, 'model') or not self.model:
            return
            
        # Nombre total d'images dans le dossier complet
        total = self.model.get_images_count()
        
        # Nombre d'images déjà traitées en BDD (COMPLETED) parmi TOUTES celles du dossier
        # On peut l'estimer via l'intersection des fichiers du dossier et de self._existing_paths du controller, 
        # ou simplement compter le nombre d'images COMPLETED actuellement dans le cache du modèle :
        counts = self.model.get_images_by_status()
        treated = counts.get(ProcessingStatus.COMPLETED, 0) + counts.get(ProcessingStatus.ERROR, 0)
        
        # Si le traitement de traitement de lot est en cours, progress.setValue(treated)
        self.progress.setValue(treated)
        self._progress_label.setText(f"Indexation : {treated} / {total} images")
        
    def update_image_status(self, path: str, status: ProcessingStatus):
        """Update the status badge indicator on a unique image node inside the view structure.

        Args:
            path (str):
                Absolute file system destination identifier tracking the targeted instance.
            status (ProcessingStatus):
                The new lifecycle configuration enum item to append.

        """
        key = str(Path(path).resolve())

        for card in self._cards:
            if str(card.image.path.resolve()) == key:
                print("STATUS", status)   # debug
                card.image.status = status

                if card.widget:
                    card.widget.set_status(status)

                break
            
    def _refresh_image_display(self):
        """Trigger update requests across active subcomponent visual layouts."""
        for card in self._cards:
            if card.widget:
                card.widget.update()

    # ─────────────────────────────────────────────
    # Process mode
    # ─────────────────────────────────────────────

    def set_processing_mode(self, running: bool):
        """Toggle action icons and local flag definitions during operations.

        Args:
            running (bool):
                State declaration confirming active thread jobs.

        """
        self.is_running = running
        self.btn_start.setIcon(self.icon_stop if running else self.icon_start)

    # ─────────────────────────────────────────────
    # Model injection
    # ─────────────────────────────────────────────

    def set_model(self, model):
        """Inject an application model structure instance to link with data transformations.

        Args:
            model (Any):
                The runtime model object holding status information.

        """
        self.model = model

    def get_model(self):
        """Fetch the injected model instance bound to this view context.

        Returns:
            The active model layer or object instance.

        """
        return self.model

    # ─────────────────────────────────────────────
    # Cleanup
    # ─────────────────────────────────────────────

    def cleanup(self):
        """Release underlying controllers and clear memory allocations safely."""
        self.connection_verificator.cleanup()
        self._clear()
        
    def _clear(self):
        """Purge tracking structures and request layout removal operations."""
        self._cards.clear()
        self._render_queue.clear()

        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        self._total_loaded = 0
        self._lazy_timer.stop()
        
    def clear(self):
        """Expose layout clearing loops to external manager layers."""
        self._clear()
        # Optionnel : On force le layout de la galerie à se recalculer vide
        if hasattr(self.gallery_layout, 'update'):
            self.gallery_layout.update()

    # ─────────────────────────────────────────────
    # THEME
    # ─────────────────────────────────────────────

    def _on_theme_changed(self, theme: str):
        """Re-render background elements and material style patterns on system theme changes.

        Args:
            theme (str):
                The target context configuration identification variable name.

        """
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
        """Refresh displayed texts across local interface frames using translation tables.

        Args:
            lang_code (str):
                Optional localized culture target code syntax. Defaults to None.

        """
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