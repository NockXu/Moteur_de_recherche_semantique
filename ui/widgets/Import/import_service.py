import json
from pathlib import Path
from typing import List, Dict, Optional

from database.DbService import DbService

from ui.widgets.Import.import_result import ImportResult
from ui.widgets.Import.DatasetConfigDataType import DatasetConfigData

from common.Image_Classes.Image import Image
from common.Image_Classes.ImageRepository import ImageRepository
from common.Dataset_Classes.Dataset import Dataset
from common.Dataset_Classes.DatasetRepository import DatasetRepository


class ImportService:
    """Service class handling the backend orchestration of catalog data imports.

    Manages system disk lookups, structures internal directory maps via persistent caching, 
    and converts JSON manifest inputs into processing-eligible Image and Dataset repositories objects.

    Args:
        configs (list[DatasetConfigData]):
            A sequence of configuration mappings detailing disk target folders and tracking names.
        mode (str):
            Operational context routing indicator (e.g., "with_dataset").

    """

    def __init__(self, configs: list[DatasetConfigData], mode : str):
        self.image_repo = ImageRepository(DbService().sqlite, DbService().faiss)
        self.dataset_repo = DatasetRepository(DbService().sqlite)
        self.configs = configs
        self.mode = mode
        self.path_cache = self._build_path_cache()

    def _build_path_cache(self) -> dict[str, tuple[str, str]]:
        """Scan all assigned directory folders exactly once at operational initialization.

        Builds an optimized lookup system to avoid iterative sequential IO disk traversal operations 
        during active row mapping phases.

        Returns:
            dict[str, tuple[str, str]]: A file lookup index structured as {filename: (full_path, dataset_name)}.

        """
        cache = {}
        
        for config in self.configs:
            base_path = Path(config["path"])
            
            if not base_path.exists() or not base_path.is_dir():
                continue
            
            # Scanner tous les fichiers du dossier
            for file_path in base_path.iterdir():
                if file_path.is_file():
                    filename = file_path.name
                    # Si le fichier existe déjà dans le cache, garde la première occurrence
                    if filename not in cache:
                        cache[filename] = (str(file_path), config["name"])

        return cache

    # -------------------------
    # LOAD JSON
    # -------------------------
    def load_file(self, file_path: str) -> dict[str, list[Image] | list[Dataset]]:
        """Parse structured catalog data manifest files based on active mode routing.

        Args:
            file_path (str):
                The local disk directory system reference to the input data manifest file.

        Returns:
            dict[str, list[Image] | list[Dataset]]: A dictionary storing extracted images and datasets lists.

        """
        if self.mode != "with_dataset":
            return self.load_file_without_dataset(file_path)
        
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        images = []
        datasets = []
        dataset_names = set()

        # Nouveau format : les images sont directement dans le dictionnaire principal
        for filename, image_data in data.items():
            if filename in ["metadata", "export_info", "datasets"]:
                continue
                
            # Récupérer le nom du dataset depuis le champ "dataset"
            dataset_name = image_data.get("dataset", "default")
            dataset_names.add(dataset_name)
            
            images.append(
                Image(
                    name=filename,
                    path=image_data.get("path"),
                    dataset=Dataset(id=None, name=dataset_name),
                    description=image_data.get("description", ""),
                    keywords=image_data.get("keywords", []),
                    embedding=image_data.get("embedding", []),
                )
            )

        # Créer les datasets uniques trouvés
        for dataset_name in dataset_names:
            datasets.append(
                Dataset(
                    name=dataset_name,
                    id=None
                )
            )

        return {"images": images, "datasets": datasets}

    # -------------------------
    # LOAD JSON WITHOUT DATASET SECTION
    # -------------------------
    def load_file_without_dataset(self, file_path: str) -> dict[str, list[Image] | list[Dataset]]:
        """Parse structural manifest definitions missing standard dataset grouping partitions.

        Args:
            file_path (str):
                The local disk directory system reference to the input legacy file.

        Returns:
            dict[str, list[Image] | list[Dataset]]: Data collections routed under unified tracking categories.

        """
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        images = []

        for filename, image_data in data.items():
            if filename in ["export_info", "metadata"]:
                continue

            images.append(
                Image(
                    name=filename,
                    path=image_data.get("path"),
                    dataset=Dataset(id=None, name="default"),  # Dataset par défaut
                    description=image_data.get("description", ""),
                    keywords=image_data.get("keywords", []),
                    embedding=image_data.get("embedding", []),
                )
            )

        # Ajouter un dataset par défaut
        default_dataset = Dataset(id=None, name="default")
        
        return {"images": images, "datasets": [default_dataset]}

    # -------------------------
    # PATH RESOLUTION
    # -------------------------
    def resolve_path(self, image: Image) -> str | None:
        """Resolve full physical storage locations instantaneously leveraging internal lookup maps.

        Args:
            image (Image):
                The tracking baseline object tracking row details missing absolute structural indicators.

        Returns:
            str | None: The absolute physical path string if located inside mapped indices, otherwise None.

        """
        if image.name in self.path_cache:
            full_path, dataset_name = self.path_cache[image.name]
            image.dataset_name = dataset_name
            return full_path
        
        image.dataset_name = "default"
        return None