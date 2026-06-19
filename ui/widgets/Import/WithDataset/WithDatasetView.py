from typing import Optional, Dict, TypedDict, List

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
from PyQt6.QtCore import pyqtSignal
from .DatasetType import DatasetConfig

class WithDatasetView(QWidget):
    """UI View component managing path configurations for pre-partitioned dataset entries.

    Displays dynamically generated configuration fields for each detected partition label 
    found inside the loaded catalog metadata.
    """
    
    dataset_path_changed = pyqtSignal(dict, str)
    
    def __init__(self):
        super().__init__()

        self.datasets_config : dict[str, DatasetConfig] = {}

        self.setup_ui()

    def setup_ui(self):
        """Configure and position the static base window layout layout panels."""
        layout = QVBoxLayout()
        
        # Label d'instruction
        self.instruction_label = QLabel("Configurez les chemins pour chaque dataset trouvé:")
        layout.addWidget(self.instruction_label)
        
        # Layout pour les configurations de dataset
        self.datasets_layout = QVBoxLayout()
        layout.addLayout(self.datasets_layout)
        
        self.setLayout(layout)

    def add_dataset_field(self, dataset_name: str):
        """Append an interactive row layout block allocated to a specific dataset designation token.

        Args:
            dataset_name (str): The logical catalog mapping identification string.

        """
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
        """Open a system folder dialog overlay to select absolute dataset directories locations.

        Args:
            config (DatasetConfig): Row dictionary containing target text box fields to update.

        """
        folder = QFileDialog.getExistingDirectory(self, f"Sélectionner le dossier pour le dataset")
        if folder:
            config["line_edit"].setText(folder)
            
    def _on_dataset_path_changed(self, config : DatasetConfig, dataset_name: str):
        """Internal intercept routine to broadcast user path inputs to the controller layer.

        Args:
            config (DatasetConfig): Modified UI subfield configuration components dictionary.
            dataset_name (str): Label matching the row record being configured.

        """
        self.dataset_path_changed.emit(config, dataset_name)

    def exist(self, name: str, exists: bool):
        """Update and display localized text tracking hints reflecting database cache matches.

        Args:
            name (str): Target dictionary configuration key lookup reference identifier.
            exists (bool): Flag tracking if data already lives within indexed storage.

        """
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