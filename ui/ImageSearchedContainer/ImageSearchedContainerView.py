import sys
import os

# Ajouter le chemin racine du projet au sys.path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import ImageInfo

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ui.ImageSearchedContainer.widget.ImageThumbnailWidget import ImageThumbnailWidget
from ui.ImageSearchedContainer.widget.PaginationWidget import PaginationWidget
from ui.ImageSearchedContainer.widget.MasonryWidget import MasonryLayout


class ImageSearchedContainerView(QWidget):
    """
    Vue principale : header + grille masonry scrollable + pagination.
    Ne gère pas la logique de pagination — c'est le Controller qui
    appelle display_images() avec la tranche déjà calculée.
    """

    image_clicked = pyqtSignal(ImageInfo)
    page_changed  = pyqtSignal(int)
    reload_requested = pyqtSignal()  # Nouveau signal pour recharger les images

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header avec bouton de rechargement
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(10)
        
        self.header_label = QLabel("0 image trouvée")
        self.header_label.setFont(QFont("Segoe UI", 10))
        header_layout.addWidget(self.header_label)
        
        # Bouton de rechargement
        self.reload_button = QPushButton("🔄 Recharger")
        self.reload_button.setFont(QFont("Segoe UI", 9))
        self.reload_button.setFixedHeight(30)
        self.reload_button.clicked.connect(self.reload_requested.emit)
        header_layout.addWidget(self.reload_button)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Zone scrollable
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Layout masonry
        self.masonry = MasonryLayout()
        self.scroll_area.setWidget(self.masonry)
        layout.addWidget(self.scroll_area, stretch=1)

        # Pagination
        self.pagination = PaginationWidget()
        self.pagination.page_changed.connect(self.page_changed)
        layout.addWidget(self.pagination)

    def _apply_styles(self):
        self.setStyleSheet("""
            QLabel#header {
                font-size: 10pt;
            }
            QPushButton {
                border: none;
                padding: 5px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        self.header_label.setObjectName("header")
        self.reload_button.setObjectName("reload_button")

    # ------------------------------------------------------------------
    # API appelée par le Controller
    # ------------------------------------------------------------------

    def display_images(self, image_data: list[ImageInfo], total_count: int,
                       current_page: int, total_pages: int):
        """
        Affiche une tranche d'images (déjà filtrée/triée/paginée par le modèle).

        image_data : liste de dicts {'path', 'title', ...}
        total_count : nombre total d'images (pour le header)
        """

        # Header
        n = total_count
        self.header_label.setText(f"{n} image{'s' if n > 1 else ''} trouvée{'s' if n > 1 else ''}")

        # Pagination
        self.pagination.set_total_pages(total_pages)
        self.pagination.set_page(current_page)

        # Cartes
        cards = []
        for image in image_data:
            card = ImageThumbnailWidget(
                image_path=str(image.path),
                title=image.name,
            )
            # Connecter le signal pour émettre l'ImageInfo quand on clique
            def create_card_click_handler(img_info):
                def handler(checked=False):
                    self.image_clicked.emit(img_info)
                return handler
            
            card.clicked.connect(create_card_click_handler(image))
            cards.append(card)

        self.masonry.set_cards(cards)
    
    def _on_masonry_image_clicked(self, image_path: str):
        """Gère le clic sur une image depuis le masonry"""
        from pathlib import Path
        from common.ImageInfo import ImageInfo
        
        # Créer un véritable objet ImageInfo à partir du chemin
        image_info = ImageInfo(
            path=Path(image_path),
            description="",
            keywords=[],
            score=0.0
        )
        self.image_clicked.emit(image_info)
    
    def clear(self):
        self.header_label.setText("0 image trouvée")
        self.masonry.clear()
        self.pagination.set_total_pages(1)
        self.pagination.set_page(1)