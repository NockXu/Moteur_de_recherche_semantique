from typing import List, Optional
import sys
import os

from database.sqlite.manager import SqliteManager
from common.Dataset_Classes.Dataset import Dataset


class DatasetRepository:
    """Repository responsible for managing Dataset persistence.

    This class provides an abstraction layer over the SQLite database
    for dataset-related operations.

    Args:
        db (SqliteManager):
            SQLite database manager used for executing queries.

    """

    def __init__(self, db: SqliteManager):
        self.db = db

    def get_all(self) -> list[Dataset]:
        """Retrieve all datasets from the database.

        Returns:
            List of Dataset objects. Returns an empty list if no datasets exist.

        """
        rows = self.db.fetch_all("SELECT id, name FROM datasets")

        if not rows:
            return []

        return [Dataset(id=row[0], name=row[1]) for row in rows]

    def get_by_id(self, dataset_id: int) -> Dataset | None:
        """Retrieve a dataset by its ID.

        Returns:
            The dataset if found, otherwise None.

        """
        row = self.db.fetch_one(
            "SELECT id, name FROM datasets WHERE id = ?",
            (dataset_id,)
        )

        if not row:
            return None

        return Dataset(id=row[0], name=row[1])

    def get_by_name(self, name: str) -> Dataset | None:
        """Retrieve a dataset by its name.

        Returns:
            The dataset if found, otherwise None.

        """
        row = self.db.fetch_one(
            "SELECT id, name FROM datasets WHERE name = ?",
            (name,)
        )

        if not row:
            return None

        return Dataset(id=row[0], name=row[1])

    def create(self, name: str) -> Dataset | None:
        """Create a dataset if it does not already exist.

        Returns:
            The created or existing dataset, or None if an error occurs.

        """
        try:
            self.db.execute(
                """
                INSERT INTO datasets (name)
                VALUES (?)
                ON CONFLICT(name) DO NOTHING
                """,
                (name,)
            )

            row = self.db.fetch_one(
                "SELECT id, name FROM datasets WHERE name = ?",
                (name,)
            )

            if row is None:
                return None

            return Dataset(id=row[0], name=row[1])

        except Exception as e:
            raise RuntimeError(f"Failed to create dataset '{name}': {e}")