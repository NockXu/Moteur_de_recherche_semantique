import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QWidget, QFileDialog)
from PyQt6.QtCore import QObject, pyqtSignal

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class WithDatasetWidget(QWidget):
    """Widget pour l'importation avec informations de dataset"""
    
    # Signaux
    dataset_config_changed = pyqtSignal(dict)  # {dataset_name: path}
    validation_changed = pyqtSignal(bool)  # valid/invalid
    
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.dataset_inputs = {}
        self.dataset_status_labels = {}
        self.datasets_config = {}
        
        self.setup_ui()
        self.analyze_file()
    
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
    
    def analyze_file(self):
        """Analyse le fichier pour trouver les datasets"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Trouver tous les datasets uniques
            datasets = set()
            for filename, image_data in data.items():
                if filename not in ["export_info", "metadata"] and "dataset" in image_data:
                    datasets.add(image_data["dataset"])
            
            # Créer un champ pour chaque dataset
            for dataset in sorted(datasets):
                self.add_dataset_field(dataset)
            
            self.instruction_label.setText(f"Configurez les chemins pour chaque dataset trouvé ({len(datasets)} trouvés):")
            
        except Exception as e:
            self.instruction_label.setText(f"❌ Erreur analyse: {e}")
    
    def add_dataset_field(self, dataset_name: str):
        """Ajoute un champ de configuration pour un dataset"""
        h_layout = QHBoxLayout()
        
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
        
        self.datasets_layout.addLayout(h_layout)
        
        # Ajouter un label de statut
        status_label = QLabel("")
        status_label.setStyleSheet("color: #666; font-size: 10px;")
        
        self.datasets_layout.addWidget(status_label)
        
        # Connecter les signaux
        browse_button.clicked.connect(lambda checked, ds=dataset_name, le=line_edit, sl=status_label: self.browse_dataset_folder(ds, le, sl))
        line_edit.textChanged.connect(lambda text, ds=dataset_name, sl=status_label: self.check_dataset_path_exists(ds, text, sl))
        
        # Stocker les références
        self.dataset_inputs[dataset_name] = line_edit
        self.dataset_status_labels[dataset_name] = status_label
    
    def browse_dataset_folder(self, dataset_name: str, line_edit: QLineEdit, status_label: QLabel):
        """Parcourt pour sélectionner un dossier de dataset"""
        folder = QFileDialog.getExistingDirectory(self, f"Sélectionner le dossier pour {dataset_name}")
        if folder:
            line_edit.setText(folder)
            self.check_dataset_path_exists(dataset_name, folder, status_label)
    
    def check_dataset_path_exists(self, dataset_name, path_text, status_label):
        """Vérifie si un dataset existe déjà dans la base de données"""
        if not path_text.strip():
            status_label.setText("")
            self.update_validation()
            return
        
        try:
            # Utiliser DatabaseManager pour éviter les imports circulaires
            from database.DatabaseManager import DatabaseManager
            
            db = DatabaseManager()
            if db.dataset_exists(dataset_name):
                status_label.setText("⚠️ Dataset existe déjà")
                status_label.setStyleSheet("color: #ff9800; font-size: 10px;")
            else:
                status_label.setText("✅ Nouveau dataset")
                status_label.setStyleSheet("color: #4caf50; font-size: 10px;")
            
            # Mettre à jour la configuration
            self.datasets_config[dataset_name] = path_text
            self.dataset_config_changed.emit(self.datasets_config)
            self.update_validation()
                
        except Exception as e:
            status_label.setText("❌ Erreur de vérification")
            status_label.setStyleSheet("color: #f44336; font-size: 10px;")
            self.validation_changed.emit(False)
    
    def update_validation(self):
        """Met à jour l'état de validation"""
        valid = True
        for dataset_name, line_edit in self.dataset_inputs.items():
            if not line_edit.text().strip():
                valid = False
                break
        
        self.validation_changed.emit(valid)
    
    def get_datasets_config(self) -> Dict[str, str]:
        """Retourne la configuration des datasets"""
        config = {}
        for dataset_name, line_edit in self.dataset_inputs.items():
            path = line_edit.text().strip()
            if path:
                config[dataset_name] = path
        return config
    
    def is_valid(self) -> bool:
        """Vérifie si la configuration est valide"""
        for line_edit in self.dataset_inputs.values():
            if not line_edit.text().strip():
                return False
        return len(self.dataset_inputs) > 0
