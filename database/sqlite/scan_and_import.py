import sqlite3
from pathlib import Path
import sys
import json
from PIL import Image

# Ajouter le chemin racine pour importer la config
sys.path.append(str(Path(__file__).parent.parent.parent / "storage"))
from config import get_database_path

# Ajouter le chemin pour importer les classes
sys.path.append(str(Path(__file__).parent.parent.parent))
from common.ImageInfo import ImageInfo, ProcessingStatus

def scan_and_import():
    """Scan tous les datasets et importe les images avec les bons chemins"""
    db_path = get_database_path()
    project_root = Path(__file__).parent.parent.parent
    dataset_root = project_root / "dataset"
    
    print(f"📁 Scan du dossier dataset: {dataset_root}")
    
    # Connexion à la base de données
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Trouver tous les sous-dossiers dans dataset
    dataset_folders = [d for d in dataset_root.iterdir() if d.is_dir() and d.name != "__pycache__"]
    
    total_images = 0
    total_datasets = 0
    
    for dataset_folder in dataset_folders:
        dataset_name = dataset_folder.name
        print(f"\n📂 Traitement du dataset: {dataset_name}")
        
        # Insérer le dataset dans la table datasets (s'il n'existe pas déjà)
        try:
            cursor.execute("INSERT OR IGNORE INTO datasets (name) VALUES (?)", (dataset_name,))
            conn.commit()
            total_datasets += 1
        except Exception as e:
            print(f"⚠️ Erreur insertion dataset {dataset_name}: {e}")
            continue
        
        # Trouver toutes les images dans ce dossier
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(dataset_folder.glob(f"*{ext}"))
            image_files.extend(dataset_folder.glob(f"*{ext.upper()}"))
        
        print(f"🖼️  {len(image_files)} images trouvées dans {dataset_name}")
        
        # Insérer chaque image
        imported_count = 0
        for image_path in image_files:
            try:
                # Créer un ImageInfo avec le VRAI chemin
                image_info = ImageInfo(
                    path=image_path,  # Utiliser le chemin réel du fichier
                    score=0.0,
                    status=ProcessingStatus.NOT_STARTED,
                    description="",
                    keywords=[],
                    embedding=[],
                    error_message="",
                    processing_start_time=None,
                    processing_end_time=None,
                    image_id=image_path.stem
                )
                
                # Insérer dans la base de données avec le nom du dataset
                cursor.execute("""
                    INSERT OR REPLACE INTO images 
                    (id, path, name, description, keywords, indexed_at, faiss_index, dataset_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    image_info.id,
                    str(image_info.path),
                    image_info.name,
                    image_info.description,
                    json.dumps(image_info.keywords),
                    "",  # indexed_at vide pour l'instant
                    None,  # faiss_index vide pour l'instant
                    dataset_name
                ))
                
                imported_count += 1
                total_images += 1
                
            except Exception as e:
                print(f"❌ Erreur insertion image {image_path.name}: {e}")
        
        conn.commit()
        print(f"✅ Dataset {dataset_name}: {imported_count}/{len(image_files)} images importées")
    
    conn.close()
    
    print(f"\n🎯 Terminé!")
    print(f"📊 {total_datasets} datasets créés")
    print(f"🖼️  {total_images} images insérées")
    print(f"💾 Base de données: {db_path}")
    
    return total_images

if __name__ == "__main__":
    scan_and_import()
