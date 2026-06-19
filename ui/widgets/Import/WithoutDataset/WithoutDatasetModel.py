from dataclasses import dataclass
from typing import List

from common.Dataset_Classes.Dataset import Dataset
from common.Dataset_Classes.DatasetRepository import DatasetRepository
from .WithoutDatasetType import WithoutDatasetData, WithoutDatasetStatus
from database.DbService import DbService

@dataclass
class WithoutDatasetModel:
    """Data model managing dataset verification and status tracking for unstructured imports.

    Maintains a pre-cached collection of existing database dataset records to perform
    instantaneous validation lookup checks without polling physical storage sequentially.
    """

    def __init__(self):
        self.mode: str = "merge"  # "merge" ou "separate"

        repository = DatasetRepository(DbService().sqlite)
        self._datasets_cache : list[Dataset] = repository.get_all()

        self.datasets_data : WithoutDatasetData = []

    # ---------------- logique simple ----------------

    def exist(self) -> None:
        """Evaluate input record names against preloaded tracking caches to append status flags.

        Updates internal mapping configurations states to determine if a target collection
        requires automatic database generation or allows structural merging.
        """
        for data in self.datasets_data:
            if any(dataset.name == data["name"] for dataset in self._datasets_cache):
                data["status"] = WithoutDatasetStatus.EXISTS
            else:
                data["status"] = WithoutDatasetStatus.NOT_EXISTS

    def update(self, datasets_data: list[WithoutDatasetData]):
        """Refresh configuration attributes layers and trigger layout dependency lookups.

        Args:
            datasets_data (list[WithoutDatasetData]):
                A structured collection representing user input parameters extracted from visual fields.

        """
        self.datasets_data = datasets_data
        self.exist()
        

        