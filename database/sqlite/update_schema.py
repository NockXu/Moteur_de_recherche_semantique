import sqlite3
from pathlib import Path
import sys

# Ajouter le chemin racine pour importer la config
sys.path.append(str(Path(__file__).parent.parent.parent / "storage"))
from config import get_database_path

def update_sqlite_schema():
    """Met à jour le schéma SQLite pour ajouter la colonne faiss_index"""
    db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Vérifier si la colonne faiss_index existe
        cursor.execute("PRAGMA table_info(images)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'faiss_index' not in columns:
            print("📝 Ajout de la colonne 'faiss_index' à la table images...")
            cursor.execute("ALTER TABLE images ADD COLUMN faiss_index INTEGER")
            conn.commit()
            print("✅ Colonne 'faiss_index' ajoutée avec succès")
        else:
            print("✅ La colonne 'faiss_index' existe déjà")
        
        # Supprimer la colonne embedding si elle existe
        if 'embedding' in columns:
            print("🗑️ Suppression de la colonne 'embedding' de la table images...")
            cursor.execute("ALTER TABLE images DROP COLUMN embedding")
            conn.commit()
            print("✅ Colonne 'embedding' supprimée")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour du schéma: {e}")
        return False

if __name__ == "__main__":
    update_sqlite_schema()
