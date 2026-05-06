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

import numpy as np

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
        if image.embedding is not None:
            blob = np.array(image.embedding, dtype=np.float32).tobytes()

        # 2. SQLite
        self.db.execute("""
            INSERT OR REPLACE INTO images
            (id, path, name, description, keywords, indexed_at, dataset_id, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            image.id,
            str(image.path),
            image.name,
            image.description,
            json.dumps(image.keywords),
            datetime.now().isoformat(),
            image.dataset_id,
            blob
        ))

        return True

    def train_index(self, batch_size: int = 1000):
        all_vectors = []

        page = 0

        # -------------------------
        # LOAD ALL EMBEDDINGS
        # -------------------------
        cursor = self.db.execute("SELECT embedding FROM images")
        rows = cursor.fetchall()

        all_vectors = []

        for (embedding_blob,) in rows:
            vec = np.frombuffer(embedding_blob, dtype=np.float32)
            all_vectors.append(vec)

        vectors = np.vstack(all_vectors).astype(np.float32)

        # -------------------------
        # AUTO CLUSTERS
        # -------------------------
        nb_vectors = len(vectors)
        n_clusters = max(1, int(nb_vectors ** 0.5))

        print(f"📊 {nb_vectors} vecteurs → {n_clusters} clusters")

        # sécurité FAISS
        if nb_vectors < n_clusters:
            print("❌ Pas assez de données pour train")
            return

        # -------------------------
        # RECREATE INDEX
        # -------------------------
        self.faiss = self._create_index(nb_vectors)

        # IMPORTANT: update clusters dynamiques dans index
        self.faiss = self._create_index(nb_vectors)
        self.faiss.index.nprobe = NPROBE

        # -------------------------
        # TRAIN + ADD
        # -------------------------
        print(f"🔧 Train FAISS sur {nb_vectors} vecteurs")

        self.faiss.train(vectors)
        self.faiss.add(vectors)

        self.faiss.save()

        print("✅ Index prêt")
    
    def search(
        self,
        query: List[float],
        threshold: float = 0.5,
        limit: int = 20
    ) -> SearchResults:

        # -------------------------
        # FAISS SEARCH (POOL)
        # -------------------------
        raw_results = self.faiss.search(query, k=200)  # pool fixe pour load-more

        if not raw_results:
            return SearchResults(images=[], next_cursor=None, has_more=False)

        # filtre threshold côté app
        raw_results = [(idx, score) for idx, score in raw_results if score >= threshold]

        if not raw_results:
            return SearchResults(images=[], next_cursor=None, has_more=False)

        # on garde un buffer + limit initial
        page_results = raw_results[:limit]
        has_more = len(raw_results) > limit

        ids = [idx for idx, _ in page_results]

        # -------------------------
        # BATCH SQL (optimisé)
        # -------------------------
        placeholders = ",".join(["?"] * len(ids))

        rows = self.db.execute(
            f"SELECT id, path, name, description, keywords, dataset_id FROM images WHERE id IN ({placeholders})",
            ids
        ).fetchall()

        row_map = {row[0]: row for row in rows}

        images = []

        for idx, score in page_results:
            row = row_map.get(idx)
            if not row:
                continue

            keywords = json.loads(row[4]) if row[4] else []
            dataset = self._get_dataset_by_id(row[5])

            if not dataset:
                continue

            images.append(Image(
                image_id=row[0],
                path=row[1],
                name=row[2],
                description=row[3] or "",
                keywords=keywords,
                dataset=dataset,
                score=score
            ))

        # -------------------------
        # CURSOR (load more)
        # -------------------------
        next_cursor = page_results[-1][1] if has_more else None

        return SearchResults(
            images=images,
            next_cursor=next_cursor,
            has_more=has_more
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
                print(f"⚠️ Dataset {row[6]} non trouvé pour l'image {row[0]}")
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
