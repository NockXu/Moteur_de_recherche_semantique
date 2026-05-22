import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

from common.Image_Classes.Image import Image
from common.Image_Classes.ImageRepository import ImageRepository, SearchResults
from common.WeightCalculator.weightCalculator import WeightSystem
from database.DbService import DbService
from embedding.embed import inputToEmbedding
from vision.ollama_wrapper import OllamaWrapper
from storage.config import FAISS_INDEX_FILE

from common.History_Classes import Tree, history
from common.WeightCalculator import get_weight_function_by_expr, WeightFunction

import numpy as np

class Research:
    def __init__(self, repository : ImageRepository) -> None:
        self.image_repository = repository
        self.embedding_wrapper = OllamaWrapper()
        self.k = 200
    
    def find(
        self,
        query: str | None = None,
        threshold: float = 0.5,
    ) -> Optional[SearchResults]:
        # -------------------------
        # ALL IMAGES MODE
        # -------------------------
        if not query or query == "DEFAULT":
            all_images = self.image_repository.get_k(self.k)
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
        
        return result

    def multi_find(
        self
    ) -> List[Optional[SearchResults]]:

        research_history = history.history_tree.get_all_ancestors()
        query_embeds = []
        results : List[SearchResults] = []
        weights : List[float] = []
        images_before : Dict[Image, int] = {}


        # -------------------------
        # FAISS CHECK
        # -------------------------
    
        if (self.image_repository.faiss is None or 
            self.image_repository.faiss.index is None or 
            self.image_repository.faiss.index.ntotal == 0):
            self.image_repository.train_index()

        # -------------------------
        # ALL IMAGES MODE
        # -------------------------
        for research in research_history:
            weight : float = 0
            sim : float = 0
            query = research.node.query
            if not query or query == "DEFAULT":
                all_images = self.image_repository.get_k(self.k)
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
                continue

            query_embeds.append(query_embed)

            # -------------------------
            # WEIGHT
            # -------------------------

            if len(query_embeds) > 1: 
                weight_function : Optional[WeightFunction] = get_weight_function_by_expr(research.node.w_expr)

                if weight_function is None:
                    weight_function = WeightFunction("", "", WeightSystem("const"))

                prev_query = query_embeds[-2]
                prev_weight = weights[-1]

                sim = weight_function.cosine(query_embed, prev_query)
                weight = weight_function.get_weights(sim, prev_weight, research.get_number_generation(), int(research.node.w_const))
            elif len(query_embeds) == 1:
                weight = 1.0
            else: # Cas de la recherche par défaut
                weight = 0.0

            weights.append(weight)

            # -------------------------
            # SEARCH
            # -------------------------
            result = self.image_repository.search(
                query=query_embed,
                threshold=research.node.threshold,
                k=self.k
            )

            if result is not None:
                results.append(result)
                # -------------------------
                # SCORES ADJUSTEMENT
                # -------------------------
                for image in result["images"]:
                    if image not in images_before:
                        images_before[image] = 1
                    else:
                        images_before[image] = images_before[image] + 1
                    image_scores[image] += image.score * weight

        if len(results) <= 0:
            return None

        # -------------------------
        # SCORES ADJUSTEMENT PART 2
        # -------------------------
        final_result = SearchResults()
        for image, count in images_before.items():
            image.score = image.score / count
            final_result["images"].append(image)
        
        return final_result
    
    def multi_query_score(
        self,
        scores: List[float],
        weights: Optional[List[float]] = None
    ) -> float:

        if weights is None:
            weights = [1.0] * len(scores)

        if len(scores) != len(weights):
            raise ValueError("scores and weights must have same length")

        weight_sum = np.sum(weights)

        if weight_sum == 0:
            return 0.0

        return float(np.dot(scores, weights) / weight_sum)

    def get_weights(self, tree : Tree) -> List[float]:
        weights : List[float] = []

        for i in range(0, tree.get_number_generation(), 1):
            weights.append(i)

        return weights

if __name__ == "__main__":
    db = DbService()
    repo = ImageRepository(db.sqlite, db.faiss)
    auto_research = Research(repo)
    print(auto_research.find())
    print(auto_research.find(query="Un chat qui est sur un ordinateur"))
