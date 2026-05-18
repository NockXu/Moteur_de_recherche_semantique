import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Set

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.Image_Classes.Image import Image, ProcessingStatus
from common.Image_Classes.ImageRepository import ImageRepository
from common.Image_Classes.ImageScanService import ImageScanService
from database.DbService import DbService


class ImportToolModel:

    PAGE_SIZE = 60

    def __init__(self):
        self.scan_service = ImageScanService()

        self._generator = None
        self._cache: List[Image] = []

        db_service = DbService()
        self._image_repository = ImageRepository(
            db_service.sqlite,
            db_service.faiss
        )

        self._db_paths: Set[str] = set()
        self.selected_folder: Optional[Path] = None

    # ─────────────────────────────────────────────
    # INIT SCAN
    # ─────────────────────────────────────────────

    def set_folder(self, folder_path: str) -> bool:
        try:
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                return False

            self.selected_folder = folder
            self._cache.clear()
            self._generator = self.scan_service.scan_lazy(folder)

            print(f"Scan initialisé: {folder.name}")
            return True

        except Exception as e:
            print(f"Erreur set_folder: {e}")
            return False

    # ─────────────────────────────────────────────
    # LOAD PAGE
    # ─────────────────────────────────────────────

    def load_next_page(self) -> List[Image]:
        if not self._generator:
            return []

        new_images = []

        for _ in range(self.PAGE_SIZE):
            try:
                image = next(self._generator)

                # Ajouter TOUTES les images (plus de filtrage)
                self._cache.append(image)
                new_images.append(image)

            except StopIteration:
                break

        return new_images

    def has_more(self) -> bool:
        return self._generator is not None

    # ─────────────────────────────────────────────
    # BDD STATUS
    # ─────────────────────────────────────────────

    def load_db_status(self):
        try:
            # Utiliser la méthode optimisée qui retourne directement les chemins
            repo = ImageRepository(DbService().sqlite, DbService().faiss)
            self._db_paths = repo.get_all_image_paths()
            print(f"🗄️ {len(self._db_paths)} images en BDD")

        except Exception as e:
            print(f"Erreur load_db_status: {e}")
            self._db_paths = set()

    # ─────────────────────────────────────────────
    # GETTERS
    # ─────────────────────────────────────────────

    def get_loaded_images(self) -> List[Image]:
        return self._cache

    def get_not_treated_images(self) -> List[Image]:
        return [img for img in self._cache if img.status != ProcessingStatus.COMPLETED]

    def get_images_count(self) -> int:
        return len(self._cache)

    def get_image_info(self, path: str) -> Optional[Image]:
        """FIX: méthode manquante — retourne l'Image correspondant au chemin donné."""
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
        keywords: List[str] = None,
        embedding: List[float] = None,
        error_message: str = "",
    ):
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

    def reset_all_status(self, images: List[Image]):
        """FIX: méthode manquante — remet toutes les images en statut PENDING avant traitement."""
        for image in images:
            image.status = ProcessingStatus.PENDING

    # ─────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────

    def get_images_by_status(self) -> Dict[ProcessingStatus, int]:
        counts = {s: 0 for s in ProcessingStatus}
        for img in self._cache:
            counts[img.status] += 1
        return counts

    def get_processing_progress(self) -> float:
        if not self._cache:
            return 0.0

        done = sum(
            1 for i in self._cache
            if i.status in (ProcessingStatus.COMPLETED, ProcessingStatus.ERROR)
        )
        return done / len(self._cache)