from pathlib import Path
from typing import List, Tuple
import numpy as np
import heapq

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

DIMENSION = 768
N_CLUSTERS = 256
NPROBE = 65


class FaissManager:

    def __init__(self, index_path: Path):
        self.index_path = Path(index_path)
        self.dimension = DIMENSION
        self.index = None

        if FAISS_AVAILABLE:
            self._load_or_create()

    # =========================
    # INIT
    # =========================
    def _load_or_create(self):
        if self.index_path.exists():
            loaded_index = faiss.read_index(str(self.index_path))
            # Si c'est un IndexIDMap, appliquer nprobe à l'index interne
            if hasattr(loaded_index, 'index') and hasattr(loaded_index.index, 'nprobe'):
                loaded_index.index.nprobe = NPROBE
            self.index = loaded_index
        else:
            self.index = self._create_index(0, N_CLUSTERS)

    def _create_index(self, nb_embeddings: int, n_clusters):
        """
        Crée un index FAISS avec un nombre de clusters adapté au volume.
        """
        # sécurité (évite clusters absurdes)
        n_clusters = min(n_clusters, nb_embeddings) if nb_embeddings > 0 else 1

        print(f"Création FAISS: {nb_embeddings} vecteurs → {n_clusters} clusters")

        quantizer = faiss.IndexFlatIP(self.dimension)
        base_index = faiss.IndexIVFFlat(
            quantizer,
            self.dimension,
            n_clusters,
            faiss.METRIC_INNER_PRODUCT
        )

        base_index.nprobe = NPROBE
        
        index = faiss.IndexIDMap(base_index)
        self.index = index

    # =========================
    # TRAIN
    # =========================
    def train(self, embeddings: List[List[float]]) -> bool:
        if not FAISS_AVAILABLE or not self.index:
            return False

        arr = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(arr)

        if len(arr) < N_CLUSTERS:
            print(f"Pas assez de vecteurs ({len(arr)} < {N_CLUSTERS})")
            return False

        if not self.index.is_trained:
            print(f"Training FAISS sur {len(arr)} vecteurs...")
            self.index.train(arr)
            print("Training terminé")

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

        if not FAISS_AVAILABLE or not self.index or self.index.ntotal == 0:
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

    def _search_flat_batch(
        self,
        query_vector: np.ndarray,
        threshold: float,
        batch_size: int = 10_000,
    ) -> List[Tuple[int, float]]:
        """
        Recherche brute-force par batch.
        Utilisée uniquement si FAISS n'est pas entraîné.
        """

        try:
            total = self.index.ntotal
            heap: list[Tuple[float, int]] = []

            query_vec = query_vector[0]

            for batch_start in range(0, total, batch_size):
                batch_count = min(batch_size, total - batch_start)

                # reconstruction des vecteurs
                batch_vectors = np.zeros((batch_count, self.dimension), dtype=np.float32)
                self.index.reconstruct_n(batch_start, batch_count, batch_vectors)

                # scores cosine (car tu normalises déjà)
                batch_scores = batch_vectors @ query_vec

                mask = batch_scores >= threshold
                if not mask.any():
                    continue

                for i_local, score in zip(np.where(mask)[0], batch_scores[mask]):
                    idx = batch_start + int(i_local)
                    heapq.heappush(heap, (float(score), idx))

            if not heap:
                return []

            # tri décroissant
            heap.sort(key=lambda x: x[0], reverse=True)

            return [(idx, score) for score, idx in heap]

        except Exception as e:
            print(f"❌ Erreur fallback search: {e}")
            return []

    # =========================
    # SAVE / LOAD
    # =========================
    def save(self):
        if not FAISS_AVAILABLE or not self.index:
            return

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))

    def reset(self):
        self._create_index(0, N_CLUSTERS)
        self.save()

    # =========================
    # STATS
    # =========================
    def stats(self):
        if not FAISS_AVAILABLE or not self.index:
            return {"available": False}

        return {
            "available": True,
            "total": self.index.ntotal,
            "dimension": self.dimension,
            "is_trained": self.index.is_trained,
            "n_clusters": N_CLUSTERS,
            "nprobe": NPROBE,
        }