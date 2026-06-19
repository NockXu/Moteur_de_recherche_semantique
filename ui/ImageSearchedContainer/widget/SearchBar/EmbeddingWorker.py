import sys
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ui.ImageSearchedContainer.Research import Research
from common.Image_Classes.ImageRepository import ImageRepository
from database.DbService import DbService
from ui.utils.i18n import tr


# =========================
# WORKER
# =========================
class EmbeddingWorker(QObject):
    """Background worker that executes the vector database search.

    Signals:
        finished (pyqtSignal[dict]): Emitted with search results when done.
        error (pyqtSignal[str]): Emitted with an error message if the search fails.

    Args:
        query (str | None): The search text prompt.
        threshold (float): Minimum similarity score limit. Defaults to 0.0.
        cursor (tuple[float, int] | None): Pagination marker for loading database pages.
        auto_research (Research | None): Research component instance. Defaults to None.
    """

    finished = pyqtSignal(dict)  # SearchResults
    error = pyqtSignal(str)

    def __init__(self, query, threshold=0.0, cursor=None, auto_research : Research =None):
        super().__init__()

        self.query = query
        self.threshold = threshold
        self.cursor = cursor

        self.auto_research = auto_research or Research(
            ImageRepository(DbService().sqlite, DbService().faiss)
        )

    def run(self) -> None:
        """Executes the search query on a background thread."""
        try:
            result = self.auto_research.multi_find()
            
            if result is None:
                self.on_finished({'images': [], 'k': self.auto_research.k})
            else:
                self.on_finished(result)

        except Exception as e:
            self.on_error(str(e))

    def on_finished(self, result : dict) -> None:
        """Emits the finished signal with the search results.

        Args:
            result (dict): The dictionary containing found images.
        """
        self.finished.emit(result)

    def on_error(self, error : str) -> None:
        """Emits the error signal with the failure description.

        Args:
            error (str): The text description of the error.
        """
        self.error.emit(error)


# =========================
# MANAGER
# =========================
class AsyncEmbeddingManager(QObject):
    """Manages lifecycles of asynchronous database embedding workers and threads.

    Signals:
        result (pyqtSignal[dict]): Broadcasts final search results dictionary payloads.
    """
    result = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.current_worker = None
        self.current_thread = None

    # -------------------------
    # START SEARCH
    # -------------------------
    def start_search(
        self,
        query,
        threshold=0.0,
        cursor=None,
        auto_research=None
    ) -> tuple[EmbeddingWorker, QThread]:
        """Stops any active query thread and spawns a new background search job.

        Args:
            query (str | None): Target text prompt keywords.
            threshold (float): Numerical search value boundaries. Defaults to 0.0.
            cursor (tuple[float, int] | None): Search page pagination markers. Defaults to None.
            auto_research (Research | None): Active search provider component. Defaults to None.

        Returns:
            A tuple tracking the newly created worker instance and thread container.
        """
        self.stop_search()

        self.current_worker = EmbeddingWorker(
            query=query,
            threshold=threshold,
            cursor=cursor,
            auto_research=auto_research
        )

        self.current_thread = QThread()
        self.current_worker.moveToThread(self.current_thread)

        # start
        self.current_thread.started.connect(self.current_worker.run)

        self.current_worker.finished.connect(self._handle_finished)
        self.current_worker.error.connect(self._handle_error)
        # internal cleanup
        self.current_worker.finished.connect(self.current_thread.quit)
        self.current_worker.error.connect(self.current_thread.quit)
        self.current_thread.finished.connect(self._cleanup)

        self.current_thread.start()

        return self.current_worker, self.current_thread

    # -------------------------
    # INTERNAL CALLBACKS
    # -------------------------
    def _handle_finished(self, result: dict) -> None:
        """Receives and forwards successfully generated background database metrics.

        Args:
            result (dict): Data payload containing list collection elements.
        """
        try:
            self.result.emit(result)
        except Exception as e:
            print(e)

    def _handle_error(self, error: str) -> None:
        """Logs worker exceptions and emits an empty fallback payload structure.

        Args:
            error (str): Error description message text.
        """
        try:
            print(f"{tr('[EmbeddingWorker ERROR]')} {error}")
            self.result.emit({})
        except Exception as e:
            print(e)

    # -------------------------
    # CLEANUP
    # -------------------------
    def _cleanup(self) -> None:
        """Safely detaches signals, deletes pointers, and flushes used thread memory."""
        thread = self.current_thread
        worker = self.current_worker

        self.current_thread = None
        self.current_worker = None

        if thread:
            try:
                thread.finished.disconnect(self._cleanup)
            except RuntimeError:
                pass
            thread.deleteLater()

        if worker:
            worker.deleteLater()

    # -------------------------
    # CONTROL
    # -------------------------
    def is_running(self) -> bool:
        """Checks whether a search worker is currently running on a background thread.

        Returns:
            True if active worker processes exist, otherwise False.
        """
        return self.current_thread is not None and self.current_thread.isRunning()

    def stop_search(self) -> None:
        """Aborts the running search thread immediately and clears tracking variables."""
        if self.current_worker:
            self.current_worker.blockSignals(True)
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.quit()
            self.current_thread.wait()
        self._cleanup()

    # -------------------------
    # COMPAT
    # -------------------------
    def start_embedding(self, text: str) -> tuple[EmbeddingWorker, QThread]:
        """Compatibility wrapper that maps incoming text strings directly to start_search.

        Args:
            text (str): Query string parameters.

        Returns:
            A tuple tracking the active initialized worker and thread context.
        """
        return self.start_search(
            query=text
        )