"""Configuration des chemins de stockage pour le moteur de recherche sémantique
"""

from pathlib import Path
import os

# Chemin racine du stockage
STORAGE_ROOT = Path(__file__).parent

# Dossiers de stockage
DATABASE_DIR = STORAGE_ROOT / "database"
INDEXES_DIR = STORAGE_ROOT / "indexes"
PREVIEW_CACHE_DIR = STORAGE_ROOT / "preview_cache"

# Fichiers
DATABASE_FILE = DATABASE_DIR / "embeddings.db"
FAISS_INDEX_FILE = INDEXES_DIR / "images.index"

# Créer les dossiers s'ils n'existent pas
DATABASE_DIR.mkdir(exist_ok=True)
INDEXES_DIR.mkdir(exist_ok=True)
PREVIEW_CACHE_DIR.mkdir(exist_ok=True)

# Configuration par type de stockage
STORAGE_CONFIG = {
    "sqlite": {
        "path": str(DATABASE_FILE),
        "backup_path": str(DATABASE_DIR / "embeddings_backup.db")
    },
    "faiss": {
        "index_path": str(FAISS_INDEX_FILE),
        "dimension": 768,
        "metric": "cosine"  # cosine similarity
    },
    "preview_cache": {
        "path": str(PREVIEW_CACHE_DIR),
        "max_size_mb": 100
    }
}

def get_storage_paths():
    """Retourne tous les chemins de stockage configurés"""
    return STORAGE_CONFIG

def get_database_path():
    """Retourne le chemin de la base de données"""
    return str(DATABASE_FILE)

def get_faiss_index_path():
    """Retourne le chemin de l'index FAISS"""
    return str(FAISS_INDEX_FILE)

def get_preview_cache_path():
    """Retourne le chemin du cache de preview"""
    return str(PREVIEW_CACHE_DIR)

def verify_storage():
    """Vérifie que tous les dossiers de stockage existent"""
    issues = []
    
    if not DATABASE_DIR.exists():
        issues.append(f"Dossier database manquant: {DATABASE_DIR}")
    
    if not INDEXES_DIR.exists():
        issues.append(f"Dossier indexes manquant: {INDEXES_DIR}")
        
    if not PREVIEW_CACHE_DIR.exists():
        issues.append(f"Dossier preview_cache manquant: {PREVIEW_CACHE_DIR}")
    
    if issues:
        print("⚠️ Problèmes de stockage détectés:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("✅ Structure de stockage vérifiée avec succès")
    return True

if __name__ == "__main__":
    print("Configuration des chemins de stockage:")
    print(f"  Racine: {STORAGE_ROOT}")
    print(f"  Base de données: {DATABASE_FILE}")
    print(f"  Index FAISS: {FAISS_INDEX_FILE}")
    print(f"  Cache preview: {PREVIEW_CACHE_DIR}")
    
    # Vérifier la structure
    verify_storage()
