from common.Image_Classes.Image import Image
from common.Dataset_Classes.DatasetRepository import DatasetRepository
from database.faiss_manager.manager import FaissManager
from database.sqlite.manager import SqliteManager
from database.DbService import DbService
import json
import hashlib
from datetime import datetime
from typing import List, TypedDict, Optional, Tuple

import numpy as np

class SearchResults(TypedDict):
    """Résultats de recherche avec k actuel"""
    images: List[Image]
    k: int

class ImageRepository:
    def __init__(self, db: SqliteManager, faiss: FaissManager):
        self.db = db
        self.faiss = faiss
        self._dataset_repo = DatasetRepository(db)
        self._dataset_cache = {}

        
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
        # 2.1 Insertion du dataset si besoin
        if not image.dataset_id:
            if image.dataset_name:
                dataset = self._dataset_repo.get_by_name(image.dataset_name)
                if dataset:
                    image.dataset_id = dataset.id
                else:
                    dataset = self._dataset_repo.create(image.dataset_name)
                    if dataset:  # Vérifier que create() a réussi
                        image.dataset_id = dataset.id
                    else:
                        dataset = self._dataset_repo.get_by_name("default")
                        if dataset:
                            image.dataset_id = dataset.id
                            image.dataset_name = dataset.name
                        

        # 2.2 Insertion de l'image
        self.db.execute("""
            INSERT INTO images (
                path, name, description, keywords,
                indexed_at, dataset_id, embedding
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                keywords = excluded.keywords,
                indexed_at = excluded.indexed_at,
                dataset_id = excluded.dataset_id,
                embedding = excluded.embedding
        """, (
            str(image.path),
            image.name,
            image.description,
            json.dumps(image.keywords),
            datetime.now().isoformat(),
            image.dataset_id,
            blob
        ))

        self.db.commit()

        return True

    def save_many_images(self, images: List[Image]) -> int:

        success_count = 0

        query = """
            INSERT INTO images (
                path,
                name,
                description,
                keywords,
                indexed_at,
                dataset_id,
                embedding
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                keywords = excluded.keywords,
                indexed_at = excluded.indexed_at,
                dataset_id = excluded.dataset_id,
                embedding = excluded.embedding
        """

        rows = []

        for image in images:

            blob = None

            if image.embedding is not None:
                blob = np.array(
                    image.embedding,
                    dtype=np.float32
                ).tobytes()

            # Dataset
            if not image.dataset_id and image.dataset_name:

                dataset = self._dataset_repo.get_by_name(image.dataset_name)

                if dataset:
                    image.dataset_id = dataset.id
                    image.dataset_name = dataset.name

                else:
                    dataset = self._dataset_repo.create(image.dataset_name)

                    if dataset:
                        image.dataset_id = dataset.id
                        image.dataset_name = dataset.name

                    else:
                        dataset = self._dataset_repo.get_by_name("default")
                        
                        if dataset:
                            image.dataset_id = dataset.id
                            image.dataset_name = dataset.name

            rows.append((
                str(image.path),
                image.name,
                image.description,
                json.dumps(image.keywords),
                datetime.now().isoformat(),
                image.dataset_id,
                blob
            ))

        try:
            # Insertion rapide
            self.db.executemany(query, rows)

            success_count = len(rows)

        except Exception as batch_error:

            # Fallback ligne par ligne
            for row in rows:

                try:
                    self.db.execute(query, row)
                    success_count += 1

                except Exception:
                    pass

        self.db.commit()

        return success_count
        

    def train_index(self) -> bool:
        # -------------------------
        # LOAD ALL EMBEDDINGS
        # -------------------------
        rows = self.db.fetch_all("SELECT id, embedding FROM images")

        all_vectors = []
        all_ids = []

        for image_id, embedding_blob in rows:
            vec = np.frombuffer(embedding_blob, dtype=np.float32)

            all_vectors.append(vec)
            all_ids.append(image_id)

        vectors = np.vstack(all_vectors).astype(np.float32)

        # -------------------------
        # AUTO CLUSTERS
        # -------------------------
        nb_vectors = len(vectors)
        n_clusters = max(1, int(nb_vectors ** 0.5))

        # -------------------------
        # RECREATE INDEX
        # -------------------------

        # IMPORTANT: update clusters dynamiques dans index
        self.faiss._create_index(nb_vectors, n_clusters)

        # -------------------------
        # TRAIN + ADD
        # -------------------------

        self.faiss.train(vectors)
        self.faiss.add(vectors, all_ids)

        return self.faiss.save()
    
    # =========================
    # SEARCH ENGINE
    # =========================
    def search(
        self,
        query: List[float],
        threshold: float = 0.5,
        k: int = 200,
        cursor: Optional[Tuple[float, int]] = None
    ) -> SearchResults:
        # =========================
        # FAISS RETRIEVAL
        # =========================

        raw_results = self.faiss.search(query, k)

        if not raw_results:
            return SearchResults(images=[], k=k)

        raw_results = [
            (idx, score)
            for idx, score in raw_results
            if idx != -1 and score >= threshold
        ]

        # stable sort
        raw_results.sort(key=lambda x: (-x[1], x[0]))

        # =========================
        # SQL FETCH (EMBEDDINGS + METADATA)
        # =========================
        ids = [idx for idx, _ in raw_results]

        placeholders = ",".join(["?"] * len(ids))

        rows = self.db.fetch_all(
            f"""
            SELECT
                id,
                embedding,
                path,
                name,
                description,
                keywords,
                dataset_id
            FROM images
            WHERE id IN ({placeholders})
            """,
            tuple(ids)
        )

        row_map = {r[0]: r for r in rows}

        query_vec = np.array(query, dtype=np.float32)

        # =========================
        # RERANK (COSINE EXACT)
        # =========================
        reranked = []

        for idx, _ in raw_results:
            row = row_map.get(idx)
            if not row:
                continue

            emb = np.frombuffer(row[1], dtype=np.float32)

            score = float(np.dot(query_vec, emb))

            reranked.append((idx, score))

        # =========================
        # DEDUP
        # =========================
        seen = set()
        deduped = []

        for idx, score in reranked:
            if idx in seen:
                continue
            seen.add(idx)
            deduped.append((idx, score))

        # =========================
        # FINAL SORT
        # =========================
        deduped.sort(key=lambda x: (-x[1], x[0]))

        # =========================
        # FINAL PAGE
        # =========================
        final_page = deduped

        # =========================
        # BUILD RESULTS
        # =========================
        images = []

        for idx, score in final_page:
            row = row_map.get(idx)

            if not row: continue

            images.append(
                Image(
                    image_id=row[0],
                    path=row[2],
                    name=row[3],
                    description=row[4] or "",
                    keywords=json.loads(row[5]) if row[5] else [],
                    dataset=self._get_dataset_by_id(row[6]),
                    score=float(score)
                )
            )

        # =========================
        # RETURN
        # =========================
        return SearchResults(
            images=images,
            k=k
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
            dataset = self._get_dataset_by_id(row[6])
            
            if not dataset:
                dataset = None
            
            # Désérialiser l'embedding depuis le blob (numpy)
            embedding = []
            if row[7]:
                try:
                    embedding = np.frombuffer(row[7], dtype=np.float32).tolist()
                except:
                    embedding = []
            
            # Création de l'image avec le vrai objet Dataset
            new_image = Image(
                path=row[1],
                dataset=dataset,  # Vrai objet Dataset
                description=row[3] or "",
                keywords=keywords,
                embedding=embedding,
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

    def image_exists(self, path: str) -> bool:
        """
        Vérifie si une image existe dans la base de données
        
        Args:
            path (str): Chemin de l'image
            
        Returns:
            bool: True si l'image existe, False sinon
        """
        return self.db.fetch_one("SELECT 1 FROM images WHERE path = ?", (path,)) is not None

    def get_all_image_paths(self) -> set[str]:
        """
        Récupère tous les chemins d'images de la base de données en un seul appel
        
        Returns:
            set[str]: Ensemble des chemins d'images existants
        """
        rows = self.db.fetch_all("SELECT path FROM images")
        return {row[0] for row in rows}

if __name__ == "__main__":
    dbm = DbService()
    repo = ImageRepository(dbm.sqlite, dbm.faiss)
    repo.train_index()
    print(repo.exist("test"))
