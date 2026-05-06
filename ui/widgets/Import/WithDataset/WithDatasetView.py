from typing import Optional, Dict, TypedDict, List

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
from PyQt6.QtCore import pyqtSignal
from .DatasetType import DatasetConfig

class WithDatasetView(QWidget):
    dataset_path_changed = pyqtSignal(dict, str)
    
    def __init__(self):
        super().__init__()

        self.datasets_config : dict[str, DatasetConfig] = {}

        self.setup_ui()

    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout()
        
        # Label d'instruction
        self.instruction_label = QLabel("Configurez les chemins pour chaque dataset trouvé:")
        layout.addWidget(self.instruction_label)
        
        # Layout pour les configurations de dataset
        self.datasets_layout = QVBoxLayout()
        layout.addLayout(self.datasets_layout)
        
        self.setLayout(layout)

    def add_dataset_field(self, dataset_name: str):
        """Ajoute un champ de configuration pour un dataset"""
        h_layout = QHBoxLayout()
        v_layout = QVBoxLayout()
        
        # Label du dataset
        label = QLabel(f"Dataset '{dataset_name}':")
        
        # Champ de chemin
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("Chemin du dossier...")
        
        # Bouton de parcours
        browse_button = QPushButton("Parcourir...")
        
        # Ajouter au layout
        h_layout.addWidget(label)
        h_layout.addWidget(line_edit)
        h_layout.addWidget(browse_button)
        
        v_layout.addLayout(h_layout)
        
        # Ajouter un label de statut
        status_label = QLabel("")
        status_label.setStyleSheet("color: #666; font-size: 10px;")
        
        v_layout.addWidget(status_label)
        
        self.datasets_layout.addLayout(v_layout)

        # Stocker les références
        self.datasets_config[dataset_name] = DatasetConfig(line_edit=line_edit, status_label=status_label)
        
        # Connecter les signaux
        browse_button.clicked.connect(
        lambda _, cfg=self.datasets_config[dataset_name]: self.browse_dataset_folder(cfg)
        )

        line_edit.textChanged.connect(
            lambda _, cfg=self.datasets_config[dataset_name], ds=dataset_name: self._on_dataset_path_changed(cfg, ds)
        )

    def browse_dataset_folder(self, config: DatasetConfig):
        """Parcourt pour sélectionner un dossier de dataset"""
        folder = QFileDialog.getExistingDirectory(self, f"Sélectionner le dossier pour le dataset")
        if folder:
            config["line_edit"].setText(folder)
            
    def _on_dataset_path_changed(self, config : DatasetConfig, dataset_name: str):
        """Gère le changement de chemin d'un dataset"""
        self.dataset_path_changed.emit(config, dataset_name)

    def exist(self, name: str, exists: bool):
        """Affiche si un dataset existe"""
        label = self.datasets_config[name]["status_label"]

        if exists:
            label.setText("✔ Dataset trouvé (fusion automatique)")
            label.setStyleSheet("color: #2e7d32; font-size: 11px;")  # vert propre
            label.show()
        else:
            label.setText("✖ Dataset inexistant (création automatique)")
            label.setStyleSheet("color: #ed6c02; font-size: 11px;")  # orange lisible
            label.show()

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    view = WithDatasetView()
    view.show()
    view.add_dataset_field("dataset1")
    view.exist("dataset1", True)
    view.add_dataset_field("dataset2")
    view.exist("dataset2", False)
    sys.exit(app.exec())