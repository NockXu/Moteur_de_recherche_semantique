from numpy import ndarray

from common.WeightCalculator import *
from typing import Any, Optional
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class WeightsCalculatorModel:
    """Data model component handling parameter tracking and random vector generation configurations.

    Manages calculations for clustering runs, dimensional limitations, and active weight profiling schemas.

    Args:
        n_runs (int):
            Number of iterations requested during execution. Defaults to 1000.
        n_vects (int):
            Number of vector instances generated inside datasets. Defaults to 10.
        dim (int):
            Dimensional size metric characterizing tracking layers. Defaults to 768.
        const (int):
            Mathematical baseline scaling attribute configuration factor. Defaults to 1.

    """
    
    def __init__(self, n_runs: int = 1000, n_vects: int = 10, dim: int = 768, const: int = 1):
        self.n_runs = n_runs
        self.n_vects = n_vects
        self.dim = dim
        self.const = const
        self.weight_fonction : WeightFunction | None = None

    @property
    def is_weight_fonction(self) -> bool:
        """Check if an active weighting function schema instance is currently registered.

        Returns:
            bool: True if the internal reference tracking configuration object is not None.

        """
        return self.weight_fonction is not None
    
    def set_n_runs(self, n_runs: int):
        """Configure simulation run threshold limits.

        Args:
            n_runs (int):
                The total calculation loops counter target value.

        """
        self.n_runs = n_runs
    
    def set_n_vects(self, n_vects: int):
        """Configure total array objects allocations parameters.

        Args:
            n_vects (int):
                Target count defining vector list size metrics.

        """
        self.n_vects = n_vects
    
    def set_dim(self, dim: int):
        """Configure numerical structure sizing dimensions constraints.

        Args:
            dim (int):
                Target width properties applied across generated items.

        """
        self.dim = dim

    def get_vects(self) -> list[ndarray]:
        """Generate clustered coordinate point distributions via structural baseline helpers.

        Returns:
            A collection of structurally clustered tracking vectors matching active configuration settings.

        """
        return WeightFunction.generate_clustered_vects(self.n_vects, self.dim)
    
    def get_vects_rand(self) -> list[ndarray]:
        """Generate uniform random spatial distribution vector rows.

        Returns:
            A collections layer sequence holding unclustered random vector metrics.

        """
        return WeightFunction.generate_random_vects(self.n_vects, self.dim)  

    def get_funcs(self) -> list:
        """Fetch all predefined processing mathematical formula templates globally declared.

        Returns:
            list: The comprehensive catalog tracking available weight operation schemas.

        """
        return weight_functions

    def set_const(self, const) -> None:
        """Update system constant attributes with fresh operational variable parameters.

        Args:
            const (Any):
                The new constant variable configuration scalar token value.

        """
        self.const = const
    
    def set_selected_weight_fn(self, weight_fonction : WeightFunction):
        """Map a targeted weight formula tracking system configuration object instance.

        Args:
            weight_fonction (WeightFunction):
                The specialized mathematical weight formulation metadata structure.

        """
        self.weight_fonction = weight_fonction
