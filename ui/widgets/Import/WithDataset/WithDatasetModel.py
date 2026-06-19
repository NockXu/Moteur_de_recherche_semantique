import sys
import os
from typing import Optional, Dict, List

from common.Dataset_Classes.Dataset import Dataset
from common.Dataset_Classes.DatasetRepository import DatasetRepository
from .DatasetType import DatasetStatus, DatasetData
from database.DbService import DbService

class WithDatasetModel:
    """Data model managing identification verification for structured dataset imports.

    Maintains execution context configurations and leverages runtime database lookup
    caches to append state indicators to tracking tokens.
    """
    
    def __init__(self):
        self.datasets_data : dict[DatasetData] = {}
        self._datasets_cache : list[Dataset] | None = None

    def update(self, name : str) -> DatasetData | None:
        """Evaluate a dataset classification string and update the tracked configuration state.

        Args:
            name (str): The logical alphanumeric label of the target dataset.

        Returns:
            DatasetData | None: Updated data descriptor object, or None if validation fails.

        """
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
        """Query storage tracking files to verify if a dataset designation is already registered.

        Args:
            dataset_name (str): Alphanumeric string key being searched inside database indexes.

        Returns:
            bool: True if a matching dataset tracking tag is located, otherwise False.

        """
        self._datasets_cache = DatasetRepository(DbService().sqlite).get_all()

        for dataset in self._datasets_cache:
            if dataset.name == dataset_name:
                return True
        return False
            
    def is_valid(self, dataset_name: str) -> bool:
        """Enforce character composition rules on incoming user data inputs.

        Args:
            dataset_name (str): The targeted raw character array to validate.

        Returns:
            bool: True if the structural composition matches validation requirements.

        """
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