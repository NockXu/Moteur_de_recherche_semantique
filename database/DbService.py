from typing import TypeVar

from database.sqlite.manager import SqliteManager
from database.faiss_manager.manager import FaissManager

from storage.config import FAISS_INDEX_FILE, DATABASE_FILE

# TypeVars pour un typage plus précis
TSqlite = TypeVar('TSqlite', bound=SqliteManager)
TFaiss = TypeVar('TFaiss', bound=FaissManager)

class DbService:
    _instance: 'DbService' = None
    
    # Attributs typés
    sqlite: TSqlite
    faiss: TFaiss

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            cls._instance.sqlite = SqliteManager(DATABASE_FILE)
            cls._instance.faiss = FaissManager(FAISS_INDEX_FILE)

        return cls._instance

if __name__ == "__main__":
    db = DbService()
    print(db.sqlite)
    print(db.faiss)