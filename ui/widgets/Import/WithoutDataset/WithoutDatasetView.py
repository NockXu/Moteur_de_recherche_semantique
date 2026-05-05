from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QWidget,
    QRadioButton, QButtonGroup, QFileDialog
)
from PyQt6.QtCore import pyqtSignal
from pathlib import Path
from typing import List

from .WithoutDatasetType import WithoutDatasetConfig

class WithoutDatasetView(QWidget):
    """Vue uniquement (UI pure)"""

    config_changed = pyqtSignal()
    mode_changed = pyqtSignal(str)
    delete_folder_requested = pyqtSignal(object)
    browse_folder_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.import_mode = "without_dataset_merge"
        self.config: List[WithoutDatasetConfig] = []
        self.merged_input = None

        self.setup_ui()

    # ---------------- UI ----------------

    def setup_ui(self):
        layout = QVBoxLayout()

        self.setup_options(layout)

        self.dynamic_layout = QVBoxLayout()
        layout.addLayout(self.dynamic_layout)

        self.setLayout(layout)

    def setup_options(self, parent):
        self.mode_group = QButtonGroup()

        self.merge_radio = QRadioButton("Fusionner dans un dataset")
        self.separate_radio = QRadioButton("Un dataset par dossier")
        self.merge_radio.setChecked(True)

        self.merge_radio.toggled.connect(self.emit_mode)
        self.separate_radio.toggled.connect(self.emit_mode)

        parent.addWidget(self.merge_radio)
        parent.addWidget(self.separate_radio)

    # ---------------- EVENTS ----------------

    def emit_mode(self):
        mode = "without_dataset_merge" if self.merge_radio.isChecked() else "without_dataset_separate"
        self.config = []
        self.import_mode = mode
        self.mode_changed.emit(mode)

    def clear_dynamic(self):
        while self.dynamic_layout.count():
            item = self.dynamic_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ---------------- MERGE ----------------

    def build_merge(self):
        self.clear_dynamic()

        row = QHBoxLayout()

        label = QLabel("Dataset destination:")

        line_edit = QLineEdit()
        line_edit.setPlaceholderText("Nom du dataset")

        merged_input = QLineEdit("")
        merged_input.setPlaceholderText("Sélectionner un dossier...")

        btn = QPushButton("Parcourir")

        btn.clicked.connect(lambda: self._browse_pair(merged_input, line_edit))

        row.addWidget(label)
        row.addWidget(line_edit)
        row.addWidget(merged_input)
        row.addWidget(btn)

        self.dynamic_layout.addLayout(row)

        self.config = [WithoutDatasetConfig(
            name=line_edit,
            path=merged_input,
            status=QLabel("")
        )]

        merged_input.textChanged.connect(lambda: self.config_changed.emit())
        line_edit.textChanged.connect(lambda: self.config_changed.emit())

    # ---------------- SEPARATE ----------------

    def build_separate(self):
        self.clear_dynamic()

        title = QLabel("Dossiers à configurer :")
        self.dynamic_layout.addWidget(title)

        add_btn = QPushButton("Ajouter un dossier")
        add_btn.clicked.connect(lambda: self.add_folder())

        self.dynamic_layout.addWidget(add_btn)

    def add_folder(self):
        """Ajout visuel d’un bloc dossier"""
        h_layout = QHBoxLayout()

        name = QLineEdit()
        name.setPlaceholderText("Nom dataset")

        path = QLineEdit()
        path.setPlaceholderText("Chemin")

        browse_btn = QPushButton("Parcourir")

        delete_btn = QPushButton("Supprimer")

        v_layout = QVBoxLayout()

        status = QLabel("")

        self.config.append(WithoutDatasetConfig(
            name=name,
            path=path,
            status=status
        ))

        browse_btn.clicked.connect(lambda: self._browse_pair(path, name))
        delete_btn.clicked.connect(lambda: self._delete_folder(v_layout))
        name.textChanged.connect(lambda: self.config_changed.emit())
        path.textChanged.connect(lambda: self.config_changed.emit())

        h_layout.addWidget(name)
        h_layout.addWidget(path)
        h_layout.addWidget(browse_btn)
        h_layout.addWidget(delete_btn)
        v_layout.addLayout(h_layout)
        v_layout.addWidget(status)

        self.dynamic_layout.insertLayout(self.dynamic_layout.count() - 1, v_layout) 

    def _browse_pair(self, path_edit, name_edit):
        folder = QFileDialog.getExistingDirectory(self, "Choisir dossier")
        if folder:
            path_edit.setText(folder)
            name_edit.setText(Path(folder).name)
            self.config_changed.emit()

    def _delete_folder(self, layout):
        # Trouver l'index du layout dans dynamic_layout et supprimer l'entrée config correspondante
        layout_index = None
        for i in range(self.dynamic_layout.count()):
            item = self.dynamic_layout.itemAt(i)
            if item and item.layout() == layout:
                layout_index = i
                break
        
        if layout_index is not None:
            # Supprimer l'entrée config correspondante
            if layout_index < len(self.config):
                del self.config[layout_index]

        # 1. supprimer tous les widgets du layout
        while layout.count():
            item = layout.takeAt(0)

            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

            sublayout = item.layout()
            if sublayout:
                self._clear_layout(sublayout)

        # 2. retirer le layout du parent
        self.dynamic_layout.removeItem(layout)

        # 3. delete layout
        layout.deleteLater()

    # ---------------- DATA ----------------

    def get_mode(self):
        return self.import_mode

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    view = WithoutDatasetView()
    view.show()
    sys.exit(app.exec())
