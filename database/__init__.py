# Imports directs pour compatibilité
from .DbService import DbService
from .faiss_manager.manager import FAISS_AVAILABLE

__all__ = [
    # Classes principales
    'DbService',
    
    # Constantes
    'FAISS_AVAILABLE'
]
