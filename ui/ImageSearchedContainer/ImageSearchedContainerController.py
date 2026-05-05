import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Dict, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

from ui.ImageSearchedContainer.ImageSearchedContainerView import ImageSearchedContainerView
from ui.ImageSearchedContainer.ImageSearchedContainerModel import ImageSearchedContainerModel
from common.Image_Classes.Image import Image


class ImageSearchedContainerController(QObject):
    """
    Contrôleur refactorisé version ImportTool style :
    - plus de pagination "page-based"
    - remplacement par LOAD MORE (infinite scroll)
    - source = BDD ou dataset déjà injecté
    """

    images_loaded = pyqtSignal(int)

    def __init__(self, max_images_per_page: int = 12, thumbnail_size: int = 150):
        super().__init__()

        self.view = ImageSearchedContainerView()
        self.model = ImageSearchedContainerModel(max_images_per_page)

        self.thumbnail_size = thumbnail_size

        # état load more
        self._loaded_count = 0
        self._all_images: List[Image] = []

        # callbacks optionnels
        self.image_click_callback: Optional[Callable[[Image], None]] = None

        self._connect_signals()

    # ─────────────────────────────────────────────
    # SIGNALS
    # ─────────────────────────────────────────────

    def _connect_signals(self):
        self.view.image_clicked.connect(self._on_image_clicked)
        self.view.load_more_requested.connect(self.load_more_images)
        self.view.reload_requested.connect(self.reload_images)

    # ─────────────────────────────────────────────
    # DATA ENTRY POINT (BDD / SEARCH RESULT)
    # ─────────────────────────────────────────────

    def set_images(self, images: List[Image]):
        """
        Remplace totalement la liste (résultat recherche / BDD).
        """
        self._all_images = images or []
        self._loaded_count = 0

        self.model.clear()
        self.load_more_images(reset=True)

    def add_images(self, images: List[Image]):
        """
        Ajoute à la liste existante (append BDD / streaming)
        """
        self._all_images.extend(images)
        self.load_more_images(reset=False)

    # ─────────────────────────────────────────────
    # LOAD MORE (équivalent ImportTool)
    # ─────────────────────────────────────────────

    def load_more_images(self, reset: bool = False):
        """
        Charge progressivement les images (lazy loading)
        """
        if reset:
            self._loaded_count = 0
            self.model.clear()

        if self._loaded_count >= len(self._all_images):
            return

        next_batch = self._all_images[
            self._loaded_count : self._loaded_count + self.model.max_images_per_page
        ]

        self.model.add_images(next_batch)
        self._loaded_count += len(next_batch)

        self._update_view()

        self.images_loaded.emit(self._loaded_count)

    # ─────────────────────────────────────────────
    # VIEW UPDATE
    # ─────────────────────────────────────────────

    def _update_view(self):
        """
        Sync model → view (ImportTool style)
        """
        self.view.display_images(
            image_data=self.model.get_all_loaded_images(),
            total_count=len(self._all_images),
            loaded_count=self._loaded_count
        )

    # ─────────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────────

    def _on_image_clicked(self, image_path: str):
        image_info = self.model.get_image_by_path(image_path)

        if self.image_click_callback and image_info:
            self.image_click_callback(image_info)

    # ─────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────

    def get_view(self):
        return self.view

    def set_image_click_callback(self, callback: Callable[[Image], None]):
        self.image_click_callback = callback

    def clear_images(self):
        self._all_images.clear()
        self._loaded_count = 0
        self.model.clear()
        self._update_view()

    def reload_images(self):
        """
        Reload BDD (version simplifiée safe)
        """
        try:
            from database.ImageRepository import get_all_images  # adapte si besoin

            images = get_all_images()

            print(f"[Controller] Reload {len(images)} images from BDD")

            self.set_images(images)

        except Exception as e:
            print(f"[Controller] reload error: {e}")

    # ─────────────────────────────────────────────
    # CONFIG
    # ─────────────────────────────────────────────

    def set_thumbnail_size(self, size: int):
        self.thumbnail_size = size
        self._update_view()

    def set_max_per_load(self, value: int):
        self.model.set_max_images_per_page(value)