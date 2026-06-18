from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, List

from ui.ImagePreview.ImagePreviewView import ImagePreviewView
from ui.ImagePreview.ImagePreviewModel import ImagePreviewModel
from common.Image_Classes.Image import Image
from common.Image_Classes.ImageRepository import ImageRepository
from database.DbService import DbService

from ui import load_from_config, save_in_config


class ImagePreviewController(QObject):
    """Controller simple type "Inspector panel"
    """

    image_changed = pyqtSignal(Image)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None, theme_changed : pyqtSignal | None = None):
        super().__init__(parent)

        self.view = ImagePreviewView()
        self.model = ImagePreviewModel()

        if theme_changed:
            theme_changed.connect(self.view._on_theme_changed)

        self._connect()

    # ─────────────────────────────
    # SIGNALS
    # ─────────────────────────────

    def _connect(self):
        self.view.reload_requested.connect(self._on_reload_requested)

    def _on_reload_requested(self):
        # reset preview
        self.clear()

    # ─────────────────────────────
    # PUBLIC API (CORE)
    # ─────────────────────────────

    def set_image(self, image: Image) -> bool:
        self.model.set_image(image)
        self.view.display_image(image)

        save_in_config("current_image", image.id)

        self.image_changed.emit(image)
        return True

    def clear(self):
        self.model.clear()
        self.view.display_image(None)

    def get_current_image(self) -> Image | None:
        return self.model.get_image()

    # ─────────────────────────────
    # UPDATE IMAGE (MODEL ONLY)
    # ─────────────────────────────

    def update_current(self, **kwargs):
        success = self.model.update(**kwargs)

        if success and self.model.get_image():
            self.view.display_image(self.model.get_image())

        return success

    # ─────────────────────────────
    # HISTORY (OPTIONAL UI HOOK)
    # ─────────────────────────────

    def get_history(self) -> list[Image]:
        return self.model.get_history()

    def load(self) -> bool:
        current_image_id = load_from_config("current_image")
        if current_image_id:
            repo = ImageRepository(DbService().sqlite, DbService().faiss)
            image = repo.get_image_by_id(current_image_id)
            if image:
                return self.set_image(image)
        return False
