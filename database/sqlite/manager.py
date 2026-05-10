from pathlib import Path
from typing import List, Optional, Tuple
import sqlite3


class SqliteManager:

    def __init__(self, db_path: str):
        if db_path is None:
            raise Exception("db_path cannot be None")
        self.db_path = Path(db_path)
        self.conn = None
        self.cursor = None
        self.connect()

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
            print(f"❌ SQL error: {e}")
            raise

    def executemany(self, query: str, params_list: List[Tuple]):

        try:
            self.cursor.executemany(query, params_list)
            self.conn.commit()

        except Exception as e:
            print(f"❌ SQL error: {e}")
            raise

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