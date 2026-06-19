import sys
import time
from typing import List, Optional
from collections.abc import Callable
from PyQt6.QtCore import QObject, pyqtSignal

from ui.ImageSearchedContainer.ImageSearchedContainerView import ImageSearchedContainerView
from ui.ImageSearchedContainer.ImageSearchedContainerModel import ImageSearchedContainerModel
from ui.ImageSearchedContainer.Research import Research
from common.Image_Classes.Image import Image
from common.Image_Classes.ImageRepository import ImageRepository, SearchResults
from database.DbService import DbService

from ui.ImageSearchedContainer.widget.SearchBar.EmbeddingWorker import AsyncEmbeddingManager
from ui.utils.i18n import tr
from vision.SAM3AsyncManager import get_sam3_manager

from common.History_Classes import history, HistoryData, Tree
from common.Image_Classes.Image import Image

from ui import save_in_config, load_from_config
from ui.ImageSearchedContainer.SAM3ProgressWindow import SAM3ProgressWindow

# =========================
# STATE
# =========================
class SearchState:
    """Stores the tracking state of the current image search session.

    Attributes:
        query (str | None): The current search text prompt.
        cursor (tuple[float, int] | None): Pagination markers for database retrieval.
        has_more (bool): Indicates if there are additional matching results to load.
    """
    def __init__(self):
        self.query: str | None = None
        self.cursor: tuple[float, int] | None = None
        self.has_more: bool = False

