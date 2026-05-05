import faiss
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent / "storage"))
from config import get_faiss_index_path, verify_storage

# ---------------------------
# CONFIG
# ---------------------------
dimension  = 768   # nomic-embed-text:v1.5
n_clusters = 256   # Nombre de clusters IVF (augmente avec le volume de données)
nprobe     = 16    # Clusters explorés par query (précision vs vitesse)

def init_faiss():
    """Initialise un index FAISS IVF vide avec la bonne configuration"""

    faiss_path = Path(get_faiss_index_path())
    faiss_path.parent.mkdir(parents=True, exist_ok=True)

    # Quantizer : cherche les centroids les plus proches (cosine via IP)
    quantizer = faiss.IndexFlatIP(dimension)

    # Index IVF : regroupe les vecteurs en clusters sémantiques
    index = faiss.IndexIVFFlat(quantizer, dimension, n_clusters, faiss.METRIC_INNER_PRODUCT)
    index.nprobe = nprobe

    faiss.write_index(index, str(faiss_path))

    print(f"✅ FAISS index initialized: {faiss_path}")
    print(f"   - Dimension:  {dimension}")
    print(f"   - Metric:     cosine similarity (Inner Product)")
    print(f"   - Type:       IndexIVFFlat ({n_clusters} clusters, nprobe={nprobe})")
    print(f"   - File size:  {faiss_path.stat().st_size} bytes")

if __name__ == "__main__":
    init_faiss()