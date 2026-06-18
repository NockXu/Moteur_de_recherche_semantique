"""Module de configuration pour le stockage centralisé
"""

from .config import (
    get_storage_paths,
    get_database_path,
    get_faiss_index_path,
    get_preview_cache_path,
    verify_storage
)

__all__ = [
    'get_database_path',
    'get_faiss_index_path',
    'get_preview_cache_path',
    'get_storage_paths',
    'verify_storage'
]
