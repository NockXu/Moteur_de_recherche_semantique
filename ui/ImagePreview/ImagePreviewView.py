import sys
import os

# Ajouter le chemin racine du projet au sys.path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QFrame, QSizePolicy, QApplication)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QPainter, QColor, QPalette
from pathlib import Path
from common.ImageInfo import ImageInfo
from typing import Optional

from common.ImageInfo import ImageInfo

class ImagePreviewView(QWidget):
    """Vue principale pour la prévisualisation d'image avec métadonnées"""
    
    # Signaux
    image_loaded = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_info: Optional[ImageInfo] = None
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Partie supérieure (50% pour l'image)
        self.image_container = self._create_image_container()
        layout.addWidget(self.image_container, 1)  # Stretch factor 1 pour 50%
        
        # Séparateur visuel
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #dee2e6; max-height: 1px;")
        layout.addWidget(separator)
        
        # Partie inférieure (50% pour les informations)
        self.info_container = self._create_info_container()
        layout.addWidget(self.info_container, 1)  # Stretch factor 1 pour 50%
    
    def _create_image_container(self) -> QWidget:
        """Crée le conteneur pour l'affichage de l'image"""
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: none;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Label pour l'image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
                padding: 20px;
                color: #6c757d;
                font-size: 14px;
            }
        """)
        self.image_label.setText("📷 Aucune image sélectionnée")
        self.image_label.setMinimumSize(200, 200)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout.addWidget(self.image_label)
        
        return container
    
    def _create_info_container(self) -> QWidget:
        """Crée le conteneur pour les informations de l'image"""
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: white;
                border: none;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Zone scrollable pour les informations
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
            QScrollBar:vertical {
                background-color: #f8f9fa;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #adb5bd;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #6c757d;
            }
        """)
        
        # Widget contenu pour les informations
        self.info_widget = QWidget()
        self.info_layout = QVBoxLayout(self.info_widget)
        self.info_layout.setContentsMargins(15, 15, 15, 15)
        self.info_layout.setSpacing(20)
        
        # Sections d'informations
        self._create_info_sections()
        
        self.scroll_area.setWidget(self.info_widget)
        layout.addWidget(self.scroll_area)
        
        return container
    
    def _create_info_sections(self):
        """Crée les différentes sections d'informations"""
        # Section Nom du fichier
        self.filename_section = self._create_section("Nom du fichier", "")
        self.info_layout.addWidget(self.filename_section)
        
        # Section Description
        self.description_section = self._create_section("Description", "Aucune description")
        self.info_layout.addWidget(self.description_section)
        
        # Section Mots-clés
        self.keywords_section = self._create_section("Mots-clés", "Aucun mot-clé")
        self.info_layout.addWidget(self.keywords_section)
        
        # Section Score
        self.score_section = self._create_section("Score", "N/A")
        self.info_layout.addWidget(self.score_section)
        
        # Section Informations techniques
        self.technical_section = self._create_section("Informations techniques", "")
        self.info_layout.addWidget(self.technical_section)
        
        # Section Traitement
        self.processing_section = self._create_section("Traitement", "Non traité")
        self.info_layout.addWidget(self.processing_section)
        
        # Espace extensible pour aligner le contenu en haut
        self.info_layout.addStretch()
    
    def _create_section(self, title: str, content: str) -> QFrame:
        """Crée une section d'information avec titre et contenu"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)
        
        # Titre
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #495057;")
        layout.addWidget(title_label)
        
        # Contenu
        content_label = QLabel(content)
        content_label.setFont(QFont("Segoe UI", 10))
        content_label.setStyleSheet("color: #6c757d;")
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(content_label)
        
        # Stocker les labels pour mise à jour
        frame.title_label = title_label
        frame.content_label = content_label
        
        return frame
    
    def _setup_style(self):
        """Configure le style général du widget"""
        self.setStyleSheet("""
            ImagePreviewView {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 12px;
            }
        """)
    
    def set_image_info(self, image_info: ImageInfo):
        """Définit l'image à afficher et met à jour les informations"""
        self.current_image_info = image_info
        
        if image_info is None:
            self._clear_display()
            return

        # Charger et afficher l'image
        success = self._load_image(image_info.path)
        
        if success:
            # Mettre à jour les informations
            self._update_info_display(image_info)
            
            # Émettre le signal
            self.image_loaded.emit()
        else:
            self._show_error("Erreur de chargement de l'image")
    
    def _load_image(self, image_path: Path) -> bool:
        """Charge et affiche l'image"""
        if not image_path.exists():
            return False
        
        # Charger l'image
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            return False
        
        # Calculer la taille maximale disponible
        available_size = self.image_label.size()
        if not available_size.isValid() or available_size.width() < 50 or available_size.height() < 50:
            available_size = QSize(400, 400)  # Taille par défaut
        
        # Redimensionner en gardant le ratio
        scaled_pixmap = pixmap.scaled(
                available_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        
        # Mettre à jour le label
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        return True
    
    def _update_info_display(self, image_info: ImageInfo):
        """Met à jour l'affichage des informations"""
        # Nom du fichier
        self.filename_section.content_label.setText(image_info.stem)
        
        # Description
        description = image_info.description
        self.description_section.content_label.setText(description)
        
        # Mots-clés
        if image_info.keywords:
            keywords_text = ", ".join(image_info.keywords)
            self.keywords_section.content_label.setText(keywords_text)
        else:
            self.keywords_section.content_label.setText("Aucun mot-clé")
        
        # Score
        if image_info.score > 0:
            score_text = f"{image_info.score:.3f}"
            self.score_section.content_label.setText(score_text)
        else:
            self.score_section.content_label.setText("N/A")
        
        # Informations techniques
        file_info = image_info.get_file_info()
        tech_info = f"""Taille: {file_info['size_mb']} MB
Format: {file_info['suffix'].upper()}
Chemin: {file_info['path']}"""
        self.technical_section.content_label.setText(tech_info)
        
        # Informations de traitement
        status_emoji = {
            "not_started": "-",
            "in_progress": "...",
            "completed": "OK",
            "error": "ERR"
        }
        
        status_text = status_emoji.get(image_info.status.value, "?")
        if image_info.is_processed and image_info.processing_duration:
            status_text += f" ({image_info.processing_duration:.1f}s)"
        
        processing_info = f"""Statut: {status_text}
ID: {image_info.id}"""
        
        if image_info.error_message:
            processing_info += f"\nErreur: {image_info.error_message}"
        
        self.processing_section.content_label.setText(processing_info)
    
    def _clear_display(self):
        """Efface l'affichage"""
        # Réinitialiser l'image
        self.image_label.clear()
        self.image_label.setText("📷 Aucune image sélectionnée")
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
                padding: 20px;
                color: #6c757d;
                font-size: 14px;
            }
        """)
        
        # Réinitialiser les informations
        self.filename_section.content_label.setText("")
        self.description_section.content_label.setText("Aucune description")
        self.keywords_section.content_label.setText("Aucun mot-clé")
        self.score_section.content_label.setText("N/A")
        self.technical_section.content_label.setText("")
        self.processing_section.content_label.setText("Non traité")
        
        self.current_image_info = None
    
    def _show_error(self, error_message: str):
        """Affiche un message d'erreur"""
        self.image_label.clear()
        self.image_label.setText(f"{error_message}")
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #fff5f5;
                border: 2px solid #f8d7da;
                border-radius: 8px;
                padding: 20px;
                color: #dc3545;
                font-size: 14px;
            }
        """)
    
    def get_current_image_info(self) -> Optional[ImageInfo]:
        """Retourne l'image actuellement affichée"""
        return self.current_image_info
    
    def clear_preview(self):
        """Efface la prévisualisation"""
        self._clear_display()
    
    def refresh_display(self):
        """Rafraîchit l'affichage de l'image actuelle"""
        if self.current_image_info:
            self.set_image_info(self.current_image_info)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Créer une ImageInfo de test
    from common.ImageInfo import ImageInfo, ProcessingStatus
    from pathlib import Path
    
    # Test avec une image existante si disponible
    test_image_path = Path("dataset/test/weezer.png") if Path("dataset/test/weezer.png").exists() else None
    
    if test_image_path:
        test_image = ImageInfo(
            path=test_image_path,
            score=0.85,
            status=ProcessingStatus.COMPLETED,
            description="Ceci est une image de test représentant le groupe Weezer avec une qualité visuelle excellente et des couleurs vives.",
            keywords=["weezer", "rock", "groupe", "musique", "test"],
            embedding=[0.1, 0.2, 0.3] * 100  # Exemple
        )
    else:
        test_image = None
    
    # Créer et afficher la vue
    window = ImagePreviewView()
    window.setWindowTitle("Image Preview - Test")
    window.setMinimumSize(600, 800)
    window.set_image_info(test_image)
    window.show()
    
    sys.exit(app.exec())
