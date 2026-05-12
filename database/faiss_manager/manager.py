from pathlib import Path
from typing import List, Tuple
import numpy as np
import heapq
import faiss

DIMENSION = 768
N_CLUSTERS = 256
NPROBE = 65

class FaissManager:

    def __init__(self, index_path: Path):
        self.index_path = Path(index_path)
        self.dimension = DIMENSION
        self.index = None

        self._load_or_create()

    # =========================
    # INIT
    # =========================
    def _load_or_create(self):
        try:
            if self.index_path.exists():
                self.index = faiss.read_index(str(self.index_path))
            else:
                self.index = self._create_index(0, N_CLUSTERS)
        except Exception as e:
            self.index = None
            raise RuntimeError(f"Erreur lors du chargement ou de la création de l'index: {e}")

    def _create_index(self, nb_embeddings: int, n_clusters):
        """
        Crée un index FAISS avec un nombre de clusters adapté au volume.
        """
        # sécurité (évite clusters absurdes)
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
    def add(self, embeddings, ids):
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
        if not self.index:
            return False

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        return True

    def reset(self):
        self.index = self._create_index(0, N_CLUSTERS)
        self.save()

    # =========================
    # STATS
    # =========================
    def stats(self):
        if not self.index:
            return {"available": False}

        return {
            "available": True,
            "total": self.index.ntotal,
            "dimension": self.dimension,
            "is_trained": self.index.is_trained,
            "n_clusters": N_CLUSTERS,
            "nprobe": NPROBE,
        }