import sys
import os

# Ajouter le chemin racine du projet au sys.path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ui.ImagePreview.ImagePreviewView import ImagePreviewView
from ui.ImagePreview.ImagePreviewModel import ImagePreviewModel
from common.ImageInfo import ImageInfo, ProcessingStatus
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Optional, Callable, List
from pathlib import Path

from common.ImageInfo import ImageInfo

class ImagePreviewController(QObject):
    """Contrôleur pour la prévisualisation d'images"""
    
    # Signaux personnalisés
    image_changed = pyqtSignal(ImageInfo)  # Émis quand l'image change
    image_loaded = pyqtSignal()  # Émis quand une image est chargée avec succès
    error_occurred = pyqtSignal(str)  # Émis en cas d'erreur
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = ImagePreviewView()
        self.model = ImagePreviewModel()
        self._connect_signals()
    
    def _connect_signals(self):
        """Connecte les signaux de la vue aux méthodes du contrôleur"""
        self.view.image_loaded.connect(self._on_image_loaded)
        self.view.error_occurred.connect(self._on_error_occurred)
    
    def _on_image_loaded(self):
        """Gère le chargement réussi d'une image"""
        self.image_loaded.emit()
        self.image_changed.emit(self.model.get_current_image())
    
    def _on_error_occurred(self, error_message: str):
        """Gère les erreurs de chargement"""
        self.error_occurred.emit(error_message)
    
    def set_image(self, image : ImageInfo) -> bool:
        """
        Définit l'image à prévisualiser.
        
        Args:
            image: Objet Image, ImageInfo ou chemin string de l'image à afficher
            
        Returns:
            bool: True si l'image a été définie avec succès
        """
        if isinstance(image, ImageInfo):
            # C'est un objet ImageInfo
            image_info = image
        else:
            return False
        
        success = self.model.set_image(image_info)
        
        if success:
            self.view.set_image_info(image_info)
        else:
            error = self.model.last_error
            self.error_occurred.emit(error)
                    
        return success
    
    def set_image_by_path(self, image_path: str) -> bool:
        """
        Définit une image par son chemin.
        
        Args:
            image_path: Chemin vers l'image
            
        Returns:
            bool: True si l'image a été chargée avec succès
        """
        success = self.model.set_image_by_path(image_path)
        
        if success:
            current_image = self.model.get_current_image()
            self.view.set_image_info(current_image)
        else:
            error = self.model.last_error
            self.error_occurred.emit(error)
        
        return success
    
    def get_current_image(self) -> Optional[ImageInfo]:
        """Retourne l'image actuellement affichée"""
        return self.model.get_current_image()
    
    def clear_preview(self):
        """Efface la prévisualisation actuelle"""
        self.model.clear_current_image()
        self.view.clear_preview()
    
    def refresh_preview(self):
        """Rafraîchit l'affichage de l'image actuelle"""
        current_image = self.model.get_current_image()
        if current_image:
            self.view.refresh_display()
    
    def toggle_auto_refresh(self, enabled: bool = None):
        """
        Active ou désactive le rafraîchissement automatique.
        
        Args:
            enabled: True pour activer, False pour désactiver, None pour inverser
        """
        current_settings = self.get_display_settings()
        current_enabled = current_settings.get("auto_refresh", False)
        
        if enabled is None:
            enabled = not current_enabled
        
        self.set_display_settings(auto_refresh=enabled)
    
    def is_image_valid(self, image_path: str) -> bool:
        """
        Vérifie si un chemin d'image est valide.
        
        Args:
            image_path: Chemin à vérifier
            
        Returns:
            bool: True si le chemin est valide
        """
        try:
            path = Path(image_path)
            return path.exists() and path.is_file() and path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}
        except Exception:
            return False
    
    def get_image_info_from_path(self, image_path: str) -> Optional[ImageInfo]:
        """
        Crée une ImageInfo depuis un chemin, en essayant de charger depuis le cache d'abord.
        
        Args:
            image_path: Chemin de l'image
            
        Returns:
            Optional[ImageInfo]: ImageInfo créée ou None si erreur
        """
        try:
            path = Path(image_path)
            
            # Essayer de charger depuis le cache d'abord
            cached_image = self.model.load_from_cache(path)
            if cached_image:
                return cached_image
            
            # Créer une nouvelle ImageInfo
            return ImageInfo(path)
            
        except Exception:
            return None
    
    def batch_load_images(self, image_paths: List[str], 
                         on_progress: Optional[Callable] = None,
                         on_complete: Optional[Callable] = None) -> List[ImageInfo]:
        """
        Charge plusieurs images en lot.
        
        Args:
            image_paths: Liste des chemins d'images
            on_progress: Callback de progression (index, total, image_info)
            on_complete: Callback de fin (loaded_images, failed_paths)
            
        Returns:
            List[ImageInfo]: Images chargées avec succès
        """
        loaded_images = []
        failed_paths = []
        
        for i, path in enumerate(image_paths):
            try:
                image_info = self.get_image_info_from_path(path)
                if image_info:
                    loaded_images.append(image_info)
                    
                    # Callback de progression
                    if on_progress:
                        on_progress(i + 1, len(image_paths), image_info)
                else:
                    failed_paths.append(path)
                    
            except Exception:
                failed_paths.append(path)
        
        # Callback de fin
        if on_complete:
            on_complete(loaded_images, failed_paths)
        
        return loaded_images


