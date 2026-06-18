from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QWidget,
    QRadioButton, QButtonGroup, QFileDialog, 
    QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
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
        self.config: list[WithoutDatasetConfig] = []
        self.merged_input = None

        self.setup_ui()

    # ---------------- UI ----------------

    def setup_ui(self):
        self.mainlayout = QVBoxLayout()
        self.mainlayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.second_layout = QVBoxLayout()

        self.setup_options(self.mainlayout)

        self.header_layout = QVBoxLayout()

        # Scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setFixedHeight(100)

        # Structure
        self.second_layout.addLayout(self.header_layout)
        self.second_layout.addWidget(self.scroll_area)

        self.mainlayout.addLayout(self.second_layout)

        self.setLayout(self.mainlayout)

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
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)

            widget = item.widget()
            if widget:
                widget.deleteLater()    

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)

            widget = item.widget()
            if widget:
                widget.deleteLater()

            sublayout = item.layout()
            if sublayout:
                self._clear_layout(sublayout)
                sublayout.deleteLater()

    def clear_header(self):
        while self.header_layout.count():
            item = self.header_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # ---------------- MERGE ----------------

    def build_merge(self):
        self.clear_dynamic()
        self.clear_header()

        self.scroll_area.show()

        # Nom du dataset (unique en haut)
        name_container = QWidget()
        name_row = QHBoxLayout(name_container)
        name_label = QLabel("Nom du dataset de destination:")
        name_line_edit = QLineEdit()
        name_row.addWidget(name_label)
        name_row.addWidget(name_line_edit)

        self.status = QLabel("")
        self.status.hide()

        # Titre pour les chemins
        title = QLabel("Dossiers sources à fusionner :")
        self.header_layout.addWidget(name_container)
        self.header_layout.addWidget(self.status)
        self.header_layout.addWidget(title)

        # Bouton pour ajouter des dossiers
        add_btn = QPushButton("Ajouter un dossier")
        add_btn.clicked.connect(self.add_merge_folder)
        self.header_layout.addWidget(add_btn)

        # Config pour le nom (global)
        self.merge_name_config = name_line_edit

    def add_merge_folder(self):
        """Ajoute un dossier source pour le mode merge (utilise le nom global)"""
        h_layout = QHBoxLayout()

        # Pas de nom pour les dossiers sources en mode merge
        # Le nom sera celui du dataset de destination
        
        path = QLineEdit()
        path.setPlaceholderText("Chemin du dossier source")
        
        browse_btn = QPushButton("Parcourir")
        delete_btn = QPushButton("Supprimer")

        v_layout = QVBoxLayout()
        container = QWidget()

        v_layout.setSpacing(2)
        v_layout.setContentsMargins(0, 0, 0, 0)

        h_layout.setSpacing(5)
        h_layout.setContentsMargins(0, 0, 0, 0)

        config = WithoutDatasetConfig(
            name=self.merge_name_config,
            path=path,
            status=self.status
        )
        self.config.append(config)

        browse_btn.clicked.connect(lambda: self._browse_pair(path, None))
        delete_btn.clicked.connect(lambda: self._delete_folder(container, config))

        path.textChanged.connect(self.config_changed.emit)

        h_layout.addWidget(path)
        h_layout.addWidget(browse_btn)
        h_layout.addWidget(delete_btn)

        v_layout.addLayout(h_layout)

        container.setLayout(v_layout)

        self.scroll_layout.addWidget(container)

    # ---------------- SEPARATE ----------------

    def build_separate(self):
        self.clear_dynamic()
        self.clear_header()

        self.scroll_area.show()

        title = QLabel("Dossiers à configurer :")
        self.header_layout.addWidget(title)

        add_btn = QPushButton("Ajouter un dossier")
        add_btn.clicked.connect(self.add_folder)

        self.header_layout.addWidget(add_btn)

    def add_folder(self):
        h_layout = QHBoxLayout()

        name = QLineEdit()
        name.setPlaceholderText("Nom dataset")

        path = QLineEdit()
        path.setPlaceholderText("Chemin")

        browse_btn = QPushButton("Parcourir")
        delete_btn = QPushButton("Supprimer")

        v_layout = QVBoxLayout()
        container = QWidget()

        v_layout.setSpacing(2)
        v_layout.setContentsMargins(0, 0, 0, 0)

        h_layout.setSpacing(5)
        h_layout.setContentsMargins(0, 0, 0, 0)

        status = QLabel("")
        status.hide()

        config = WithoutDatasetConfig(
            name=name,
            path=path,
            status=status
        )
        self.config.append(config)

        browse_btn.clicked.connect(lambda: self._browse_pair(path, name))
        delete_btn.clicked.connect(lambda: self._delete_folder(container, config))

        name.textChanged.connect(self.config_changed.emit)
        path.textChanged.connect(self.config_changed.emit)

        h_layout.addWidget(name)
        h_layout.addWidget(path)
        h_layout.addWidget(browse_btn)
        h_layout.addWidget(delete_btn)

        v_layout.addLayout(h_layout)
        v_layout.addWidget(status)

        container.setLayout(v_layout)

        self.scroll_layout.addWidget(container)

    def _browse_multiple_paths(self, paths_input: QLineEdit):
        """Ouvre un dialogue pour sélectionner plusieurs dossiers sources"""
        from PyQt6.QtWidgets import QFileDialog
        
        folders = QFileDialog.getExistingDirectories(
            self,
            "Sélectionner les dossiers sources",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folders:
            # Joindre les chemins avec des points-virgules
            paths_text = ";".join(folders)
            paths_input.setText(paths_text)

    def _browse_pair(self, path_edit, name_edit):
        """Ouvre un dialogue pour sélectionner un dossier"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner un dossier",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            path_edit.setText(folder)
            # Ne modifier le nom que si on est en mode separate (name_edit n'est pas None)
            if name_edit is not None:
                name_edit.setText(Path(folder).name)
            self.config_changed.emit()

    def _delete_folder(self, widget, config):
        if config in self.config:
            self.config.remove(config)

        widget.setParent(None)
        widget.deleteLater()

        self.config_changed.emit()

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
