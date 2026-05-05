import sys
import os

# Ajouter la racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.Image_Classes.Image import Image
from common.Dataset_Classes.DatasetRepository import DatasetRepository
from database.faiss_manager.manager import FaissManager
from database.sqlite.manager import SqliteManager
from database import DbService
import json
from datetime import datetime
from typing import List, TypedDict, Optional

class SearchResults(TypedDict):
    """Résultats de recherche avec pagination"""
    images: List[Image]
    next_cursor: Optional[float]
    has_more: bool

    def __init__(self, images: List[Image], next_cursor: Optional[float], has_more: bool):
        self.images = images
        self.next_cursor = next_cursor
        self.has_more = has_more

class ImageRepository:
    def __init__(self, db: SqliteManager, faiss: FaissManager):
        self.db = db
        self.faiss = faiss
        self._dataset_repo = DatasetRepository(db)
        self._dataset_cache = {}  # Cache pour éviter les requêtes répétées
        
    def _get_dataset_by_id(self, dataset_id: int):
        """
        Récupère un dataset par son ID avec cache pour éviter les requêtes répétées
        
        Args:
            dataset_id: ID du dataset
            
        Returns:
            Dataset ou None si non trouvé
        """
        # Vérifier le cache d'abord
        if dataset_id in self._dataset_cache:
            return self._dataset_cache[dataset_id]
        
        # Récupérer depuis la BDD
        dataset = self._dataset_repo.get_by_id(dataset_id)
        
        # Mettre en cache
        if dataset:
            self._dataset_cache[dataset_id] = dataset
        
        return dataset
    
    def save_image(self, image: Image) -> bool:
        # 1. FAISS
        faiss_index = None
        if image.embedding:
            indexes = self.faiss.add([image.embedding])
            faiss_index = indexes[0] if indexes else None

        # 2. SQLite
        self.db.execute("""
            INSERT OR REPLACE INTO images
            (id, path, name, description, keywords, indexed_at, faiss_index, dataset_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            image.id,
            str(image.path),
            image.name,
            image.description,
            json.dumps(image.keywords),
            datetime.now().isoformat(),
            faiss_index,
            image.dataset_id
        ))

        return True
    
    def search(
        self,
        query: List[float],
        threshold: float = 0.5,
        limit: int = 20,
        cursor_score: float | None = None  # Score du dernier résultat affiché
    ) -> SearchResults:
        """
        Args:
            cursor_score: Score du dernier item affiché (None = première page)
            limit:        Nombre de résultats à retourner

        Returns:
            SearchResults: Résultats de recherche avec pagination
        """
        # Récupération des datasets
        dataset_repo = DatasetRepository(self.db)
        datasets = dataset_repo.get_all()

        raw_results = self.faiss.search(
            query=query,
            threshold=threshold,
        )
        # raw_results est déjà trié par score décroissant

        # Reprise depuis le curseur
        if cursor_score is not None:
            raw_results = [(idx, s) for idx, s in raw_results if s < cursor_score]

        # Slice de la page courante + 1 pour détecter has_more
        page_results = raw_results[:limit + 1]
        has_more     = len(page_results) > limit
        page_results = page_results[:limit]

        images = []
        for idx, score in page_results:
            row = self.db.fetch_one(
                "SELECT * FROM images WHERE faiss_index = ?", (idx,)
            )
            if row:
                # Désérialiser les keywords depuis JSON
                keywords = []
                if row[4]:
                    try:
                        keywords = json.loads(row[4])
                    except:
                        keywords = []
                
                # Récupérer le dataset par ID
                dataset = self._get_dataset_by_id(row[7])
                
                if not dataset:
                    print(f"⚠️ Dataset {row[7]} non trouvé pour l'image {row[0]}")
                    continue
                
                # Création de l'image avec le vrai objet Dataset
                new_image = Image(
                    path=row[1],
                    dataset=dataset,  # Vrai objet Dataset
                    description=row[3] or "",
                    keywords=keywords,
                    image_id=row[0],
                    score=score
                )

                # Ajout de l'image à la liste
                images.append(new_image)

        # Détermination du prochain curseur
        next_cursor = page_results[-1][1] if has_more and page_results else None

        # Retour des résultats sous forme de SearchResults
        return SearchResults(
            images=images,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def get_all(self) -> List[Image]:
        """
        Récupère toutes les images de la base de données.
        
        Returns:
            List[Image]: Liste de toutes les images
        """
        rows = self.db.fetch_all("SELECT * FROM images")
        images = []
        for row in rows:
            # Désérialiser les keywords depuis JSON
            keywords = []
            if row[4]:
                try:
                    keywords = json.loads(row[4])
                except:
                    keywords = []
            
            # Récupérer le dataset par ID
            dataset = self._get_dataset_by_id(row[7])
            
            if not dataset:
                print(f"⚠️ Dataset {row[7]} non trouvé pour l'image {row[0]}")
                continue
            
            # Création de l'image avec le vrai objet Dataset
            new_image = Image(
                path=row[1],
                dataset=dataset,  # Vrai objet Dataset
                description=row[3] or "",
                keywords=keywords,
                image_id=row[0]
            )
            
            images.append(new_image)
        
        return images

    def exist(self, path : str) -> bool:
        """
        Vérifie si une image existe dans la base de données.
        
        Args:
            path (str): Chemin de l'image
            
        Returns:
            bool: True si l'image existe, False sinon
        """
        return self.db.fetch_one("SELECT 1 FROM images WHERE path = ?", (path,)) is not None

if __name__ == "__main__":
    dbm = DbService()
    repo = ImageRepository(dbm.sqlite, dbm.faiss)
    print(repo.exist("test"))
