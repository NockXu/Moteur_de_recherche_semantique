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

    # ─────────────────────────────────────────────
    # DATA MANAGEMENT (append only)
    # ─────────────────────────────────────────────

    def append_results(self, search_results : SearchResults):
        """
        Ajoute un batch SearchResults (LOAD MORE)
        """
        if not search_results:
            return

        self.images.extend(search_results['images'])
        self.next_cursor = search_results['next_cursor']
        self.has_more = search_results['has_more']

    def reset(self):
        """Reset complet (nouvelle recherche)"""
        self.images.clear()
        self.next_cursor = None
        self.has_more = True

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
    # LOAD MORE STATE
    # ─────────────────────────────────────────────

    def can_load_more(self) -> bool:
        return self.has_more

    def get_cursor(self) -> Optional[float]:
        return self.next_cursor

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
            "has_more": self.has_more,
            "next_cursor": self.next_cursor,
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