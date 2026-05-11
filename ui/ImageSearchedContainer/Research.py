import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

from common.Image_Classes.Image import Image
from common.Image_Classes.ImageRepository import ImageRepository, SearchResults
from database.DbService import DbService
from embedding.embed import inputToEmbedding
from vision.ollama_wrapper import OllamaWrapper
from storage.config import FAISS_INDEX_FILE

class Research:
    def __init__(self, repository : ImageRepository) -> None:
        self.image_repository = repository
        self.embedding_wrapper = OllamaWrapper()
        self.k = 200

    def _find_all_images(self) -> Optional[SearchResults]:
        return self.image_repository.get_all()
    
    def find(
        self,
        query: str | None = None,
        threshold: float = 0.5,
    ) -> Optional[SearchResults]:
        # -------------------------
        # ALL IMAGES MODE
        # -------------------------
        if query is None:
            all_images = self._find_all_images()
            result = SearchResults(
                images=all_images if all_images else [],
                k=self.k
            )
            return result

        # -------------------------
        # EMBEDDING GENERATION
        # -------------------------
        query_embed = inputToEmbedding(self.embedding_wrapper, query)

        if query_embed is None:
            return None

        # -------------------------
        # FAISS CHECK
        # -------------------------
        
        if self.image_repository.faiss and self.image_repository.faiss.index:
            print(f"[DEBUG] index.ntotal: {self.image_repository.faiss.index.ntotal}")
        
        if (self.image_repository.faiss is None or 
            self.image_repository.faiss.index is None or 
            self.image_repository.faiss.index.ntotal == 0):
            self.image_repository.train_index()

        # -------------------------
        # SEARCH
        # -------------------------
        result = self.image_repository.search(
            query=query_embed,
            threshold=threshold,
            k=self.k
        )
        if result:
            print(f"[DEBUG] Nombre d'images trouvées: {len(result.get('images', []))}")
        else:
            print("[DEBUG] Résultat de search() est None")
        
        return result

if __name__ == "__main__":
    db = DbService()
    repo = ImageRepository(db.sqlite, db.faiss)
    auto_research = Research(repo)
    print(auto_research.find())
    print(auto_research.find(query="Un chat qui est sur un ordinateur"))
