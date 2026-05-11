from embedding.embed import inputToEmbedding
from vision.ollama_wrapper import OllamaWrapper

class SearchBarModel:
    def __init__(self):
        self.text = None

    def embed_input(self, wrapper: OllamaWrapper = None, text: str = None) -> list[float]:
        """Effectue l'embedding du texte de recherche"""
        
        # Utiliser le texte fourni ou celui stocké dans le modèle
        search_text = text if text is not None else self.text
        
        # Validation du texte
        if not search_text or not search_text.strip():
            return []
        
        # Validation du wrapper
        if wrapper is None:
            raise ValueError("Wrapper Ollama non fourni - impossible d'effectuer l'embedding")
        
        try:
            # Validation que le wrapper est fonctionnel
            if not hasattr(wrapper, 'embed'):
                raise ValueError("Wrapper Ollama invalide - méthode 'embed' manquante")
            
            # Effectuer l'embedding avec gestion d'erreurs
            response = inputToEmbedding(wrapper, search_text)
            
            # Validation de la réponse
            if response is None:
                raise RuntimeError("L'embedding a retourné None - vérifiez la connexion Ollama")
            
            if not isinstance(response, list) or len(response) == 0:
                raise RuntimeError(f"Réponse d'embedding invalide: {type(response)} - attendu: list[float]")
            
            return response
            
        except ConnectionError as e:
            raise ConnectionError(f"Erreur de connexion à Ollama: {str(e)}")
        except TimeoutError as e:
            raise TimeoutError(f"Timeout lors de l'embedding avec Ollama: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Erreur lors de l'embedding Ollama: {str(e)}")
    
    def clear(self):
        self.text = None
    
    def add_images(self, images):
        """Ajoute des images au modèle (pour la recherche)"""
        pass  # Pour l'instant, ne fait rien