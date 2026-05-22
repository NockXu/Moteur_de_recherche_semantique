from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QSlider,
    QComboBox
)

from common.History_Classes import HistoryData, Tree, history

from common.WeightCalculator import weight_functions, get_weight_function_by_expr
from common.WeightCalculator.weightCalculator import WeightSystem
from ui.widgets.WeightsCalculator.WeightsCalculatorController import WeightCalculatorController

from ui.utils import colored_icon

import os


class HistoryPreview(QWidget):
    # ---------------- SIGNALS ----------------

    action_done = pyqtSignal()
    close_clicked = pyqtSignal()

    # ---------------- INIT ----------------

    def __init__(self, parent= None) -> None:
        super().__init__(parent)

        self.setObjectName("HistoryPreview")

        self.current_node: Tree | None = None

        self._setup_ui()

        self.weight_calculator.data_changed.connect(self._on_weight_calculator_data_changed)

        self._apply_stylesheets()

    # ---------------- UI ----------------

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setLayout(root_layout)

        # WRAPPER (celui qui aura le background)
        self.container = QWidget()
        self.container.setObjectName("HistoryPreviewContainer")

        container_layout = QVBoxLayout(self.container)

        # ---------- CLOSE BUTTON ----------
        header = QHBoxLayout()
        header.setAlignment(Qt.AlignmentFlag.AlignRight)
        container_layout.addLayout(header)

        self.close_button = QPushButton()
        self.close_button.clicked.connect(self.close_clicked.emit)
        header.addWidget(self.close_button)

        # ---------- QUERY EDIT ----------
        self.query_edit = QTextEdit()
        self.query_edit.setPlaceholderText("Entrer la requête ici")
        container_layout.addWidget(self.query_edit)

        # ---------- THRESHOLD SLIDER ----------
        
        threshold_label = QLabel("Seuil:")
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(50)
        self.threshold_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.threshold_slider.setTickInterval(10)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        
        # Label pour afficher la valeur actuelle
        self.threshold_value_label = QLabel("50%")
        self.threshold_value_label.setMinimumWidth(50)

        self.threshold_layout = QHBoxLayout()
        self.threshold_layout.addWidget(threshold_label)
        self.threshold_layout.addWidget(self.threshold_slider)
        self.threshold_layout.addWidget(self.threshold_value_label)
        container_layout.addLayout(self.threshold_layout)

        # ---------- BUTTONS ----------
        buttons_layout = QHBoxLayout()

        self.update_button = QPushButton()
        self.delete_button = QPushButton()
        self.add_child_button = QPushButton()

        self.update_button.clicked.connect(self._on_update_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.add_child_button.clicked.connect(self._on_add_child_clicked)

        buttons_layout.addWidget(self.update_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addWidget(self.add_child_button)

        container_layout.addLayout(buttons_layout)
        container_layout.addStretch()

        # ---------- WEIGHT CALCULATOR ----------

        self.weight_calculator = WeightCalculatorController()
        container_layout.addWidget(self.weight_calculator.view)

        # on ajoute le container au widget principal
        root_layout.addWidget(self.container)

    def _apply_stylesheets(self) -> None:
        self.close_button.setIcon(colored_icon("./ui/Icon/close.svg", os.environ["QTMATERIAL_PRIMARYCOLOR"]))
        self.update_button.setIcon(colored_icon("./ui/Icon/download.svg", os.environ["QTMATERIAL_PRIMARYCOLOR"]))
        self.delete_button.setIcon(colored_icon("./ui/Icon/delete.svg", os.environ["QTMATERIAL_PRIMARYCOLOR"]))
        self.add_child_button.setIcon(colored_icon("./ui/Icon/add.svg", os.environ["QTMATERIAL_PRIMARYCOLOR"]))

        self.setStyleSheet(f"""
            QPushButton {{
                padding: 5px 12px;
                border: none;
                border-radius: 4px;
                color: {os.environ["QTMATERIAL_PRIMARYCOLOR"]};
            }}
        """)

    # ---------------- PUBLIC ----------------

    def set_node(self, node: Tree | None) -> None:
        self.current_node = node

        self.threshold_slider.setValue(int(node.node.threshold * 100))
        self.threshold_value_label.setText(f"{int(node.node.threshold * 100)}%")

        weight_functions = get_weight_function_by_expr(node.node.w_expr)

        self.weight_calculator.set_data(node.node.w_const, weight_functions)

        if node is None:
            self.query_edit.clear()
            return

        if node.node.query == "DEFAULT":
            self.delete_button.hide()
            self.update_button.hide()
        else:
            self.delete_button.show()
            self.update_button.show()

        text = ""

        if node.node and hasattr(node.node, "query"):
            text = node.node.query or ""

        self.query_edit.setText(text)

    # ---------------- EVENTS ----------------
    
    def _on_threshold_changed(self) -> None:
        self.threshold_value_label.setText(f"{self.threshold_slider.value()}%")

    def _on_update_clicked(self) -> None:
        if self.current_node is None:
            return

        self.current_node.node.query = self.query_edit.toPlainText()
        self.current_node.node.threshold = self.threshold_slider.value() / 100

        self.action_done.emit()
        history.set_current_search(self.current_node)
        self.close_clicked.emit()

    def _on_delete_clicked(self) -> None:
        if self.current_node is None:
            return

        confirm = QMessageBox.question(
            self,
            "Supprimer Nœud",
            "Supprimer ce nœud ? (Cette action suprimera tout les nœuds sous celui détruit)"
        )

        if confirm == QMessageBox.StandardButton.Yes:
            if self.current_node.is_root:
                pass
            else:
                parent = self.current_node.parent
                self.current_node.disconect()
                self.action_done.emit()
                self.close_clicked.emit()
                if parent is not None:
                    history.set_current_search(parent)
                else:
                    history.set_current_search(history.history_tree)

    def _on_add_child_clicked(self) -> None:
        if self.current_node is None:
            return

        self.current_node.add_child(Tree(HistoryData()))

        self.action_done.emit()
        self.close_clicked.emit()
    
    def _on_theme_changed(self) -> None:
        self._apply_stylesheets()

    # ---------- WEIGHT CALCULATOR -------------

    def _on_weight_calculator_data_changed(self, const : float, expr : WeightSystem) -> None:
        self.current_node.node.w_const = const
        self.current_node.node.w_expr = expr
        history.save()
