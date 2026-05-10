import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

from common.Image_Classes.Image import Image
from common.Image_Classes.ImageRepository import ImageRepository, SearchResults
from common.LRUCache import LRUCache
from database.DbService import DbService
from embedding.embed import inputToEmbedding
from vision.ollama_wrapper import OllamaWrapper
from storage.config import FAISS_INDEX_FILE

class Research:
    def __init__(self, repository : ImageRepository) -> None:
        self.image_repository = repository
        self.embedding_wrapper = OllamaWrapper()

    def _find_all_images(self) -> Optional[SearchResults]:
        return self.image_repository.get_all()
    
    def find(
        self,
        query: str | None = None,
        threshold: float = 0.5,
        limit: int = 50,
        cursor: tuple[float, int] | None = None
    ) -> Optional[SearchResults]:

        # -------------------------
        # ALL IMAGES MODE
        # -------------------------
        if query is None:
            return SearchResults(
                images=self._find_all_images(),
                next_cursor=None,
                has_more=False
            )

        # -------------------------
        # EMBEDDING
        # -------------------------
        query_embed = inputToEmbedding(
            wrapper=self.embedding_wrapper,
            input=query
        )

        if query_embed is None:
            return None

        # -------------------------
        # TRAIN IF EMPTY
        # -------------------------
        if self.image_repository.faiss.index.ntotal == 0:
            self.image_repository.train_index()

        # -------------------------
        # SEARCH ENGINE
        # -------------------------
        return self.image_repository.search(
            query=query_embed,
            threshold=threshold,
            limit=limit,
            cursor=cursor
        )

if __name__ == "__main__":
    db = DbService()
    repo = ImageRepository(db.sqlite, db.faiss)
    auto_research = Research(repo)
    print(auto_research.find())
    print(auto_research.find(query="Un chat qui est sur un ordinateur"))
