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

from common.History_Classes import history, HistoryData, Tree

from ui import save_in_config, load_from_config

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
        self.view.threshold_changed.connect(self._on_threshold_changed)
        history.current_search_updated.connect(self.search)

    # ─────────────────────────────
    # SEARCH ENTRY POINT
    # ─────────────────────────────
    def _on_search_triggered(self, search_text: str):
        self.state.query = search_text
        self.state.cursor = None
        self.state.has_more = False

        self.model.reset()
        self.view.clear()
        self._update_view()

        self._loading = True

        self.save_search()

        self.embedding_manager.start_search(
            query=search_text,
            threshold=self.model.threshold,
            cursor=self.state.cursor,
            auto_research=self.research
        )

    def search(self):
        search_text = history.current_search.node.query

        self.view.search_controller.set_text(search_text)
        self.set_threshold(history.current_search.node.threshold)

        self.state.query = search_text
        self.state.cursor = None
        self.state.has_more = False

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

        self.research.k += 500

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
    def _on_image_clicked(self, image_path: str):
        image_info = self.model.get_image_by_path(image_path)

        if self.image_click_callback and image_info:
            self.image_click_callback(image_info)

    # ─────────────────────────────
    # PUBLIC API
    # ─────────────────────────────
    def get_view(self):
        return self.view

    def set_image_click_callback(self, callback: Callable[[Image], None]):
        self.image_click_callback = callback

    def clear_images(self):
        self.model.reset()
        self.state = SearchState()
        self._update_view()

    def reload_images(self):
        self.model.reset()
        self.view.clear()
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
            history.set_current_search(Tree(HistoryData(search.get("query", ""), search.get("threshold", 0.5))))

    def save_search(self):
        data = HistoryData(self.state.query, self.model.threshold)

        if data:
            save_in_config("current_search", data.to_dict())

            current_search = Tree(data)
            history.current_search.add_child(current_search)
            history.history_changed.emit()

            history.current_search_updated.disconnect(self.search)
            history.set_current_search(current_search)
            history.current_search_updated.connect(self.search)

            history.save()
             

        


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)

    controller = ImageSearchedContainerController()

    controller.view.show()

    sys.exit(app.exec())