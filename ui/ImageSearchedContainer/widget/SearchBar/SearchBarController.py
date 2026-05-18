
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
        self.view.set_text(text)
        
    def clear_search(self):
        self.view.clear()
        self.model.clear()
