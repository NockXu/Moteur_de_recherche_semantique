import sys
import os
from dotenv import load_dotenv
from numpy import save

from .ImageAnalysator.ImageAnalysator import ImageAnalysator

# Load environment variables from the .env file
load_dotenv()

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QDockWidget, QTabWidget,
    QSplashScreen
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

from qt_material import apply_stylesheet
# Widget imports (relative paths to ui/)
from ui.ImportTool.ImportToolController import ImportToolController
from ui.ImageSearchedContainer.ImageSearchedContainerController import ImageSearchedContainerController
from ui.ImagePreview.ImagePreviewController import ImagePreviewController
from ui.MenuBar import create_menu_bar
from ui.HistoryTree.HistoryTreeController import HistoryTreeController

from ui import load_config, load_from_config, save_in_config
from ui.utils.Timer import Timer

from common.Image_Classes.Image import Image
from common.History_Classes import HistoryRepository, history, app

# Controller wrappers
from vision.ollama_wrapper import OllamaWrapper
# Database service
from database.DbService import DbService

from ui.utils.i18n import tr, extract_translations, init_translations

from typing import Dict, Optional

os.environ['QT_LOGGING_RULES'] = 'qt.gui.icc=false'

class MainWindow(QMainWindow):
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
    VISION_MODEL = "qwen2.5vl:7b"
    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        
        self._setup_language()
        
        self.setWindowTitle(tr("Moteur de Recherche Sémantique"))
        self.setMinimumSize(1200, 800)
        
        app = QApplication.instance()

        # Load UI configuration and theme properties
        self.config = load_config()
        self.current_theme = self.config.get("theme", "dark_teal.xml")

        # Apply style sheet to the global application instance
        apply_stylesheet(app, theme=self.current_theme)
        
        self.showMaximized()
        
        # Render the splash loading screen
        self._show_loading_screen()
        
        # Synchronously initialize background resources in a stable sequence
        self._initialize_heavy_components()

        QTimer.singleShot(0, self._load_all)
        
        # Extract source dictionary strings in the background
        extract_translations(project_root=".", language_list=["fr", "en"])

    def _setup_language(self):
        """Initialise les traductions"""
        translations_config : dict[str, str] = load_from_config("translations")
        if not translations_config:
            current_language : str | None = None
            return
        
        current_language : str = translations_config.get("current_language", "fr")

        init_translations(current_language)
        
        # 1. Main Window
        self.setWindowTitle(tr("Moteur de Recherche Sémantique"))

        # 2. Tabs
        if hasattr(self, "tabs"):
            self.tabs.setTabText(0, tr("Search Results"))
            self.tabs.setTabText(1, tr("History Tree"))

        # 3. Docks
        if hasattr(self, "import_dock"):
            self.import_dock.setWindowTitle(tr("Import d'images"))

        if hasattr(self, "preview_dock"):
            self.preview_dock.setWindowTitle(tr("Aperçu"))
        
        # 4. Widgets
        if hasattr(self, 'image_preview_controller'):
            self.image_preview_controller.view._on_language_changed()
        if hasattr(self, 'history_tree_controller'):
            self.history_tree_controller.view._on_language_changed()
        if hasattr(self, 'image_container_controller'):
            self.image_container_controller.view._on_language_changed()
            self.image_container_controller._sam3_progress_window._on_language_changed()
        if hasattr(self, 'import_tool_controller'):
            self.import_tool_controller.view._on_language_changed()
            self.import_tool_controller.view.connection_verificator.view._on_language_changed()
        if hasattr(self, 'menu_controller'):
            self.menu_controller._on_language_changed()

    def _initialize_heavy_components(self):
        """Initialise les composants lourds"""
        # Initialize the wrapper with configuration
        self.wrapper = OllamaWrapper(base_url=self.OLLAMA_BASE_URL, timeout_s=500)
        
        # Create controllers
        QTimer.singleShot(0, self._setup_controllers)
        
        # Replace base interface with full interface
        QTimer.singleShot(0, self._setup_complete_ui)
        
    def _show_loading_screen(self):
        pixmap = QPixmap(500, 300)
        pixmap.fill(Qt.GlobalColor.white)

        self.splash = QSplashScreen(pixmap)
        self.splash.showMessage(
            tr("Chargement des composants..."),
            Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.black
        )

        self.splash.show()

        # Force immediate display
        QApplication.processEvents()
    
    def _setup_complete_ui(self):
        """Remplace l'interface de base par l'interface complète"""
        # Replace central widget with full interface
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout for the central widget
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(True)

        self.tabs.addTab(
            self.image_container_controller.view,
            tr("Search Results")
        )

        self.tabs.addTab(
            self.history_tree_controller.view,
            tr("History Tree")
        )

        main_layout.addWidget(self.tabs, 1)
        
        # Replace docks
        self._replace_docks()
    
    def _replace_docks(self):
        """Remplace les docks temporaires par les vrais widgets"""
        # Replace left dock
        if hasattr(self, 'import_dock'):
            self.removeDockWidget(self.import_dock)
        
        import_dock = QDockWidget(tr("Import d'images"))
        import_dock.setWidget(self.import_tool_controller.get_view())
        import_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        import_dock.setFixedWidth(280)
        import_dock.setMinimumWidth(250)
        import_dock.setMaximumWidth(320)
        
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, import_dock)
        self.import_dock = import_dock
        
        # Replace right dock
        if hasattr(self, 'preview_dock'):
            self.removeDockWidget(self.preview_dock)
        
        preview_dock = QDockWidget(tr("Aperçu"))
        preview_dock.setWidget(self.image_preview_controller.view)
        preview_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        preview_dock.hide()
        
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, preview_dock)
        self.preview_dock = preview_dock
    
    def _setup_controllers(self):
        """Initialise tous les contrôleurs"""
        # Import Tool (in a dock) with wrapper and model
        self.import_tool_controller = ImportToolController(self.wrapper, self.VISION_MODEL, self.theme_changed)
        
        # Searched image container (in a tab)
        self.image_container_controller = ImageSearchedContainerController(theme_changed=self.theme_changed)
        
        # Image Preview (in a dock)
        self.image_preview_controller = ImagePreviewController(theme_changed=self.theme_changed)
        
        # History Tree (in a tab)
        self.history_tree_controller = HistoryTreeController(theme_changed=self.theme_changed)
        
        # Create the menu bar
        self.menu_controller = create_menu_bar(self)
        self.setMenuBar(self.menu_controller.get_menu_bar())

        self._connect_signals()
        
        self.splash.finish(self)

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
        # When an image is clicked in the container
        self.image_container_controller.view.image_clicked.connect(self._on_image_clicked)
        self.import_tool_controller.view.image_clicked.connect(self._on_image_clicked)
        
        # Connect Ollama connection widget
        connection_widget = self.import_tool_controller.view.connection_verificator
        connection_widget.connection_status_changed.connect(self._on_connection_status_changed)
        
        # Connect menu signals
        self.menu_controller.file_quit_requested.connect(self.close)
        self.menu_controller.file_import_requested.connect(self._on_menu_import)
        self.menu_controller.file_export_requested.connect(self._on_menu_export)
        self.menu_controller.toggle_import_tool.connect(self._on_toggle_import_tool)
        self.menu_controller.theme_changed.connect(self._on_theme_changed)
        self.menu_controller.language_changed.connect(self._setup_language)

        # Connect preview signals
        self.image_preview_controller.view.image_analysator.image_view.results_displayed.connect(self.image_container_controller._on_results_displayed)
        self.image_preview_controller.view.image_analysator.sam3_widget.results_cleared.connect(self.image_container_controller._on_results_cleared)
        self.image_preview_controller.view.image_analysator.sam3_widget.multi_prompts_send.connect(self.image_container_controller._on_multi_send)

    def _on_theme_changed(self, theme: str):
        """Gère le changement de thème"""
        # Emit theme changed signal
        self.theme_changed.emit(theme)

        # Save configuration
        save_in_config("theme", theme)
    
    def _on_image_clicked(self, img: Image):
        """Gère le clic sur une image"""
        # Display image in preview
        self.image_preview_controller.set_image(img)
        
        # Show preview dock if hidden
        if self.preview_dock.isHidden():
            self.preview_dock.show()
    
    def _on_connection_status_changed(self, state, version: str, error_message: str):
        """Gère les changements de statut de connexion Ollama"""
        from ui.ImportTool.widget.ConnectionVerificator.ConnectionVerificatorModel import State
        
        if state == State.CONNECTED:
            print(f"{tr('Ollama connecté - Version')}: {version}")
        elif state == State.ERROR:
            print(f"{tr('Erreur Ollama')}: {error_message}")
        else:
            print(f"{tr('Ollama')}: {tr('Non connecté')}")
    def _on_menu_import(self):
        """Gère l'import depuis le menu"""
        # The menu already handles import via handle_import()
        # Refresh display if necessary
        if hasattr(self.import_tool_controller, 'view'):
            self.import_tool_controller.view._refresh_image_display()
    
    def _on_menu_export(self):
        """Gère l'export depuis le menu"""
        # The menu already handles export via handle_export()
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
            # Clean up all controllers with running threads properly
            if hasattr(self, 'import_tool_controller'):
                self.import_tool_controller.cleanup()

            if hasattr(self, 'image_container_controller'):
                self.image_container_controller.cleanup()

            # Force shutdown of all PyQt6 threads
            from PyQt6.QtCore import QThreadPool
            pool = QThreadPool.globalInstance()

            pool.clear()        # stop new tasks
            pool.waitForDone()  # wait for thread completion

            DbService().faiss.reset()
            
        except Exception as e:
            print(f"{tr('Erreur lors du nettoyage de MainWindow')}: {e}")
            import traceback
            traceback.print_exc()
    
    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre"""
        try:
            QTimer.singleShot(0, self.cleanup)
            event.accept()
        except Exception as e:
            print(f"{tr('Erreur lors de la fermeture')}: {e}")
            event.accept()  # Force closure even if errors occur
            
        os._exit(0)


if __name__ == "__main__":
    import signal
    
    # Handle Ctrl+C cleanly
    def signal_handler(signum, frame):
        print(f"\n{tr('Interruption détectée, fermeture propre')}...")
        if 'window' in locals():
            # Clean up first, then close
            QTimer.singleShot(0, window.cleanup)
            window.close()
        else:
            # If the window does not exist yet, just exit
            app.quit()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and display the main window
    window = MainWindow()
    
    print(f"{tr('Application démarrée')}")
    print(f"{tr('Utilisez Ctrl+C pour fermer proprement')}")
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print(f"\n{tr('Au revoir')} !")
