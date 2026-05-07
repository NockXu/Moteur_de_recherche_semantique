
import sys
import os

from PyQt6.QtCore import pyqtSignal, QObject
from ui.ImageSearchedContainer.widget.SearchBar.SearchBarView import SearchBarView
from ui.ImageSearchedContainer.widget.SearchBar.SearchBarModel import SearchBarModel
from ui.ImageSearchedContainer.widget.SearchBar.EmbeddingWorker import AsyncEmbeddingManager
from vision.ollama_wrapper import OllamaWrapper

class SearchBarController(QObject):
    # Signal émis quand la recherche est terminée avec l'embedding
    search_completed = pyqtSignal(str, list)
    def __init__(self, ollama_wrapper: OllamaWrapper = None):
        super().__init__()
        self.view = SearchBarView()
        self.model = SearchBarModel()
        self.ollama_wrapper = ollama_wrapper
        self.embedding_manager = AsyncEmbeddingManager()
        self._connect_signals()
        
    def _connect_signals(self):
        self.view.search_triggered.connect(self._handle_search)
        self.view.search_text_changed.connect(self._handle_text_changed)
        
    def _handle_search(self, search_text: str):
        """Lance la recherche sémantique de manière asynchrone pour ne pas bloquer l'UI"""
        if not search_text or not search_text.strip():
            return
            
        # Mettre à jour le modèle
        self.model.text = search_text
            
        # Désactiver la barre de recherche pendant la recherche
        self.view.set_enabled(False)
        
        # Appeler la méthode de statut si disponible (pour le test)
        if hasattr(self, '_update_search_status'):
            self._update_search_status(self.model.text)
        
        # Lancer la recherche sémantique asynchrone
        self.embedding_manager.start_search(
            query=self.model.text,
            on_finished=self.on_search_finished,
            on_error=self._on_embedding_error
        )
    
    def on_search_finished(self, result):

        self.model.clear()

        self.model.add_images(result.images)
        self._update_view()

        self.state.cursor = result.next_cursor
        self.state.has_more = result.has_more
    
    def _on_embedding_error(self, error_msg):
        """Appelé en cas d'erreur pendant l'embedding"""
        # Réactiver la barre de recherche
        self.view.set_enabled(True)
        print(f"Erreur d'embedding: {error_msg}")
        
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
    
    # Créer le wrapper Ollama
    ollama_url = os.getenv("OLLAMA_BASE_URL")
    if not ollama_url:
        print("Erreur: OLLAMA_BASE_URL non défini dans le fichier .env")
        sys.exit(1)
    
    wrapper = OllamaWrapper(ollama_url)
    print(f"Connexion à Ollama: {ollama_url}")

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
            self.search_controller = SearchBarController(ollama_wrapper=wrapper)
            
            # Remplacer les callbacks du contrôleur pour afficher les résultats
            self.original_on_finished = self.search_controller._on_embedding_finished
            self.original_on_error = self.search_controller._on_embedding_error
            self.search_controller._on_embedding_finished = self._on_embedding_finished
            self.search_controller._on_embedding_error = self._on_embedding_error
            
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
        
        def _on_embedding_finished(self, embedding):
            """Affiche les résultats de l'embedding"""
            self.search_controller.view.set_enabled(True)
            self.status_label.setText("Embedding terminé avec succès!")
            
            # Afficher les résultats
            result_text = f"✅ Embedding réussi!\n"
            result_text += f"📏 Dimensions: {len(embedding)}\n"
            result_text += f"📊 Premières valeurs: {embedding[:5]}...\n"
            result_text += f"🔢 Type: {type(embedding).__name__}\n"
            result_text += f"⚡ Somme: {sum(embedding):.4f}\n"
            result_text += f"📐 Norme: {(sum(x**2 for x in embedding) ** 0.5):.4f}"
            
            self.results_area.setText(result_text)
        
        def _on_embedding_error(self, error_msg):
            """Affiche les erreurs"""
            self.search_controller.view.set_enabled(True)
            self.status_label.setText(f"Erreur: {error_msg}")
            
            error_text = f"Erreur d'embedding!\n\n"
            error_text += f"Message: {error_msg}\n"
            error_text += f"Verifiez:\n"
            error_text += f"   • Connexion à Ollama ({ollama_url})\n"
            error_text += f"   • Modèle 'nomic-embed-text:v1.5' disponible\n"
            error_text += f"   • Service Ollama en cours d'exécution"
            
            self.results_area.setText(error_text)
        
        def closeEvent(self, event):
            """Ferme proprement les threads avant de quitter"""
            if self.search_controller.embedding_manager.is_running():
                self.search_controller.embedding_manager.stop_embedding()
            event.accept()

    # Lancer l'application
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    
    print("🚀 Test de la barre de recherche avec Ollama")
    print(f"📍 URL Ollama: {ollama_url}")
    print("💡 Tapez un texte et appuyez sur Entrée pour tester l'embedding")
    
    sys.exit(app.exec())
