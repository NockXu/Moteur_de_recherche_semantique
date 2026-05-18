import os
import sys
from typing import List, Dict, Optional

from common.Image_Classes.Image import Image
from common.Image_Classes.ImageRepository import SearchResults


class ImageSearchedContainerModel:
    """
    Version CLEAN compatible Load More + SearchResults
    - pas de pagination interne
    - pas de duplication de logique SQL
    - cache UI uniquement
    """

    def __init__(self):
        self.images: List[Image] = []

        # state LOAD MORE
        self.next_cursor: Optional[float] = None
        self.has_more: bool = True

        # UI state
        self.sort_by: str = "score"
        self.sort_order: str = "desc"
        self.filter_tags: List[str] = []
        self.threshold: float = 0.5

    # ─────────────────────────────────────────────
    # DATA MANAGEMENT (append only)
    # ─────────────────────────────────────────────

    def append_results(self, search_results : SearchResults) -> Optional[List[Image]]:
        """
        Ajoute un batch SearchResults (LOAD MORE) - sans duplication
        """
        new_images = [img for img in search_results['images'] if img not in self.images]
        self.images.extend(new_images)
        self.k = search_results['k']
        
        return new_images

    def reset(self):
        """Reset complet (nouvelle recherche)"""
        self.images.clear()
        self.k = 200

    # ─────────────────────────────────────────────
    # FILTERS (UI only)
    # ─────────────────────────────────────────────

    def apply_filters(self) -> List[Image]:
        if not self.filter_tags:
            return self.images

        return [
            img for img in self.images
            if any(tag in img.keywords for tag in self.filter_tags)
        ]

    # ─────────────────────────────────────────────
    # SORTING (UI only)
    # ─────────────────────────────────────────────

    def apply_sorting(self, images: List[Image]) -> List[Image]:
        reverse = self.sort_order == "desc"

        if self.sort_by == "score":
            return sorted(images, key=lambda x: x.score, reverse=reverse)

        if self.sort_by == "title":
            return sorted(images, key=lambda x: x.name.lower(), reverse=reverse)

        if self.sort_by == "path":
            return sorted(images, key=lambda x: str(x.path).lower(), reverse=reverse)

        return images

    # ─────────────────────────────────────────────
    # VIEW DATA (IMPORTANT)
    # ─────────────────────────────────────────────

    def get_visible_images(self) -> List[Image]:
        """
        Ce que la vue doit afficher
        """
        filtered = self.apply_filters()
        return self.apply_sorting(filtered)

    # ─────────────────────────────────────────────
    # SINGLE IMAGE ACCESS
    # ─────────────────────────────────────────────

    def get_image_by_path(self, path: str) -> Optional[Image]:
        for img in self.images:
            if str(img.path) == path:
                return img
        return None

    # ─────────────────────────────────────────────
    # TAGS
    # ─────────────────────────────────────────────

    def get_all_tags(self) -> List[str]:
        tags = set()
        for img in self.images:
            tags.update(img.keywords)
        return sorted(tags)

    # ─────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────

    def get_statistics(self) -> Dict:
        visible = self.get_visible_images()

        return {
            "total_images": len(self.images),
            "visible_images": len(visible),
            "unique_tags": len(self.get_all_tags()),
            "avg_score": (
                sum(i.score for i in self.images) / len(self.images)
                if self.images else 0
            )
        }

    # ─────────────────────────────────────────────
    # FILTER API
    # ─────────────────────────────────────────────

    def set_filter_tags(self, tags: List[str]):
        self.filter_tags = list(tags)

    def clear_filters(self):
        self.filter_tags.clear()

    def set_sorting(self, sort_by: str, sort_order: str = "desc"):
        self.sort_by = sort_by
        self.sort_order = sort_order

    def set_threshold(self, threshold: float):
        """Définit le threshold de recherche"""
        self.threshold = threshold