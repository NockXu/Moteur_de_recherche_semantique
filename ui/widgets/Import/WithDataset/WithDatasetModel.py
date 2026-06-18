import sys
import os
from typing import Optional, Dict, List

from common.Dataset_Classes.Dataset import Dataset
from common.Dataset_Classes.DatasetRepository import DatasetRepository
from .DatasetType import DatasetStatus, DatasetData
from database.DbService import DbService

class WithDatasetModel:
    def __init__(self):
        self.datasets_data : dict[DatasetData] = {}
        self._datasets_cache : list[Dataset] | None = None

    def update(self, name : str) -> DatasetData | None:
        # Cas invalide
        if not self.is_valid(name):
            return None

        # Cas ajout/modification d'un dataset dans le modèle
        else:
            status = DatasetStatus.NOT_EXISTS

            if self.exists(name):
                status = DatasetStatus.EXISTS

            self.datasets_data[name] = DatasetData(name=name, status=status)

            return self.datasets_data[name]

    def exists(self, dataset_name: str) -> bool:
        """Vérifie si un dataset existe déjà dans la base de données"""
        self._datasets_cache = DatasetRepository(DbService().sqlite).get_all()

        for dataset in self._datasets_cache:
            if dataset.name == dataset_name:
                return True
        return False
            
    def is_valid(self, dataset_name: str) -> bool:
        """Vérifie si la configuration est valide"""
        if not dataset_name.strip():
            return False
        return True

if __name__ == "__main__":
    model = WithDatasetModel()
    print(model.update("dataset1"))
    print(model.update("dataset2"))
    print(model.update(""))
    print(model.update("dataset1"))
    print(model.update("dataset2"))