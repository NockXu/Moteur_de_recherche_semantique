import os
import sys
from typing import Optional, List, Dict

# Ajouter la racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.Image_Classes.Image import Image


class ImagePreviewModel:
    """Data store holding the currently active inspected image structure and historical views tracker."""

    def __init__(self):
        self.current_image: Image | None = None
        self.history: list[Image] = []
        self.max_history_size = 30

    # ─────────────────────────────
    # IMAGE CURRENT
    # ─────────────────────────────

    def set_image(self, image: Image):
        """Sets the active selection image and appends the replaced object to the navigation logs.

        Args:
            image (Image): The new primary image data object to register.
        """
        if self.current_image and self.current_image.path != image.path:
            self._add_history(self.current_image)

        self.current_image = image

    def get_image(self) -> Image | None:
        """Retrieves the active focused image entity reference.

        Returns:
            The raw image model reference currently inspected, or None.
        """
        return self.current_image

    def clear(self):
        """Purges the active context pointer and shifts existing elements onto backlogs."""
        if self.current_image:
            self._add_history(self.current_image)
        self.current_image = None

    # ─────────────────────────────
    # HISTORY (simple)
    # ─────────────────────────────

    def _add_history(self, image: Image):
        """Inserts an image entity onto the front logs and crops entries passing memory caps.

        Args:
            image (Image): The target historical reference instance to save.
        """
        self.history.insert(0, image)

        if len(self.history) > self.max_history_size:
            self.history = self.history[:self.max_history_size]

    def get_history(self) -> list[Image]:
        """Provides the collection sequence tracking previously browsed image snapshots.

        Returns:
            The complete sequential list tracking unique historical items.
        """
        return self.history

    # ─────────────────────────────
    # UPDATE IMAGE
    # ─────────────────────────────

    def update(self, **kwargs):
        """Modifies attributes matching keys directly on the focused active model layout target.

        Args:
            **kwargs: Arbitrary property fields paired with overriding update values.

        Returns:
            True if assignments were made successfully, otherwise False.
        """
        if not self.current_image:
            return False

        for k, v in kwargs.items():
            if hasattr(self.current_image, k):
                setattr(self.current_image, k, v)

        return True