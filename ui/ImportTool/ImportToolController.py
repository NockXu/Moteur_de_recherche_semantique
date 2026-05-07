import sys
import os
from pathlib import Path
from typing import Optional, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot

from ui.ImportTool.ImportToolView import ImportToolView
from ui.ImportTool.ImportToolModel import ImportToolModel
from ui.ImportTool.ProcessingWorker import BatchProcessingManager
from common.Image_Classes.Image import ProcessingStatus, Image
from common.Image_Classes.ImageRepository import ImageRepository
from database.DbService import DbService
from vision.ollama_wrapper import OllamaWrapper

# ─────────────────────────────────────────────
# Thread BDD (non bloquant)
# ─────────────────────────────────────────────
class _DbStatusLoader(QThread):
    finished = pyqtSignal()

    def __init__(self, model: ImportToolModel):
        super().__init__()
        self.model = model

    def run(self):
        self.model.load_db_status()
        self.finished.emit()


# ─────────────────────────────────────────────
# CONTROLLER
# ─────────────────────────────────────────────
class ImportToolController(QObject):

    processing_started = pyqtSignal()
    processing_finished = pyqtSignal()
    processing_stopped = pyqtSignal()

    folder_loaded = pyqtSignal(int)

    def __init__(self, ollama_wrapper: OllamaWrapper = None, model_name: str = "qwen2.5vl:7b"):
        super().__init__()

        self.view = ImportToolView(ollama_base_url=getattr(ollama_wrapper, "base_url", None))
        
        # Créer et injecter le modèle correctement
        self.model = ImportToolModel()
        self.view.set_model(self.model)

        db_service = DbService()
        self.image_repository = ImageRepository(db_service.sqlite, db_service.faiss)

        self.processing_manager = BatchProcessingManager(ollama_wrapper)

        self.current_worker = None
        self._db_loader: Optional[_DbStatusLoader] = None

        # pagination state UI
        self._has_more = True
        self._loading_page = False  # Optimisation anti-double chargement
        
        # Filtrage des images existantes
        self._existing_paths: Optional[set[str]] = None

        self._connect_signals()
        self._load_default_dataset_folder()

    # ─────────────────────────────────────────────
    # SIGNALS
    # ─────────────────────────────────────────────
    def _connect_signals(self):
        self.view.folder_selected.connect(self._handle_folder_selection)
        self.view.start_processing_requested.connect(self._start_processing)
        self.view.stop_processing_requested.connect(self._stop_processing)
        self.view.image_clicked.connect(self._handle_image_clicked)
        self.view.load_more_requested.connect(self._load_next_page_throttled)

    # ─────────────────────────────────────────────
    # FOLDER LOAD
    # ─────────────────────────────────────────────
    def _handle_folder_selection(self, folder_path: str):
        success = self.model.set_folder(folder_path)
        self.view.set_folder(folder_path, success)

        if not success:
            return

        # reset pagination state
        self._has_more = True

        # Récupérer tous les chemins d'images existants en BDD (un seul appel)
        self._existing_paths = self.image_repository.get_all_image_paths()
        
        # first page SANS filtrage (on veut tout afficher)
        images = self.model.load_next_page()
        
        # Marquer les statuts des images existantes
        self._update_images_status_from_db(images)
        
        self.view.load_images(images)

        self.folder_loaded.emit(len(images))

        # load DB status async
        self._start_db_loader()

    # ─────────────────────────────────────────────
    # FILTRAGE IMAGES
    # ─────────────────────────────────────────────
    def _update_images_status_from_db(self, images: List[Image]):
        """Met à jour le statut des images selon leur présence en BDD"""
        if not self._existing_paths:
            return
        
        for img in images:
            if str(img.path) in self._existing_paths:
                img.status = ProcessingStatus.COMPLETED
            else:
                img.status = ProcessingStatus.PENDING

    # ─────────────────────────────────────────────
    # PAGINATION
    # ─────────────────────────────────────────────
    def _load_next_page(self):
        if not self._has_more:
            return

        images = self.model.load_next_page()

        if not images:
            self._has_more = False
            return

        # Mettre à jour les statuts avant d'ajouter
        self._update_images_status_from_db(images)
        self.view.append_images(images)

    def _load_next_page_throttled(self):
        """Version optimisée avec throttling pour éviter les appels multiples"""
        if not self._has_more:
            return
        
        # Éviter les chargements multiples rapides (optimisation performance)
        if hasattr(self, '_loading_page') and self._loading_page:
            return
        
        self._loading_page = True
        
        try:
            images = self.model.load_next_page()
            
            if not images:
                self._has_more = False
                return
            
            # Mettre à jour les statuts avant d'ajouter
            self._update_images_status_from_db(images)
            self.view.append_images(images)
        finally:
            self._loading_page = False

    # ─────────────────────────────────────────────
    # DB LOADER
    # ─────────────────────────────────────────────
    def _start_db_loader(self):
        if self._db_loader and self._db_loader.isRunning():
            self._db_loader.quit()
            self._db_loader.wait()

        self._db_loader = _DbStatusLoader(self.model)
        self._db_loader.finished.connect(self._on_db_loaded)
        self._db_loader.start()

    @pyqtSlot()
    def _on_db_loaded(self):
        # refresh UI statuses (COMPLETED badges etc.)
        self.view._refresh_image_display()
        self.view._update_progress_display()

    # ─────────────────────────────────────────────
    # PROCESSING
    # ─────────────────────────────────────────────
    def _start_processing(self):
        if self.processing_manager.is_processing():
            return

        images = self.model.get_loaded_images()
        if not images:
            return

        self.model.reset_all_status()

        self.current_worker = self.processing_manager.start_batch_processing(
            images,
            on_progress=self._on_image_progress,
            on_image_processed=self._on_image_processed,
            on_image_error=self._on_image_error,
            on_complete=self._on_processing_complete,
            on_stopped=self._on_processing_stopped,
        )

        self.view.set_processing_mode(True)
        self.processing_started.emit()

    def _stop_processing(self):
        if not self.processing_manager.is_processing():
            return

        self.processing_manager.stop_current_processing()
        self._on_processing_stopped()

    # ─────────────────────────────────────────────
    # CALLBACKS PROCESSING
    # ─────────────────────────────────────────────
    def _on_image_progress(self, image_path: str, status: ProcessingStatus):
        self.model.update_image_status(image_path, status)
        self.view.update_image_status(image_path, status)

    def _on_image_processed(self, image_path: str, description: str, embedding: list):
        self.model.update_image_status(
            image_path,
            ProcessingStatus.COMPLETED,
            description=description,
            embedding=embedding
        )

    def _on_image_error(self, image_path: str, error: str):
        self.model.update_image_status(
            image_path,
            ProcessingStatus.ERROR,
            error_message=error
        )

    def _on_processing_complete(self):
        self.view.set_processing_mode(False)
        self.processing_finished.emit()

    def _on_processing_stopped(self):
        self.view.set_processing_mode(False)
        self.processing_stopped.emit()

    # ─────────────────────────────────────────────
    # UI EVENTS
    # ─────────────────────────────────────────────
    def _handle_image_clicked(self, img):
        info = self.model.get_image_info(img.path)
        if info:
            print(f"{Path(img.path).name} - {info.status.value}")

    # ─────────────────────────────────────────────
    # DEFAULT FOLDER
    # ─────────────────────────────────────────────
    def _load_default_dataset_folder(self):
        try:
            project_root = Path(__file__).resolve().parents[3]
            dataset_path = project_root / "dataset"

            if dataset_path.exists():
                self._handle_folder_selection(str(dataset_path))
        except Exception as e:
            print(f"Erreur auto dataset: {e}")

    # ─────────────────────────────────────────────
    # API
    # ─────────────────────────────────────────────
    def get_view(self):
        return self.view

    def get_model(self):
        return self.model

    def is_processing(self) -> bool:
        return self.processing_manager.is_processing()

    def cleanup(self):
        if self._db_loader and self._db_loader.isRunning():
            self._db_loader.quit()
            self._db_loader.wait()

        if self.is_processing():
            self.processing_manager.stop_current_processing()

        self.view.cleanup()

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    controller = ImportToolController()
    controller.get_view().show()
    sys.exit(app.exec())
