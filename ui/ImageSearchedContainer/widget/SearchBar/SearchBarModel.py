from embedding.embed import inputToEmbedding
from vision.ollama_wrapper import OllamaWrapper

class SearchBarModel:
    def __init__(self):
        self.text = None
    
    def clear(self):
        self.text = None
    
    def add_images(self, images):
        """Ajoute des images au modèle (pour la recherche)"""
        pass  # Pour l'instant, ne fait rien