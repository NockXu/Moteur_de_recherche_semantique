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
from common.weightCalculator import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

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

        self._apply_stylesheets()

        self.selected_weight_fn = update_sum
        self._update_preview_plot()

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

        # ---------- WEIGHT FUNCTION SELECTOR ----------

        self.weight_selector = QComboBox()

        self.weight_functions = {
            "Sum": update_sum,
            "Mult": update_mult,
            "Mult + 1": update_mult_one,
            "p + prev * sim": update_mult_with_position,
            "p + prev + sim": update_add_with_position,
            "p * prev * sim": update_mult_with_position_mult,
        }

        self.weight_selector.addItems(self.weight_functions.keys())

        self.weight_selector.currentIndexChanged.connect(self._on_weight_function_changed)

        container_layout.addWidget(QLabel("Fonction de calcul de poids:"))
        container_layout.addWidget(self.weight_selector)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        container_layout.addWidget(self.canvas)

        # on ajoute le container au widget principal
        root_layout.addWidget(self.container)

    def _update_preview_plot(self):

        N_RUNS = 1000
        N_VECTS = 10
        DIM = 768

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # accumulateur
        avg_weights = None
        avg_rand = None

        for _ in range(N_RUNS):

            vects = generate_clustered_vects(N_VECTS, DIM)
            vects_rand = generate_random_vects(N_VECTS, DIM)

            w = np.array(weights_from_cosines(vects, self.selected_weight_fn))
            w2 = np.array(weights_from_cosines(vects_rand, self.selected_weight_fn))

            if avg_weights is None:
                avg_weights = w
                avg_rand = w2
            else:
                avg_weights += w
                avg_rand += w2

        avg_weights /= N_RUNS
        avg_rand /= N_RUNS

        ax.plot(avg_weights, label="Cluster (avg 1000 runs)")
        ax.plot(avg_rand, label="Random (avg 1000 runs)")

        ax.set_title("Weight function preview (Monte Carlo)")
        ax.set_xlabel("Depth")
        ax.set_ylabel("Weight")
        ax.legend()

        self.canvas.draw()

    def _on_weight_function_changed(self, index: int):
        name = self.weight_selector.currentText()
        self.selected_weight_fn = self.weight_functions[name]
        print("Selected fn:", self.selected_weight_fn)
        self._update_preview_plot()

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