# =========================
# CONTROLLER
# =========================
class ImageSearchedContainerController(QObject):
    """Coordinates search input, asynchronous AI processing, and gallery display updates.

    Signals:
        images_loaded (pyqtSignal[int]): Emitted with the count of successfully processed images.

    Args:
        thumbnail_size (int): Default display height for gallery images. Defaults to 150.
        theme_changed (pyqtSignal | None): Optional signal to broadcast visual UI theme updates.
    """
    
    images_loaded = pyqtSignal(int)

    def __init__(self, thumbnail_size: int = 150, theme_changed: pyqtSignal | None = None):
        super().__init__()

        self.view = ImageSearchedContainerView()
        if theme_changed:
            theme_changed.connect(self.view._on_theme_changed)

        self.model = ImageSearchedContainerModel()

        db = DbService()
        self.repo = ImageRepository(db.sqlite, db.faiss)
        self.research = Research(self.repo)

        # async engine
        self.embedding_manager = AsyncEmbeddingManager()
        self.sam3_manager = get_sam3_manager()
        self._sam3_jobs: dict[str, Image] = {}
        self._sam3_progress_window = SAM3ProgressWindow()
        self._sam3_progress_window.cancelled.connect(self._on_sam3_cancelled)
        self._sam3_done = 0
        self.old_prompt = None

        # state
        self.state = SearchState()

        self.thumbnail_size = thumbnail_size
        self._loading = False

        self.image_click_callback: Callable[[Image], None] | None = None

        self._connect_signals()

    # ─────────────────────────────
    # SIGNALS
    # ─────────────────────────────
    def _connect_signals(self) -> None:
        """Connects UI component actions and background worker signals to internal slots."""
        self.view.image_clicked.connect(self._on_image_clicked)
        self.view.load_more_requested.connect(self.load_more_images)
        self.view.reload_requested.connect(self.reload_images)
        self.view.search_controller.view.search_triggered.connect(self._on_search_triggered)
        self.embedding_manager.result.connect(self._on_search_finished)
        self.sam3_manager.result.connect(self._on_sam3_image_finished)
        self.sam3_manager.error.connect(self._on_sam3_image_error)
        self.view.threshold_changed.connect(self._on_threshold_changed)
        history.current_search_updated.connect(self.search)
        self.view.image_count_spinbox.valueChanged.connect(self._on_image_count_changed)
        
    def _on_image_count_changed(self, value: int) -> None:
        """Handles changes in the target image count and restarts the search.

        Args:
            value (int): The new maximum number of search results requested.
        """
        self.research.k = value
        self.embedding_manager.start_search(
            query=self.state.query,
            threshold=self.model.threshold,
            cursor=None,
            auto_research=self.research
        )

    def _on_results_displayed(self, results: dict[str, list[dict]]) -> None:
        """Updates thumbnails with segmented coordinates and prediction scores.
        
        reiceve :
            [{"type":"result", "prompt":str, "index":int,
              "score":float, "box":[x1,y1,x2,y2],
              "color": QColor, ...}, ...]

        Args:
            results (dict[str, list[dict]]): A dictionary mapping image paths to their overlay data.
        """
        self.view.update_images(results)

    def _on_results_cleared(self, image_paths: list[str]) -> None:
        """Clears temporary prediction results from the specified images.

        Args:
            image_paths (list[str]): Filepaths of images that need their results cleared.
        """
        self.view.clear_results(image_paths)

    def _on_multi_send(self, prompts: list[dict]) -> None:
        """Sends multi-modal text prompts to the SAM3 model for batch image analysis.

        Args:
            prompts (list[dict]): A list of point coordinates or label options.
        """
        if not prompts:
            return

        # Annuler les jobs en cours et réinitialiser
        if self._sam3_jobs:
            self.sam3_manager.cancel_all()
            self._sam3_jobs.clear()

        if prompts != self.old_prompt:
            self.old_prompt = prompts
            images = self.model.get_visible_images()
            self.view.clear_results([str(image.path) for image in images])
            self.view.filter_combo.setCurrentIndex(0)  # reset filter

            self._sam3_done = 0
            self._sam3_progress_window.start(len(images))
        else:
            lenght_all_image = len(self.model.get_visible_images())
            images = self.model.get_image_without_sam3_result()
            self._sam3_done = lenght_all_image - len(images)
            self._sam3_progress_window.start(lenght_all_image, initial_done=self._sam3_done)

        for image in images:
            job_id = self.sam3_manager.process_image(str(image.path), prompts)
            image.set_prompts(prompts)
            self._sam3_jobs[job_id] = image

    def _on_sam3_image_finished(self, job_id: str, image_path: str, results) -> None:
        """Receives completed segmentation data for a single image job.

        Args:
            job_id (str): Unique tracking identifier for the completed worker thread.
            image_path (str): The file system location of the handled image.
            results (list[dict]): Raw detection layer information.
        """
        image = self._sam3_jobs.pop(job_id, None)
        if image is None:
            return

        image.set_SAM3_results(results)

        # Convertir le format brut SAM3 → format draw_results
        display_results = self._convert_sam3_results(results)
        if display_results:
            self.view.update_images({str(image.path): display_results})

        self._sam3_done += 1
        from pathlib import Path
        self._sam3_progress_window.update_progress(self._sam3_done, Path(image_path).name)

        if not self._sam3_jobs:
            self._sam3_progress_window.finish()

    def _on_sam3_image_error(self, job_id: str, error: str) -> None:
        """Handles an error encountered during the segmentation process of an image.

        Args:
            job_id (str): Unique tracking identifier for the failed job.
            error (str): Text message detailing the processing failure.
        """
        if not job_id or job_id not in self._sam3_jobs:
            return

        image = self._sam3_jobs.pop(job_id, None)
        if image:
            print(f"{tr('[SAM3 multi-image ERROR]')} {image.path}: {error}")

        if not self._sam3_jobs:
            self._sam3_progress_window.finish()

    def _convert_sam3_results(self, results: list[dict]) -> list[dict]:
        """Converts raw SAM3 data structures into standard display formatting.

        Args:
            results (list[dict]): Raw multidimensional tensor bounding fields from the model.

        Returns:
            A clean list of dictionaries formatted for rendering overlays on images.
        """
        from PyQt6.QtGui import QColor

        COLORS = [
            QColor(80, 160, 255),
            QColor(255, 100, 100),
            QColor(100, 255, 100),
            QColor(255, 200, 50),
            QColor(200, 100, 255),
        ]

        display = []
        for i, entry in enumerate(results):
            boxes = entry.get("boxes")
            masks = entry.get("masks")
            scores = entry.get("scores")

            if boxes is None or masks is None:
                continue

            # boxes shape: (N, 4), masks shape: (N, 1, H, W)
            n = boxes.shape[0] if hasattr(boxes, "shape") else len(boxes)
            for j in range(n):
                box = boxes[j].tolist() if hasattr(boxes[j], "tolist") else boxes[j]
                mask = masks[j] if hasattr(masks, "__getitem__") else None
                score = scores[j].item() if scores is not None else 0.0

                display.append({
                    "box": box,
                    "mask": mask,
                    "color": COLORS[i % len(COLORS)],
                    "score": score,
                    "prompt": entry.get("prompt", ""),
                    "type": "result",
                })

        return display

    def _on_sam3_cancelled(self) -> None:
        """Aborts all currently running image segmentation tasks."""
        self.sam3_manager.cancel_all()
        self._sam3_jobs.clear()
        self._sam3_progress_window.reset()

    # ─────────────────────────────
    # SEARCH ENTRY POINT
    # ─────────────────────────────
    def _on_search_triggered(self, search_text: str) -> None:
        """Clears old states and runs a brand new asynchronous semantic search.

        Args:
            search_text (str): Raw string keywords typed by the user.
        """
        if self._sam3_jobs:
            self.sam3_manager.cancel_all()
            self._sam3_jobs.clear()
            
        self.old_prompt = None
        self._sam3_progress_window.reset()
        self.state.query = search_text
        self.state.cursor = None
        self.state.has_more = False

        self.model.reset()
        self.view.clear()
        self._update_view()

        self.research.k = self.view.image_count_spinbox.value()

        self._loading = True

        self.save_search()

        self.embedding_manager.start_search(
            query=search_text,
            threshold=self.model.threshold,
            cursor=self.state.cursor,
            auto_research=self.research
        )

    def search(self) -> None:
        """Runs a search based on the current history log selection context."""
        if self._sam3_jobs:
            self.sam3_manager.cancel_all()
            self._sam3_jobs.clear()
        self.old_prompt = None
        self._sam3_progress_window.reset()
        if not history.current_search:
            history.current_search = history.history_tree
            
        search_text = history.current_search.node.query

        self.view.search_controller.set_text(search_text)
        self.set_threshold(history.current_search.node.threshold if history.current_search else 0.5)

        self.state.query = search_text
        self.state.cursor = None
        self.state.has_more = False

        self.research.k = self.view.image_count_spinbox.value()

        self.model.reset()
        self.view.clear()
        self._update_view()

        self._loading = True

        self.embedding_manager.start_search(
            query=search_text,
            threshold=self.model.threshold,
            cursor=self.state.cursor,
            auto_research=self.research
        )

    # ─────────────────────────────
    # SEARCH CALLBACK
    # ─────────────────────────────
    def _on_search_finished(self, result) -> None:
        """Processes and displays the results after a search finishes.

        Args:
            result (dict): Data dictionary containing image entities and total results count.
        """
        self._loading = False

        if result is None:
            return

        self.model.reset()
        self.model.append_results({'images': result.get('images', []), 'k': result.get('k', 200)})
        self._update_view()

    def _on_search_error(self, error: str) -> None:
        """Logs search processing exceptions received from background handlers.

        Args:
            error (str): Error message string describing why the query failed.
        """
        self._loading = False
        print(f"{tr('[Search ERROR]')} {error}")

    def _on_threshold_changed(self, threshold: float) -> None:
        """Updates the internal minimum similarity threshold filter.

        Args:
            threshold (float): Similarity percentage value limit between 0.0 and 1.0.
        """
        self.model.set_threshold(threshold)

    # ─────────────────────────────
    # LOAD MORE (INFINITE SCROLL)
    # ─────────────────────────────
    def load_more_images(self, reset: bool = False) -> None:
        """Fetches the next batch of images for infinite scrolling.

        Args:
            reset (bool): Unused cleanup indicator flag placeholder. Defaults to False.
        """
        if self._loading:
            return
        
        if (self.view.filter_combo.isVisible() and 
            self.view.filter_combo.currentData() != "none"):
            return

        self._loading = True

        self.research.k = self.view.image_count_spinbox.value()

        try:
            result = self.research.multi_find()

            new_images = self.model.append_results(result)
            
            self.view.image_count_spinbox.valueChanged.disconnect()
            self.view.display_images(
                image_data=new_images,
                total_count=len(self.model.images),
            )
            self.view.image_count_spinbox.valueChanged.connect(self._on_image_count_changed)

        except Exception as e:
            print(f"{tr('[Load more ERROR]')} {e}")

        finally:
            self._loading = False

    # ─────────────────────────────
    # VIEW UPDATE
    # ─────────────────────────────
    def _update_view(self) -> None:
        """Pushes active visible data models into the gallery view component."""
        self.view.display_images(
            image_data=self.model.get_visible_images(),
            total_count=len(self.model.images),
        )

    # ─────────────────────────────
    # CLICK
    # ─────────────────────────────
    def _on_image_clicked(self, image: Image | None) -> None:
        """Triggers the registered click callback when an image thumbnail is selected.

        Args:
            image (Image | None): The specific image instance that was clicked.
        """
        if self.image_click_callback and image:
            self.image_click_callback(image)

    # ─────────────────────────────
    # PUBLIC API
    # ─────────────────────────────
    def get_view(self) -> ImageSearchedContainerView:
        """Returns the main visual widget managed by this controller.

        Returns:
            The underlying image gallery view instance.
        """
        return self.view

    def set_image_click_callback(self, callback: Callable[[Image], None]) -> None:
        """Registers a callback function to handle image thumbnail click events.

        Args:
            callback (Callable[[Image], None]): Function triggered upon image selection.
        """
        self.image_click_callback = callback

    def clear_images(self) -> None:
        """Resets the internal model cache and purges all displayed images."""
        self._sam3_jobs.clear()
        self.model.reset()
        self.state = SearchState()
        self._update_view()

    def reload_images(self) -> None:
        """Reloads and refreshes the current batch of display elements from scratch."""
        self._sam3_jobs.clear()
        self.model.reset()
        self.view.clear()
        self.research.k = self.view.image_count_spinbox.value()
        search_results = self.research.multi_find()
        self.model.append_results(search_results)
        self._update_view()

    # ─────────────────────────────
    # CONFIG
    # ─────────────────────────────
    def set_thumbnail_size(self, size: int) -> None:
        """Changes the scale dimensions of image thumbnails in the gallery.

        Args:
            size (int): Target pixel scale size value constraints.
        """
        self.thumbnail_size = size
        self._update_view()

    def set_threshold(self, value: float) -> None:
        """Sets the search validation score filter value and updates the UI sliders.

        Args:
            value (float): Percentage factor threshold rating value.
        """
        self.model.set_threshold(value)
        self.view.threshold_slider.setValue(int(value * 100))
        self.view.threshold_value_label.setText(f"{int(value * 100)}%")

    def load(self) -> None:
        """Restores the previous query prompt text and configurations from local files."""
        search = load_from_config("current_search")
        if search:
            self.view.search_controller.set_text(search.get("query", ""))
            self.set_threshold(search.get("threshold", 0.5))

            history.set_current_search(history.current_search)

    def cleanup(self) -> None:
        """Safely stops active search worker threads before closing the component."""
        self.embedding_manager.stop_search()

    def save_search(self) -> None:
        """Saves current search parameters into configuration records and updates history."""
        data = HistoryData(self.state.query, self.model.threshold)

        if data:
            save_in_config("current_search", data.to_dict())

            new_search = Tree(data)
            history.current_search.add_brother(new_search)
            history.history_changed.emit()

            history.current_search_updated.disconnect(self.search)
            history.set_current_search(new_search)
            history.current_search_updated.connect(self.search)

            history.save()

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)

    controller = ImageSearchedContainerController()

    controller.view.show()

    sys.exit(app.exec())