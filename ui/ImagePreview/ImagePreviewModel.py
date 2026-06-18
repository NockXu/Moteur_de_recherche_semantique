import os
import sys
from typing import Optional, List, Dict

# Ajouter la racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.Image_Classes.Image import Image


class ImagePreviewModel:
    """Modèle simple pour la preview d'une image"""

    def __init__(self):
        self.current_image: Image | None = None
        self.history: list[Image] = []
        self.max_history_size = 30

    # ─────────────────────────────
    # IMAGE CURRENT
    # ─────────────────────────────

    def set_image(self, image: Image):
        if self.current_image and self.current_image.path != image.path:
            self._add_history(self.current_image)

        self.current_image = image

    def get_image(self) -> Image | None:
        return self.current_image

    def clear(self):
        if self.current_image:
            self._add_history(self.current_image)
        self.current_image = None

    # ─────────────────────────────
    # HISTORY (simple)
    # ─────────────────────────────

    def _add_history(self, image: Image):
        self.history.insert(0, image)

        if len(self.history) > self.max_history_size:
            self.history = self.history[:self.max_history_size]

    def get_history(self) -> list[Image]:
        return self.history

    # ─────────────────────────────
    # UPDATE IMAGE
    # ─────────────────────────────

    def update(self, **kwargs):
        if not self.current_image:
            return False

        for k, v in kwargs.items():
            if hasattr(self.current_image, k):
                setattr(self.current_image, k, v)

        return True