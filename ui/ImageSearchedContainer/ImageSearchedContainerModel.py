import os
import sys
from typing import List, Dict, Optional

from common.Image_Classes.Image import Image
from common.Image_Classes.ImageRepository import SearchResults


class ImageSearchedContainerModel:
    """CLEAN version compatible with Load More + SearchResults.

    - no internal pagination
    - no SQL logic duplication
    - UI cache only

    Attributes:
        images (list[Image]): Active collection of underlying loaded image entities.
        next_cursor (float | None): Pagination index key tracking state for subsequent loads.
        has_more (bool): Status flag tracking if further database pages exist.
        sort_by (str): Targeted domain metadata attribute key used for sorting criteria.
        sort_order (str): Directional configuration rule sequence order flag ('asc' or 'desc').
        filter_tags (list[str]): Whitelist reference tags subset defining active display matches.
        threshold (float): Configured validation score baseline for processing constraints.

    """

    def __init__(self):
        self.images: list[Image] = []

        # state LOAD MORE
        self.next_cursor: float | None = None
        self.has_more: bool = True

        # UI state
        self.sort_by: str = "score"
        self.sort_order: str = "desc"
        self.filter_tags: list[str] = []
        self.threshold: float = 0.5

    # ─────────────────────────────────────────────
    # DATA MANAGEMENT (append only)
    # ─────────────────────────────────────────────

    def append_results(self, search_results : SearchResults) -> list[Image] | None:
        """Ajoute un batch SearchResults (LOAD MORE) - sans duplication.

        Args:
            search_results (SearchResults): The typed database payload dictionary containing 
                new images data packages.

        Returns:
            Filtered list of novel image instances appended during this cycle.

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

    def apply_filters(self) -> list[Image]:
        """Filter the internal image list matching localized UI criteria guidelines.

        Returns:
            Subset collection containing images fulfilling filter conditions.

        """
        if not self.filter_tags:
            return self.images

        return [
            img for img in self.images
            if any(tag in img.keywords for tag in self.filter_tags)
        ]

    # ─────────────────────────────────────────────
    # SORTING (UI only)
    # ─────────────────────────────────────────────

    def apply_sorting(self, images: list[Image]) -> list[Image]:
        """Reorder target array sequence matching strict UI attribute configurations.

        Args:
            images (list[Image]): Target raw collection items list needing order sequence update.

        Returns:
            A freshly initialized, sorted copy sequence of input images elements.

        """
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

    def get_visible_images(self) -> list[Image]:
        """Get the displayed images.

        Returns:
            The list of displayed images.

        """
        filtered = self.apply_filters()
        return self.apply_sorting(filtered)

    def get_image_without_sam3_result(self) -> list[Image]:
        """Retrieve items containing uninitialized computer vision segmentation properties.

        Returns:
            Unprocessed dataset elements awaiting neural network segmentation execution.

        """
        filtered = self.apply_filters()

        images : list[Image] = []

        for image in filtered:
            if image._sam3_results is None:
                images.append(image)

        return images

    # ─────────────────────────────────────────────
    # SINGLE IMAGE ACCESS
    # ─────────────────────────────────────────────

    def get_image_by_path(self, path: str) -> Image | None:
        """Fetch targeted image domain entity matching clean relative filepath strings.

        Args:
            path (str): The unique string absolute identifier path reference.

        Returns:
            Underlying matched object data model reference if discovered, else None.

        """
        for img in self.images:
            if str(img.path) == path:
                return img
        return None

    # ─────────────────────────────────────────────
    # TAGS
    # ─────────────────────────────────────────────

    def get_all_tags(self) -> list[str]:
        """Compile a globally unique sorted string array index representing present tags.

        Returns:
            Lexicographically ordered sequence tracking matching available metadata keys.

        """
        tags = set()
        for img in self.images:
            tags.update(img.keywords)
        return sorted(tags)

    # ─────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────

    def get_statistics(self) -> dict:
        """Compute visual dashboard analytics indicators tracking cached entities metrics.

        Returns:
            Calculated status indicators payload mapping numeric metrics keys.

        """
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

    def set_filter_tags(self, tags: list[str]) -> None:
        """Assign active filter tags constraint whitelist ruleset arrays.

        Args:
            tags (list[str]): Targeted string keywords collection tracking filtering operations.

        Returns:
            None

        """
        self.filter_tags = list(tags)

    def clear_filters(self) -> None:
        """Purge and reset active category label tags tracking parameters.

        Returns:
            None

        """
        self.filter_tags.clear()

    def set_sorting(self, sort_by: str, sort_order: str = "desc") -> None:
        """Assign explicit key sequencing rules parameters targeting upcoming display renders.

        Args:
            sort_by (str): Intended metadata target field column selector.
            sort_order (str): Ascending or descending orientation toggle string flag. Defaults to "desc".

        Returns:
            None

        """
        self.sort_by = sort_by
        self.sort_order = sort_order

    def set_threshold(self, threshold: float) -> None:
        """Set the research threshold.

        Args:
            threshold (float): Target validation filter score constraint boundary value.

        Returns:
            None

        """
        self.threshold = threshold