from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from typing import List, Callable, Union, Dict
import faiss

class WeightFunction:
    def __init__(self, name: str, description: str, weight_fn: WeightSystem):
        self.name = name
        self.description = description
        self.weight_fn = weight_fn

    def cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def weights_from_cosines(
        self,
        vects: List[np.ndarray],
        const: float = 1.0
    ) -> List[float]:
        """
        Generic weight builder for vector chains (for the preview).

        Parameters
        ----------
        vects : list of embeddings
        weight_fn :
            function(prev_weight, similarity, position) -> new_weight
        """

        if not vects:
            return []

        weights = [1.0]

        for p in range(1, len(vects)):
            sim = self.cosine(vects[p], vects[p - 1])

            new_w = self.weight_fn(
                weights[-1],
                sim, 
                p, 
                const
                )

            weights.append(new_w)

        return weights

    def get_weights(self, sim: float, parent_weight: float,  position: int, const: int):
        return self.weight_fn(parent_weight, sim, position, const)

    @staticmethod
    def generate_random_vects(n: int, dim: int) -> List[np.ndarray]:
        vects = np.random.randn(n, dim).astype(np.float32)
        faiss.normalize_L2(vects)
        return list(vects)


    @staticmethod
    def generate_clustered_vects(n: int, dim: int, k_clusters=3, noise=0.1) -> List[np.ndarray]:
        centers = np.random.randn(k_clusters, dim).astype(np.float32)

        vects = []
        for _ in range(n):
            c = centers[np.random.randint(0, k_clusters)]
            v = c + noise * np.random.randn(dim).astype(np.float32)
            vects.append(v)

        vects = np.array(vects, dtype=np.float32)
        faiss.normalize_L2(vects)

        return list(vects)

    def __str__(self) -> str:
        return self.name

    @property
    def describe(self) -> str:
        return self.description

    def to_dict(self) -> Dict[str, Dict[str, Union[str, Callable[[float, float, int, float], float]]]]:
        return {self.name: {
            "description": self.description,
            "weight_fn": self.weight_fn
        }}

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WeightFunction):
            return other.weight_fn == self.weight_fn
        return False
        
    
class WeightSystem:
    """
    System allowing a custom weight function defined as a string expression.

    The expression is evaluated with the following variables:

    Args:
        prev (float):
            Weight of the previous (parent) node.
        sim (float):
            Cosine similarity between the current vector and the previous one.
        p (int):
            Position index of the current vector (root = 0).
        const (float):
            Constant value provided externally.

    Notes:
        The expression is evaluated dynamically and must use only the variables above.
    """
    def __init__(self, expr: str):
        self.expr = expr

    def __call__(self, prev: float, sim: float, p: int, const: float) -> float:
        return eval(
            self.expr,
            {"__builtins__": {}},
            {
                "prev": prev,
                "sim": sim,
                "p": p,
                "const": const
            }
        )

    def __str__(self) -> str:
        return self.expr

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WeightSystem):
            return self.expr == other.expr
        return False

if __name__ == "__main__":
    import numpy as np
    import matplotlib.pyplot as plt
    
    def run_experiment(generator, N_RUNS, N_VECTS, DIM):

        expressions = {
            "sum": "prev + sim",
            "mult": "prev * sim",
            "mult_one": "const + prev * sim",
            "pos_mult": "p + prev * sim",
            "pos_add": "p + prev + sim",
            "pos_mult_mult": "p * prev * sim",
            "equal": "const"
        }

        systems = {
            name: WeightFunction(name, name, WeightSystem(expr))
            for name, expr in expressions.items()
        }

        accum = {name: None for name in systems}

        for _ in range(N_RUNS):
            vects = generator(N_VECTS, DIM)

            results = {
                name: np.array(fn.weights_from_cosines(vects))
                for name, fn in systems.items()
            }

            for name, values in results.items():
                if accum[name] is None:
                    accum[name] = values
                else:
                    accum[name] += values

        return {name: accum[name] / N_RUNS for name in accum}

    def plot(name, c, r):
        plt.figure()
        plt.plot(c, label="Cluster")
        plt.plot(r, label="Random")
        plt.title(name)
        plt.legend()
        plt.show()

    N_RUNS = 100
    N_VECTS = 25
    DIM = 768

    # cluster
    cluster = run_experiment(
        WeightFunction.generate_clustered_vects,
        N_RUNS, N_VECTS, DIM
    )

    # random
    random = run_experiment(
        WeightFunction.generate_random_vects,
        N_RUNS, N_VECTS, DIM
    )

    for k in cluster:
        plot(k, cluster[k], random[k])