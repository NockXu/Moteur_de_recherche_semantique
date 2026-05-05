from typing import List, Optional
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.sqlite.manager import SqliteManager
from common.Dataset_Classes.Dataset import Dataset


class DatasetRepository:
    def __init__(self, db: SqliteManager):
        self.db = db

    def get_all(self) -> List[Dataset]:
        rows = self.db.execute_query("SELECT id, name FROM datasets")
        return [Dataset(id=row[0], name=row[1]) for row in rows]

    def get_by_id(self, dataset_id: int) -> Optional[Dataset]:
        row = self.db.fetch_one(
            "SELECT id, name FROM datasets WHERE id = ?",
            (dataset_id,)
        )
        return Dataset(*row) if row else None

    def get_by_name(self, name: str) -> Optional[Dataset]:
        row = self.db.fetch_one(
            "SELECT id, name FROM datasets WHERE name = ?",
            (name,)
        )
        return Dataset(*row) if row else None

    def create(self, name: str) -> Dataset:
        self.db.execute(
            "INSERT INTO datasets (name) VALUES (?)",
            (name,)
        )
        dataset_id = self.db.lastrowid
        return Dataset(id=dataset_id, name=name)