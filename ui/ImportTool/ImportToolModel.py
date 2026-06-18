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

    PAGE_SIZE = 60

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
        """Retourne le nombre brut total calculé à l'initialisation."""
        return self._total_images_count

    # ─────────────────────────────────────────────
    # LOAD PAGE
    # ─────────────────────────────────────────────

    def load_next_page(self) -> list[Image]:
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
        return self._generator is not None

    # ─────────────────────────────────────────────
    # BDD STATUS
    # ─────────────────────────────────────────────

    def load_db_status(self):
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
        return self._cache

    def get_not_treated_images(self) -> list[Image]:
        return [img for img in self._cache if img.status != ProcessingStatus.COMPLETED]

    def get_images_count(self) -> int:
        return len(self._cache)

    def get_image_info(self, path: str) -> Image | None:
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
        keywords: list[str] = None,
        embedding: list[float] = None,
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

    def reset_all_status(self, images: list[Image]):
        """FIX: méthode manquante — remet toutes les images en statut PENDING avant traitement."""
        for image in images:
            image.status = ProcessingStatus.PENDING

    # ─────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────

    def get_images_by_status(self) -> dict[ProcessingStatus, int]:
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