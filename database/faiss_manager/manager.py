from pathlib import Path
from typing import List, Tuple, Sequence, Dict, Any
import numpy as np
import heapq
import faiss

DIMENSION = 768
N_CLUSTERS = 256
NPROBE = 65

class FaissManager:
    """
    Manages a FAISS vector index for similarity search and clustering-based optimization.

    This class loads an existing index from disk or creates a new one if it does not exist.

    Important:
        The FAISS index is mutable and may change when new embeddings are added.
        Therefore, embedding metadata should be stored separately (e.g., in a SQLite database).

    Args:
        index_path (Path):
            Path to the FAISS index file.
    """

    def __init__(self, index_path: Path):
        self.index_path = Path(index_path)
        self.dimension = DIMENSION
        self.index = None

        self._load_or_create()

    # =========================
    # INIT
    # =========================
    def _load_or_create(self) -> None:
        """
        Load an existing FAISS index or create a new one if it does not exist.

        If the index file is found, it is loaded from disk.
        Otherwise, a new empty index is created.

        Returns:
            None

        Raises:
            RuntimeError:
                If loading or creation of the index fails.
        """
        try:
            if self.index_path.exists():
                self.index = faiss.read_index(str(self.index_path))
            else:
                self.index = self._create_index(0, N_CLUSTERS)

        except Exception as e:
            self.index = None
            raise RuntimeError(
                f"Error loading or creating FAISS index: {e}"
            )

    def _create_index(self, nb_embeddings: int, n_clusters: int):
        """
        Create a FAISS index optimized for the number of embeddings.

        The number of clusters is automatically adjusted to avoid invalid
        or inefficient configurations when the dataset is small.

        Args:
            nb_embeddings (int):
                Number of embeddings available in the dataset.

            n_clusters (int):
                Desired number of clusters for the IVF index.

        Returns:
            A FAISS IndexIDMap wrapping an IndexIVFFlat instance.
        """
        # Safety check: ensure valid number of clusters
        n_clusters = min(n_clusters, nb_embeddings) if nb_embeddings > 0 else 1

        quantizer = faiss.IndexFlatIP(self.dimension)

        base_index = faiss.IndexIVFFlat(
            quantizer,
            self.dimension,
            n_clusters,
            faiss.METRIC_INNER_PRODUCT
        )

        base_index.nprobe = NPROBE

        return faiss.IndexIDMap(base_index)

    # =========================
    # TRAIN
    # =========================

    def train(self, embeddings: List[List[float]]) -> bool:
        """
        Train the FAISS index using a list of embeddings.

        The embeddings are normalized before training. Training is only
        performed if the index is initialized and there are enough samples.

        Args:
            embeddings (List[List[float]]):
                List of embedding vectors used for training.

        Returns:
            True if the index was successfully trained, False otherwise.
        """
        if not self.index:
            return False

        arr = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(arr)

        if len(arr) < N_CLUSTERS:
            return False

        if not self.index.is_trained:
            self.index.train(arr)

        return True

    # =========================
    # ADD
    # =========================
    def add(self, embeddings: List[List[float]], ids: Sequence[int]) -> None:
        """
        Add embeddings and their associated IDs to the FAISS index.

        The embeddings are normalized before insertion, and the index is
        automatically saved after the operation.

        Args:
            embeddings (List[List[float]]):
                List of embedding vectors to add to the index.

            ids (Sequence[int]):
                Corresponding IDs for each embedding.

        Returns:
            None
        """
        arr = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(arr)

        ids_np = np.array(ids, dtype=np.int64)

        self.index.add_with_ids(arr, ids_np)
        self.save()

    # =========================
    # SEARCH
    # =========================
    def search(
        self,
        query: List[float],
        k: int = 200
    ) -> List[Tuple[int, float]]:
        """
        Search for the nearest neighbors in the FAISS index.

        The query vector is normalized before searching. The results are
        sorted by similarity score in descending order.

        Args:
            query (List[float]):
                Query embedding vector.

            k (int):
                Number of nearest neighbors to retrieve.

        Returns:
            List of (id, similarity score) pairs sorted by relevance.
            Returns an empty list if the index is not initialized or empty.
        """
        if not self.index or self.index.ntotal == 0:
            return []

        q = np.array([query], dtype=np.float32)
        faiss.normalize_L2(q)

        scores, idxs = self.index.search(q, k)

        scores = scores[0]
        idxs = idxs[0]

        results = [
            (int(i), float(s))
            for i, s in zip(idxs, scores)
            if i != -1
        ]

        results.sort(key=lambda x: x[1], reverse=True)

        return results

    # =========================
    # SAVE / LOAD
    # =========================
    def save(self) -> bool:
        """
        Save the FAISS index to disk.

        Returns:
            True if the index was successfully saved, False otherwise.
        """
        if self.index is None:
            return False

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))

        return True

    def reset(self) -> bool:
        """
        Reset the FAISS index by creating a new empty index and saving it.

        This operation removes all previously stored embeddings.

        Returns:
            True if the index was successfully reset, False otherwise.
        """
        self.index = self._create_index(0, N_CLUSTERS)
        
        return self.save()

    # =========================
    # STATS
    # =========================
    def stats(self) -> Dict[str, Any]:
        """
        Return statistics about the FAISS index.

        This includes information about index availability, size,
        dimension, training state, and clustering parameters.

        Returns:
            Dictionary containing FAISS index metadata.
            If the index is not initialized, returns {"available": False}.
        """
        if self.index is None:
            return {"available": False}

        return {
            "available": True,
            "total": self.index.ntotal,
            "dimension": self.dimension,
            "is_trained": self.index.is_trained,
            "n_clusters": N_CLUSTERS,
            "nprobe": NPROBE,
        }