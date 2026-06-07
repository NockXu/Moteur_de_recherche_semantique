import sys
import os
from dotenv import load_dotenv
from numpy import save

from .ImageAnalysator.ImageAnalysator import ImageAnalysator

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QDockWidget, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal

from qt_material import apply_stylesheet
# Import des widgets (chemins relatifs à ui/)
from ui.ImportTool.ImportToolController import ImportToolController
from ui.ImageSearchedContainer.ImageSearchedContainerController import ImageSearchedContainerController
from ui.ImagePreview.ImagePreviewController import ImagePreviewController
from ui.MenuBar import create_menu_bar
from ui import load_config, save_in_config
from ui.HistoryTree.HistoryTreeController import HistoryTreeController

from common.Image_Classes.Image import Image
from common.History_Classes import HistoryRepository, history, app

# Wrapper pour les controllers
from vision.ollama_wrapper import OllamaWrapper
# Base de données
from database.DbService import DbService

os.environ['QT_LOGGING_RULES'] = 'qt.gui.icc=false'

class MainWindow(QMainWindow):
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
    VISION_MODEL = "qwen2.5vl:7b"
    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Moteur de Recherche Sémantique")
        self.setMinimumSize(1200, 800)
        
        # Appliquer le thème d'abord
        app = QApplication.instance()

        # Charger la configuration UI
        self.config = load_config()
        self.current_theme = self.config.get("theme", "dark_teal.xml")

        apply_stylesheet(app, theme=self.current_theme)

        # Initialiser les composants lourds en arrière-plan
        self._initialize_heavy_components()
        
        # Connecter les signaux
        self._connect_signals()

        self.showMaximized()

        self._load_all()

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
        
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(True)

        self.tabs.addTab(
            self.image_container_controller.view,
            "Search Results"
        )

        self.tabs.addTab(
            self.history_tree_controller.view,
            "History Tree"
        )

        main_layout.addWidget(self.tabs, 1)
        
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
        self.import_tool_controller = ImportToolController(self.wrapper, self.VISION_MODEL, self.theme_changed)
        
        # Conteneur d'images recherchées (dans un onglet)
        self.image_container_controller = ImageSearchedContainerController(theme_changed=self.theme_changed)
        
        # Preview d'image (dans un dock)
        self.image_preview_controller = ImagePreviewController(theme_changed=self.theme_changed)
        
        # History Tree (dans un onglet)
        self.history_tree_controller = HistoryTreeController(theme_changed=self.theme_changed)

    def _load_all(self):
        """Charge tous les éléments de l'interface"""
        history.load()
        self.import_tool_controller.load()
        if self.image_preview_controller.load():
            self.preview_dock.show()
        self.image_container_controller.load()
        self.history_tree_controller.load()
    
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
        self.menu_controller.toggle_import_tool.connect(self._on_toggle_import_tool)
        self.menu_controller.theme_changed.connect(self._on_theme_changed)

        # Connection des signaux de la preview
        self.image_preview_controller.view.image_analysator.image_view.results_displayed.connect(self.image_container_controller._on_results_displayed)
        self.image_preview_controller.view.image_analysator.sam3_widget.results_cleared.connect(self.image_container_controller._on_results_cleared)
        self.image_preview_controller.view.image_analysator.sam3_widget.multi_prompts_send.connect(self.image_container_controller._on_multi_send)

    def _on_theme_changed(self, theme: str):
        """Gère le changement de thème"""
        print(f"Changement de thème: {theme}")

        # Émettre le signal de changement de thème
        self.theme_changed.emit(theme)

        # Sauvegarder la configuration
        save_in_config("theme", theme)
    
    def _on_image_clicked(self, img: Image):
        """Gère le clic sur une image"""
        
        # Afficher l'image dans le preview
        self.image_preview_controller.set_image(img)
        
        # Afficher le dock de preview s'il est caché
        if self.preview_dock.isHidden():
            self.preview_dock.show()
    
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
    
    def _on_toggle_import_tool(self):
        if self.import_dock.isHidden():
            self.import_dock.show()
            self.import_dock.raise_()
            self.import_dock.activateWindow()
        else:
            self.import_dock.hide()
    
    def cleanup(self):
        """Nettoie les ressources avant la fermeture"""
        try:
            print("Nettoyage de MainWindow...")
            
            # Arrêter proprement tous les contrôleurs avec threads
            if hasattr(self, 'import_tool_controller'):
                print("Arrêt de ImportTool...")
                self.import_tool_controller.cleanup()

            if hasattr(self, 'image_container_controller'):
                print("Arret de ImageSearchedContainer...")
                self.image_container_controller.cleanup()
                
                # Attendre que tous les threads se terminent
                import time
                time.sleep(1)  # Donner du temps aux threads de se terminer
            
            # Arrêter le wrapper Ollama
            if hasattr(self, 'wrapper'):
                print("Fermeture du wrapper Ollama...")
                # Le wrapper n'a pas de méthode cleanup, mais on peut s'assurer qu'il est bien libéré
            
            # Forcer la fermeture de tous les threads PyQt6
            from PyQt6.QtCore import QThreadPool
            pool = QThreadPool.globalInstance()

            pool.clear()        # stop new tasks
            pool.waitForDone()  # attend fin des threads

            DbService().faiss.reset()
            
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
    
    print("Application démarrée")
    print("Utilisez Ctrl+C pour fermer proprement")
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nAu revoir !")
