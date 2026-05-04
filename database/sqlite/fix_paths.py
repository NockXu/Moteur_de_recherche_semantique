import sqlite3
from pathlib import Path
import sys

# Ajouter le chemin racine pour importer la config
sys.path.append(str(Path(__file__).parent.parent.parent / "storage"))
from config import get_database_path

def fix_image_paths():
    """Corrige les chemins des images dans la base de données"""
    db_path = get_database_path()
    project_root = Path(__file__).parent.parent.parent
    dataset_path = project_root / "dataset" / "Dataset_01"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Récupérer toutes les images
        cursor.execute("SELECT id, path FROM images")
        rows = cursor.fetchall()
        
        print(f"🔧 Correction de {len(rows)} chemins d'images...")
        print(f"📁 Dataset cible: {dataset_path}")
        
        updated_count = 0
        for image_id, old_path in rows:
            # Extraire juste le nom du fichier du chemin ancien
            old_path_obj = Path(old_path)
            filename = old_path_obj.name
            
            # Créer le nouveau chemin vers le dataset local
            new_path = dataset_path / filename
            
            # Vérifier si le fichier existe
            if new_path.exists():
                # Mettre à jour le chemin
                cursor.execute("UPDATE images SET path = ? WHERE id = ?", (str(new_path), image_id))
                updated_count += 1
                print(f"✅ {image_id}: {filename} -> {new_path}")
            else:
                print(f"⚠️ {image_id}: Fichier non trouvé {new_path}")
        
        # Sauvegarder les changements
        conn.commit()
        print(f"🎯 {updated_count}/{len(rows)} chemins mis à jour")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la correction des chemins: {e}")
        return False

if __name__ == "__main__":
    fix_image_paths()
