import sys
import os

# Ajouter le chemin racine du projet au sys.path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Dict, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

from ui.ImageSearchedContainer.ImageSearchedContainerView import ImageSearchedContainerView
from ui.ImageSearchedContainer.ImageSearchedContainerModel import ImageSearchedContainerModel
from common.ImageInfo import ImageInfo


class ImageSearchedContainerController:
    """Contrôleur pour gérer le conteneur d'images recherchées"""
    
    def __init__(self, max_images_per_page: int = 12, thumbnail_size: int = 150):
        self.view = ImageSearchedContainerView()
        self.model = ImageSearchedContainerModel()
        self.max_images_per_page = max_images_per_page
        self.thumbnail_size = thumbnail_size
        
        # Configurer le modèle
        self.model.set_max_images_per_page(max_images_per_page)
        
        # Callbacks personnalisés
        self.image_click_callback: Optional[Callable[[ImageInfo], str]] = None
        self.page_change_callback: Optional[Callable[[int, int], None]] = None
        
        self._connect_signals()
        
    def _connect_signals(self):
        """Connecte les signaux de la vue"""
        self.view.image_clicked.connect(self._on_image_clicked)
        self.view.page_changed.connect(self._on_page_changed)
        self.view.reload_requested.connect(self.reload_images)
        
    def _on_image_clicked(self, image_path: str):
        """Gère le clic sur une image"""
        # Récupérer l'objet ImageInfo correspondant
        image_info = self.model.get_image_by_path(image_path)
        
        # Appeler le callback personnalisé si défini
        if self.image_click_callback:
            if image_info:
                # Renvoyer l'objet Image complet
                self.image_click_callback(image_info)
            else:
                # Fallback: renvoyer le chemin si l'image n'est pas trouvée
                self.image_click_callback(image_path)
                
    def _on_page_changed(self, page: int):
        """Gère le changement de page"""
        # Mettre à jour le modèle
        self.model.set_current_page(page)
        
        # Mettre à jour la vue
        self._update_view()
        
        # Appeler le callback personnalisé si défini
        if self.page_change_callback:
            self.page_change_callback(page, self.model.total_pages)
                
    def _update_view(self):
        """Met à jour la vue avec les données du modèle"""
        # Obtenir les images de la page actuelle
        page_image_infos = self.model.get_current_page_images()
        
        # Mettre à jour la vue avec la nouvelle API
        self.view.display_images(
            image_data=page_image_infos,
            total_count=self.model.get_filtered_count(),
            current_page=self.model.current_page,
            total_pages=self.model.total_pages
        )
        
    def add_image(self, image: ImageInfo, score: float = 0.0):
        """Ajoute une image au conteneur"""
        self.model.add_image(image)
        self._update_view()
            
    def add_images(self, images: List[ImageInfo], scores: List[float] = None):
        """Ajoute plusieurs images au conteneur
        images: liste d'objets Image
        scores: liste optionnelle de scores correspondants
        """
        self.model.add_images(images)
        self._update_view()
            
    def set_images(self, images: List[ImageInfo]):
        """Définit la liste complète des images"""
        self.model.set_images(images)
        self._update_view()
            
    def remove_image(self, image: ImageInfo) -> bool:
        """Retire une image du conteneur"""
        success = self.model.remove_image(image)
        if success:
            self._update_view()
        return success
            
    def clear_images(self):
        """Efface toutes les images"""
        self.model.clear()
        self._update_view()
            
    def set_max_images_per_page(self, max_images: int):
        """Définit le nombre maximum d'images par page"""
        self.max_images_per_page = max_images
        self.model.set_max_images_per_page(max_images)
        self._update_view()
            
            
    def set_thumbnail_size(self, size: int):
        """Définit la taille des miniatures"""
        self.thumbnail_size = size
        self._update_view()
            
    def set_sorting(self, sort_by: str, sort_order: str = "desc"):
        """Définit le tri des images"""
        self.model.set_sorting(sort_by, sort_order)
        self._update_view()
            
    def set_filter_tags(self, tags: List[str]):
        """Définit les tags de filtre"""
        self.model.set_filter_tags(tags)
        self._update_view()
            
    def add_filter_tag(self, tag: str):
        """Ajoute un tag de filtre"""
        self.model.add_filter_tag(tag)
        self._update_view()
            
    def remove_filter_tag(self, tag: str):
        """Retire un tag de filtre"""
        self.model.remove_filter_tag(tag)
        self._update_view()
            
    def clear_filters(self):
        """Efface tous les filtres"""
        self.model.clear_filters()
        self._update_view()
            
    def go_to_page(self, page: int):
        """Va à une page spécifique"""
        if 1 <= page <= self.model.total_pages:
            self.model.set_current_page(page)
            self._update_view()
            
    def next_page(self):
        """Va à la page suivante"""
        current = self.model.current_page
        if current < self.model.total_pages:
            self.go_to_page(current + 1)
            
    def previous_page(self):
        """Va à la page précédente"""
        current = self.model.current_page
        if current > 1:
            self.go_to_page(current - 1)
            
    def get_current_page(self) -> int:
        """Retourne la page actuelle"""
        return self.model.current_page
        
    def get_total_pages(self) -> int:
        """Retourne le nombre total de pages"""
        return self.model.total_pages
        
    def get_image_count(self) -> int:
        """Retourne le nombre total d'images"""
        return self.model.get_image_count()
        
    def get_filtered_count(self) -> int:
        """Retourne le nombre d'images filtrées"""
        return self.model.get_filtered_count()
        
    def get_statistics(self) -> Dict:
        """Retourne des statistiques sur les images"""
        return self.model.get_statistics()
        
    def get_all_tags(self) -> List[str]:
        """Retourne tous les tags uniques"""
        return self.model.get_all_tags()
        
    def get_image_info(self, path: str) -> Optional[ImageInfo]:
        """Retourne les informations d'une image"""
        return self.model.get_image_by_path(path)
        
    def set_image_click_callback(self, callback: Callable[[ImageInfo], None]):
        """Définit un callback personnalisé pour le clic sur une image"""
        self.image_click_callback = callback
        
    def set_page_change_callback(self, callback: Callable[[int, int], None]):
        """Définit un callback personnalisé pour le changement de page"""
        self.page_change_callback = callback
        
    def set_enabled(self, enabled: bool):
        """Active ou désactive le conteneur"""
        self.view.setEnabled(enabled)
        
    def is_enabled(self) -> bool:
        """Vérifie si le conteneur est activé"""
        return self.view.isEnabled()
    
    def reload_images(self):
        """Recharge toutes les images depuis le stockage en utilisant autoResearchDataset"""
        # Importer le chargeur de dataset
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from AutoResearch import AutoResearch
            
        # Créer le chargeur et charger les images
        loader = AutoResearch()
        images = loader.find()
        
        if images:
            print(f"Rechargement de {len(images)} images depuis le dossier storage")
            # Les images devraient déjà avoir des paths valides grâce à la classe Image
            self.set_images(images)
            print("Images rechargées avec succès")
        else:
            print("AVERTISSEMENT: Aucune image trouvée dans le dossier storage")


