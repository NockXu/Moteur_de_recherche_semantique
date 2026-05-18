from typing import TypeVar
import threading

from database.sqlite.manager import SqliteManager
from database.faiss_manager.manager import FaissManager

from storage.config import FAISS_INDEX_FILE, DATABASE_FILE

# TypeVars pour un typage plus précis
TSqlite = TypeVar('TSqlite', bound=SqliteManager)
TFaiss = TypeVar('TFaiss', bound=FaissManager)

class DbService:
    """
    Singleton service that provides access to database and FAISS index managers.

    This class ensures a single shared instance of database services across
    the application.
    """

    _thread_local = threading.local()

    # Typed attributes
    sqlite: TSqlite
    faiss: TFaiss

    def __new__(cls) -> "DbService":
        """
        Create or return the singleton instance.

        Initializes database managers on first creation.

        Returns:
            The singleton instance.
        """
        # If already created in this thread → reuse
        if hasattr(cls._thread_local, "instance"):
            return cls._thread_local.instance

        # Else create a new instance for this thread
        instance = super().__new__(cls)

        instance.sqlite = SqliteManager(DATABASE_FILE)
        instance.faiss = FaissManager(FAISS_INDEX_FILE)

        cls._thread_local.instance = instance

        return cls._thread_local.instance

if __name__ == "__main__":
    db = DbService()
    print(db.sqlite)
    print(db.faiss)