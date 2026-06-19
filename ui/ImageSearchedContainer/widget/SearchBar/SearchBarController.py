
import sys
import os

from PyQt6.QtCore import pyqtSignal, QObject
from ui.ImageSearchedContainer.widget.SearchBar.SearchBarView import SearchBarView
from ui.ImageSearchedContainer.widget.SearchBar.SearchBarModel import SearchBarModel
from ui.ImageSearchedContainer.widget.SearchBar.EmbeddingWorker import AsyncEmbeddingManager
from vision.ollama_wrapper import OllamaWrapper

class SearchBarController(QObject):
    """Coordinates search text entries between the input bar view and its model data layers.

    Args:
        ollama_wrapper (OllamaWrapper | None): Optional AI model engine framework connector. Defaults to None.
    """
    def __init__(self, ollama_wrapper: OllamaWrapper = None):
        super().__init__()
        
        self.view = SearchBarView()
        self.model = SearchBarModel()
        
        self._connect_signals()
        
    def _connect_signals(self) -> None:
        """Connects interactive entry fields signals to processing slots."""
        self.view.search_text_changed.connect(self._handle_text_changed)
        
    def _handle_text_changed(self, text : str):
        """Saves updated raw search characters into the active model storage state.

        Args:
            text (str): Incoming characters typed by the user.
        """
        self.model.text = text
        
    def get_current_text(self) -> str:
        """Retrieves the active search input prompt recorded in the model.

        Returns:
            The raw text string currently saved in the model.
        """
        return self.model.text
        
    def set_text(self, text : str) -> None:
        """Forces the search field text value updates across both data and display components.

        Args:
            text (str): Target string message values to display.
        """
        self.model.text = text
        self.view.set_text(text)
        
    def clear_search(self) -> None:
        """Flushes written history data caches and empties structural display input fields."""
        self.view.clear()
        self.model.clear()
