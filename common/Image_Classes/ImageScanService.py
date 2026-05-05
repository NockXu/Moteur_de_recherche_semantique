from pathlib import Path
from typing import List, Optional, Iterable
import os
import sys

# Ajouter la racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.Dataset_Classes.Dataset import Dataset
from common.Image_Classes.Image import Image


class ImageScanService:
    """
    Service dédié au scan de répertoires d'images.

    Responsabilités :
    - Scanner un dossier
    - Filtrer les fichiers image
    - Créer des objets Image "light" (sans embedding)
    """

    SUPPORTED_EXTENSIONS = {
        ".jpg", ".jpeg", ".png", ".gif",
        ".bmp", ".tiff", ".webp"
    }

    def __init__(self):
        pass

    # ─────────────────────────────────────────────
    # SCAN COMPLET
    # ─────────────────────────────────────────────
    def scan(
        self,
        directory: str,
        dataset: Optional[Dataset] = None
    ) -> List[Image]:
        """
        Scan complet (attention: peut être lourd sur gros dossier)
        """
        return list(self._scan_generator(directory, dataset))

    # ─────────────────────────────────────────────
    # SCAN LAZY (MEILLEUR POUR UI)
    # ─────────────────────────────────────────────
    def scan_lazy(
        self,
        directory: str,
        dataset: Optional[Dataset] = None
    ) -> Iterable[Image]:
        """
        Générateur → idéal pour pagination / load progressif
        """
        return self._scan_generator(directory, dataset)

    # ─────────────────────────────────────────────
    # CORE LOGIC
    # ─────────────────────────────────────────────
    def _scan_generator(
        self,
        directory: str,
        dataset: Optional[Dataset]
    ) -> Iterable[Image]:

        base_path = Path(directory)

        if not base_path.exists() or not base_path.is_dir():
            return

        for file_path in base_path.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            yield Image(
                path=file_path,
                dataset=dataset,   # peut être None → OK
                description="",
                keywords=[],
                embedding=[],
                image_id=None
            )

    # ─────────────────────────────────────────────
    # SCAN PAGINÉ DIRECT (OPTION)
    # ─────────────────────────────────────────────
    def scan_page(
        self,
        directory: str,
        page: int,
        page_size: int,
        dataset: Optional[Dataset] = None
    ) -> List[Image]:
        """
        Scan + pagination directe (évite de tout charger)
        """
        start = page * page_size
        end = start + page_size

        results = []
        count = 0

        for image in self._scan_generator(directory, dataset):
            if count >= start and count < end:
                results.append(image)

            if count >= end:
                break

            count += 1

        return results