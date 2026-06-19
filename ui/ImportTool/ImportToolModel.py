import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Set

from ui.utils.i18n import tr

from common.Image_Classes.Image import Image, ProcessingStatus
from common.Image_Classes.ImageRepository import ImageRepository
from common.Image_Classes.ImageScanService import ImageScanService
from database.DbService import DbService


class ImportToolModel:
    """Model component responsible for managing state and business data during image ingestion.

    Handles directory scanning, pagination offsets, asset cache tracking, and synchronizes
    processing statistics with the persistence layer.

    """

    PAGE_SIZE = 50

    def __init__(self):
        self.scan_service = ImageScanService()
        self._generator = None
        self._cache: list[Image] = []

        db_service = DbService()
        self._image_repository = ImageRepository(
            db_service.sqlite,
            db_service.faiss
        )
        self._db_paths: set[str] = set()
        self.selected_folder: Path | None = None

    # ─────────────────────────────────────────────
    # INIT SCAN
    # ─────────────────────────────────────────────

    def set_folder(self, folder_path: str) -> bool:
        """Initialize the targeted folder and prepare the lazy image stream scanner.

        Args:
            folder_path (str):
                The absolute file system path to the target folder.

        Returns:
            True if the directory exists and was initialized successfully, otherwise False.

        """
        try:
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                return False

            self.selected_folder = folder
            self._cache.clear()
            
            # Le générateur lazy reste activé pour la pagination visuelle
            self._generator = self.scan_service.scan_lazy(folder)

            # ─── COMPTAGE ULTRA-RAPIDE SANS CHARGEMENT DE DONNÉES ───
            valid_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}
            self._total_images_count = sum(
                1 for f in folder.iterdir() 
                if f.is_file() and f.suffix.lower() in valid_exts
            )

            print(f"Dossier initialisé : {self._total_images_count} fichiers détectés.")
            return True

        except Exception as e:
            print(f"Erreur set_folder: {e}")
            self._total_images_count = 0
            return False

    def get_total_images_count(self) -> int:
        """Retrieve the raw total count of images discovered during path initialization.

        Returns:
            The total integer amount of matching image files found.

        """
        return self._total_images_count
    
    def calculate_already_processed_count(self, existing_paths: set[str]) -> int:
        """Calculate the total number of images in the directory that already exist in the database.

        Performs a rapid path intersection check without compiling structural Image instances
        or assigning memory allocations for matching view components.

        Args:
            existing_paths (set[str]):
                A set containing absolute file path strings extracted from the database cache.

        Returns:
            The total number of images that have already been saved to the database.

        """
        if not self.selected_folder or not existing_paths:
            self._already_processed_count = 0
            return 0

        valid_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}
        count = 0
        
        # On parcourt le dossier et on vérifie si le chemin résolu est dans le Set de la BDD
        for f in self.selected_folder.iterdir():
            if f.is_file() and f.suffix.lower() in valid_exts:
                if str(f.resolve()) in existing_paths:
                    count += 1
                    
        self._already_processed_count = count
        return count

    def get_already_processed_count(self) -> int:
        """Retrieve the count of images verified as already stored during the initial load check.

        Returns:
            The pre-calculated integer sum of existing database matching items.

        """
        """Retourne le nombre total d'images déjà traitées au chargement initial."""
        return getattr(self, '_already_processed_count', 0)

    # ─────────────────────────────────────────────
    # LOAD PAGE
    # ─────────────────────────────────────────────

    def load_next_page(self) -> list[Image]:
        """Fetch the next block chunk of Image items using the structural pipeline generator.

        Returns:
            A list containing up to PAGE_SIZE Image instances newly loaded into the model cache.

        """
        if not self._generator:
            return []

        new_images = []
        for _ in range(self.PAGE_SIZE):
            try:
                image = next(self._generator)
                self._cache.append(image)
                new_images.append(image)
            except StopIteration:
                self._generator = None  # Épuisé
                break

        return new_images

    def has_more(self) -> bool:
        """Determine whether the lazy structural directory generator holds additional objects.

        Returns:
            True if more items are available for pagination loading, otherwise False.

        """
        return self._generator is not None

    # ─────────────────────────────────────────────
    # BDD STATUS
    # ─────────────────────────────────────────────

    def load_db_status(self):
        """Fetch and cache all image destination path references stored across database indexes."""
        try:
            # Utiliser la méthode optimisée qui retourne directement les chemins
            repo = ImageRepository(DbService().sqlite, DbService().faiss)
            self._db_paths = repo.get_all_image_paths()

        except Exception as e:
            print(f"{tr("Erreur load_db_status")}: {e}")
            self._db_paths = set()

    # ─────────────────────────────────────────────
    # GETTERS
    # ─────────────────────────────────────────────

    def get_loaded_images(self) -> list[Image]:
        """Retrieve all Image model data structures loaded inside the model memory allocation.

        Returns:
            A list containing all structural Image models stored in cache.

        """
        return self._cache

    def get_not_treated_images(self) -> list[Image]:
        """Extract a filtered collection of loaded images whose state values do not match completed parameters.

        Returns:
            A list containing uncompleted or faulty Image objects.

        """
        return [img for img in self._cache if img.status != ProcessingStatus.COMPLETED]

    def get_images_count(self) -> int:
        """Count the current amount of model records stored in internal list indexes.

        Returns:
            The integer total length of the active cache.

        """
        return len(self._cache)

    def get_image_info(self, path: str) -> Image | None:
        """Find and extract a cached Image matching an exact absolute system path value.

        Args:
            path (str):
                The file system destination key used to match the Image model object.

        Returns:
            The matching Image instance if found, otherwise None.

        """
        key = str(Path(path).resolve())
        for img in self._cache:
            if str(img.path.resolve()) == key:
                return img
        return None

    # ─────────────────────────────────────────────
    # STATUS
    # ─────────────────────────────────────────────

    def update_image_status(
        self,
        image_path: str,
        status: ProcessingStatus,
        description: str = "",
        keywords: list[str] = None,
        embedding: list[float] = None,
        error_message: str = "",
    ):
        """Update processing lifecycle properties and evaluation metrics on a targeted cached image.

        Args:
            image_path (str):
                Absolute file location string used to lookup the targeted asset instance.
            status (ProcessingStatus):
                The updated lifecycle state context definition to attach.
            description (str):
                Optional multimodal vision language text description. Defaults to "".
            keywords (list[str]):
                Optional set of labels extracted via evaluation steps. Defaults to None.
            embedding (list[float]):
                Optional vector feature extraction list representation. Defaults to None.
            error_message (str):
                Optional diagnostic trace information log recorded if failures occur. Defaults to "".

        """
        for image in self._cache:
            if str(image.path.resolve()) == str(Path(image_path).resolve()):
                image.status = status
                if description:
                    image.description = description
                if keywords:
                    image.keywords = keywords
                if embedding:
                    image.embedding = embedding
                if error_message:
                    image.error_message = error_message
                return

    def reset_all_status(self, images: list[Image]):
        """Revert processing status values across an explicit collection back to pending definitions.

        Args:
            images (list[Image]):
                The explicit list of image data nodes targeted for property modification reset routines.

        """
        """FIX: méthode manquante — remet toutes les images en statut PENDING avant traitement."""
        for image in images:
            image.status = ProcessingStatus.PENDING

    # ─────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────

    def get_images_by_status(self) -> dict[ProcessingStatus, int]:
        """Aggregate data metrics grouping image occurrence records per processing status enum key.

        Returns:
            A dictionary mapping processing states to their current total counts inside the cache.

        """
        counts = {s: 0 for s in ProcessingStatus}
        for img in self._cache:
            counts[img.status] += 1
        return counts

    def get_processing_progress(self) -> float:
        """Calculate the completed workload ratio against total cached image instances.

        Returns:
            The calculated processing ratio between 0.0 and 1.0.

        """
        if not self._cache:
            return 0.0

        done = sum(
            1 for i in self._cache
            if i.status in (ProcessingStatus.COMPLETED, ProcessingStatus.ERROR)
        )
        return done / len(self._cache)