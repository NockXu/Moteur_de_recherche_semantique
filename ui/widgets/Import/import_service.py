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

    def __init__(self, configs: List[DatasetConfigData], mode : str):
        self.image_repo = ImageRepository(DbService().sqlite, DbService().faiss)
        self.dataset_repo = DatasetRepository(DbService().sqlite)
        self.configs = configs
        self.mode = mode
        self.path_cache = self._build_path_cache()

    def _build_path_cache(self) -> Dict[str, tuple[str, str]]:
        """
        Scanne tous les dossiers UNE SEULE FOIS au démarrage
        Retourne: {nom_fichier: (chemin_complet, nom_dataset)}
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
    def load_file(self, file_path: str) -> Dict[str, List[Image] | List[Dataset]]:
        if self.mode != "with_dataset":
            return self.load_file_without_dataset(file_path)
        
        with open(file_path, "r", encoding="utf-8") as f:
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
    def load_file_without_dataset(self, file_path: str) -> Dict[str, List[Image] | List[Dataset]]:
        """Pour les JSON qui n'ont pas de section datasets"""
        with open(file_path, "r", encoding="utf-8") as f:
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
    def resolve_path(self, image: Image) -> Optional[str]:
        """Résout le chemin INSTANTANÉMENT via le cache"""
        
        if image.name in self.path_cache:
            full_path, dataset_name = self.path_cache[image.name]
            image.dataset_name = dataset_name
            return full_path
        
        image.dataset_name = "default"
        return None