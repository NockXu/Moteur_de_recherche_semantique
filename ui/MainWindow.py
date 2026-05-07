import sys
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QDockWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from qt_material import apply_stylesheet

# Import des widgets (chemins relatifs à ui/)
from ui.ImportTool.ImportToolController import ImportToolController
from ui.ImageSearchedContainer.ImageSearchedContainerController import ImageSearchedContainerController
from ui.ImagePreview.ImagePreviewController import ImagePreviewController
from ui.ImageSearchedContainer.AutoResearch import AutoResearch
from ui.MenuBar import create_menu_bar

from common.Image_Classes.Image import Image
from common.Image_Classes.ImageRepository import ImageRepository

# Wrapper pour les controllers
from vision.ollama_wrapper import OllamaWrapper
# Base de données
from database.DbService import DbService

os.environ['QT_LOGGING_RULES'] = 'qt.gui.icc=false'

class MainWindow(QMainWindow):
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
    VISION_MODEL = "qwen2.5vl:7b"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Moteur de Recherche Sémantique")
        self.setMinimumSize(1200, 800)
        
        # Appliquer le thème d'abord
        app = QApplication.instance()
        if app:
            try:
                apply_stylesheet(app, theme='dark_lightgreen.xml')
            except Exception as e:
                print(f"Warning: Impossible d'appliquer le thème dark_lightgreen.xml: {e}")
                # Essayer un thème par défaut
                apply_stylesheet(app, theme='dark_teal.xml')
        
        # Afficher l'interface de chargement simple
        self._setup_loading_ui()
        self.show()
        
        # Initialiser les composants lourds en arrière-plan
        self._initialize_heavy_components()
        
        # Connecter les signaux
        self._connect_signals()
    
    def _setup_loading_ui(self):
        """Configure l'interface de chargement simple"""
        # Widget central obligatoire avec QMainWindow
        central = QWidget()
        self.setCentralWidget(central)
        
        # Layout principal pour le widget central
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Texte de chargement centré
        loading_label = QLabel("Chargement...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet("""
            color: #2c3e50; 
            font-size: 24px; 
            font-weight: bold;
            margin: 50px;
        """)
        
        main_layout.addWidget(loading_label)
    
    def _setup_basic_docks(self):
        """Configure les docks de base rapidement"""
        # Pas de docks pendant le chargement
        pass
    
    def _initialize_heavy_components(self):
        """Initialise les composants lourds"""
        # Initialise le wrapper avec la configuration
        self.wrapper = OllamaWrapper(base_url=self.OLLAMA_BASE_URL, timeout_s=500)
        
        # Créer les contrôleurs
        self._setup_controllers()
        
        # Créer la barre de menu
        self.menu_controller = create_menu_bar(self)
        self.setMenuBar(self.menu_controller.get_menu_bar())
        
        # Remplacer l'interface de base par l'interface complète
        self._setup_complete_ui()
    
    def _setup_complete_ui(self):
        """Remplace l'interface de base par l'interface complète"""
        # Remplacer le widget central par l'interface complète
        central = QWidget()
        self.setCentralWidget(central)
        
        # Layout principal pour le widget central
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Zone centrale : Conteneur d'images
        main_layout.addWidget(self.image_container_controller.view, 1)  # Stretch factor 1
        
        # Remplacer les docks
        self._replace_docks()
    
    def _replace_docks(self):
        """Remplace les docks temporaires par les vrais widgets"""
        # Remplacer le dock gauche
        if hasattr(self, 'import_dock'):
            self.removeDockWidget(self.import_dock)
        
        import_dock = QDockWidget("Import d'images")
        import_dock.setWidget(self.import_tool_controller.get_view())
        import_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        import_dock.setFixedWidth(280)
        import_dock.setMinimumWidth(250)
        import_dock.setMaximumWidth(320)
        
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, import_dock)
        self.import_dock = import_dock
        
        # Remplacer le dock droit
        if hasattr(self, 'preview_dock'):
            self.removeDockWidget(self.preview_dock)
        
        preview_dock = QDockWidget("Aperçu")
        preview_dock.setWidget(self.image_preview_controller.view)
        preview_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        preview_dock.hide()
        
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, preview_dock)
        self.preview_dock = preview_dock
    
    def _setup_controllers(self):
        """Initialise tous les contrôleurs"""
        # Import Tool (dans un dock) avec wrapper et modèle
        self.import_tool_controller = ImportToolController(self.wrapper, self.VISION_MODEL)
        
        # Conteneur d'images recherchées
        self.image_container_controller = ImageSearchedContainerController()
        
        # Preview d'image (dans un dock)
        self.image_preview_controller = ImagePreviewController()
    
    def _setup_ui(self):
        """Configure l'interface utilisateur"""
        # Widget central obligatoire avec QMainWindow
        central = QWidget()
        self.setCentralWidget(central)
        
        # Layout principal pour le widget central
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Zone centrale : Conteneur d'images
        main_layout.addWidget(self.image_container_controller.view, 1)  # Stretch factor 1
        
        # Créer les docks
        self.setup_docks()
    
    def setup_docks(self):
        """Configure les docks latéraux"""
        
        # Dock gauche : Import Tool
        self.import_dock = QDockWidget("Import d'images")
        self.import_dock.setWidget(self.import_tool_controller.get_view())
        self.import_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        # Définir une taille fixe pour le dock Import Tool
        self.import_dock.setFixedWidth(280)  # Largeur fixe de 280px
        self.import_dock.setMinimumWidth(250)  # Largeur minimale
        self.import_dock.setMaximumWidth(320)  # Largeur maximale
        
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, import_dock)
        
        # Dock droit : Preview d'image
        self.preview_dock = QDockWidget("Aperçu")
        self.preview_dock.setWidget(self.image_preview_controller.view)
        self.preview_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, preview_dock)
        
        # Masquer le dock de preview par défaut (s'ouvrira au clic sur une image)
        self.preview_dock.hide()
    
    def _connect_signals(self):
        """Connecte les signaux entre les widgets"""
        # Quand une image est cliquée dans le conteneur
        self.image_container_controller.view.image_clicked.connect(self._on_image_clicked)
        self.import_tool_controller.view.image_clicked.connect(self._on_image_clicked)
        
        # Connexion du widget de connexion Ollama
        connection_widget = self.import_tool_controller.view.connection_verificator
        connection_widget.connection_status_changed.connect(self._on_connection_status_changed)
        
        # Connexion des signaux du menu
        self.menu_controller.file_quit_requested.connect(self.close)
        self.menu_controller.file_import_requested.connect(self._on_menu_import)
        self.menu_controller.file_export_requested.connect(self._on_menu_export)
    
    def _on_image_clicked(self, img: Image):
        """Gère le clic sur une image"""
        print(f"DEBUG: MainWindow reçu clic sur {os.path.basename(img.path)}")
        
        # Afficher l'image dans le preview
        self.image_preview_controller.set_image(img)
        
        # Afficher le dock de preview s'il est caché
        if self.preview_dock.isHidden():
            self.preview_dock.show()
        
        print(f"Image sélectionnée: {os.path.basename(img.path)}")
    
    def _on_connection_status_changed(self, state, version: str, error_message: str):
        """Gère les changements de statut de connexion Ollama"""
        from ui.ImportTool.widget.ConnectionVerificator.ConnectionVerificatorModel import State
        
        if state == State.CONNECTED:
            print(f"Ollama connecté - Version: {version}")
        elif state == State.ERROR:
            print(f"Erreur Ollama: {error_message}")
        else:
            print(f"Ollama: Non connecté")
    
    def _on_menu_import(self):
        """Gère l'import depuis le menu"""
        # Le menu gère déjà l'import via handle_import()
        # On peut rafraîchir l'affichage si nécessaire
        if hasattr(self.import_tool_controller, 'view'):
            self.import_tool_controller.view._refresh_image_display()
    
    def _on_menu_export(self):
        """Gère l'export depuis le menu"""
        # Le menu gère déjà l'export via handle_export()
        pass
    
    def cleanup(self):
        """Nettoie les ressources avant la fermeture"""
        try:
            print("Nettoyage de MainWindow...")
            
            # Arrêter proprement tous les contrôleurs avec threads
            if hasattr(self, 'import_tool_controller'):
                print("Arrêt de ImportTool...")
                self.import_tool_controller.cleanup()
                
                # Attendre que tous les threads se terminent
                import time
                time.sleep(1)  # Donner du temps aux threads de se terminer
            
            # Arrêter le wrapper Ollama
            if hasattr(self, 'wrapper'):
                print("Fermeture du wrapper Ollama...")
                # Le wrapper n'a pas de méthode cleanup, mais on peut s'assurer qu'il est bien libéré
            
            # Forcer la fermeture de tous les threads PyQt6
            from PyQt6.QtCore import QThreadPool
            QThreadPool.globalInstance().waitForDone(3000)  # Attendre 3 secondes max
            
            print("Nettoyage de MainWindow terminé")
            
        except Exception as e:
            print(f"Erreur lors du nettoyage de MainWindow: {e}")
            import traceback
            traceback.print_exc()
    
    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre"""
        try:
            self.cleanup()
            event.accept()
        except Exception as e:
            print(f"Erreur lors de la fermeture: {e}")
            event.accept()  # Forcer la fermeture même en cas d'erreur


if __name__ == "__main__":
    import signal
    
    app = QApplication(sys.argv)
    
    # Gérer Ctrl+C proprement
    def signal_handler(signum, frame):
        print("\nInterruption détectée, fermeture propre...")
        if 'window' in locals():
            # D'abord nettoyer, puis fermer
            window.cleanup()
            window.close()
        else:
            # Si la fenêtre n'existe pas encore, juste quitter
            app.quit()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Créer et afficher la fenêtre principale
    window = MainWindow()
    window.show()
    
    print("Application démarrée")
    print("Utilisez Ctrl+C pour fermer proprement")
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nAu revoir !")