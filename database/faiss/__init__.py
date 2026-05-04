# Module FAISS pour la recherche vectorielle
from .manager import FaissManager, FAISS_AVAILABLE
from .init import init_faiss

__all__ = [
    'FaissManager',
    'FAISS_AVAILABLE', 
    'init_faiss'
]
