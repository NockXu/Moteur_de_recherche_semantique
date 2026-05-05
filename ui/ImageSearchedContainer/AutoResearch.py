import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Ajouter le chemin racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)  # insert(0) pour prioriser le chemin racine

from common.Image_Classes.Image import Image
from common.Image_Classes.ImageRepository import ImageRepository, SearchResults
from database.DbService import DbService
from embedding.embed import inputToEmbedding
from vision.ollama_wrapper import OllamaWrapper

class AutoResearch:
    def __init__(self) -> None:
        db_service = DbService()
        self.image_repository : ImageRepository = ImageRepository(db_service.sqlite, db_service.faiss)

    def _find_all_images(self) -> Optional[SearchResults]:
        return self.image_repository.get_all()
    
    def find(self, query : str | None = None, threshold : float = 0.7) -> Optional[SearchResults]:
        """
        Recherche automatique d'images selon le query et la liste d'images donnée.
        
        Args:
            query: Query de recherche sémantique
            image_list: Liste d'images à rechercher dans
            
        Returns:
            Liste d'images correspondantes
        """
        db_service = DbService()

        if self.image_repository is None:
            self.image_repository = ImageRepository(db_service.sqlite, db_service.faiss)
        
        if query is None:
            return self._find_all_images()
        else:
            # On embed le query
            # Créer un wrapper temporaire pour l'embedding
            load_dotenv()
            temp_wrapper = OllamaWrapper(os.getenv("OLLAMA_BASE_URL"))
            
            query_embed = inputToEmbedding(wrapper=temp_wrapper, input=query)

            if query_embed is None:
                return None
            
            
            return db_service.faiss.search(query_embed, threshold=threshold)

if __name__ == "__main__":
    auto_research = AutoResearch()
    print(auto_research.find())
    print(auto_research.find(query="chat"))
