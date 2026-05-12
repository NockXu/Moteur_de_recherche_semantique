from pathlib import Path
from typing import List, Optional, Tuple
import sqlite3

from storage.config import get_database_path


class SqliteManager:

    def __init__(self, db_path: str = None):
        # Utiliser get_database_path() par défaut si db_path n'est pas fourni
        if db_path is None:
            db_path = get_database_path()
        
        if db_path is None:
            raise Exception("db_path cannot be None")
        
        self.db_path = Path(db_path)
        self.conn = None
        self.cursor = None
        
        # Vérifier si la base de données existe, sinon l'initialiser
        self._ensure_database_exists()
        
        self.connect()

    # =========================
    # DATABASE INITIALIZATION
    # =========================
    def _ensure_database_exists(self):
        """Vérifie si la base de données existe, sinon l'initialise"""
        if not self.db_path.exists():
            self._initialize_database()

    def _initialize_database(self):
        """Initialise la base de données en utilisant le script d'initialisation"""
        try:
            import sqlite3
            from database.sqlite.init import CREATE_TABLE_SQL
            
            # S'assurer que le dossier existe
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Créer une connexion spécifique à ce chemin
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Exécuter chaque requête CREATE TABLE séparément
            statements = CREATE_TABLE_SQL.split(';')
            
            for i, statement in enumerate(statements):
                statement = statement.strip()
                if statement:
                    try:
                        cursor.execute(statement)
                    except sqlite3.OperationalError as e:
                        # Ignorer les erreurs "table already exists"
                        if "already exists" not in str(e):
                            raise Exception(f"Error in statement {i+1}: {e}")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            raise RuntimeError(f"Error initializing database: {e}")

    # =========================
    # CONNECTION
    # =========================
    def connect(self):
        try:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.cursor = self.conn.cursor()
        except Exception as e:
            raise RuntimeError(f"Erreur connexion SQLite: {e}")

    def close(self):
        if self.conn:
            self.conn.close()

    # =========================
    # EXECUTION
    # =========================
    def execute(self, query: str, params: Tuple = ()):
        try:
            self.cursor.execute(query, params)
        except Exception as e:
            raise RuntimeError(f"SQL error: {e}")

    def executemany(self, query: str, params_list: List[Tuple]):

        try:
            self.cursor.executemany(query, params_list)
            self.conn.commit()

        except Exception as e:
            raise RuntimeError(f"SQL error: {e}")

    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Tuple]:
        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    def fetch_all(self, query: str, params: Tuple = ()) -> List[Tuple]:
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    # =========================
    # TRANSACTIONS
    # =========================
    def begin(self):
        self.conn.execute("BEGIN")

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    # =========================
    # CONTEXT MANAGER
    # =========================
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

if __name__ == "__main__":
    manager = SqliteManager(get_database_path())