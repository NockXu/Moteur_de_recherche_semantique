from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget, QComboBox, QLabel, QVBoxLayout, QSpinBox
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from typing import List
from collections.abc import Callable

from common.WeightCalculator.weightCalculator import WeightFunction
from ui.utils.i18n import tr

class WeightCalculatorView(QWidget):
    """View component that renders the weight selection layout controls and preview graphs.

    Provides dropdown lists, parameter spin boxes, and embedded Matplotlib canvas plots 
    to visualize mathematical simulation metrics.

    Args:
        parent (QWidget):
            Optional parent widget container. Defaults to None.
        n_runs (int):
            Default loop iteration baseline count for preview rendering routines. Defaults to 1000.
        n_vects (int):
            Default array count tracking vector quantities. Defaults to 10.
        dim (int):
            Dimensional properties matching generated coordinates elements. Defaults to 768.

    """
    
    def __init__(self, parent = None, n_runs : int = 1000, n_vects : int = 10, dim : int = 768) -> None:
        super().__init__(parent)
        self.n_runs = n_runs
        self.n_vects = n_vects
        self.dim = dim

        self._setup_ui()

    def _setup_ui(self):
        """Construct child display items and configure coordinate alignment layouts."""

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        
        # ---------- WEIGHT FUNCTION SELECTOR ----------

        self.selector_layout = QHBoxLayout()
        self.main_layout.addLayout(self.selector_layout)

        self.const_selector = QSpinBox()
        self.const_selector.setMinimum(0)
        self.const_selector.setMaximum(100)
        self.const_selector.setSingleStep(1)
        self.const_selector.setValue(1)

        self.weight_selector = QComboBox()

        self.label = QLabel(f"{tr("Methode de calcul de poids")}:")
        self.main_layout.addWidget(self.label)
        self.selector_layout.addWidget(self.weight_selector, stretch=3)
        self.selector_layout.addWidget(self.const_selector, stretch=1)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        self.main_layout.addWidget(self.canvas)

    def set_weight_functions(self, functions: list):
        """Populate the combo box drop-down structure with mathematical formula models.

        Args:
            functions (list):
                A list containing the catalog tracking available WeightFunction objects.

        """
        self.weight_functions = functions

        self.weight_selector.clear()

        for function in functions:
            self.weight_selector.addItem(function.name, function)

            if function:
                self.weight_selector.setToolTip(function.description)

    def _update_preview_plot(self, weight_fn, n_runs, vects, vects_rand, const=1):
        """Clear and replot average simulated vector weights over multiple iterative runs.

        Args:
            weight_fn (Any):
                The formula schema executing structural scaling transformations.
            n_runs (int):
                The validation evaluation loop termination threshold.
            vects (Any):
                Clustered model rows context matrices payload.
            vects_rand (Any):
                Randomly generated coordinates rows context matrices payload.
            const (float):
                Constant multiplier modifying baseline scaling profiles. Defaults to 1.

        """
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        avg_weights = None
        avg_rand = None

        for _ in range(n_runs):
            w = np.array(weight_fn.weights_from_cosines(vects, const))
            w2 = np.array(weight_fn.weights_from_cosines(vects_rand, const))

            if avg_weights is None:
                avg_weights = w
                avg_rand = w2
            else:
                avg_weights += w
                avg_rand += w2

        avg_weights /= n_runs
        avg_rand /= n_runs

        ax.plot(avg_weights, label=tr("Cluster"))
        ax.plot(avg_rand, label=tr("Random"))

        ax.set_title(tr("Evolution du Poid selon la génération"))
        ax.set_xlabel(tr("Génération"))
        ax.set_ylabel(tr("Poid"))
        ax.legend()

        self.canvas.draw()
        
    def _build_plot(self):
        """Reconstruct blank, unpopulated background axes coordinates configurations on the plot canvas."""
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        self.ax.set_title(tr("Evolution du Poid selon la génération"))
        self.ax.set_xlabel(tr("Génération"))
        self.ax.set_ylabel(tr("Poid"))

        self.canvas.draw()
        
    def _on_language_changed(self):
        """Re-translate layout strings and refresh structural descriptions when runtime translations switch."""
        self.label.setText(f"{tr("Methode de calcul de poids")}:")
        self._build_plot()
            