# Test du contrôleur
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QLabel, QLineEdit
    from PyQt6.QtCore import Qt
    
    class TestControllerWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Test Controller ImageSearchedContainer")
            self.setGeometry(100, 100, 1000, 700)
            
            # Widget central
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            layout = QVBoxLayout()
            central_widget.setLayout(layout)
            
            # Contrôles de test
            controls_layout = QHBoxLayout()
            
            # Input pour ajouter des images
            self.path_input = QLineEdit()
            self.path_input.setPlaceholderText("Chemin de l'image...")
            controls_layout.addWidget(QLabel("Chemin:"))
            controls_layout.addWidget(self.path_input)
            
            # Input pour le titre
            self.title_input = QLineEdit()
            self.title_input.setPlaceholderText("Titre...")
            controls_layout.addWidget(QLabel("Titre:"))
            controls_layout.addWidget(self.title_input)
            
            self.clear_button = QPushButton("Tout effacer")
            self.clear_button.clicked.connect(self.clear_images)
            controls_layout.addWidget(self.clear_button)
            
            # Configuration
            self.max_input = QLineEdit("12")
            self.max_input.setFixedWidth(50)
            controls_layout.addWidget(QLabel("Max/page:"))
            controls_layout.addWidget(self.max_input)
            
            self.size_input = QLineEdit("150")
            self.size_input.setFixedWidth(50)
            controls_layout.addWidget(QLabel("Taille:"))
            controls_layout.addWidget(self.size_input)
            
            self.config_button = QPushButton("Appliquer")
            self.config_button.clicked.connect(self.apply_config)
            controls_layout.addWidget(self.config_button)
            
            controls_layout.addStretch()
            
            layout.addLayout(controls_layout)
            
            # Label de statut
            self.status_label = QLabel("Prêt à tester...")
            layout.addWidget(self.status_label)
            
            # Créer le contrôleur du conteneur d'images
            self.image_controller = ImageSearchedContainerController()
            
            # Connecter les callbacks
            self.image_controller.set_image_click_callback(self.on_image_selected)
            self.image_controller.set_page_change_callback(self.on_page_change)
            
            # Ajouter la vue
            layout.addWidget(self.image_controller.view)
            
        def clear_images(self):
            """Efface toutes les images"""
            self.image_controller.clear_images()
            
        def apply_config(self):
            """Applique la configuration"""
            try:
                max_images = int(self.max_input.text())
                size = int(self.size_input.text())
                self.image_controller.set_max_images_per_page(max_images)
                self.image_controller.set_thumbnail_size(size)
                self.status_label.setText(f"Configuration appliquée: {max_images} images/page, taille {size}px")
            except ValueError:
                self.status_label.setText("Valeurs invalides")
                
        def on_image_selected(self, image):
            """Gère la sélection d'une image"""
            self.status_label.setText(f"Image sélectionnée: {image.name} ({image.path})")
            
        def on_page_change(self, current, total):
            """Gère le changement de page"""
            self.status_label.setText(f"Page {current}/{total}")
    
    # Lancer l'application
    app = QApplication(sys.argv)
    window = TestControllerWindow()
    window.show()
    
    print("Test du contrôleur ImageSearchedContainer")
    print("Ajoutez des images avec le formulaire ou utilisez les images de test")
    print("Cliquez sur les images pour les sélectionner")
    print("Testez la pagination avec les boutons")
    
    sys.exit(app.exec())
