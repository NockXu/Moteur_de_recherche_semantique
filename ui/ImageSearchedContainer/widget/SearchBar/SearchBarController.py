
import sys
import os

from PyQt6.QtCore import pyqtSignal, QObject
from ui.ImageSearchedContainer.widget.SearchBar.SearchBarView import SearchBarView
from ui.ImageSearchedContainer.widget.SearchBar.SearchBarModel import SearchBarModel
from ui.ImageSearchedContainer.widget.SearchBar.EmbeddingWorker import AsyncEmbeddingManager
from vision.ollama_wrapper import OllamaWrapper

class SearchBarController(QObject):
    def __init__(self, ollama_wrapper: OllamaWrapper = None):
        super().__init__()
        self.view = SearchBarView()
        self.model = SearchBarModel()
        
        self._connect_signals()
        
    def _connect_signals(self):
        self.view.search_text_changed.connect(self._handle_text_changed)
        
    def _handle_text_changed(self, text):
        self.model.text = text
        
    def get_current_text(self):
        return self.model.text
        
    def set_text(self, text):
        self.model.text = text
        
    def clear_search(self):
        self.view.clear()
        self.model.clear()

if __name__ == "__main__":
    import sys
    import os
    from dotenv import load_dotenv
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QTextEdit
    from PyQt6.QtCore import Qt

    # Charger les variables d'environnement depuis le fichier .env
    load_dotenv()

    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Test Barre de Recherche avec Ollama")
            self.setMinimumSize(800, 600)
            
            # Widget central
            central = QWidget()
            self.setCentralWidget(central)
            
            # Layout
            layout = QVBoxLayout(central)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)
            
            # Label d'instructions
            instructions = QLabel("Test de la barre de recherche avec embedding Ollama:")
            instructions.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout.addWidget(instructions)
            
            # Créer le contrôleur avec le wrapper
            self.search_controller = SearchBarController()
            
            layout.addWidget(self.search_controller.view)
            
            # Zone de résultats
            self.results_area = QTextEdit()
            self.results_area.setPlaceholderText("Les résultats d'embedding apparaîtront ici...")
            self.results_area.setMaximumHeight(200)
            layout.addWidget(self.results_area)
            
            # Label de statut
            self.status_label = QLabel("Prêt à tester...")
            layout.addWidget(self.status_label)
            
        def _update_search_status(self, text):
            """Met à jour le statut de recherche"""
            self.status_label.setText(f"Recherche en cours pour: '{text}'...")
            self.results_area.clear()

    # Lancer l'application
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    
    print("🚀 Test de la barre de recherche avec Ollama")
    print(f"📍 URL Ollama: {ollama_url}")
    print("💡 Tapez un texte et appuyez sur Entrée pour tester l'embedding")
    
    sys.exit(app.exec())
