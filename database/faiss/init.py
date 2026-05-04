import faiss
import numpy as np
from pathlib import Path
import sys

# Ajouter le chemin racine pour importer la config
sys.path.append(str(Path(__file__).parent.parent.parent / "storage"))
from config import get_faiss_index_path, verify_storage

# ---------------------------
# CONFIG
# ---------------------------
dimension = 768  # nomic-embed-text:v1.5

def init_faiss():
    """Initialise un index FAISS vide avec la bonne configuration"""
    
    # Utiliser la configuration centralisée
    faiss_path = Path(get_faiss_index_path())
    
    # S'assurer que le dossier existe
    faiss_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Créer un index cosine similarity (IndexFlatIP)
    index = faiss.IndexFlatIP(dimension)
    
    # Sauvegarder l'index vide
    faiss.write_index(index, str(faiss_path))
    
    print(f"✅ FAISS index initialized: {faiss_path}")
    print(f"   - Dimension: {dimension}")
    print(f"   - Metric: cosine similarity (Inner Product)")
    print(f"   - File size: {faiss_path.stat().st_size} bytes")

if __name__ == "__main__":
    init_faiss()