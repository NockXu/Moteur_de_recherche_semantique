from typing import List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import json

# Import des managers spécialisés depuis les modules structurés
from .sqlite import SqliteManager
from .faiss import FaissManager, FAISS_AVAILABLE
from common.ImageInfo import ImageInfo


class DatabaseManager:
    """
    Classe principale qui combine SQLite et FAISS pour la gestion d'images.
    SQLite: Métadonnées et stockage persistant
    FAISS: Recherche vectorielle ultra-rapide
    """
    
    def __init__(self, db_path: Optional[str] = None, faiss_index_path: Optional[Path] = None):
        """
        Initialise le gestionnaire de base de données avec FAISS
        
        Args:
            db_path: Chemin vers la base SQLite. Si None, utilise storage/embeddings.db
            faiss_index_path: Chemin vers l'index FAISS. Si None, utilise storage/images.index
        """
        # Initialiser le gestionnaire SQLite
        self.sqlite_manager = SqliteManager(db_path)
        
        # Initialiser le gestionnaire FAISS (indépendant)
        self.faiss_manager = FaissManager(faiss_index_path)
    
    # --- Délégation des méthodes SQLite ---
    
    def dataset_exists(self, dataset_name: str) -> bool:
        """
        Vérifie si un dataset existe déjà dans la base de données
        """
        return self.sqlite_manager.dataset_exists(dataset_name)
    
    def insert_image(self, image: ImageInfo, dataset_name: str = None) -> bool:
        """
        Insère une image dans la base de données et dans FAISS
        """
        try:
            # Ajouter à FAISS d'abord pour récupérer l'index
            faiss_index = None
            if self.faiss_manager and image.embedding and len(image.embedding) > 0:
                faiss_index = self.faiss_manager.add_embedding(image.id, image.embedding)
            
            # Insérer dans SQLite avec le mapping FAISS
            dataset_id = self.sqlite_manager._get_or_create_dataset_id(dataset_name or "unknown")
            row_data = (
                image.id,
                str(image.path),
                image.name,
                image.description,
                json.dumps(image.keywords),
                datetime.now().isoformat(),
                faiss_index,
                dataset_id
            )
            
            self.sqlite_manager.cursor.execute("""
                INSERT OR REPLACE INTO images 
                (id, path, name, description, keywords, indexed_at, faiss_index, dataset_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, row_data)
            self.sqlite_manager.conn.commit()
            print(f"✅ Ajouté à SQLite: {image.id} (dataset: {dataset_name or 'unknown'})")
            return True
            
        except Exception as e:
            print(f"❌ Erreur insertion image {image.id}: {e}")
            return False
    
    def insert_images_batch(self, images_data: List[Tuple[ImageInfo, str]]) -> Tuple[int, int]:
        """
        Insère plusieurs images en batch avec gestion FAISS
        
        Args:
            images_data: Liste de tuples (ImageInfo, dataset_name)
            
        Returns:
            Tuple (success_count, total_count)
        """
        if not images_data:
            return 0, 0
        
        success_count = 0
        total_count = len(images_data)
        
        try:
            # Commencer une transaction sur le SqliteManager
            self.sqlite_manager.cursor.execute("BEGIN TRANSACTION")
            
            # Obtenir le base index pour les FAISS
            self.sqlite_manager.cursor.execute("SELECT MAX(faiss_index) FROM images")
            max_index_result = self.sqlite_manager.cursor.fetchone()[0]
            base_index = (max_index_result + 1) if max_index_result is not None else 0
            
            print(f"DEBUG: Base index pour ce batch: {base_index} (max_index existant: {max_index_result})")
            
            # Préparer les données pour l'insertion en lot
            rows_data = []
            for i, (image, dataset_name) in enumerate(images_data):
                try:
                    # Calculer l'index unique pour cette image
                    faiss_index = base_index + i
                    
                    # Debug: afficher les informations de cette image
                    print(f"DEBUG: Préparation image {i+1}/{len(images_data)}")
                    print(f"  - ID: {image.id}")
                    print(f"  - Dataset: {dataset_name}")
                    print(f"  - Path: {image.path}")
                    print(f"  - Final FAISS Index: {faiss_index}")
                    print(f"  - Embedding length: {len(image.embedding) if image.embedding else 0}")
                    
                    # Préparer les données complètes pour cette image
                    dataset_id = self.sqlite_manager._get_or_create_dataset_id(dataset_name)
                    
                    # Insérer l'embedding dans FAISS si présent
                    actual_faiss_index = faiss_index  # Valeur par défaut
                    if image.embedding and len(image.embedding) > 0:
                        # add_embedding retourne la position réelle dans FAISS
                        actual_faiss_index = self.faiss_manager.add_embedding(image.id, image.embedding)
                        if actual_faiss_index is not False:
                            print(f"  ✅ Embedding FAISS inséré pour {image.id} (position: {actual_faiss_index})")
                        else:
                            print(f"  ❌ Erreur insertion embedding FAISS pour {image.id}")
                            actual_faiss_index = faiss_index  # Fallback sur notre index calculé
                    else:
                        print(f"  ⚠️ Pas d'embedding pour {image.id}")
                    
                    row_data = (
                        image.id,
                        str(image.path),
                        image.name,
                        image.description,
                        json.dumps(image.keywords),
                        datetime.now().isoformat(),
                        actual_faiss_index,  # Vraie position FAISS
                        dataset_id  # dataset_id
                    )
                    rows_data.append(row_data)
                    
                    print(f"  ✅ Image {image.id} préparée avec succès")
                except Exception as e:
                    print(f"❌ Erreur préparation image {image.id}: {e}")
                    continue
            
            # Exécuter l'insertion en lot avec executemany
            if rows_data:
                print(f"DEBUG: Exécution de l'insertion batch de {len(rows_data)} images...")
                
                self.sqlite_manager.cursor.executemany("""
                    INSERT OR REPLACE INTO images 
                    (id, path, name, description, keywords, indexed_at, faiss_index, dataset_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, rows_data)
                
                # Commit de la transaction
                self.sqlite_manager.conn.commit()
                success_count = len(rows_data)
                
                print(f"DEBUG: Transaction commitée avec succès")
                print(f"✅ Insertion batch: {success_count}/{total_count} images insérées")
                
                # Vérifier le nombre d'images dans la base après insertion
                self.sqlite_manager.cursor.execute("SELECT COUNT(*) FROM images")
                count_after = self.sqlite_manager.cursor.fetchone()[0]
                print(f"DEBUG: Total images en BDD après insertion: {count_after}")
                
            else:
                # Rollback si aucune donnée valide
                self.sqlite_manager.conn.rollback()
                print(f"❌ Aucune image valide à insérer")
                
        except Exception as e:
            # Rollback en cas d'erreur
            self.sqlite_manager.conn.rollback()
            print(f"❌ Erreur insertion batch: {e}")
            return 0, total_count
        
        return success_count, total_count
    
    def get_all_images(self) -> List[ImageInfo]:
        """Récupère toutes les images de la base de données"""
        return self.sqlite_manager.get_all_images()
    
    def get_image_by_id(self, image_id: str) -> Optional[ImageInfo]:
        """Récupère une image par son ID"""
        return self.sqlite_manager.get_image_by_id(image_id)
    
    def get_images_with_embeddings(self) -> List[ImageInfo]:
        """Récupère uniquement les images qui ont des embeddings"""
        return self.sqlite_manager.get_images_with_embeddings()
    
    def delete_image(self, image_id: str) -> bool:
        """Supprime une image de la base de données"""
        return self.sqlite_manager.delete_image(image_id)
    
    # --- Méthodes FAISS ---
    
    def search_similar_images(self, query_embedding: List[float], k: int = 10, tolerance: float = 0.7) -> List[ImageInfo]:
        """
        Recherche les images similaires using FAISS
        
        Args:
            query_embedding: Embedding de la requête
            k: Nombre de résultats à retourner
            tolerance: Score minimum de similarité (0-1)
            
        Returns:
            Liste d'ImageInfo avec scores
        """
        if not self.faiss_manager:
            print("⚠️ FAISS non disponible, recherche vectorielle désactivée")
            return []
        
        try:
            # Recherche FAISS
            faiss_results = self.faiss_manager.search_similar(query_embedding, k, tolerance)
            print(f"🔍 FAISS: {len(faiss_results)} résultats trouvés")
            
            # Récupérer les ImageInfo complètes depuis SQLite
            similar_images = []
            for image_id, score in faiss_results:
                image = self.sqlite_manager.get_image_by_id(image_id)
                if image:
                    image.score = score
                    similar_images.append(image)
                else:
                    print(f"⚠️ Image {image_id} non trouvée en SQLite")
            
            return similar_images
        except Exception as e:
            print(f"❌ Erreur recherche FAISS: {e}")
            return []
    
    def sync_faiss_with_sqlite(self) -> bool:
        """
        Synchronise l'index FAISS avec la base SQLite
        Utile après import/export manuel
        """
        if not self.faiss_manager:
            print("⚠️ FAISS non disponible")
            return False
        
        try:
            # Récupérer toutes les images avec embeddings
            all_images = self.sqlite_manager.get_images_with_embeddings()
            print(f"🔄 Synchronisation: {len(all_images)} images avec embeddings")
            
            # Reconstruire l'index FAISS
            success = self.faiss_manager.rebuild_index(all_images)
            if success:
                print("✅ Synchronisation FAISS/SQLite terminée")
            else:
                print("❌ Échec synchronisation FAISS")
            
            return success
        except Exception as e:
            print(f"❌ Erreur synchronisation: {e}")
            return False
    
    def get_sync_stats(self) -> dict:
        """
        Retourne des statistiques de synchronisation entre FAISS et SQLite
        """
        stats = {
            "sqlite_total": 0,
            "sqlite_with_embeddings": 0,
            "faiss_total": 0,
            "synced": False
        }
        
        try:
            # Stats SQLite
            all_images = self.sqlite_manager.get_all_images()
            stats["sqlite_total"] = len(all_images)
            
            images_with_embeddings = self.sqlite_manager.get_images_with_embeddings()
            stats["sqlite_with_embeddings"] = len(images_with_embeddings)
            
            # Stats FAISS
            if self.faiss_manager:
                faiss_stats = self.faiss_manager.get_stats()
                stats["faiss_total"] = faiss_stats.get("total_vectors", 0)
                stats["synced"] = stats["faiss_total"] == stats["sqlite_with_embeddings"]
            
            return stats
        except Exception as e:
            print(f"❌ Erreur stats: {e}")
            return stats
    
    def rebuild_faiss_index(self) -> bool:
        """Reconstruit l'index FAISS à partir de toutes les images en base"""
        if not self.faiss_manager:
            print("⚠️ FAISS non disponible")
            return False
        
        all_images = self.sqlite_manager.get_all_images()
        return self.faiss_manager.rebuild_index(all_images)
    
    def get_faiss_stats(self) -> dict:
        """Retourne des statistiques sur l'index FAISS"""
        if not self.faiss_manager:
            return {"available": False}
        
        return self.faiss_manager.get_stats()
    
    # --- Gestion des connexions ---
    
    def close_connection(self):
        """Ferme toutes les connexions"""
        self.sqlite_manager.close_connection()
        # FAISS n'a pas de connexion à fermer (sauvegarde automatique)
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close_connection()


# --- Instance globale et fonctions wrapper pour compatibilité ---

# Instance globale pour compatibilité avec le code existant
_db_manager = DatabaseManager()

# Fonctions globales pour compatibilité
def insert_image(image: ImageInfo) -> bool:
    """Insère une image dans la base de données (wrapper)"""
    return _db_manager.insert_image(image)

def get_all_images() -> List[ImageInfo]:
    """Récupère toutes les images de la base de données (wrapper)"""
    return _db_manager.get_all_images()

def get_image_by_id(image_id: str) -> Optional[ImageInfo]:
    """Récupère une image par son ID (wrapper)"""
    return _db_manager.get_image_by_id(image_id)

def get_images_with_embeddings() -> List[ImageInfo]:
    """Récupère uniquement les images qui ont des embeddings (wrapper)"""
    return _db_manager.get_images_with_embeddings()

def delete_image(image_id: str) -> bool:
    """Supprime une image de la base de données (wrapper)"""
    return _db_manager.delete_image(image_id)

def close_connection():
    """Ferme la connexion à la base de données (wrapper)"""
    _db_manager.close_connection()

# Fonctions FAISS
def search_similar_images(query_embedding: List[float], k: int = 10, tolerance: float = 0.7) -> List[ImageInfo]:
    """Recherche les images similaires (wrapper)"""
    return _db_manager.search_similar_images(query_embedding, k, tolerance)

def rebuild_faiss_index() -> bool:
    """Reconstruit l'index FAISS (wrapper)"""
    return _db_manager.rebuild_faiss_index()

def get_faiss_stats() -> dict:
    """Retourne les statistiques FAISS (wrapper)"""
    return _db_manager.get_faiss_stats()

def sync_faiss_with_sqlite() -> bool:
    """Synchronise FAISS avec SQLite (wrapper)"""
    return _db_manager.sync_faiss_with_sqlite()

def get_sync_stats() -> dict:
    """Retourne les statistiques de synchronisation (wrapper)"""
    return _db_manager.get_sync_stats()

def init_database():
    """Initialise la base de données (wrapper)"""
    # Déjà fait dans __init__
    pass

def is_faiss_available() -> bool:
    """Vérifie si FAISS est disponible"""
    return FAISS_AVAILABLE
