import sys
from pathlib import Path

# Ajouter les chemins pour les imports
sys.path.append(str(Path(__file__).parent))

from database.DatabaseManager import DatabaseManager

print("=== CORRECTION DES CHEMINS DANS LA BDD ===")

# Initialiser la base de données
db = DatabaseManager()

# Récupérer toutes les images
all_images = db.get_all_images()
print(f"Total images en BDD: {len(all_images)}")

# Compter les chemins cassés
broken_paths = 0
fixed_paths = 0

for img in all_images:
    original_path = str(img.path)
    
    # Vérifier si le chemin existe
    if not Path(original_path).exists():
        broken_paths += 1
        
        # Essayer de trouver le fichier dans les dossiers dataset
        possible_paths = [
            f"dataset/2017/test2017/{img.name}",
            f"dataset/2017/train2017/{img.name}",
            f"dataset/val2017/{img.name}",
            f"dataset/{img.name}"
        ]
        
        # Chercher le fichier
        found_path = None
        for possible_path in possible_paths:
            if Path(possible_path).exists():
                found_path = possible_path
                break
        
        if found_path:
            print(f"✅ Correction: {img.name}")
            print(f"   Ancien: {original_path}")
            print(f"   Nouveau: {found_path}")
            
            # Mettre à jour le chemin dans la BDD
            try:
                db.sqlite_manager.cursor.execute(
                    "UPDATE images SET path = ? WHERE id = ?",
                    (found_path, img.id)
                )
                db.sqlite_manager.conn.commit()
                fixed_paths += 1
            except Exception as e:
                print(f"❌ Erreur mise à jour: {e}")
        else:
            print(f"❌ Non trouvé: {img.name} ({original_path})")

print(f"\nRésumé:")
print(f"  - Chemins cassés: {broken_paths}")
print(f"  - Chemins corrigés: {fixed_paths}")
print(f"  - Non trouvés: {broken_paths - fixed_paths}")

# Vérifier après correction
print(f"\nVérification après correction:")
all_images_after = db.get_all_images()
still_broken = sum(1 for img in all_images_after if not Path(img.path).exists())
print(f"  - Images encore cassées: {still_broken}")

db.close_connection()
