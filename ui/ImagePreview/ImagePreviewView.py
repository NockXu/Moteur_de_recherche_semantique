import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea,
    QFrame, QHBoxLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap

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

        # ✅ IMAGE DISPLAY WIDGET
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(200)
        self.image_label.setMaximumWidth(280)  # ✅ Limiter la largeur
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background-color: #f9f9f9;
                color: #999;
            }
        """)
        self.image_label.setText("Aucune image")
        root.addWidget(self.image_label)

        # IMAGE INFO PANEL (simple et correct, pas de scroll horizontal)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(8)
        # ✅ Forcer la largeur maximale pour éviter le dépassement
        self.container.setMaximumWidth(280)

        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)

        # FIELDS simples
        self.name_label = QLabel()
        self.name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.layout.addWidget(self.name_label)
        
        self.path_label = QLabel()
        self.path_label.setFont(QFont("Segoe UI", 9))
        self.layout.addWidget(self.path_label)
        
        self.desc_label = QLabel()
        self.desc_label.setFont(QFont("Segoe UI", 9))
        self.layout.addWidget(self.desc_label)
        
        self.tags_label = QLabel()
        self.tags_label.setFont(QFont("Segoe UI", 9))
        self.layout.addWidget(self.tags_label)

        for w in [self.path_label, self.desc_label, self.tags_label]:
            w.setWordWrap(True)

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

        # ✅ Charger et afficher l'image
        try:
            pixmap = QPixmap(str(image.path))
            if not pixmap.isNull():
                # Redimensionner pour le preview (max 280px de largeur)
                scaled_pixmap = pixmap.scaled(
                    280, 280, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setStyleSheet("""
                    QLabel {
                        border: 2px solid #ddd;
                        border-radius: 8px;
                        background-color: white;
                    }
                """)
            else:
                self.image_label.setText("Image non chargeable")
                self.image_label.clear()
        except Exception as e:
            print(f"[PREVIEW] Erreur chargement image: {e}")
            self.image_label.setText("Erreur chargement")
            self.image_label.clear()

        self.name_label.setText(image.name)
        
        # ✅ Chemin complet avec word wrap comme la description
        self.path_label.setText(f"Chemin:\n{image.path}")
        
        self.desc_label.setText(f"Description:\n{image.description or 'Aucune'}")

        # ✅ Tags sur plusieurs lignes
        tags = image.keywords or []
        if tags:
            # Mettre chaque tag sur une ligne avec •
            tags_text = "\n".join(f"• {tag}" for tag in tags)
            self.tags_label.setText(f"Tags:\n{tags_text}")
        else:
            self.tags_label.setText("Tags: Aucun")

    def _clear(self):
        self.title.setText("Aucune image sélectionnée")

        # ✅ Nettoyer l'image
        self.image_label.clear()
        self.image_label.setText("Aucune image")
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background-color: #f9f9f9;
                color: #999;
            }
        """)

        self.path_label.clear()
        self.name_label.clear()
        self.desc_label.clear()
        self.tags_label.clear()

        self.empty.show()