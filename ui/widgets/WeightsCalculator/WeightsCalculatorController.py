from typing import Tuple

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal

from common.WeightCalculator.weightCalculator import WeightFunction, WeightSystem
from .WeightsCalculatorView import WeightCalculatorView
from .WeightsCalculatorModel import WeightsCalculatorModel

class WeightCalculatorController(QWidget):

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
        self.view.weight_selector.currentIndexChanged.connect(self.update_weight_fn)
        self.view.const_selector.valueChanged.connect(self.on_const_changed)

    def update_weight_fn(self, index: int):
        weight_fn = self.view.weight_selector.itemData(index)

        self.model.weight_fonction = weight_fn

        if weight_fn is not None:
            self.view.weight_selector.setToolTip(weight_fn.description)

        self.update_view()

    def on_const_changed(self, const):
        self.model.set_const(const)
        self.update_view()

    def set_data(self, const: float, function: WeightFunction):
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
        self.view._update_preview_plot(self.model.weight_fonction, self.model.n_runs, self.model.get_vects(), self.model.get_vects_rand(), self.model.const)
        self.data_changed.emit(self.model.const, self.model.weight_fonction.weight_fn)

    def init_funcs(self) -> None:
        self.view.set_weight_functions(self.model.get_funcs())

    def get_data(self) -> Tuple[float, WeightSystem]:
        return (self.model.const, self.model.weight_fonction.weight_fn)

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = WeightCalculatorController()
    window.view.show()
    sys.exit(app.exec())
