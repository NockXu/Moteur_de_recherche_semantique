import sys
import time
from typing import List, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

from ui.ImageSearchedContainer.ImageSearchedContainerView import ImageSearchedContainerView
from ui.ImageSearchedContainer.ImageSearchedContainerModel import ImageSearchedContainerModel
from ui.ImageSearchedContainer.Research import Research
from common.Image_Classes.Image import Image
from common.Image_Classes.ImageRepository import ImageRepository, SearchResults
from database.DbService import DbService

from ui.ImageSearchedContainer.widget.SearchBar.EmbeddingWorker import AsyncEmbeddingManager
from vision.SAM3AsyncManager import get_sam3_manager

from common.History_Classes import history, HistoryData, Tree
from common.Image_Classes.Image import Image

from ui import save_in_config, load_from_config
from ui.ImageSearchedContainer.SAM3ProgressWindow import SAM3ProgressWindow

# =========================
# STATE
# =========================
class SearchState:
    def __init__(self):
        self.query: Optional[str] = None
        self.cursor: Optional[tuple[float, int]] = None
        self.has_more: bool = False

# =========================
# CONTROLLER
# =========================
class ImageSearchedContainerController(QObject):

    images_loaded = pyqtSignal(int)

    def __init__(self, thumbnail_size: int = 150, theme_changed: Optional[pyqtSignal] = None):
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

        self.image_click_callback: Optional[Callable[[Image], None]] = None

        self._connect_signals()

    # ─────────────────────────────
    # SIGNALS
    # ─────────────────────────────
    def _connect_signals(self):
        self.view.image_clicked.connect(self._on_image_clicked)
        self.view.load_more_requested.connect(self.load_more_images)
        self.view.reload_requested.connect(self.reload_images)
        self.view.search_controller.view.search_triggered.connect(self._on_search_triggered)
        self.embedding_manager.result.connect(self._on_search_finished)
        self.sam3_manager.result.connect(self._on_sam3_image_finished)
        self.sam3_manager.error.connect(self._on_sam3_image_error)
        self.view.threshold_changed.connect(self._on_threshold_changed)
        history.current_search_updated.connect(self.search)

    def _on_results_displayed(self, results: dict[str, list[dict]]):
        """
        Slot connecté à Image Preview

        Reçoit la liste de dicts :
            [{"type":"result", "prompt":str, "index":int,
              "score":float, "box":[x1,y1,x2,y2],
              "color": QColor, ...}, ...]

        Quand la liste contient tous les résultats (aucune sélection),
        ResultsTable les émet tous — on les affiche tous normalement.
        """
        self.view.update_images(results)

    def _on_results_cleared(self, image_paths: list[str]):
        """
        Slot connecté à Image Preview

        Quand les résultats sont effacés, on met à jour la vue.
        """
        self.view.clear_results(image_paths)

    def _on_multi_send(self, prompts: list[dict]):
        """
        Slot connecté à SAM3Widget

        Reçoit la liste de prompts et les envoie à l'embedding manager.
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

    def _on_sam3_image_finished(self, job_id: str, image_path: str, results):
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

    def _on_sam3_image_error(self, job_id: str, error: str):
        if not job_id or job_id not in self._sam3_jobs:
            return

        image = self._sam3_jobs.pop(job_id, None)
        if image:
            print(f"[SAM3 multi-image ERROR] {image.path}: {error}")

        if not self._sam3_jobs:
            self._sam3_progress_window.finish()

    def _convert_sam3_results(self, results: list[dict]) -> list[dict]:
        """Convertit le format brut SAM3 en format attendu par draw_results."""
        from PyQt6.QtGui import QColor
        import torch

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

    def _on_sam3_cancelled(self):
        self.sam3_manager.cancel_all()
        self._sam3_jobs.clear()
        self.old_prompt = None  # force un retraitement complet au prochain send
        self._sam3_progress_window.reset()

    # ─────────────────────────────
    # SEARCH ENTRY POINT
    # ─────────────────────────────
    def _on_search_triggered(self, search_text: str):
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

    def search(self):
        if self._sam3_jobs:
            self.sam3_manager.cancel_all()
            self._sam3_jobs.clear()
        self.old_prompt = None
        self._sam3_progress_window.reset()
        search_text = history.current_search.node.query

        self.view.search_controller.set_text(search_text)
        self.set_threshold(history.current_search.node.threshold)

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
    def _on_search_finished(self, result):
        self._loading = False

        if result is None:
            return

        self.model.reset()
        self.model.append_results({'images': result.get('images', []), 'k': result.get('k', 200)})
        self._update_view()

    def _on_search_error(self, error: str):
        self._loading = False
        print(f"[Search ERROR] {error}")

    def _on_threshold_changed(self, threshold: float):
        """Appelé quand le threshold change depuis la vue"""
        self.model.set_threshold(threshold)

    # ─────────────────────────────
    # LOAD MORE (INFINITE SCROLL)
    # ─────────────────────────────
    def load_more_images(self, reset: bool = False):
        if self._loading:
            return

        self._loading = True

        self.research.k = self.view.image_count_spinbox.value()

        try:
            result = self.research.find(
                query=self.state.query,
                threshold=self.model.threshold
            )

            new_images = self.model.append_results(result)
            
            self.view.display_images(
                image_data=new_images,
                total_count=len(self.model.images),
            )

        except Exception as e:
            print(f"Load more error: {e}")

        finally:
            self._loading = False

    # ─────────────────────────────
    # VIEW UPDATE
    # ─────────────────────────────
    def _update_view(self):
        self.view.display_images(
            image_data=self.model.get_visible_images(),
            total_count=len(self.model.images),
        )

    # ─────────────────────────────
    # CLICK
    # ─────────────────────────────
    def _on_image_clicked(self, image: Optional[Image]) -> None:
        if self.image_click_callback and image:
            self.image_click_callback(image)

    # ─────────────────────────────
    # PUBLIC API
    # ─────────────────────────────
    def get_view(self):
        return self.view

    def set_image_click_callback(self, callback: Callable[[Image], None]):
        self.image_click_callback = callback

    def clear_images(self):
        self._sam3_jobs.clear()
        self.model.reset()
        self.state = SearchState()
        self._update_view()

    def reload_images(self):
        self._sam3_jobs.clear()
        self.model.reset()
        self.view.clear()
        self.research.k = self.view.image_count_spinbox.value()
        search_results = self.research.find()
        self.model.append_results(search_results)
        self._update_view()

    # ─────────────────────────────
    # CONFIG
    # ─────────────────────────────
    def set_thumbnail_size(self, size: int):
        self.thumbnail_size = size
        self._update_view()

    def set_threshold(self, value: float):
        self.model.set_threshold(value)
        self.view.threshold_slider.setValue(int(value * 100))
        self.view.threshold_value_label.setText(f"{int(value * 100)}%")

    def load(self):
        search = load_from_config("current_search")
        if search:
            self.view.search_controller.set_text(search.get("query", ""))
            self.set_threshold(search.get("threshold", 0.5))

            history.set_current_search(history.current_search)

    def cleanup(self):
        self.embedding_manager.stop_search()

    def save_search(self):
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