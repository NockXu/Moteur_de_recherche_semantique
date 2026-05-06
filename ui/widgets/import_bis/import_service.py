import json
from pathlib import Path
from typing import List, Dict, Optional

from database.DbService import DbService

from ui.widgets.import_bis.import_result import ImportResult
from ui.widgets.import_bis.DatasetConfigDataType import DatasetConfigData

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

        # Lire les images depuis la section "images"
        images_data = data.get("images", {})
        datasets_data = data.get("datasets", {})
        
        for filename, image_data in images_data.items():
            # Récupérer le nom du dataset depuis dataset_id
            dataset_id = image_data.get("dataset_id")
            dataset_name = "default"
            
            # Chercher le nom du dataset correspondant
            for dataset in datasets_data:
                if dataset["id"] == dataset_id:
                    dataset_name = dataset["name"]
                    break
            
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

        for dataset_name, dataset_data in datasets_data.items():
            datasets.append(
                Dataset(
                    name=dataset_name,
                    id=dataset_data.get("id")
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
        """Résout le chemin de l'image"""

        # Chercher la config qui correspond au nom du dataset de l'image
        for config in self.configs:
            if config["name"] == image.dataset_name:  # Comparer avec le nom du dataset
                base_path = Path(config["path"])
                
                if base_path.exists() and base_path.is_dir():
                    result = str(base_path / image.path)
                    return result

        # Sinon on essaye pour chaque config
        for config in self.configs:
            base_path = Path(config["path"])
            
            if base_path.exists() and base_path.is_dir():
                result = str(base_path / image.path)
                image.dataset_name = config["name"]
                return result

        image.dataset_name = "default"
        return None

    # -------------------------
    # MAIN IMPORT PIPELINE
    # -------------------------
    def import_file(self, file_path: str) -> ImportResult:
        result = ImportResult()
        data = self.load_file(file_path)

        # Créer les datasets d'abord et récupérer leurs IDs
        dataset_ids = {}
        print("datasets:", data["datasets"])
        for dataset in data["datasets"]:
            success = self.dataset_repo.create(dataset.name)
            print("Success:", success)

            if success is None:
                result.add_error(f"DB insert failed: {dataset.name}")
            else:
                result.success += 1
                # Récupérer l'ID du dataset créé
                dataset_obj = self.dataset_repo.get_by_name(dataset.name)
                if dataset_obj:
                    dataset_ids[dataset.name] = dataset_obj.id

        # Mettre à jour les images avec les bons dataset_id
        for image in data["images"]:
            if image.dataset and image.dataset.name in dataset_ids:
                image.dataset_id = dataset_ids[image.dataset.name]

        for image in data["images"]:
            try:
                final_path = self.resolve_path(image)

                if not final_path:
                    result.add_error(f"Mapping failed: {image.name}")
                    continue

                image.path = final_path

                success = self.image_repo.save_image(image)

                if success is None:
                    result.add_error(f"DB insert failed: {image.name}")
                else:
                    result.success += 1

            except Exception as e:
                result.add_error(f"{image.name}: {str(e)}")

        return result