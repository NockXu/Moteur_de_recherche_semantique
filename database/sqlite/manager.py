import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple

# Import de la configuration
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from storage.config import *
from common.ImageInfo import ImageInfo, ProcessingStatus


class SqliteManager:
    """Classe pour gérer la base de données SQLite"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialise le gestionnaire SQLite
        
        Args:
            db_path: Chemin vers la base de données. Si None, utilise storage/embeddings.db
        """
        if db_path is None:
            # Utiliser la configuration centralisée
            db_path = get_database_path()
            
            # S'assurer que le dossier existe
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = Path(db_path)
        self.conn = None
        self.cursor = None
        self._connect()
    
    def _connect(self):
        """Établit la connexion à la base de données"""
        try:
            # Permettre l'utilisation dans différents threads
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.cursor = self.conn.cursor()
        except Exception as e:
            print(f"❌ Erreur de connexion à la BDD: {e}")
            raise
    
    def image_info_to_db_row(self, image: ImageInfo, dataset_name: str = None, faiss_index: int = None) -> tuple:
        """Convertit ImageInfo en tuple pour insertion BDD"""
        # Extraire le nom du dataset du chemin si non fourni
        if dataset_name is None:
            path_parts = Path(image.path).parts
            # Chercher 'dataset' dans le chemin et prendre le dossier suivant
            if 'dataset' in path_parts:
                dataset_index = path_parts.index('dataset')
                if dataset_index + 1 < len(path_parts):
                    dataset_name = path_parts[dataset_index + 1]
            else:
                dataset_name = "unknown"
        
        # Obtenir ou créer le dataset et récupérer son ID
        dataset_id = self._get_or_create_dataset_id(dataset_name)
        
        return (
            image.id,
            str(image.path),
            image.name,
            image.description,
            json.dumps(image.keywords),
            datetime.now().isoformat(),
            faiss_index,  # faiss_index passé en paramètre
            dataset_id  # dataset_id au lieu de dataset_name
        )
    
    def db_row_to_image_info(self, row: tuple) -> ImageInfo:
        """Convertit une ligne de BDD en objet ImageInfo"""
        id, path, name, description, keywords_json, indexed_at, faiss_index, dataset_id = row
        
        # Parser les champs JSON
        keywords = json.loads(keywords_json) if keywords_json else []
        
        # Récupérer le nom du dataset depuis l'ID
        dataset_name = self._get_dataset_name_by_id(dataset_id)
        
        # Créer ImageInfo avec les bons paramètres
        image_info = ImageInfo(
            path=Path(path),
            description=description,
            keywords=keywords,
            embedding=[],  # Sera chargé séparément si besoin
            image_id=id
        )
        
        # IMPORTANT: Assigner le name APRÈS l'initialisation pour éviter l'écrasement
        # ImageInfo.__init__ écrase name avec self.path.name, donc on doit le réassigner
        image_info.name = name if name else image_info.name  # Utiliser le name de la BDD s'il existe
        image_info.indexed_at = indexed_at
        image_info.faiss_index = faiss_index
        image_info.dataset_name = dataset_name
        
        return image_info
    
    def insert_image(self, image: ImageInfo, dataset_name: str = "default") -> bool:
        """Insère une image dans la base de données"""
        try:
            row_data = self.image_info_to_db_row(image, dataset_name)
            self.cursor.execute("""
                INSERT OR REPLACE INTO images 
                (id, path, name, description, keywords, indexed_at, faiss_index, dataset_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, row_data)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Erreur insertion BDD: {e}")
            return False
    
    def _get_or_create_dataset_id(self, dataset_name: str) -> int:
        """Obtient l'ID d'un dataset ou le crée s'il n'existe pas"""
        try:
            # Vérifier si le dataset existe
            self.cursor.execute("SELECT id FROM datasets WHERE name = ?", (dataset_name,))
            result = self.cursor.fetchone()
            
            if result:
                return result[0]  # Retourner l'ID existant
            else:
                # Créer le dataset
                self.cursor.execute("INSERT INTO datasets (name) VALUES (?)", (dataset_name,))
                self.conn.commit()
                return self.cursor.lastrowid  # Retourner le nouvel ID
        except Exception as e:
            print(f"❌ Erreur gestion dataset {dataset_name}: {e}")
            return 1  # ID par défaut en cas d'erreur
    
    def _get_dataset_name_by_id(self, dataset_id: int) -> str:
        """Récupère le nom du dataset depuis son ID"""
        try:
            self.cursor.execute("SELECT name FROM datasets WHERE id = ?", (dataset_id,))
            result = self.cursor.fetchone()
            return result[0] if result else "unknown"
        except Exception as e:
            print(f"❌ Erreur récupération nom dataset ID {dataset_id}: {e}")
            return "unknown"
    
    def get_all_images(self) -> List[ImageInfo]:
        """Récupère toutes les images de la base de données"""
        try:
            self.cursor.execute("SELECT * FROM images ORDER BY indexed_at DESC")
            rows = self.cursor.fetchall()
            
            images = []
            for row in rows:
                image = self.db_row_to_image_info(row)
                images.append(image)
            
            return images
        except Exception as e:
            print(f"Erreur lors de la récupération des images: {e}")
            return []
    
    def get_image_by_id(self, image_id: str) -> Optional[ImageInfo]:
        """Récupère une image par son ID"""
        try:
            self.cursor.execute("SELECT * FROM images WHERE id = ?", (image_id,))
            row = self.cursor.fetchone()
            
            if row:
                return self.db_row_to_image_info(row)
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération de l'image {image_id}: {e}")
            return None
    
    def get_images_with_embeddings(self) -> List[ImageInfo]:
        """Récupère les images qui ont des embeddings"""
        try:
            self.cursor.execute("""
                SELECT * FROM images 
                WHERE faiss_index IS NOT NULL 
                ORDER BY indexed_at DESC
            """)
            rows = self.cursor.fetchall()
            
            images = []
            for row in rows:
                images.append(self.db_row_to_image_info(row))
            
            return images
        except Exception as e:
            print(f"❌ Erreur récupération images avec embeddings: {e}")
            return []
    
    def delete_image(self, image_id: str) -> bool:
        """Supprime une image de la base de données"""
        try:
            self.cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            print(f"Erreur lors de la suppression de l'image {image_id}: {e}")
            return False
    
    def dataset_exists(self, dataset_name: str) -> bool:
        """
        Vérifie si un dataset existe déjà dans la base de données
        """
        try:
            self.cursor.execute("SELECT COUNT(*) FROM datasets WHERE name = ?", (dataset_name,))
            count = self.cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            print(f"Erreur lors de la vérification du dataset: {e}")
            return False
    
    def close_connection(self):
        """Ferme la connexion à la base de données"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close_connection()
