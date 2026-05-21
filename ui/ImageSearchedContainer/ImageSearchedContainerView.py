import sys
import os

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QPushButton, QHBoxLayout, QSlider, QSpinBox, QSlider
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from common.Image_Classes.Image import Image
from ui.ImageSearchedContainer.widget.ImageThumbnailWidget import ImageThumbnailWidget
from ui.ImageSearchedContainer.widget.SearchBar.SearchBarController import SearchBarController
from ui.ImageSearchedContainer.widget.MasonryWidget import MasonryLayout
from ui.utils.colored_icon import colored_icon

class LazyImageCard:
    """
    Wrapper pour gérer le lazy loading d'une carte
    """
    def __init__(self, image: Image):
        self.image = image
        self.widget: ImageThumbnailWidget | None = None
        self.is_visible = False
    
    @property
    def is_loaded(self):
        """Délègue au widget s'il existe"""
        return self.widget.is_loaded if self.widget else False


class ImageSearchedContainerView(QWidget):
    """
    Vue en mode LOAD MORE + LAZY LOADING :
    - charge les thumbnails uniquement quand visibles
    - limite le nombre de renders simultanés
    - compatible avec BaseImageThumbnailWidget existant
    """

    image_clicked = pyqtSignal(Image)
    load_more_requested = pyqtSignal()
    reload_requested = pyqtSignal()
    search_requested = pyqtSignal(str, list)
    threshold_changed = pyqtSignal(float)

    def __init__(self, parent=None, enable_lazy_loading: bool = True):
        super().__init__(parent)

        self._cards: list[LazyImageCard] = []
        self._loading = False
        
        # LAZY LOADING CONFIG
        self._lazy_enabled = enable_lazy_loading
        self._lazy_render_timer = QTimer()
        self._lazy_render_timer.timeout.connect(self._lazy_render_batch)
        self._lazy_render_timer.setInterval(50)  # Check toutes les 50ms
        
        self._render_queue: list[LazyImageCard] = []
        self._max_renders_per_batch = 10  # Charger max 10 images à la fois
        
        # Stats pour debug
        self._total_loaded = 0

        # Créer la SearchBar
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

        # Threshold selector
        threshold_label = QLabel("Seuil:")
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(50)
        self.threshold_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.threshold_slider.setTickInterval(10)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        
        # Label pour afficher la valeur actuelle
        self.threshold_value_label = QLabel("50%")
        self.threshold_value_label.setMinimumWidth(50)

        self.threshold_layout = QHBoxLayout()
        self.threshold_layout.addWidget(threshold_label)
        self.threshold_layout.addWidget(self.threshold_slider)
        self.threshold_layout.addWidget(self.threshold_value_label)

        self.button_layout = QHBoxLayout()
        header.addLayout(self.button_layout)

        self.reload_button = QPushButton()
        self.reload_button.clicked.connect(self.reload_requested.emit)

        self.button_layout.addWidget(self.reload_button)
        
        # Espace restant pour la recherche (dynamique)
        header.addStretch()

        self.search_controller.view.setMinimumWidth(300)
        header.addWidget(self.search_controller.view)

        layout.addLayout(header)

        # SCROLL AREA
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.masonry = MasonryLayout()
        self.scroll_area.setWidget(self.masonry)

        layout.addWidget(self.scroll_area)

        # Footer avec nombre d'images
        footer = QHBoxLayout()

        self.number_img_label = QLabel("0 image")
        self.number_img_label.setFont(QFont("Segoe UI", 10))

        # Partie gauche
        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addLayout(self.threshold_layout)

        footer.addWidget(left_widget)
        footer.addStretch()
        footer.addWidget(self.number_img_label)
        layout.addLayout(footer)

    def _apply_styles(self):
        self.reload_button.setIcon(colored_icon("./ui/Icon/refresh.svg", os.environ["QTMATERIAL_PRIMARYCOLOR"], 64))
        self.setStyleSheet(f"""
            QPushButton {{
                border: none;
                padding: 5px 12px;
                border-radius: 4px;
                font-weight: bold;
            }}
        """)

        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {os.environ["QTMATERIAL_SECONDARYLIGHTCOLOR"]};
                border: 10px solid {os.environ["QTMATERIAL_SECONDARYLIGHTCOLOR"]};
            }}
        """)

    def resizeEvent(self, event):
        """Ajuster la largeur de la recherche dynamiquement"""
        super().resizeEvent(event)
        self._update_search_width()

    def _update_search_width(self):
        """Calcule 1/2 de la largeur disponible"""
        if hasattr(self, 'search_controller') and self.search_controller:
            available_width = self.width() - 40  # Marge pour les autres éléments
            if available_width > 300:  # Minimum raisonnable
                search_width = max(300, available_width // 2)
                self.search_controller.view.setMinimumWidth(search_width)

    # ─────────────────────────────────────────────
    # SCROLL → LOAD MORE + LAZY LOADING
    # ─────────────────────────────────────────────

    def _on_scroll(self, value: int):

        # lazy loading
        if self._lazy_enabled:
            self._check_visible_cards()

        if self._loading:
            return

        bar = self.scroll_area.verticalScrollBar()

        # distance restante avant le bas
        remaining = bar.maximum() - value

        # trigger quand il reste < 300px
        if remaining < 300:
            self._trigger_load_more()

    def _trigger_load_more(self):
        self._loading = True
        QTimer.singleShot(100, self._emit_load_more)

    def _emit_load_more(self):
        self._loading = False
        self.load_more_requested.emit()

    # ─────────────────────────────────────────────
    # ✅ LAZY LOADING LOGIC
    # ─────────────────────────────────────────────

    def _check_visible_cards(self):
        """
        Détecte quelles cartes sont visibles dans le viewport
        et les ajoute à la queue de rendu
        """
        if not self._lazy_enabled:
            return
        
        viewport = self.scroll_area.viewport()
        viewport_rect = viewport.rect()
        
        for card in self._cards:
            # Si déjà chargée, skip
            if card.is_loaded:
                continue
            
            # Si pas de widget, skip
            if not card.widget:
                continue
            
            # Vérifier si visible dans le viewport
            try:
                widget_pos = card.widget.mapTo(viewport, card.widget.rect().topLeft())
                widget_rect = card.widget.rect()
                widget_rect.moveTo(widget_pos)
                
                # Avec marge de 200px pour preload
                viewport_extended = viewport_rect.adjusted(-200, -200, 200, 200)
                
                is_visible = viewport_extended.intersects(widget_rect)
                
                if is_visible and not card.is_visible:
                    card.is_visible = True
                    if card not in self._render_queue:
                        self._render_queue.append(card)
                elif not is_visible:
                    card.is_visible = False
                    
            except RuntimeError:
                # Widget peut être détruit pendant l'itération
                continue
        
        # Start timer si queue non vide
        if self._render_queue and not self._lazy_render_timer.isActive():
            self._lazy_render_timer.start()

    def _lazy_render_batch(self):
        """
        Charge un batch de thumbnails (max X à la fois)
        """
        if not self._render_queue:
            self._lazy_render_timer.stop()
            return
        
        # Prendre les N premiers
        batch = self._render_queue[:self._max_renders_per_batch]
        self._render_queue = self._render_queue[self._max_renders_per_batch:]
        
        for card in batch:
            if not card.is_loaded:
                self._load_thumbnail(card)
        
        # Si queue vide, stop timer
        if not self._render_queue:
            self._lazy_render_timer.stop()

    def _load_thumbnail(self, card: LazyImageCard):
        """
        Charge réellement le thumbnail
        """
        if card.widget and hasattr(card.widget, 'load_image'):
            try:
                card.widget.load_image()
                self._total_loaded += 1
                
                # Debug optionnel
                if self._total_loaded % 50 == 0:
                    print(f"[LAZY] {self._total_loaded}/{len(self._cards)} images chargées")
                    
            except Exception as e:
                print(f"[LAZY] Erreur chargement: {e}")

    def _on_image_size_changed(self):
        """
        ✅ Appelé quand une image lazy est chargée et change de taille
        Force le recalcul du layout Masonry
        """
        try:
            # Forcer le recalcul du layout Masonry
            self.masonry._relayout()
            
            # Optionnel: forcer le repaint immédiat
            self.masonry.update()
            
        except Exception as e:
            print(f"[LAYOUT] Erreur recalcul: {e}")

    # ─────────────────────────────────────────────
    # API CONTROLLER
    # ─────────────────────────────────────────────

    def display_images(self, image_data: list[Image], total_count: int):
        """
        Ajoute des images en mode lazy
        """
        self.number_img_label.setText(f"{total_count} image(s)")

        new_cards = []
        new_widgets = []

        for image in image_data:
            # Créer le wrapper lazy
            lazy_card = LazyImageCard(image)
            
            # Créer le widget avec ou sans lazy
            card = ImageThumbnailWidget(
                image_path=str(image.path),
                title=image.name,
                lazy=self._lazy_enabled,  # ✅ Mode lazy activable
                score=image.score  # ✅ Ajouter le score
            )

            card.clicked.connect(
                lambda _, img=image: self.image_clicked.emit(img)
            )
            
            # ✅ Connecter le signal de chargement pour recalculer le layout
            card.image_loaded.connect(self._on_image_size_changed)

            lazy_card.widget = card
            new_cards.append(lazy_card)
            new_widgets.append(card)

        self._cards.extend(new_cards)
        
        # Ajouter au masonry
        current_widgets = [c.widget for c in self._cards if c.widget]
        self.masonry.set_cards(current_widgets)
        
        # ✅ Check immédiat des visibles après layout
        if self._lazy_enabled:
            QTimer.singleShot(100, self._check_visible_cards)

    # ─────────────────────────────────────────────
    # CLEAR
    # ─────────────────────────────────────────────

    def _on_threshold_changed(self, value: int):
        """Appelé quand le threshold change"""
        threshold = value / 100.0  # Convertir % en float
        self.threshold_value_label.setText(f"{value}%")
        self.threshold_changed.emit(threshold)

    def clear(self):
        self._cards.clear()
        self._render_queue.clear()
        self._lazy_render_timer.stop()
        self.masonry.clear()
        self.number_img_label.setText("0 image")
        self._loading = False
        self._total_loaded = 0

    # ─────────────────────────────────────────────
    # CONFIG
    # ─────────────────────────────────────────────
    
    def set_lazy_batch_size(self, size: int):
        """Configure combien d'images charger simultanément"""
        self._max_renders_per_batch = size
    
    def enable_lazy_loading(self, enabled: bool):
        """Active/désactive le lazy loading"""
        self._lazy_enabled = enabled
        if not enabled:
            # Charger toutes les images immédiatement
            for card in self._cards:
                if not card.is_loaded and card.widget:
                    self._load_thumbnail(card)
    
    def get_lazy_stats(self) -> dict:
        """Statistiques de lazy loading pour debug"""
        return {
            "total_cards": len(self._cards),
            "loaded": self._total_loaded,
            "queue": len(self._render_queue),
            "percentage": (self._total_loaded / len(self._cards) * 100) if self._cards else 0
        }

    # ─────────────────────────────────────────────
    # THEME
    # ─────────────────────────────────────────────
    
    def _on_theme_changed(self):
        """Appelé quand le thème change"""
        self._apply_styles()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from database.DbService import DbService
    from common.Image_Classes.ImageRepository import ImageRepository

    db = DbService()
    repo = ImageRepository(db.sqlite, db.faiss)
    
    app = QApplication(sys.argv)

    # ✅ Test avec lazy loading activé
    view = ImageSearchedContainerView(enable_lazy_loading=True)
    view.set_lazy_batch_size(15)  # Charger 15 images à la fois
    view.show()

    images = repo.get_all()
    view.display_images(images, len(images))
    
    # Afficher stats toutes les 2 secondes
    def show_stats():
        stats = view.get_lazy_stats()
        print(f"Stats: {stats['loaded']}/{stats['total_cards']} ({stats['percentage']:.1f}%)")
    
    timer = QTimer()
    timer.timeout.connect(show_stats)
    timer.start(2000)
    
    sys.exit(app.exec())