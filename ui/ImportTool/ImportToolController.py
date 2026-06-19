import sys
import os
from pathlib import Path
from typing import Optional, List

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from ui.ImportTool.ImportToolView import ImportToolView
from ui.ImportTool.ImportToolModel import ImportToolModel
from ui.ImportTool.ProcessingWorker import BatchProcessingManager
from common.Image_Classes.Image import ProcessingStatus, Image
from common.Image_Classes.ImageRepository import ImageRepository
from database.DbService import DbService
from vision.ollama_wrapper import OllamaWrapper

from ui import load_config, load_from_config, save_in_config


# ─────────────────────────────────────────────
# CONTROLLER
# ─────────────────────────────────────────────
class ImportToolController(QObject):
    """Controller component coordinating the dataset ingestion and batch vision-language analysis.

    Binds the ImportToolView interaction events with the ImportToolModel business layer state,
    orchestrates paginated scrolling, and handles background worker task execution loops.

    Args:
        ollama_wrapper (OllamaWrapper):
            Optional API backend service wrapper instance targeting local model serving. Defaults to None.
        model_name (str):
            The target multimodal model configuration name. Defaults to "qwen2.5vl:7b".
        theme_changed (pyqtSignal):
            Optional external state transmission signal capturing visual color changes. Defaults to None.

    """

    processing_started = pyqtSignal()
    processing_finished = pyqtSignal()
    processing_stopped = pyqtSignal()

    folder_loaded = pyqtSignal(int)

    def __init__(self, ollama_wrapper: OllamaWrapper = None, model_name: str = "qwen2.5vl:7b", theme_changed: pyqtSignal = None):
        super().__init__()

        self.view = ImportToolView(ollama_base_url=getattr(ollama_wrapper, "base_url", None))
        if theme_changed:
            theme_changed.connect(self.view._on_theme_changed)
        
        self.model = ImportToolModel()
        self.view.set_model(self.model)

        db_service = DbService()
        self.image_repository = ImageRepository(db_service.sqlite, db_service.faiss)

        self.processing_manager = BatchProcessingManager(ollama_wrapper)
        self.current_worker = None

        # pagination state UI
        self._has_more = True
        self._loading_page = False 
        
        # Filtrage des images existantes
        self._existing_paths: set[str] | None = None

        self._connect_signals()

    # ─────────────────────────────────────────────
    # SIGNALS
    # ─────────────────────────────────────────────
    def _connect_signals(self):
        """Map user interaction signals from the UI view component to operational controller handlers."""
        self.view.folder_selected.connect(self._on_folder_selected)
        self.view.start_processing_requested.connect(self._start_processing)
        self.view.stop_processing_requested.connect(self._stop_processing)
        self.view.image_clicked.connect(self._handle_image_clicked)
        self.view.load_more_requested.connect(self._load_next_page_throttled)

    def _on_folder_selected(self, folder_path: str):
        """Save selected target variables to system configurations and execute folder setup routines.

        Args:
            folder_path (str):
                The absolute directory file path targeted for file scanning.

        """
        save_in_config("import_image_folder", folder_path)
        self._handle_folder_selection(folder_path)

    # ─────────────────────────────────────────────
    # FOLDER LOAD
    # ─────────────────────────────────────────────
    def _handle_folder_selection(self, folder_path: str):
        """Flush old visual layouts, parse data inputs, and update overall tracking limits.

        Args:
            folder_path (str):
                The verified file location string to process.

        """
        # ─── FIX : Nettoyer l'ancienne vue pour éviter l'accumulation ───
        if hasattr(self.view, 'clear') and callable(self.view.clear):
            self.view.clear()
        elif hasattr(self.view, 'clear_images') and callable(self.view.clear_images):
            self.view.clear_images()
        elif hasattr(self.view, 'image_grid') and self.view.image_grid:
            # Sécurité si aucune méthode de clear n'existe : on vide manuellement le layout
            layout = self.view.image_grid.layout() if hasattr(self.view.image_grid, 'layout') else getattr(self.view, 'layout', lambda: None)()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

        # Init du modèle
        success = self.model.set_folder(folder_path)
        self.view.set_folder(folder_path, success)

        if not success:
            return

        self._has_more = True
        self._existing_paths = self.image_repository.get_all_image_paths()
        
        # ─── Calcul global des images déjà traitées dans ce dossier ───
        already_processed = self.model.calculate_already_processed_count(self._existing_paths)
        
        # Charger la première page visuelle (60 images)
        images = self.model.load_next_page()
        self._update_images_status_from_db(images)
        
        # La vue affiche uniquement les 60 nouvelles images du nouveau dossier
        self.view.display_images(images)
        
        # ─── SYNCHRONISATION PROGRESSION MET À JOUR AVEC LE VRAI TOTAL TRAITÉ ───
        total_count = self.model.get_total_images_count()
        
        if hasattr(self.view, 'progress'):
            self.view.progress.setMaximum(total_count)
            # On initialise la barre de progression au nombre déjà traité globalement
            self.view.progress.setValue(already_processed)
            
        if hasattr(self.view, '_progress_label'):
            self.view._progress_label.setText(
                f"En attente… ({already_processed} / {total_count} images traitées)"
            )

        self.folder_loaded.emit(total_count)

    # ─────────────────────────────────────────────
    # FILTRAGE IMAGES
    # ─────────────────────────────────────────────
    def _update_images_status_from_db(self, images: list[Image]):
        """Match memory entities against stored assets to determine lifecycle states.

        Args:
            images (list[Image]):
                A list containing the newly paginated image data items.

        """
        if not self._existing_paths:
            for img in images:
                img.status = ProcessingStatus.NOT_STARTED
            return

        for img in images:
            # Sécurité : On s'assure de comparer des chaînes de caractères standardisées
            img_path_str = str(Path(img.path).resolve())
            
            if img_path_str in self._existing_paths:
                # Récupération des données depuis le repository local
                data = self.image_repository.get_image_by_path(img_path_str)
                if data:
                    img.description = data.description
                    img.embedding = data.embedding
                    img.keywords = data.keywords
                    img.status = ProcessingStatus.COMPLETED
                else:
                    img.status = ProcessingStatus.NOT_STARTED
            else:
                img.status = ProcessingStatus.NOT_STARTED

    # ─────────────────────────────────────────────
    # PAGINATION
    # ─────────────────────────────────────────────
    # ─────────────────────────────────────────────
    # PAGINATION
    # ─────────────────────────────────────────────
    def _load_next_page(self):
        """Request supplementary image elements from the model stream and push them onto the layout."""
        if not self._has_more:
            return

        images = self.model.load_next_page()
        if not images:
            self._has_more = False
            return

        self._update_images_status_from_db(images)
        self.view.append_images(images)
        
        # On force le maintien des compteurs globaux
        self._force_global_progress_maintenance()

    def _load_next_page_throttled(self):
        """Fetch elements from the data pipeline while blocking overlapping concurrent requests."""
        if not self._has_more or self._loading_page:
            return

        self._loading_page = True
        try:
            images = self.model.load_next_page()
            if not images:
                self._has_more = False
                return

            self._update_images_status_from_db(images)
            self.view.append_images(images)
            
            # On force le maintien des compteurs globaux
            self._force_global_progress_maintenance()
        finally:
            self._loading_page = False

    def _force_global_progress_maintenance(self):
        """Prevent runtime updates from reset-overwriting global statistics during layout lazy-loading."""
        if hasattr(self.model, 'get_total_images_count'):
            total_count = self.model.get_total_images_count()
            already_processed = self.model.get_already_processed_count() # Récupère le compte global
            
            # 1. On appelle d'abord la méthode de la vue pour qu'elle fasse sa popote interne
            if hasattr(self.view, '_update_progress_display'):
                try:
                    self.view._update_progress_display()
                except TypeError:
                    pass
            
            # 2. IMMEDIATEMENT APRÈS, on ré-écrase ses compteurs avec la réalité globale si on ne traite pas
            if not self.is_processing():
                if hasattr(self.view, 'progress'):
                    self.view.progress.setMaximum(total_count)
                    self.view.progress.setValue(already_processed) # Évite le reset à 0
                if hasattr(self.view, '_progress_label'):
                    self.view._progress_label.setText(
                        f"En attente… ({already_processed} / {total_count} images traitées)"
                    )

    # ─────────────────────────────────────────────
    # PROCESSING
    # ─────────────────────────────────────────────
    def _start_processing(self):
        """Instantiate tracking records, launch asynchronous extraction, and toggle view states."""
        if self.processing_manager.is_processing():
            return

        if not self.model.selected_folder:
            return

        # 1. Initialisation du Repository des Datasets
        from database.DbService import DbService
        from common.Dataset_Classes.DatasetRepository import DatasetRepository # Ajuste l'import selon ton projet
        
        db_service = DbService()
        dataset_repo = DatasetRepository(db_service.sqlite)

        # 2. On prend le nom du dossier comme nom de Dataset (ex: "MesVacances2026")
        dataset_name = self.model.selected_folder.name
        
        # 3. Récupération ou création automatique du Dataset en BDD
        current_dataset = dataset_repo.create(dataset_name)
        
            # Compteur live = ce qui était déjà traité avant de lancer ce batch
        self._live_processed_count = self.model.get_already_processed_count()

        # 4. On transmet ce dataset au processing manager / worker
        self.current_worker = self.processing_manager.start_batch_processing(
            folder_path=self.model.selected_folder,
            existing_paths=self._existing_paths if self._existing_paths else set(),
            dataset=current_dataset,  # <--- ON AJOUTE LE DATASET ICI
            on_progress=self._on_image_progress,
            on_image_processed=self._on_image_processed,
            on_image_error=self._on_image_error,
            on_complete=self._on_processing_complete,
            on_stopped=self._on_processing_stopped,
        )

        self.view.set_processing_mode(True)
        self.processing_started.emit()

    def _stop_processing(self):
        """Request active worker threads to halt execution loops and clear internal routines."""
        if not self.processing_manager.is_processing():
            return

        self.processing_manager.stop_current_processing()
        self._on_processing_stopped()

    # ─────────────────────────────────────────────
    # CALLBACKS PROCESSING
    # ─────────────────────────────────────────────
    def _on_image_progress(self, image_path: str, status: ProcessingStatus):
        """Update file lifecycle status markers inside the tracking components.

        Args:
            image_path (str):
                The file location string target.
            status (ProcessingStatus):
                The target lifecycle status configuration.

        """
        self.model.update_image_status(image_path, status)
        self.view.update_image_status(image_path, status)

    def _on_image_processed(self, image_path: str, description: str, embedding: list):
        """Commit analysis extraction properties to the matching component data slots.

        Args:
            image_path (str):
                The file path string identifying the object.
            description (str):
                The vision-language text analysis output.
            embedding (list):
                The matching vector features list array.

        """
        self.model.update_image_status(
            image_path,
            ProcessingStatus.COMPLETED,
            description=description,
            embedding=embedding
        )
        self.view.update_image_status(image_path, ProcessingStatus.COMPLETED)

        self._live_processed_count += 1
        total_count = self.model.get_total_images_count()

        if hasattr(self.view, 'progress'):
            self.view.progress.setValue(self._live_processed_count)
        if hasattr(self.view, '_progress_label'):
            self.view._progress_label.setText(
                f"Traitement… ({self._live_processed_count} / {total_count} images traitées)"
            )
            
    def _on_image_error(self, image_path: str, error: str):
        """Mark faulty processing statuses onto components when tracking operational failures.

        Args:
            image_path (str):
                The absolute target path identifier.
            error (str):
                The trace description content detailing execution failures.

        """
        self.model.update_image_status(
            image_path,
            ProcessingStatus.ERROR,
            error_message=error
        )
        self.view.update_image_status(image_path, ProcessingStatus.ERROR)

    def _on_processing_complete(self):
        """Disable processing display flags and dispatch a completion notification signal."""
        self.view.set_processing_mode(False)
        self.processing_finished.emit()

    def _on_processing_stopped(self):
        """Disable processing layout flags and emit termination notification signals."""
        self.view.set_processing_mode(False)
        self.processing_stopped.emit()

    # ─────────────────────────────────────────────
    # UI EVENTS
    # ─────────────────────────────────────────────
    def _handle_image_clicked(self, img):
        """Inspect and print metadata values associated with an explicitly clicked component node.

        Args:
            img (Image):
                The structural data object linked to the target thumbnail node.

        """
        info = self.model.get_image_info(img.path)
        if info:
            print(f"{Path(img.path).name} - {info.status.value}")

    def _load_default_dataset_folder(self):
        """Query configuration caches to automatically load previous ingestion locations."""
        folder = load_from_config("import_image_folder")
        if folder:
            self._handle_folder_selection(folder)

    def get_view(self):
        """Fetch the tracking UI dashboard layer instance.

        Returns:
            The display view component context.

        """
        return self.view

    def get_model(self):
        """Fetch the runtime model context tracker instance.

        Returns:
            The internal model architecture system.

        """
        return self.model

    def is_processing(self) -> bool:
        """Evaluate if the model thread worker layer is running batch extraction routines.

        Returns:
            True if operations are actively spinning, otherwise False.

        """
        return self.processing_manager.is_processing()

    def cleanup(self):
        """Safely terminate processing thread routines and deallocate layout memory mappings."""
        if self.is_processing():
            self.processing_manager.stop_current_processing(wait=True)
        self.view.cleanup()

    def load(self):
        """Boot default configurations and mount pipeline assets during lifecycle initialization phases."""
        self._load_default_dataset_folder()


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    controller = ImportToolController()
    controller.get_view().show()
    sys.exit(app.exec())