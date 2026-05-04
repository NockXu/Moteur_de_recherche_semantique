# Module principal d'indexation
from .DatabaseManager import (
    DatabaseManager,
    insert_image,
    get_all_images,
    get_image_by_id,
    get_images_with_embeddings,
    delete_image,
    close_connection,
    search_similar_images,
    rebuild_faiss_index,
    get_faiss_stats,
    init_database,
    is_faiss_available
)

# Imports directs pour compatibilité
from .sqlite import SqliteManager
from .faiss import FaissManager, FAISS_AVAILABLE

__all__ = [
    # Classes principales
    'DatabaseManager',
    'SqliteManager', 
    'FaissManager',
    
    # Fonctions wrapper
    'insert_image',
    'get_all_images',
    'get_image_by_id',
    'get_images_with_embeddings',
    'delete_image',
    'close_connection',
    'search_similar_images',
    'rebuild_faiss_index',
    'get_faiss_stats',
    'init_database',
    'is_faiss_available',
    
    # Constantes
    'FAISS_AVAILABLE'
]
