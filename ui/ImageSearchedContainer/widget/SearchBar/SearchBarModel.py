from embedding.embed import inputToEmbedding
from vision.ollama_wrapper import OllamaWrapper

class SearchBarModel:
    """Stores the active raw text data layer for the search bar component."""
    
    def __init__(self):
        self.text = None
    
    def clear(self) -> None:
        """Resets the recorded query string back to an empty state."""
        self.text = None