import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Ajouter le chemin racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)  # insert(0) pour prioriser le chemin racine

from common.ImageInfo import ImageInfo
from database.DatabaseManager import get_all_images, DatabaseManager
from embedding.embed import inputToEmbedding
from database.VectResearch import VectResearch
from vision.ollama_wrapper import OllamaWrapper

class AutoResearch:
    def __init__(
        self, 
        storage_path : str = Path(__file__).parent.parent.parent / "storage", 
        image_extensions : set = {'.jpg', '.jpeg', '.png', '.webp'}
        ) -> None:

        self.storage_path = storage_path
        self.image_extensions = image_extensions
        self.db_manager = None  # Sera initialisé dans find()

    def _find_all_images(self) -> List[ImageInfo] | []:
        return get_all_images()
    
    def find(self, query : str | None = None, image_list : List[ImageInfo] | None = None, tolerance : float = 0.7) -> List[ImageInfo] | []:
        """
        Recherche automatique d'images selon le query et la liste d'images donnée.
        
        Args:
            query: Query de recherche sémantique
            image_list: Liste d'images à rechercher dans
            
        Returns:
            Liste d'images correspondantes
        """

        if image_list is None:
            image_list = self._find_all_images()
        
        # Initialiser le DatabaseManager dans ce thread
        if self.db_manager is None:
            self.db_manager = DatabaseManager()
        
        if query is None:
            return image_list
        else:
            # On embed le query
            # Créer un wrapper temporaire pour l'embedding
            load_dotenv()
            temp_wrapper = OllamaWrapper(os.getenv("OLLAMA_BASE_URL"))
            
            query_embedding = inputToEmbedding(wrapper=temp_wrapper, input=query)

            if query_embedding is None:
                return []
            
            # On cherche les images les plus similaires avec VectResearch
            similar_images = VectResearch(query_embedding, image_list)

            # On filtre les images par tolérance
            similar_images = [image for image in similar_images if image.score >= tolerance]
            
            return similar_images

if __name__ == "__main__":
    auto_research = AutoResearch()
    print(auto_research.find())
