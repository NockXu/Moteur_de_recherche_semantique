from dataclasses import dataclass
from typing import List

from common.Dataset_Classes.Dataset import Dataset
from common.Dataset_Classes.DatasetRepository import DatasetRepository
from .WithoutDatasetType import WithoutDatasetData, WithoutDatasetStatus
from database.DbService import DbService

@dataclass
class WithoutDatasetModel:

    def __init__(self):
        self.mode: str = "merge"  # "merge" ou "separate"

        repository = DatasetRepository(DbService().sqlite)
        self._datasets_cache : List[Dataset] = repository.get_all()

        self.datasets_data : WithoutDatasetData = []

    # ---------------- logique simple ----------------

    def exist(self) -> None:
        """Vérifie si le modèle est valide"""
        for data in self.datasets_data:
            if any(dataset.name == data["name"] for dataset in self._datasets_cache):
                data["status"] = WithoutDatasetStatus.EXISTS
            else:
                data["status"] = WithoutDatasetStatus.NOT_EXISTS

    def update(self, datasets_data: List[WithoutDatasetData]):
        """Met à jour le modèle avec les données fournies"""
        self.datasets_data = datasets_data
        self.exist()
        

        