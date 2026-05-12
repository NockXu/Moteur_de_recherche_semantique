import sqlite3
from storage.config import get_database_path

CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS datasets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE,
        name TEXT,
        description TEXT,
        keywords TEXT,
        indexed_at TEXT,
        dataset_id INTEGER,
        embedding BLOB,
        FOREIGN KEY (dataset_id) REFERENCES datasets(id)
    );

    INSERT OR IGNORE INTO datasets (name) VALUES ('default');
    """

def init_sqlite():
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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE,
        name TEXT,
        description TEXT,
        keywords TEXT,
        indexed_at TEXT,
        dataset_id INTEGER,
        embedding BLOB,
        FOREIGN KEY (dataset_id) REFERENCES datasets(id)
    );

    INSERT INTO datasets (name) VALUES ('default');
    """

    # Créer sa propre connexion pour être autonome
    db_path = get_database_path()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Exécuter chaque requête CREATE TABLE séparément
    statements = CREATE_TABLE_SQL.split(';')
    
    for i, statement in enumerate(statements):
        statement = statement.strip()
        if statement:
            try:
                cursor.execute(statement)
            except Exception as e:
                raise Exception(f"Error in statement {i+1}: {e}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_sqlite()