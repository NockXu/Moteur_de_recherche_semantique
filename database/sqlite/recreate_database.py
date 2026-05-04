import sqlite3
from pathlib import Path
import sys
import shutil

# Ajouter le chemin racine pour importer la config
sys.path.append(str(Path(__file__).parent.parent.parent / "storage"))
from config import get_database_path

def recreate_database():
    """Recrée la base de données avec la nouvelle structure incluant la colonne dataset"""
    db_path = Path(get_database_path())
    
    print(f"🔄 Recréation de la base de données: {db_path}")
    
    # Sauvegarder l'ancienne base de données si elle existe
    if db_path.exists():
        backup_path = db_path.with_suffix('.db.backup')
        print(f"💾 Sauvegarde de l'ancienne base: {backup_path}")
        shutil.copy2(db_path, backup_path)
    
    # Supprimer l'ancienne base de données
    if db_path.exists():
        db_path.unlink()
        print("🗑️ Ancienne base de données supprimée")
    
    # Créer la nouvelle base de données
    from init import init_sqlite
    init_sqlite()
    
    print("✅ Base de données recréée avec la colonne 'dataset'")
    print("📊 Structure de la table:")
    
    # Afficher la structure de la table
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(images)")
    columns = cursor.fetchall()
    
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    conn.close()
    return True

if __name__ == "__main__":
    recreate_database()
