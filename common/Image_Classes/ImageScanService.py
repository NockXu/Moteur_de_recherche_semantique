from pathlib import Path
from typing import List, Optional, Iterable
import os
import sys

from common.Dataset_Classes.Dataset import Dataset
from common.Image_Classes.Image import Image


from pathlib import Path
from typing import Iterable

class ImageScanService:
    """
    Service responsible for scanning directories and discovering image files.

    Responsibilities:
        - Scan a directory recursively
        - Filter supported image formats
        - Produce lightweight Image objects (without embeddings)
    """

    SUPPORTED_EXTENSIONS: set[str] = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }

    def __init__(self) -> None:
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
        Scan a directory and return all discovered images.

        This method performs a full scan of the given directory.
        It may be expensive on large folders.

        Args:
            directory (str):
                Path to the directory to scan.

            dataset (Optional[Dataset]):
                Optional dataset to associate with scanned images.

        Returns:
            List of discovered Image objects.
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
        Lazily scan a directory and yield Image objects.

        This generator is optimized for:
            - Large directories
            - Streaming processing
            - Progressive loading / pagination

        Args:
            directory (str):
                Path to the directory to scan.

            dataset (Optional[Dataset]):
                Optional dataset associated with scanned images.

        Yields:
            Next discovered Image object.
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
        """
        Internal generator that recursively scans a directory
        and yields Image objects for supported file types.

        Args:
            directory (str):
                Directory path to scan.

            dataset (Optional[Dataset]):
                Dataset associated with scanned images.

        Yields:
            Image:
                Lightweight Image object (no embedding, no processing).
        """

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
                dataset=dataset,
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
        Scan a directory with pagination support.

        This method avoids loading all results in memory by using
        a lazy generator and slicing results on the fly.

        Args:
            directory (str):
                Path to the directory to scan.

            page (int):
                Page index (0-based).

            page_size (int):
                Number of items per page.

            dataset (Optional[Dataset]):
                Optional dataset associated with images.

        Returns:
            Paginated list of Image objects.
        """

        if page < 0 or page_size <= 0:
            return []

        start = page * page_size
        end = start + page_size

        results: List[Image] = []

        for idx, image in enumerate(self._scan_generator(directory, dataset)):
            if idx < start:
                continue

            if idx >= end:
                break

            results.append(image)

        return results