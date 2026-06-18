from common.WeightCalculator import *
from typing import Optional
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class WeightsCalculatorModel:
    def __init__(self, n_runs: int = 1000, n_vects: int = 10, dim: int = 768, const: int = 1):
        self.n_runs = n_runs
        self.n_vects = n_vects
        self.dim = dim
        self.const = const
        self.weight_fonction : WeightFunction | None = None

    @property
    def is_weight_fonction(self) -> bool:
        return self.weight_fonction is not None
    
    def set_n_runs(self, n_runs: int):
        self.n_runs = n_runs
    
    def set_n_vects(self, n_vects: int):
        self.n_vects = n_vects
    
    def set_dim(self, dim: int):
        self.dim = dim

    def get_vects(self):
        return WeightFunction.generate_clustered_vects(self.n_vects, self.dim)
    
    def get_vects_rand(self):
        return WeightFunction.generate_random_vects(self.n_vects, self.dim)  

    def get_funcs(self) -> list:
        return weight_functions

    def set_const(self, const) -> None:
        self.const = const
    
    def set_selected_weight_fn(self, weight_fonction : WeightFunction):
        self.weight_fonction = weight_fonction
