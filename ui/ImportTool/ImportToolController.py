import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ui.ImportTool.ImportToolView import ImportToolView
from ui.ImportTool.ImportToolModel import ImportToolModel
from ui.ImportTool.ProcessingWorker import ProcessingWorker, BatchProcessingManager
from common.ImageInfo import ProcessingStatus, ImageInfo
from vision.ollama_wrapper import OllamaWrapper
from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
from typing import Optional
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Worker léger : charge le statut BDD sans bloquer l'UI
# ─────────────────────────────────────────────────────────────────────────────

class _DbStatusLoader(QThread):
    """Charge en arrière-plan les chemins déjà présents en BDD."""
    finished = pyqtSignal()

    def __init__(self, model: ImportToolModel):
        super().__init__()
        self._model = model

    def run(self):
        self._model.load_db_status()
        self.finished.emit()


# ─────────────────────────────────────────────────────────────────────────────
# Contrôleur principal
# ─────────────────────────────────────────────────────────────────────────────

class ImportToolController(QObject):

    processing_started  = pyqtSignal()
    processing_finished = pyqtSignal()
    processing_stopped  = pyqtSignal()
    image_processed     = pyqtSignal(str, str, list)
    image_error         = pyqtSignal(str, str)
    folder_loaded       = pyqtSignal(int)

    def __init__(self, ollama_wrapper: OllamaWrapper = None, model: str = "qwen2.5vl:7b", parent=None):
        super().__init__(parent)

        base_url = getattr(ollama_wrapper, 'base_url', None) if ollama_wrapper else None
        self.view = ImportToolView(ollama_base_url=base_url)
        self.model = self.view.get_model()
        self.ollama_wrapper  = ollama_wrapper
        self.model_name      = model
        self.processing_manager = BatchProcessingManager(ollama_wrapper)
        self.current_worker  = None
        self._stop_requested = False
        self._db_loader: Optional[_DbStatusLoader] = None

        self._connect_signals()
        self._load_default_dataset_folder()

    def _connect_signals(self):
        self.view.folder_selected.connect(self._handle_folder_selection)
        self.view.start_processing_requested.connect(self._start_processing)
        self.view.stop_processing_requested.connect(self._stop_processing)
        self.view.image_clicked.connect(self._handle_image_clicked)

    # ─────────────────────────────────────────────────────────────────────────
    # Sélection dossier
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_folder_selection(self, folder_path: str):
        try:
            # 1. Scan des fichiers (rapide — juste des Path)
            success = self.model.set_folder(folder_path)
            self.view.set_folder(folder_path, success)

            if not success:
                self.folder_loaded.emit(0)
                return

            # 2. Afficher immédiatement la première page (sans statut BDD)
            self.view.load_images([])   # reset + première page depuis le modèle
            self.folder_loaded.emit(self.model.get_images_count())

            # 3. Charger le statut BDD en arrière-plan, puis rafraîchir
            self._start_db_loader()

        except Exception as e:
            print(f"Erreur sélection dossier: {e}")
            self.view.set_folder(folder_path, False)
            self.folder_loaded.emit(0)

    def _start_db_loader(self):
        """Lance le chargement BDD dans un thread séparé."""
        if self._db_loader and self._db_loader.isRunning():
            self._db_loader.quit()
            self._db_loader.wait()

        self._db_loader = _DbStatusLoader(self.model)
        self._db_loader.finished.connect(self._on_db_loaded)
        self._db_loader.start()

    @pyqtSlot()
    def _on_db_loaded(self):
        """Rafraîchit l'affichage une fois le statut BDD connu."""
        print("✅ Statut BDD chargé — rafraîchissement de la vue")
        # Réinitialiser l'affichage pour que les badges COMPLETED apparaissent
        self.view._refresh_image_display()
        self.view._update_progress_display()

    # ─────────────────────────────────────────────────────────────────────────
    # Traitement
    # ─────────────────────────────────────────────────────────────────────────

    def _start_processing(self):
        if self.processing_manager.is_processing():
            return

        # get_all_images() instancie toutes les ImageInfo (acceptable ici car
        # l'utilisateur a cliqué "Commencer" — l'attente est attendue)
        images = self.model.get_all_images()
        if not images:
            return

        has_unprocessed = any(img.status == ProcessingStatus.NOT_STARTED for img in images)
        if has_unprocessed:
            self.model.reset_unprocessed_status()

        self._stop_requested = False

        try:
            self.current_worker = self.processing_manager.start_batch_processing(
                images,
                on_progress=self._on_image_progress,
                on_image_processed=self._on_image_processed,
                on_image_error=self._on_image_error,
                on_complete=self._on_processing_complete,
                on_stopped=self._on_processing_stopped,
                model=self.model_name,
            )
            self.view.set_processing_mode(True)
            self.processing_started.emit()

        except Exception as e:
            print(f"Erreur démarrage traitement: {e}")
            self.view.set_processing_mode(False)

    def _stop_processing(self):
        if not self.processing_manager.is_processing():
            return
        self.view.set_stop_requested()
        self.processing_manager.stop_current_processing()
        self._on_processing_stopped()

    def _on_image_progress(self, image_path: str, status: ProcessingStatus):
        self.model.update_image_status(image_path, status)
        self.view.update_image_status(image_path, status)

    def _on_image_processed(self, image_path: str, description: str, embedding: list):
        if self._stop_requested:
            return
        self.model.update_image_status(image_path, ProcessingStatus.COMPLETED,
                                       description=description, embedding=embedding)
        self.image_processed.emit(image_path, description, embedding)

    def _on_image_error(self, image_path: str, error_message: str):
        if self._stop_requested:
            return
        self.model.update_image_status(image_path, ProcessingStatus.ERROR,
                                       error_message=error_message)
        self.image_error.emit(image_path, error_message)

    def _on_processing_complete(self):
        self.current_worker = None
        self.view.set_processing_mode(False)
        self.processing_finished.emit()
        total     = self.model.get_images_count()
        completed = self.model.get_completed_count()
        errors    = self.model.get_error_count()
        print(f"\nTraitement terminé: {completed}/{total} OK, {errors} erreurs")

    def _on_processing_stopped(self):
        if getattr(self, "_is_stopping", False):
            return
        self._is_stopping = True
        self.current_worker = None
        self.view.set_processing_mode(False)
        self.model.reset_in_progress_status()
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.view._refresh_image_display)
        self.processing_stopped.emit()
        self._is_stopping = False

    # ─────────────────────────────────────────────────────────────────────────
    # Misc
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_image_clicked(self, img: ImageInfo):
        info = self.model.get_image_info(img.path)
        if info:
            print(f"\nImage: {Path(img.path).name} — {info.status.value}")

    def get_view(self) -> ImportToolView:
        return self.view

    def get_model(self) -> ImportToolModel:
        return self.model

    def set_ollama_wrapper(self, wrapper: OllamaWrapper):
        self.ollama_wrapper = wrapper
        self.processing_manager.ollama_wrapper = wrapper

    def is_processing(self) -> bool:
        return self.processing_manager.is_processing()

    def get_connection_verificator(self):
        return self.view.get_connection_verificator()

    def cleanup(self):
        if self._db_loader and self._db_loader.isRunning():
            self._db_loader.quit()
            self._db_loader.wait()
        if self.is_processing():
            self.processing_manager.stop_current_processing()
        try:
            self.view.cleanup()
        except Exception:
            pass

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass

    def _load_default_dataset_folder(self):
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            dataset_path = os.path.join(project_root, "dataset")
            if os.path.exists(dataset_path) and os.path.isdir(dataset_path):
                print(f"Chargement automatique: {dataset_path}")
                self._handle_folder_selection(dataset_path)
        except Exception as e:
            print(f"Erreur chargement dataset: {e}")

    # Stubs compatibilité
    def reset_all(self):
        if self.is_processing():
            self._stop_processing()
        self.model.reset_all_status()
        self.view._on_reset_clicked()

    def get_statistics(self) -> dict:
        counts = self.model.get_images_by_status()
        total  = self.model.get_images_count()
        return {
            "total_images":  total,
            "not_started":   counts.get(ProcessingStatus.NOT_STARTED, 0),
            "in_progress":   counts.get(ProcessingStatus.IN_PROGRESS, 0),
            "completed":     counts.get(ProcessingStatus.COMPLETED, 0),
            "errors":        counts.get(ProcessingStatus.ERROR, 0),
            "success_rate":  (counts.get(ProcessingStatus.COMPLETED, 0) / total * 100) if total > 0 else 0,
            "selected_folder": str(self.model.selected_folder) if self.model.selected_folder else None,
        }

    def save_results(self, output_file=None) -> bool:
        return False

    def load_results(self, input_file=None) -> bool:
        return False


def create_import_tool(ollama_wrapper: OllamaWrapper = None, model: str = "qwen2.5vl:7b") -> ImportToolController:
    return ImportToolController(ollama_wrapper, model)