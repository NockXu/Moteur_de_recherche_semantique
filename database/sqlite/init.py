import sqlite3
from pathlib import Path
import sys
import os

# Ajouter le chemin racine pour importer la config
sys.path.append(str(Path(__file__).parent.parent.parent / "storage"))
from config import get_database_path, verify_storage

# ---------------------------
# PATH
# ---------------------------
db_path = get_database_path()

# ---------------------------
# CONNECTION
# ---------------------------
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# ---------------------------
# TABLE
# ---------------------------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY,
    path TEXT UNIQUE,
    name TEXT,
    description TEXT,
    keywords TEXT,
    indexed_at TEXT,
    dataset_id INTEGER,
    embedding BLOB,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id)
);
"""

def init_sqlite():
    # Exécuter chaque requête CREATE TABLE séparément
    statements = CREATE_TABLE_SQL.split(';')
    for statement in statements:
        statement = statement.strip()
        if statement:
            cursor.execute(statement)
    conn.commit()
    conn.close()
    print("SQLite database initialized.")

if __name__ == "__main__":
    init_sqlite()