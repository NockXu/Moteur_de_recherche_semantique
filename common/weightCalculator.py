import numpy as np
from typing import List, Callable
import faiss

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)

def update_sum(prev, sim, p):
    return prev + sim


def update_mult(prev, sim, p):
    return prev * sim


def update_mult_one(prev, sim, p):
    return 1 + prev * sim


def update_mult_with_position(prev, sim, p):
    return p + prev * sim


def update_add_with_position(prev, sim, p):
    return p + prev + sim


def update_mult_with_position_mult(prev, sim, p):
    return p * prev * sim

def weights_from_cosines(
    vects: List[np.ndarray],
    update_fn: Callable[[float, float, int], float]
) -> List[float]:
    """
    Generic weight builder for vector chains.

    Parameters
    ----------
    vects : list of embeddings
    update_fn :
        function(prev_weight, similarity, position) -> new_weight
    """

    if not vects:
        return []

    weights = [1.0]

    for p in range(1, len(vects)):
        sim = cosine(vects[p], vects[p - 1])
        new_w = update_fn(weights[-1], sim, p)
        weights.append(new_w)

    return weights

def generate_random_vects(n: int, dim: int) -> List[np.ndarray]:
    vects = np.random.randn(n, dim).astype(np.float32)
    faiss.normalize_L2(vects)
    return list(vects)

def generate_clustered_vects(n, dim, k_clusters=3, noise=0.1):
    centers = np.random.randn(k_clusters, dim).astype(np.float32)

    vects = []

    for _ in range(n):
        c = centers[np.random.randint(0, k_clusters)]
        v = c + noise * np.random.randn(dim).astype(np.float32)
        vects.append(v)

    vects = np.array(vects, dtype=np.float32)
    faiss.normalize_L2(vects)

    return list(vects)

import numpy as np
import matplotlib.pyplot as plt


if __name__ == "__main__":
    def run_experiment(generator, N_RUNS, N_VECTS, DIM):

        w_sum = None
        w_mult = None
        w_mult_one = None
        w_pos_mult = None
        w_pos_add = None
        w_pos_mult_mult = None

        for _ in range(N_RUNS):

            vects = generator(N_VECTS, DIM)

            w1 = np.array(weights_from_cosines(vects, update_sum))
            w2 = np.array(weights_from_cosines(vects, update_mult))
            w3 = np.array(weights_from_cosines(vects, update_mult_one))
            w4 = np.array(weights_from_cosines(vects, update_mult_with_position))
            w5 = np.array(weights_from_cosines(vects, update_add_with_position))
            w6 = np.array(weights_from_cosines(vects, update_mult_with_position_mult))

            if w_sum is None:
                w_sum = w1
                w_mult = w2
                w_mult_one = w3
                w_pos_mult = w4
                w_pos_add = w5
                w_pos_mult_mult = w6
            else:
                w_sum += w1
                w_mult += w2
                w_mult_one += w3
                w_pos_mult += w4
                w_pos_add += w5
                w_pos_mult_mult += w6

        return (
            w_sum / N_RUNS,
            w_mult / N_RUNS,
            w_mult_one / N_RUNS,
            w_pos_mult / N_RUNS,
            w_pos_add / N_RUNS,
            w_pos_mult_mult / N_RUNS
        )

    N_RUNS = 1000
    N_VECTS = 25
    DIM = 768

    # ---- cluster ----
    c_sum, c_mult, c_mult_one, c_pos_mult, c_pos_add, c_pos_mult_mult = run_experiment(
        generate_clustered_vects,
        N_RUNS, N_VECTS, DIM
    )

    # ---- random ----
    r_sum, r_mult, r_mult_one, r_pos_mult, r_pos_add, r_pos_mult_mult = run_experiment(
        generate_random_vects,
        N_RUNS, N_VECTS, DIM
    )

    # ---- PLOT SUM ----
    plt.figure()
    plt.plot(c_sum, label="Cluster")
    plt.plot(r_sum, label="Random")
    plt.title("Sum of cosines")
    plt.xticks(range(N_VECTS))
    plt.yticks(np.arange(0, int(max(np.max(c_sum), np.max(r_sum))) + 1, 1))
    plt.legend()
    plt.show()

    # ---- PLOT MULT ----
    plt.figure()
    plt.plot(c_mult, label="Cluster")
    plt.plot(r_mult, label="Random")
    plt.title("Multiplicative")
    plt.xticks(range(N_VECTS))
    plt.yticks(np.arange(0, int(max(np.max(c_mult), np.max(r_mult))) + 1, 1))
    plt.legend()
    plt.show()

    # ---- PLOT MULT + 1 ----
    plt.figure()
    plt.plot(c_mult_one, label="Cluster")
    plt.plot(r_mult_one, label="Random")
    plt.title("Mult + 1")
    plt.xticks(range(N_VECTS))
    plt.yticks(np.arange(0, int(max(np.max(c_mult_one), np.max(r_mult_one))) + 1, 1))
    plt.legend()
    plt.show()

    # ---- PLOT POSITION MULT ----
    plt.figure()
    plt.plot(c_pos_mult, label="Cluster")
    plt.plot(r_pos_mult, label="Random")
    plt.title("Position + prev * sim")
    plt.xticks(range(N_VECTS))
    plt.yticks(np.arange(0, int(max(np.max(c_pos_mult), np.max(r_pos_mult))) + 1, 1))
    plt.legend()
    plt.show()

    # ---- PLOT POSITION ADD ----
    plt.figure()
    plt.plot(c_pos_add, label="Cluster")
    plt.plot(r_pos_add, label="Random")
    plt.title("Position + prev + sim")
    plt.xticks(range(N_VECTS))
    plt.yticks(np.arange(0, int(max(np.max(c_pos_add), np.max(r_pos_add))) + 1, 1))
    plt.legend()
    plt.show()

    # ---- PLOT POSITION MULT MULT ----
    plt.figure()
    plt.plot(c_pos_mult_mult, label="Cluster")
    plt.plot(r_pos_mult_mult, label="Random")
    plt.title("Position * prev * sim")
    plt.xticks(range(N_VECTS))
    plt.yticks(np.arange(0, int(max(np.max(c_pos_mult_mult), np.max(r_pos_mult_mult))) + 1, 1))
    plt.legend()
    plt.show()