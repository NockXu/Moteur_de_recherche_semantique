import os
import sys
from typing import TypeVar

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.sqlite.manager import SqliteManager
from database.faiss_manager.manager import FaissManager

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

            db_path = os.path.join(os.path.dirname(__file__), '..', 'storage', 'database', 'embeddings.db')
            faiss_index_path = os.path.join(os.path.dirname(__file__), '..', 'storage', 'indexes', 'images.index')

            cls._instance.sqlite = SqliteManager(db_path)
            cls._instance.faiss = FaissManager(faiss_index_path)

        return cls._instance

if __name__ == "__main__":
    db = DbService()
    print(db.sqlite)
    print(db.faiss)