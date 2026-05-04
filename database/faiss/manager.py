from pathlib import Path
from typing import List, Optional

# Imports FAISS
try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    print("⚠️ FAISS non disponible, recherche vectorielle désactivée")
    FAISS_AVAILABLE = False

# Import de la configuration
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from storage.config import *
from common.ImageInfo import ImageInfo

class FaissManager:
    """Singleton pour éviter les créations multiples d'index FAISS"""
    
    _instance = None
    _index = None
    _image_ids = []
    
    def __new__(cls, *args, **kwargs):
        """Pattern singleton"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, index_path: Optional[Path] = None, dimension: int = 768):
        """
        Initialise le gestionnaire FAISS (une seule fois grâce au singleton)
        
        Args:
            index_path: Chemin vers l'index FAISS. Si None, utilise la configuration
            dimension: Dimension des embeddings (768 pour nomic-embed-text:v1.5)
        """
        # N'initialiser qu'une seule fois
        if hasattr(self, '_initialized'):
            return
        
        # Utiliser la configuration centralisée
        if index_path is None:
            index_path = Path(get_faiss_index_path())
        
        # Attributs de classe (partagés par toutes les instances)
        FaissManager._index_path = Path(index_path)
        FaissManager._dimension = dimension
        FaissManager._image_ids = []  # Pour mapper les indices FAISS aux IDs d'images
        
        if FAISS_AVAILABLE:
            self._load_or_create_index()
        
        # Marquer comme initialisé
        self._initialized = True
    
    @classmethod
    def _load_or_create_index(cls):
        """Charge un index existant ou en crée un nouveau"""
        try:
            if cls._index_path.exists():
                cls._index = faiss.read_index(str(cls._index_path))
                print(f"✅ Index FAISS chargé: {cls._index.ntotal} vecteurs")
            else:
                # Créer un nouvel index (cosine similarity)
                cls._index = faiss.IndexFlatIP(cls._dimension)
                print(f"🆕 Index FAISS créé (dimension: {cls._dimension})")
        except Exception as e:
            print(f"❌ Erreur lors du chargement de l'index FAISS: {e}")
            cls._index = faiss.IndexFlatIP(cls._dimension)
    
    @classmethod
    def get_next_index(cls) -> int:
        """Retourne le prochain index disponible pour FAISS"""
        if not FAISS_AVAILABLE or not cls._index:
            return 0
        return cls._index.ntotal
    
    @classmethod
    def add_embedding(cls, image_id: str, embedding: List[float]) -> bool:
        """Ajoute un embedding à l'index FAISS"""
        if not FAISS_AVAILABLE or not cls._index:
            return False
        
        try:
            # Convertir en numpy array et normaliser
            embedding_array = np.array([embedding], dtype=np.float32)
            faiss.normalize_L2(embedding_array)
            
            # Ajouter à l'index et récupérer la position
            vector_index = cls._index.ntotal
            cls._index.add(embedding_array)
            cls._image_ids.append(image_id)
            
            # Sauvegarder l'index
            cls._save_index()
            
            # Retourner la position pour le mapping SQLite
            return vector_index
        except Exception as e:
            print(f"❌ Erreur ajout embedding FAISS: {e}")
            return False
    
    @classmethod
    def search_similar(cls, query_embedding: List[float], k: int = 10, tolerance: float = 0.7) -> List[tuple]:
        """
        Recherche les embeddings similaires
        
        Args:
            query_embedding: Embedding de la requête
            k: Nombre de résultats à retourner
            tolerance: Score minimum de similarité (0-1)
            
        Returns:
            Liste de tuples (image_id, score)
        """
        if not FAISS_AVAILABLE or not cls._index or cls._index.ntotal == 0:
            return []
        
        try:
            # Normaliser la requête
            query_array = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_array)
            
            # Rechercher
            distances, indices = cls._index.search(query_array, min(k, cls._index.ntotal))
            
            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx >= 0 and idx < len(cls._image_ids) and dist >= tolerance:
                    image_id = cls._image_ids[idx]
                    results.append((image_id, float(dist)))
            
            return results
        except Exception as e:
            print(f"❌ Erreur recherche FAISS: {e}")
            return []
    
    @classmethod
    def _save_index(cls):
        """Sauvegarde l'index FAISS sur disque"""
        if not FAISS_AVAILABLE or not cls._index:
            return
        
        try:
            faiss.write_index(cls._index, str(cls._index_path))
        except Exception as e:
            print(f"❌ Erreur sauvegarde index FAISS: {e}")
    
    @classmethod
    def rebuild_index(cls, images: List[ImageInfo]) -> bool:
        """Reconstruit complètement l'index à partir d'une liste d'images"""
        if not FAISS_AVAILABLE:
            return False
        
        try:
            # Créer un nouvel index
            cls._index = faiss.IndexFlatIP(cls._dimension)
            cls._image_ids.clear()
            
            # Ajouter tous les embeddings
            for image in images:
                if image.embedding and len(image.embedding) == cls._dimension:
                    cls.add_embedding(image.id, image.embedding)
            
            print(f"✅ Index FAISS reconstruit: {cls._index.ntotal} vecteurs")
            return True
        except Exception as e:
            print(f"❌ Erreur reconstruction index FAISS: {e}")
            return False
    
    @classmethod
    def get_stats(cls) -> dict:
        """Retourne des statistiques sur l'index FAISS"""
        if not FAISS_AVAILABLE or not cls._index:
            return {"available": False}
        
        return {
            "available": True,
            "total_vectors": cls._index.ntotal,
            "dimension": cls._dimension,
            "index_path": str(cls._index_path),
            "index_exists": cls._index_path.exists()
        }
