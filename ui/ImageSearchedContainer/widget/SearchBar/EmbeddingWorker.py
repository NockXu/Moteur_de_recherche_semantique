import sys
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ui.ImageSearchedContainer.Research import Research
from common.Image_Classes.ImageRepository import ImageRepository
from database.DbService import DbService


# =========================
# WORKER
# =========================
class EmbeddingWorker(QObject):

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

    def run(self):
        try:
            result = self.auto_research.find(
                query=self.query,
                threshold=self.threshold
            )
            
            if result is None:
                self.on_finished({'images': [], 'k': self.auto_research.k})
            else:
                self.on_finished(result)

        except Exception as e:
            self.on_error(str(e))

    def on_finished(self, result : dict) -> None:
        self.finished.emit(result)

    def on_error(self, error : str) -> None:
        self.error.emit(error)


# =========================
# MANAGER
# =========================
class AsyncEmbeddingManager(QObject):
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
    ):

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

        # internal cleanup
        self.current_worker.finished.connect(self._handle_finished)
        self.current_worker.error.connect(self._handle_error)
        self.current_worker.finished.connect(self.current_thread.quit)
        self.current_worker.error.connect(self.current_thread.quit)
        self.current_thread.finished.connect(self._cleanup)

        self.current_thread.start()

        return self.current_worker, self.current_thread

    # -------------------------
    # INTERNAL CALLBACKS
    # -------------------------
    def _handle_finished(self, result):
        try:
            self.result.emit(result)
        finally:
            self._cleanup()

    def _handle_error(self, error):
        try:
            print(f"[EmbeddingWorker ERROR] {error}")
            self.result.emit({})
        finally:
            self._cleanup()

    # -------------------------
    # CLEANUP
    # -------------------------
    def _cleanup(self):
        if self.current_thread:
            self.current_thread.quit()
            self.current_thread.wait()
            self.current_thread.deleteLater()
            self.current_thread = None

        if self.current_worker:
            self.current_worker.deleteLater()
            self.current_worker = None

    # -------------------------
    # CONTROL
    # -------------------------
    def is_running(self):
        return self.current_thread is not None and self.current_thread.isRunning()

    def stop_search(self):
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.quit()
            self.current_thread.wait()

        self._cleanup()

    # -------------------------
    # COMPAT
    # -------------------------
    def start_embedding(self, text):
        return self.start_search(
            query=text
        )