# Fonction utilitaire pour créer une instance complète
def create_image_preview() -> ImagePreviewController:
    """Crée une instance complète du contrôleur de prévisualisation"""
    return ImagePreviewController()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QLabel
    from PyQt6.QtCore import Qt
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Test ImagePreview")
            self.setMinimumSize(1200, 800)
            
            # Widget central
            central = QWidget()
            self.setCentralWidget(central)
            
            # Layout principal
            main_layout = QHBoxLayout(central)
            main_layout.setContentsMargins(20, 20, 20, 20)
            main_layout.setSpacing(20)
            
            # Panneau de gauche (contrôles)
            left_panel = QWidget()
            left_layout = QVBoxLayout(left_panel)
            left_panel.setMaximumWidth(300)
            
            # Titre
            title = QLabel("Test ImagePreview")
            title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            title.setStyleSheet("color: #495057; margin-bottom: 20px;")
            left_layout.addWidget(title)
            
            # Boutons de test
            self.load_btn = QPushButton("Charger une image")
            self.load_btn.clicked.connect(self.load_test_image)
            left_layout.addWidget(self.load_btn)
            
            self.clear_btn = QPushButton("Effacer")
            self.clear_btn.clicked.connect(self.clear_preview)
            left_layout.addWidget(self.clear_btn)
            
            self.refresh_btn = QPushButton("Rafraîchir")
            self.refresh_btn.clicked.connect(self.refresh_preview)
            left_layout.addWidget(self.refresh_btn)
            
            # Historique
            history_label = QLabel("Historique:")
            history_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            left_layout.addWidget(history_label)
            
            self.history_list = QListWidget()
            self.history_list.setMaximumHeight(200)
            self.history_list.itemDoubleClicked.connect(self.load_from_history)
            left_layout.addWidget(self.history_list)
            
            # Statistiques
            self.stats_label = QLabel("Statistiques:")
            self.stats_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            left_layout.addWidget(self.stats_label)
            
            self.stats_text = QLabel()
            self.stats_text.setWordWrap(True)
            self.stats_text.setStyleSheet("color: #6c757d; font-size: 11px;")
            left_layout.addWidget(self.stats_text)
            
            left_layout.addStretch()
            
            # Créer le contrôleur ImagePreview
            self.preview_controller = create_image_preview()
            
            # Connecter les signaux
            self.preview_controller.image_changed.connect(self.on_image_changed)
            self.preview_controller.error_occurred.connect(self.on_error)
            
            # Ajouter les widgets au layout principal
            main_layout.addWidget(left_panel)
            main_layout.addWidget(self.preview_controller.view, 1)
        
        def load_test_image(self):
            """Charge une image de test"""
            from PyQt6.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Sélectionner une image",
                "",
                "Images (*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.webp)"
            )
            
            if file_path:
                self.preview_controller.set_image_by_path(file_path)
        
        def clear_preview(self):
            """Efface la prévisualisation"""
            self.preview_controller.clear_preview()
        
        def refresh_preview(self):
            """Rafraîchit la prévisualisation"""
            self.preview_controller.refresh_preview()
        
        def load_from_history(self, item):
            """Charge une image depuis l'historique"""
            image_path = item.data(Qt.ItemDataRole.UserRole)
            self.preview_controller.load_from_history(image_path)
        
        def on_image_changed(self, image_info):
            """Gère le changement d'image"""
            print(f"Image changée: {image_info.name if image_info else 'Aucune'}")
        
        def on_error(self, error_message):
            """Gère les erreurs"""
            print(f"Erreur: {error_message}")
    
    # Lancer l'application
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    
    print("🚀 Test de ImagePreview")
    print("💡 Utilisez les boutons pour tester les fonctionnalités")
    
    sys.exit(app.exec())
