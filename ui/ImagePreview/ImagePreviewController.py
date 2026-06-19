from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, List

from ui.ImagePreview.ImagePreviewView import ImagePreviewView
from ui.ImagePreview.ImagePreviewModel import ImagePreviewModel
from common.Image_Classes.Image import Image
from common.Image_Classes.ImageRepository import ImageRepository
from database.DbService import DbService

from ui import load_from_config, save_in_config


class ImagePreviewController(QObject):
    """Coordinates lifecycle events between the image inspector view and its history tracking model.

    Signals:
        image_changed (pyqtSignal[Image]): Emitted whenever a new image context is successfully loaded.
        error_occurred (pyqtSignal[str]): Emitted with structural exception descriptions when processing fails.

    Args:
        parent (QObject | None): Optional structural parent component context. Defaults to None.
        theme_changed (pyqtSignal | None): Global broadcast channel alerting color updates. Defaults to None.
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

    def _connect(self) -> None:
        """Hooks layout interactive slots up to shared component trigger updates."""
        self.view.reload_requested.connect(self._on_reload_requested)

    def _on_reload_requested(self) -> None:
        """Handles reload structural calls and safely resets internal preview view contexts."""
        # reset preview
        self.clear()

    # ─────────────────────────────
    # PUBLIC API (CORE)
    # ─────────────────────────────

    def set_image(self, image: Image) -> bool:
        """Updates the tracking data structure, rewrites layout images, and saves app config.

        Args:
            image (Image): Target image entity to process.

        Returns:
            True once layouts are completely assigned.
        """
        self.model.set_image(image)
        self.view.display_image(image)

        save_in_config("current_image", image.id)

        self.image_changed.emit(image)
        return True

    def clear(self) -> None:
        """Wipes active image parameters from models and updates layouts back to empty previews."""
        self.model.clear()
        self.view.display_image(None)

    def get_current_image(self) -> Image | None:
        """Extracts the primary active focused inspector image pointer.

        Returns:
            The raw image model reference currently tracked, or None.
        """
        return self.model.get_image()

    # ─────────────────────────────
    # UPDATE IMAGE (MODEL ONLY)
    # ─────────────────────────────

    def update_current(self, **kwargs) -> bool:
        """Overrides properties on the live target image and triggers layout redrawing updates.

        Args:
            **kwargs: Dict collections pairing model keys with target assignment changes.

        Returns:
            True if settings updates are mapped successfully, otherwise False.
        """
        success = self.model.update(**kwargs)

        if success and self.model.get_image():
            self.view.display_image(self.model.get_image())

        return success

    # ─────────────────────────────
    # HISTORY (OPTIONAL UI HOOK)
    # ─────────────────────────────

    def get_history(self) -> list[Image]:
        """Provides the backlog tracking historical image objects evaluated during the run session.

        Returns:
            The sequential list tracking unique historical items.
        """
        return self.model.get_history()

    def load(self) -> bool:
        """Restores structural application tracking keys and re-populates saved target parameters.

        Returns:
            True if valid context targets match existing entities, otherwise False.
        """
        current_image_id = load_from_config("current_image")
        if current_image_id:
            repo = ImageRepository(DbService().sqlite, DbService().faiss)
            image = repo.get_image_by_id(current_image_id)
            if image:
                return self.set_image(image)
        return False
