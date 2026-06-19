from PyQt6.QtCore import QThread, pyqtSignal
from typing import List, Optional
from collections.abc import Callable
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from vision.ollama_wrapper import OllamaWrapper
from vision.ImageProcessor import ImageProcessor
from common.Image_Classes.Image import ProcessingStatus, Image
from common.Image_Classes.ImageRepository import ImageRepository
from common.Dataset_Classes.Dataset import Dataset
from database.DbService import DbService

from ui.utils.i18n import tr


class ProcessingWorker(QThread):
    """Worker thread responsible for processing a folder of images asynchronously.

    This class handles multi-threaded image processing, including generating
    descriptions via Ollama and text embeddings, and updating the database.

    Args:
        folder_path (Path):
            Path to the directory containing images to process.
        existing_paths (set[str]):
            Set of image file paths already existing in the database to be skipped.
        dataset (Dataset):
            The Dataset instance linked to this processing pipeline.
        model (str):
            The name of the vision model to use for analysis. Defaults to "qwen2.5vl:7b".

    """
    
    progress_updated = pyqtSignal(str, ProcessingStatus)
    image_processed = pyqtSignal(str, str, list)
    image_error = pyqtSignal(str, str)
    processing_complete = pyqtSignal()
    processing_stopped = pyqtSignal()

    def __init__(self, folder_path: Path, existing_paths: set[str], dataset : Dataset, model: str = "qwen2.5vl:7b"):
        super().__init__()
        self.folder_path = folder_path
        self.existing_paths = existing_paths  # Les chemins déjà en BDD pour un skip instantané
        self.dataset = dataset
        self.model = model
        self.ollama_wrapper = OllamaWrapper()

        db_service = DbService()
        self._image_repository = ImageRepository(db_service.sqlite, db_service.faiss)

        self._is_running = False
        self._current_index = 0

        self.image_processor = None
        if self.ollama_wrapper:
            self.image_processor = ImageProcessor(self.ollama_wrapper, self.model)

    # ─────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────
    def run(self):
        """Execute the main processing loop over the target image folder.

        Iterates through valid image files, checks for exclusions, extracts descriptions 
        and embeddings, and updates progress indicators.

        """
        self._is_running = True
        self._current_index = 0
        stopped_manually = False

        valid_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}

        try:
            files = [f for f in self.folder_path.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
            total_images = len(files)

            for i, file_path in enumerate(files):
                if not self._is_running:
                    stopped_manually = True
                    break

                self._current_index = i
                img_path_str = str(file_path.resolve())

                if img_path_str in self.existing_paths:
                    continue

                # FIX ICI : Utilise le dataset lié à ce traitement
                image = Image(path=file_path, dataset=self.dataset)
                
                progress_text = f"{i+1}/{total_images} - {file_path.name}"
                self.progress_updated.emit(progress_text, ProcessingStatus.IN_PROGRESS)

                try:
                    self._process_single_image(image)
                except Exception as e:
                    print(f"{tr('Erreur image')} {file_path.name}: {e}")
                    self.progress_updated.emit(img_path_str, ProcessingStatus.ERROR)

        finally:
            self._is_running = False
            if stopped_manually:
                self.processing_stopped.emit()
            else:
                self.processing_complete.emit()

    # ─────────────────────────────
    # PROCESS SINGLE IMAGE
    # ─────────────────────────────
    def _process_single_image(self, image: Image):
        """Process a single Image object through description, embedding, and storage steps.

        Args:
            image (Image):
                The image instance to be processed and saved.

        """
        if not self._is_running:
            return

        image.status = ProcessingStatus.IN_PROGRESS
        self.progress_updated.emit(str(image.path), ProcessingStatus.IN_PROGRESS)

        if not self.image_processor:
            raise RuntimeError(tr("ImageProcessor non initialisé"))

        # STEP 1 : Description Ollama
        self.image_processor.ImageToData(image)
        if not self._is_running or not image.description:
            return

        # STEP 2 : Embedding
        self.image_processor.TextToEmbedding(image)
        if not self._is_running or not image.embedding:
            return

        # STEP 3 : Dataset & DB
        image.dataset_name = self.folder_path.name
        try:
            self._image_repository.save_image(image)
        except Exception as e:
            print(f"{tr('Erreur DB')}: {e}")

        # Émission du succès vers l'UI pour mise à jour dynamique des vignettes visibles
        self.progress_updated.emit(str(image.path), ProcessingStatus.COMPLETED)
        self.image_processed.emit(str(image.path), image.description, image.embedding)

    # ─────────────────────────────
    # STOP SAFE (IMPORTANT FIX)
    # ─────────────────────────────
    def stop(self):
        """Safely request the processing loop to stop execution."""
        self._is_running = False

    # ─────────────────────────────
    # STATE
    # ─────────────────────────────
    def is_running(self) -> bool:
        """Check if the worker thread is actively processing.

        Returns:
            True if the worker loop is running, otherwise False.

        """
        return self._is_running

    def get_progress(self) -> float:
        """Calculate the current processing progress.

        Returns:
            The completion ratio between 0.0 and 1.0.

        """
        if not self.images:
            return 1.0
        return min(1.0, self._current_index / len(self.images))

    def get_current_image(self) -> str | None:
        """Retrieve the file path string of the image currently being processed.

        Returns:
            The absolute path of the image as a string, or None if out of bounds.

        """
        if 0 <= self._current_index < len(self.images):
            return str(self.images[self._current_index].path)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Batch manager (CLEAN VERSION)
# ─────────────────────────────────────────────────────────────────────────────

class BatchProcessingManager:
    """Manager responsible for controlling batch image processing workflows.

    Coordinates the creation, monitoring, and lifecycle of the underlying 
    ProcessingWorker thread.

    Args:
        ollama_wrapper (OllamaWrapper):
            Optional Ollama API abstraction instance. Defaults to None.

    """

    def __init__(self, ollama_wrapper: OllamaWrapper = None):
        self.ollama_wrapper = ollama_wrapper
        self.current_worker = None

    def start_batch_processing(
        self,
        folder_path: Path,
        existing_paths: set[str],
        dataset: Dataset,
        on_progress: Callable = None,
        on_image_processed: Callable = None,
        on_image_error: Callable = None,
        on_complete: Callable = None,
        on_stopped: Callable = None,
        model: str = "qwen2.5vl:7b"
    ) -> ProcessingWorker:
        """Initialize and start a new batch processing worker thread.

        Args:
            folder_path (Path):
                Directory containing images to process.
            existing_paths (set[str]):
                Set of strings representing file paths already processed.
            dataset (Dataset):
                Target dataset mapping for the images.
            on_progress (Callable):
                Callback triggered when individual image progress updates. Defaults to None.
            on_image_processed (Callable):
                Callback triggered when an image is successfully processed. Defaults to None.
            on_image_error (Callable):
                Callback triggered when an error occurs during image processing. Defaults to None.
            on_complete (Callable):
                Callback triggered when the entire batch finishes successfully. Defaults to None.
            on_stopped (Callable):
                Callback triggered when processing is aborted manually. Defaults to None.
            model (str):
                Name of the model to use for visual extraction. Defaults to "qwen2.5vl:7b".

        Returns:
            The instantiated and running ProcessingWorker instance.

        """
        if self.current_worker and self.current_worker.isRunning():
            raise RuntimeError(tr("Traitement déjà en cours"))

        # MODIFICATION ICI : On transmet le dataset au ProcessingWorker
        self.current_worker = ProcessingWorker(folder_path, existing_paths, dataset, model)

        # signaux
        if on_progress:
            self.current_worker.progress_updated.connect(on_progress)

        if on_image_processed:
            self.current_worker.image_processed.connect(on_image_processed)

        if on_image_error:
            self.current_worker.image_error.connect(on_image_error)

        if on_complete:
            self.current_worker.processing_complete.connect(on_complete)

        if on_stopped:
            self.current_worker.processing_stopped.connect(on_stopped)

        self.current_worker.finished.connect(
            lambda worker=self.current_worker: self._clear_worker(worker)
        )
        self.current_worker.start()
        return self.current_worker

    def _clear_worker(self, worker: ProcessingWorker):
        """Clean up the internal reference and memory footprint of a finished worker.

        Args:
            worker (ProcessingWorker):
                The worker instance to discard.

        """
        if self.current_worker is worker:
            self.current_worker = None
        worker.deleteLater()

    def stop_current_processing(self, wait: bool = False) -> None:
        """Clean up the internal reference and memory footprint of a finished worker.

        Args:
            wait (bool):
                bool that decide if we need to stop the current process

        """
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.stop()
            if wait:
                self.current_worker.wait()

    def is_processing(self) -> bool:
        """Determine whether a batch process is currently active.

        Returns:
            True if a worker exists and is executing, otherwise False.

        """
        return self.current_worker is not None and self.current_worker.isRunning()

    def get_current_progress(self) -> float:
        """Fetch the tracking progression from the current worker.

        Returns:
            The progress ratio between 0.0 and 1.0, or 1.0 if no worker is running.

        """
        if self.current_worker:
            return self.current_worker.get_progress()
        return 1.0
