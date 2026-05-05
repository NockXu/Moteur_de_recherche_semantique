from pathlib import Path
from typing import List, Tuple, Optional
import heapq
import sys
import os

try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# ---------------------------
# CONFIG IVF
# ---------------------------
N_CLUSTERS = 256  # Augmenter si > 100k vecteurs (règle : sqrt(total))
NPROBE     = 16   # Clusters explorés par query (précision vs vitesse)


class FaissManager:

    def __init__(self, index_path: Path, dimension: int = 768):
        self.index_path = Path(index_path)
        self.dimension  = dimension
        self.index      = None

        if FAISS_AVAILABLE:
            self._load_or_create()

    # =========================
    # INIT
    # =========================
    def _load_or_create(self):
        if self.index_path.exists():
            try:
                self.index        = faiss.read_index(str(self.index_path))
                self.index.nprobe = NPROBE
                print(f"✅ FAISS chargé ({self.index.ntotal} vecteurs, trained={self.index.is_trained})")
            except Exception as e:
                print(f"❌ Erreur chargement FAISS: {e}")
                self.index = self._create_index()
        else:
            self.index = self._create_index()

    def _create_index(self) -> "faiss.IndexIVFFlat":
        print(f"🆕 Création index FAISS IVF (dim={self.dimension}, clusters={N_CLUSTERS})")
        quantizer = faiss.IndexFlatIP(self.dimension)
        index     = faiss.IndexIVFFlat(quantizer, self.dimension, N_CLUSTERS, faiss.METRIC_INNER_PRODUCT)
        index.nprobe = NPROBE
        return index

    # =========================
    # SAVE
    # =========================
    def save(self):
        if not FAISS_AVAILABLE or not self.index:
            return

        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(self.index_path))
        except Exception as e:
            print(f"❌ Erreur sauvegarde FAISS: {e}")

    # =========================
    # ADD
    # =========================
    def add(self, embeddings: List[List[float]]) -> List[int]:
        """
        Ajoute plusieurs embeddings.
        Entraîne automatiquement l'index IVF si ce n'est pas encore fait.
        Retourne les indices FAISS assignés.
        """
        if not FAISS_AVAILABLE or not self.index:
            return []

        try:
            arr = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(arr)

            # Entraînement IVF obligatoire avant le premier add
            if not self.index.is_trained:
                if len(arr) < N_CLUSTERS:
                    print(f"⚠️  Pas assez de vecteurs pour entraîner ({len(arr)} < {N_CLUSTERS} clusters)")
                    print(f"   Réduis N_CLUSTERS ou accumule plus de vecteurs avant d'indexer.")
                    return []

                print(f"🔧 Entraînement IVF sur {len(arr)} vecteurs...")
                self.index.train(arr)
                print(f"✅ Entraînement terminé")

            start_idx = self.index.ntotal
            self.index.add(arr)
            self.save()

            return list(range(start_idx, start_idx + len(arr)))

        except Exception as e:
            print(f"❌ Erreur ajout FAISS: {e}")
            return []

    # =========================
    # SEARCH
    # =========================
    def search(
        self,
        query: List[float],
        threshold: float,
    ) -> List[Tuple[int, float]]:
        if not FAISS_AVAILABLE or not self.index or self.index.ntotal == 0:
            return []

        query_vector = np.array([query], dtype=np.float32)
        faiss.normalize_L2(query_vector)

        if self.index.is_trained:
            return self._search_ivf(query_vector, threshold)
        else:
            return self._search_flat_batch(query_vector, threshold)

    def _search_ivf(
        self,
        query_vector: "np.ndarray",
        threshold: float,
    ) -> List[Tuple[int, float]]:
        """
        Recherche IVF native : explore seulement nprobe clusters.
        """
        try:
            scores, indices = self.index.search(query_vector, self.index.ntotal)

            mask            = (indices[0] >= 0) & (scores[0] >= threshold)
            filtered_scores = scores[0][mask]
            filtered_idxs   = indices[0][mask]

            if len(filtered_idxs) == 0:
                return []

            order = np.argsort(-filtered_scores)

            return list(zip(filtered_idxs[order].tolist(), filtered_scores[order].tolist()))

        except Exception as e:
            print(f"❌ Erreur recherche IVF: {e}")
            return []

    def _search_flat_batch(
        self,
        query_vector: "np.ndarray",
        threshold: float,
        batch_size: int = 10_000,
    ) -> List[Tuple[int, float]]:
        """
        Fallback scan par batch + MinHeap.
        Utilisé si l'index n'est pas encore entraîné.
        Mémoire : bornée à batch_size vecteurs simultanément.
        """
        try:
            total = self.index.ntotal
            heap: list[Tuple[float, int]] = []

            for batch_start in range(0, total, batch_size):
                batch_count   = min(batch_size, total - batch_start)
                batch_vectors = np.zeros((batch_count, self.index.d), dtype=np.float32)
                self.index.reconstruct_n(batch_start, batch_count, batch_vectors)

                batch_scores = batch_vectors @ query_vector[0]

                mask = batch_scores >= threshold
                if not mask.any():
                    continue

                for score, idx in zip(batch_scores[mask].tolist(), (np.where(mask)[0] + batch_start).tolist()):
                    heapq.heappush(heap, (score, idx))  # Plus de limite fixe, on garde tout

            if not heap:
                return []

            return [(idx, score) for score, idx in sorted(heap, key=lambda x: -x[0])]

        except Exception as e:
            print(f"❌ Erreur recherche batch: {e}")
            return []

    # =========================
    # RESET
    # =========================
    def reset(self):
        """Recrée un index vide (non entraîné)"""
        if not FAISS_AVAILABLE:
            return

        self.index = self._create_index()
        self.save()
        print("🔄 Index FAISS réinitialisé")

    # =========================
    # STATS
    # =========================
    def stats(self) -> dict:
        if not FAISS_AVAILABLE or not self.index:
            return {"available": False}

        return {
            "available":   True,
            "total":       self.index.ntotal,
            "dimension":   self.dimension,
            "is_trained":  self.index.is_trained,
            "n_clusters":  N_CLUSTERS,
            "nprobe":      NPROBE,
            "path":        str(self.index_path)
        }

if __name__ == "__main__":
    faiss_index_path = os.path.join(os.path.dirname(__file__), '..', 'storage', 'indexes', 'images.index')
    faiss_manager = FaissManager(faiss_index_path)