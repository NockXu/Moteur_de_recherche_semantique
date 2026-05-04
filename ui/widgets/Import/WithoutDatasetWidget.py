import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QWidget, 
                             QRadioButton, QButtonGroup, QGroupBox, QFileDialog)
from PyQt6.QtCore import QObject, pyqtSignal

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class WithoutDatasetWidget(QWidget):
    """Widget pour l'importation sans informations de dataset"""
    
    # Signaux
    config_changed = pyqtSignal(dict)  # configuration des dossiers
    validation_changed = pyqtSignal(bool)  # valid/invalid
    mode_changed = pyqtSignal(str)  # changement de mode
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.import_mode = "without_dataset_merge"
        self.folder_configs = []
        self.merged_folder_input = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout()
        
        # Options de traitement
        self.setup_options(layout)
        
        # Configuration dynamique
        self.dynamic_layout = QVBoxLayout()
        layout.addLayout(self.dynamic_layout)
        
        self.setLayout(layout)
        
        # Afficher la configuration initiale
        self.update_config_display()
    
    def setup_options(self, parent_layout):
        """Configure les options de traitement"""
        options_layout = QVBoxLayout()
        
        # Radio buttons
        self.mode_group = QButtonGroup()
        
        self.merge_radio = QRadioButton("Fusionner toutes les images dans un seul dataset")
        self.separate_radio = QRadioButton("Créer un dataset par dossier d'origine")
        self.merge_radio.setChecked(True)
        
        # Descriptions
        merge_desc = QLabel("Toutes les images seront placées dans un seul dataset que vous choisirez")
        merge_desc.setStyleSheet("color: #666; font-size: 11px; margin-left: 20px;")
        
        separate_desc = QLabel("Chaque dossier source créera un dataset séparé")
        separate_desc.setStyleSheet("color: #666; font-size: 11px; margin-left: 20px;")
        
        # Ajouter au layout
        options_layout.addWidget(self.merge_radio)
        options_layout.addWidget(merge_desc)
        options_layout.addWidget(self.separate_radio)
        options_layout.addWidget(separate_desc)
        
        # Connecter les signaux
        self.merge_radio.toggled.connect(self.on_mode_changed)
        self.separate_radio.toggled.connect(self.on_mode_changed)
        
        parent_layout.addLayout(options_layout)
    
    def on_mode_changed(self):
        """Gère le changement de mode"""
        if self.merge_radio.isChecked():
            self.import_mode = "without_dataset_merge"
        elif self.separate_radio.isChecked():
            self.import_mode = "without_dataset_separate"
        
        # Émettre le signal de changement de mode
        self.mode_changed.emit(self.import_mode)
        
        self.update_config_display()
        self.validate_config()
    
    def get_import_mode(self):
        """Retourne le mode d'importation actuel"""
        return self.import_mode
    
    def update_config_display(self):
        """Met à jour l'affichage selon le mode sélectionné"""
        # Vider la configuration précédente
        self.clear_layout(self.dynamic_layout)
        
        if self.merge_radio.isChecked():
            self.setup_merge_config()
        elif self.separate_radio.isChecked():
            self.setup_separate_config()
    
    def setup_merge_config(self):
        """Configure l'interface pour le mode fusion"""
        h_layout = QHBoxLayout()
        
        label = QLabel("Dataset de destination:")
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("Chemin du dossier pour le dataset...")
        browse_button = QPushButton("Parcourir...")
        
        # Connecter les signaux
        browse_button.clicked.connect(lambda: self.browse_single_folder(line_edit))
        line_edit.textChanged.connect(self.on_config_changed)
        
        # Ajouter au layout
        h_layout.addWidget(label)
        h_layout.addWidget(line_edit)
        h_layout.addWidget(browse_button)
        
        self.dynamic_layout.addLayout(h_layout)
        self.merged_folder_input = line_edit
    
    def setup_separate_config(self):
        """Configure l'interface pour le mode séparé"""
        # Label d'instruction
        label = QLabel("Configurez les chemins pour chaque dossier d'origine:")
        self.dynamic_layout.addWidget(label)
        
        # Bouton pour ajouter des configurations
        h_layout = QHBoxLayout()
        add_button = QPushButton("Ajouter un dossier")
        add_button.clicked.connect(self.add_folder_config)
        h_layout.addWidget(add_button)
        h_layout.addStretch()
        
        self.dynamic_layout.addLayout(h_layout)
    
    def add_folder_config(self):
        """Ajoute une configuration de dossier"""
        h_layout = QHBoxLayout()
        
        # Champ de nom
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Nom du dataset...")
        
        # Champ de chemin
        path_edit = QLineEdit()
        path_edit.setPlaceholderText("Chemin du dossier...")
        
        # Boutons
        browse_button = QPushButton("Parcourir...")
        delete_button = QPushButton("Supprimer")
        
        # Label de statut
        status_label = QLabel("")
        status_label.setStyleSheet("color: #666; font-size: 10px;")
        
        # Ajouter au layout (insérer avant le bouton "Ajouter")
        self.dynamic_layout.insertLayout(self.dynamic_layout.count() - 1, h_layout)
        
        # Ajouter les widgets au layout
        h_layout.addWidget(name_edit)
        h_layout.addWidget(path_edit)
        h_layout.addWidget(browse_button)
        h_layout.addWidget(delete_button)
        
        # Ajouter le statut en dessous
        self.dynamic_layout.insertWidget(self.dynamic_layout.count() - 1, status_label)
        
        # Connecter les signaux
        delete_button.clicked.connect(lambda checked, cd={'name_edit': name_edit, 'path_edit': path_edit, 'layout': h_layout, 'status_label': status_label}: self.delete_folder_config(cd))
        name_edit.textChanged.connect(lambda text, cd={'name_edit': name_edit, 'status_label': status_label}: self.check_dataset_exists(cd))
        path_edit.textChanged.connect(self.on_config_changed)
        browse_button.clicked.connect(lambda checked, pe=path_edit, ne=name_edit, sl=status_label: self.browse_folder_path(pe, ne, sl))
        
        # Stocker la configuration
        config_data = {
            'name_edit': name_edit, 
            'path_edit': path_edit, 
            'layout': h_layout, 
            'status_label': status_label
        }
        self.folder_configs.append(config_data)
        
        self.validate_config()
    
    def browse_folder_path(self, path_edit: QLineEdit, name_edit: QLineEdit, status_label: QLabel):
        """Parcourt pour sélectionner un chemin de dossier et remplit automatiquement le nom"""
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier")
        if folder:
            path_edit.setText(folder)
            # Remplir automatiquement le nom du dataset avec le nom du dossier
            folder_name = Path(folder).name
            name_edit.setText(folder_name)
            # Vérifier si le dataset existe
            self.check_dataset_exists({'name_edit': name_edit, 'status_label': status_label})
    
    def check_dataset_exists(self, config_data: dict):
        """Vérifie si un dataset existe déjà et met à jour le statut"""
        dataset_name = config_data['name_edit'].text().strip()
        status_label = config_data['status_label']
        
        if not dataset_name:
            status_label.setText("")
            self.validate_config()
            return
            
        try:
            # Importer DatabaseManager ici pour éviter les imports circulaires
            from database.DatabaseManager import DatabaseManager
            
            db = DatabaseManager()
            if db.dataset_exists(dataset_name):
                status_label.setText("⚠️ Fusionnera avec le dataset existant")
                status_label.setStyleSheet("color: #ff9800; font-size: 10px;")
                status_label.setVisible(True)
            else:
                status_label.setText("")
                status_label.setStyleSheet("color: #4caf50; font-size: 10px;")
                status_label.setVisible(False)
                
            self.validate_config()
                
        except Exception as e:
            print(f"Erreur de vérification DatabaseManager: {e}")
            status_label.setText("❌ Erreur de vérification")
            status_label.setStyleSheet("color: #f44336; font-size: 10px;")
            status_label.setVisible(True)
            self.validation_changed.emit(False)
    
    def browse_single_folder(self, line_edit: QLineEdit):
        """Parcourt pour sélectionner un dossier unique"""
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier de destination")
        if folder:
            line_edit.setText(folder)
            self.on_config_changed()
    
    def delete_folder_config(self, config_data: dict):
        """Supprime une configuration de dossier"""
        print(f"DEBUG: delete_folder_config appelée pour {config_data.get('name_edit', {}).text()}")
        
        # Masquer le label de statut avant suppression
        status_label = config_data['status_label']
        status_label.setVisible(False)
        
        # Supprimer le layout et tous ses widgets
        layout = config_data['layout']
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Supprimer le label de statut lui-même
        status_label.deleteLater()
        
        # Retirer de la liste des configurations
        if config_data in self.folder_configs:
            self.folder_configs.remove(config_data)
        
        self.validate_config()
    
    def clear_layout(self, layout):
        """Vide proprement un layout et tous ses widgets"""
        if not layout:
            return
        
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
    
    def on_config_changed(self):
        """Gère le changement de configuration"""
        config = self.get_config()
        self.config_changed.emit(config)
        self.validate_config()
    
    def validate_config(self):
        """Valide la configuration actuelle"""
        valid = False
        
        if self.merge_radio.isChecked():
            valid = self.merged_folder_input and bool(self.merged_folder_input.text().strip())
        elif self.separate_radio.isChecked():
            valid = len(self.folder_configs) > 0
            for config in self.folder_configs:
                name = config['name_edit'].text().strip()
                path = config['path_edit'].text().strip()
                if not name or not path:
                    valid = False
                    break
        
        self.validation_changed.emit(valid)
    
    def get_config(self) -> Dict[str, str]:
        """Retourne la configuration actuelle"""
        config = {}
        
        if self.merge_radio.isChecked() and self.merged_folder_input:
            path = self.merged_folder_input.text().strip()
            if path:
                config["merged_folder"] = path
        
        elif self.separate_radio.isChecked():
            for folder_config in self.folder_configs:
                name = folder_config['name_edit'].text().strip()
                path = folder_config['path_edit'].text().strip()
                if name and path:
                    config[name] = path
        
        return config
    
    def get_import_mode(self) -> str:
        """Retourne le mode d'importation"""
        return self.import_mode
    
    def is_valid(self) -> bool:
        """Vérifie si la configuration est valide"""
        if self.merge_radio.isChecked():
            return self.merged_folder_input and bool(self.merged_folder_input.text().strip())
        elif self.separate_radio.isChecked():
            if len(self.folder_configs) == 0:
                return False
            for config in self.folder_configs:
                name = config['name_edit'].text().strip()
                path = config['path_edit'].text().strip()
                if not name or not path:
                    return False
            return True
        return False
