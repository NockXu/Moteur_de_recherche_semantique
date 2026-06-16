from common.Image_Classes.Image import Image
from common.Dataset_Classes.DatasetRepository import DatasetRepository
from common.Dataset_Classes.Dataset import Dataset
from database.faiss_manager.manager import FaissManager
from database.sqlite.manager import SqliteManager
from database.DbService import DbService
import json
import hashlib
from datetime import datetime
from typing import List, TypedDict, Optional, Tuple

import numpy as np

class SearchResults(TypedDict):
    """
    Represents the result of a search operation.

    This structure contains the retrieved images and the number
    of results requested (k).

    Args:
        images (List[Image]):
            List of retrieved images.
        k (int):
            Number of results requested.
    """
    images: List[Image]
    k: int

class ImageRepository:
    """
    Repository responsible for managing Image persistence and search operations.

    This class acts as a bridge between:
    - SQLite database (metadata storage)
    - FAISS index (vector search)

    Args:
        db (SqliteManager):
            SQLite database manager.

        faiss (FaissManager):
            FAISS index manager used for similarity search.
    """

    def __init__(self, db: SqliteManager, faiss: FaissManager):
        self.db = db
        self.faiss = faiss
        self._dataset_repo = DatasetRepository(db)
        self._dataset_cache = {}
        
    def _get_dataset_by_id(self, dataset_id: int) -> Optional[Dataset]:
        """
        Retrieve a Dataset by its ID using an internal cache to reduce database queries.

        This method first checks the cache before querying the repository.

        Args:
            dataset_id (int):
                ID of the dataset to retrieve.

        Returns:
            The dataset if found, otherwise None.
        """
        # Check cache first
        if dataset_id in self._dataset_cache:
            return self._dataset_cache[dataset_id]

        # Fetch from repository
        dataset = self._dataset_repo.get_by_id(dataset_id)

        # Store in cache if found
        if dataset is not None:
            self._dataset_cache[dataset_id] = dataset

        return dataset
    
    def save_image(self, image: Image) -> bool:
        """
        Save or update an image in both SQLite and FAISS storage.

        This method:
        - ensures dataset existence
        - stores image metadata in SQLite
        - prepares embedding for FAISS storage (if available)

        Returns:
            True if the operation succeeded, False otherwise.
        """
        try:
            blob = None

            # 1. FAISS embedding preparation
            if image.embedding is not None:
                blob = np.array(image.embedding, dtype=np.float32).tobytes()

            # 2. Ensure dataset exists
            if image.dataset_id is None and image.dataset_name:
                dataset = self._dataset_repo.get_by_name(image.dataset_name)

                if dataset is None:
                    dataset = self._dataset_repo.create(image.dataset_name)

                if dataset:
                    image.dataset_id = dataset.id
                    image.dataset_name = dataset.name
                else:
                    default_dataset = self._dataset_repo.get_by_name("default")
                    if default_dataset:
                        image.dataset_id = default_dataset.id
                        image.dataset_name = default_dataset.name

            # 3. SQLite insert/update
            self.db.execute(
                """
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
                """,
                (
                    str(image.path),
                    image.name,
                    image.description,
                    json.dumps(image.keywords),
                    datetime.now().isoformat(),
                    image.dataset_id,
                    blob
                )
            )

            self.db.commit()
            self.train_index()
            return True

        except Exception:
            return False

    def save_many_images(self, images: List[Image]) -> int:
        """
        Save multiple images in batch into SQLite.

        This method uses bulk insertion (executemany) with a fallback
        to row-by-row insertion in case of failure.

        Returns:
            Number of successfully saved images.
        """
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
        success_count = 0

        for image in images:
            blob = None

            # Embedding
            if image.embedding is not None:
                blob = np.array(image.embedding, dtype=np.float32).tobytes()

            # Dataset resolution
            if image.dataset_id is None and image.dataset_name:
                dataset = self._dataset_repo.get_by_name(image.dataset_name)

                if dataset is None:
                    dataset = self._dataset_repo.create(image.dataset_name)

                if dataset:
                    image.dataset_id = dataset.id
                    image.dataset_name = dataset.name
                else:
                    default = self._dataset_repo.get_by_name("default")
                    if default:
                        image.dataset_id = default.id
                        image.dataset_name = default.name

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
            self.db.executemany(query, rows)
            success_count = len(rows)

        except Exception:
            # fallback safe row-by-row
            success_count = 0

            for row in rows:
                try:
                    self.db.execute(query, row)
                    success_count += 1
                except Exception:
                    continue

        self.db.commit()
        return success_count

    def train_index(self) -> bool:
        """
        Rebuild and train the FAISS index from all stored image embeddings.

        Returns:
            True if training and indexing succeeded, False otherwise.
        """
        # -------------------------
        # LOAD ALL EMBEDDINGS
        # -------------------------
        rows = self.db.fetch_all("SELECT id, embedding FROM images")

        all_vectors = []
        all_ids = []

        for image_id, embedding_blob in rows:
            if embedding_blob is None:
                embedding = []
            else:
                embedding = np.frombuffer(
                    embedding_blob,
                    dtype=np.float32
                ).tolist()

            if len(embedding) == 0:
                continue

            all_vectors.append(embedding)
            all_ids.append(image_id)

        if not all_vectors:
            return False

        vectors = np.vstack(all_vectors).astype(np.float32)

        # -------------------------
        # AUTO CLUSTERS
        # -------------------------
        nb_vectors = len(vectors)
        n_clusters = max(1, int(nb_vectors ** 0.5))

        # -------------------------
        # RECREATE INDEX
        # -------------------------
        self.faiss._create_index(nb_vectors, n_clusters)

        # -------------------------
        # TRAIN + ADD
        # -------------------------
        if not self.faiss.train(vectors):
            return False

        self.faiss.add(vectors, all_ids)

        return self.faiss.save()
    
    # =========================
    # SEARCH ENGINE
    # =========================
    def search(
        self,
        query: List[float],
        threshold: float = 0.5,
        k: int = 200
    ) -> SearchResults:
        """
        Search similar images using FAISS + SQLite metadata + reranking.

        Args:
            query (List[float]):
                Query embedding.
            threshold (float):
                Minimum similarity score.
            k (int):
                Number of results to return.

        Returns:
            List of matched images sorted by similarity score.
        """

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

        raw_results.sort(key=lambda x: (-x[1], x[0]))

        # =========================
        # VALIDATE IDS
        # =========================
        ids = [idx for idx, _ in raw_results]

        if not ids:
            return SearchResults(images=[], k=k)

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

        if not rows:
            return SearchResults(images=[], k=k)

        row_map = {r[0]: r for r in rows}

        query_vec = np.array(query, dtype=np.float32)

        # =========================
        # RERANK
        # =========================
        reranked = []

        for idx, _ in raw_results:
            row = row_map.get(idx)
            if row is None:
                continue

            emb = np.frombuffer(row[1], dtype=np.float32)

            if emb.size == 0:
                continue

            # cosine-like score (FAISS cohérent si normalisé)
            score = float(np.dot(query_vec, emb))

            reranked.append((idx, score))

        # =========================
        # DEDUP + SORT
        # =========================
        seen = set()
        final_page = []

        for idx, score in sorted(reranked, key=lambda x: (-x[1], x[0])):
            if idx in seen:
                continue
            seen.add(idx)
            final_page.append((idx, score))

        # =========================
        # BUILD RESULTS
        # =========================
        images = []

        for idx, score in final_page:
            row = row_map.get(idx)
            if row is None:
                continue

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

        return SearchResults(
            images=images,
            k=k
        )

    def get_k(self, k : int) -> List[Image]:
        """
        Retrieve the first k images from the database.

        Args:
            k (int):
                Number of images to retrieve

        Returns:
            List of k images
        """
        
        query = """
            SELECT
                id,
                path,
                name,
                description,
                keywords,
                dataset_id,
                embedding
            FROM images
            LIMIT ?
        """
        params = [k]

        rows = self.db.fetch_all(query, params)

        return self._construct_from_rows(rows)

    def get_all(self) -> List[Image]:
        """
        Retrieve all images from the database.

        Returns:
            List of all stored images.
        """

        rows = self.db.fetch_all(
            """
            SELECT
                id,
                path,
                name,
                description,
                keywords,
                dataset_id,
                embedding
            FROM images
            """
        )

        return self._construct_from_rows(rows)

    def get_image_by_id(self, image_id: int) -> Optional[Image]:
        """
        Retrieve an image by its ID.

        Args:
            image_id (int):
                ID of the image to retrieve

        Returns:
            Image with the given ID, or None if not found
        """
        
        query = """
            SELECT
                id,
                path,
                name,
                description,
                keywords,
                dataset_id,
                embedding
            FROM images
            WHERE id = ?
        """
        params = [image_id]

        row = self.db.fetch_one(query, params)

        if row is None:
            return None

        return self._construct_from_rows([row])[0]

    def get_image_by_path(self, path: str) -> Optional[Image]:
        """
        Retrieve an image by its path.

        Args:
            path (str):
                Path of the image to retrieve

        Returns:
            Image with the given path, or None if not found
        """
        
        query = """
            SELECT
                id,
                path,
                name,
                description,
                keywords,
                dataset_id,
                embedding
            FROM images
            WHERE path = ?
        """
        params = [path]

        row = self.db.fetch_one(query, params)

        if row is None:
            return None

        return self._construct_from_rows([row])[0]

    def _construct_from_rows(self, rows) -> List[Image]:
        """
        Build Image objects from database rows.

        This method converts raw rows retrieved from the database into
        Image instances. It deserializes keywords stored as JSON, retrieves
        the associated dataset, reconstructs embeddings from binary data,
        and gracefully handles invalid or missing values.

        Args:
            rows:
                Iterable containing database rows representing images.

        Returns:
            List[Image]:
                A list of Image objects built from the provided rows.
                Returns an empty list if no rows are provided.
        """
        images = []

        for row in rows:
            image_id, path, name, description, keywords_json, dataset_id, embedding_blob = row

            # -------------------------
            # Keywords
            # -------------------------
            try:
                keywords = json.loads(keywords_json) if keywords_json else []
            except json.JSONDecodeError:
                keywords = []

            # -------------------------
            # Dataset
            # -------------------------
            dataset = self._get_dataset_by_id(dataset_id)

            # -------------------------
            # Embedding
            # -------------------------
            try:
                embedding = (
                    np.frombuffer(embedding_blob, dtype=np.float32).tolist()
                    if embedding_blob
                    else []
                )
            except Exception:
                embedding = []

            # -------------------------
            # Build Image
            # -------------------------
            images.append(
                Image(
                    path=path,
                    dataset=dataset,
                    description=description or "",
                    keywords=keywords,
                    embedding=embedding,
                    image_id=image_id,
                    name=name
                )
            )

        return images

    def exist(self, path: str) -> bool:
        """
        Check if an image exists in the database.

        Args:
            path (str):
                Path of the image.

        Returns:
            True if the image exists, otherwise False.
        """
        return (
            self.db.fetch_one(
                "SELECT 1 FROM images WHERE path = ?",
                (path,)
            )
            is not None
        )

    def get_all_image_paths(self) -> set[str]:
        """
        Retrieve all image paths stored in the database.

        Returns:
            Set of existing image paths.
        """
        rows = self.db.fetch_all("SELECT path FROM images")
        return {row[0] for row in rows}

if __name__ == "__main__":
    dbm = DbService()
    repo = ImageRepository(dbm.sqlite, dbm.faiss)
    repo.train_index()
    print(repo.exist("test"))
