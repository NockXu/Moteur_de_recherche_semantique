import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, List
from pathlib import Path

from ui.ImagePreview.ImagePreviewView import ImagePreviewView
from ui.ImagePreview.ImagePreviewModel import ImagePreviewModel
from common.Image_Classes.Image import Image


class ImagePreviewController(QObject):
    """
    Controller simple type "Inspector panel"
    """

    image_changed = pyqtSignal(Image)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.view = ImagePreviewView()
        self.model = ImagePreviewModel()

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
        if not image:
            self.error_occurred.emit("Image invalide")
            return False

        self.model.set_image(image)
        self.view.display_image(image)

        self.image_changed.emit(image)
        return True

    def clear(self):
        self.model.clear()
        self.view.display_image(None)

    def get_current_image(self) -> Optional[Image]:
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

    def get_history(self) -> List[Image]:
        return self.model.get_history()