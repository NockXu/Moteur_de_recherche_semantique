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

    def __init__(self, thumbnail_size: int = 150):
        super().__init__()

        self.view = ImageSearchedContainerView()
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

        print('start')

        self.embedding_manager.start_search(
            query=search_text,
            threshold=self.model.threshold,
            cursor=self.state.cursor,
            auto_research=self.research
        )
        print('end')

    # ─────────────────────────────
    # SEARCH CALLBACK
    # ─────────────────────────────
    def _on_search_finished(self, result):
        print(f"[DEBUG] _on_search_finished appelé avec result: {type(result)}")

        self._loading = False

        if result is None:
            print("[DEBUG] Result est None, pas de résultats à afficher")
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
        if not self.state.query:
            return

        if self._loading:
            return

        self._loading = True

        self.research.k += 500

        try:
            result = self.research.find(
                query=self.state.query,
                threshold=self.model.threshold
            )

            print(f"[DEBUG] Load more: {len(result.get('images', []))} images trouvées")
            new_images = self.model.append_results(result)
            print(f"[DEBUG] Total images dans modèle: {len(self.model.images)}")
            
            self.view.display_images(
                image_data=new_images,
                total_count=len(self.model.images),
            )

        except Exception as e:
            print(f"Load more error: {e}")

        finally:
            print("[DEBUG] Fin du chargement")
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

    def set_max_per_load(self, value: int):
        # Cette méthode n'existe pas dans le modèle, on l'ignore pour l'instant
        pass

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)

    controller = ImageSearchedContainerController()

    controller.view.show()

    sys.exit(app.exec())