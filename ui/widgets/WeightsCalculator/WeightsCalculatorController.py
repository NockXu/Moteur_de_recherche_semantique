from typing import Tuple

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal, QTimer

from common.WeightCalculator.weightCalculator import WeightFunction, WeightSystem
from .WeightsCalculatorView import WeightCalculatorView
from .WeightsCalculatorModel import WeightsCalculatorModel

class WeightCalculatorController(QWidget):
    """Controller component bridging the weights calculator layout view and data model layer.

    Coordinates reactive interface events, mathematical profile queries, and emits synchronized 
    weight parameter configuration modifications.
    """

    data_changed = pyqtSignal(float, WeightSystem)

    def __init__(self):
        super().__init__()
        self.view = WeightCalculatorView()
        self.model = WeightsCalculatorModel()

        self.init_funcs()

        self._connect_signals()

        if self.view.weight_selector.count() > 0:
            self.view.weight_selector.setCurrentIndex(0)
            self.update_weight_fn(0)
        
    def _connect_signals(self):
        """Map user interface interactive widgets to internal logical controller slots."""
        self.view.weight_selector.currentIndexChanged.connect(self.update_weight_fn)
        self.view.const_selector.valueChanged.connect(self.on_const_changed)

    def update_weight_fn(self, index: int):
        """Update active model system settings based on the combo box selection index mapping.

        Args:
            index (int):
                The interactive view dropdown item position indicator.

        """
        weight_fn = self.view.weight_selector.itemData(index)
        self.model.weight_fonction = weight_fn

        if weight_fn is not None:
            self.view.weight_selector.setToolTip(weight_fn.description)
        self.update_view()

    def on_const_changed(self, const):
        """Update data parameters following modification instances on numeric constant inputs.

        Args:
            const (float):
                The updated mathematical scaling variable value.

        """
        self.model.set_const(const)
        self.update_view()

    def set_data(self, const: float, function: WeightFunction):
        """Enforce external configuration parameter values onto matching view and model elements.

        Args:
            const (float):
                The raw target scaling attribute baseline.
            function (WeightFunction):
                The specific weighting formulation metadata model requested.

        """
        self.model.set_const(const)
        self.model.set_selected_weight_fn(function)

        self.view.const_selector.setValue(int(const))

        # recherche de la fonction dans le combo
        for i in range(self.view.weight_selector.count()):
            item = self.view.weight_selector.itemData(i)

            if item is not None and item.weight_fn.expr == function.weight_fn.expr:
                self.view.weight_selector.setCurrentIndex(i)
                self.view.weight_selector.setToolTip(item.description)
                break

        self.update_view()

    def update_view(self):
        """Schedule canvas replots on the event loop and dispatch external data synchronization signals."""
        QTimer.singleShot(0, lambda: self.view._update_preview_plot(self.model.weight_fonction, self.model.n_runs, self.model.get_vects(), self.model.get_vects_rand(), self.model.const))
        self.data_changed.emit(self.model.const, self.model.weight_fonction.weight_fn)
        
    def init_funcs(self) -> None:
        """Fetch mathematical formulations from data layers and register items inside view states."""
        self.view.set_weight_functions(self.model.get_funcs())

    def get_data(self) -> tuple[float, WeightSystem]:
        """Fetch current mathematical attributes cached inside processing configurations.

        Returns:
            tuple[float, WeightSystem]: A tuple tracking active constant values and weight schemas.

        """
        return (self.model.const, self.model.weight_fonction.weight_fn)

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = WeightCalculatorController()
    window.view.show()
    sys.exit(app.exec())
