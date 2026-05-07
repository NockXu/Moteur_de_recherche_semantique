import sys
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ui.ImageSearchedContainer.Research import Research
from common.Image_Classes.ImageRepository import ImageRepository
from database.DbService import DbService


# =========================
# WORKER
# =========================
class EmbeddingWorker(QObject):

    finished = pyqtSignal(object)  # SearchResults
    error = pyqtSignal(str)

    def __init__(self, query, threshold=0.0, cursor=None, auto_research=None):
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
                threshold=self.threshold,
                cursor=self.cursor
            )

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))


# =========================
# MANAGER
# =========================
class AsyncEmbeddingManager:

    def __init__(self):
        self.current_worker = None
        self.current_thread = None

        # callbacks
        self.on_finished_cb = None
        self.on_error_cb = None

    # -------------------------
    # START SEARCH
    # -------------------------
    def start_search(
        self,
        query,
        threshold=0.0,
        cursor=None,
        auto_research=None,
        on_finished=None,
        on_error=None
    ):

        self.stop_search()

        self.on_finished_cb = on_finished
        self.on_error_cb = on_error

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

        self.current_thread.start()

        return self.current_worker, self.current_thread

    # -------------------------
    # INTERNAL CALLBACKS
    # -------------------------
    def _handle_finished(self, result):
        try:
            if self.on_finished_cb:
                self.on_finished_cb(result)
        finally:
            self._cleanup()

    def _handle_error(self, error):
        try:
            if self.on_error_cb:
                self.on_error_cb(error)
            else:
                print(f"[EmbeddingWorker ERROR] {error}")
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
    def start_embedding(self, model, text, wrapper=None, on_finished=None, on_error=None):
        return self.start_search(
            query=text,
            on_finished=on_finished,
            on_error=on_error
        )