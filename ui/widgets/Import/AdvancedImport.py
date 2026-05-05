import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFileDialog, QRadioButton, 
                             QButtonGroup, QLineEdit, QListWidget, 
                             QMessageBox, QCheckBox, QGroupBox, QTextEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.DbService import DbService
from common.Image_Classes.Image import Image, ProcessingStatus

class ImportWorkerThread(QThread):
    """Thread pour l'importation en arrière-plan"""
    progress_updated = pyqtSignal(str)
    finished = pyqtSignal(int, int)  # (succès, total)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_path: str, import_mode: str, datasets_config: dict):
        super().__init__()
        self.file_path = file_path
        self.import_mode = import_mode
        self.datasets_config = datasets_config
        self.db = DatabaseManager()
    
    def run(self):
        """Exécute l'importation en arrière-plan"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Supprimer les métadonnées
            images_data = {k: v for k, v in data.items() if k not in ["export_info", "metadata"]}
            
            total_images = len(images_data)
            success_count = 0
            
            self.progress_updated.emit(f"DEBUG: Mode import = {self.import_mode}")
            self.progress_updated.emit(f"DEBUG: Config datasets = {self.datasets_config}")
            
            # Afficher un exemple de structure de données
            if images_data:
                first_key = list(images_data.keys())[0]
                self.progress_updated.emit(f"DEBUG: Structure données - Clé: {first_key}")
                self.progress_updated.emit(f"DEBUG: Structure données - Valeur: {list(images_data[first_key].keys())}")
            
            # Préparer toutes les images pour l'insertion en batch
            batch_images = []
            failed_images = []
            
            for i, (filename, image_data) in enumerate(images_data.items()):
                try:
                    self.progress_updated.emit(f"Préparation de {filename} ({i+1}/{total_images})")
                    
                    # Créer l'ImageInfo
                    image_info = ImageInfo(
                        path="",  # Path sera déterminé plus tard
                        status=ProcessingStatus.COMPLETED if image_data.get("description") else ProcessingStatus.NOT_STARTED,
                        description=image_data.get("description", ""),
                        keywords=image_data.get("keywords", []),
                        embedding=image_data.get("embedding", [])
                    )
                    
                    # Déterminer le dataset et le chemin selon le mode
                    dataset_name, final_path = self._determine_dataset_and_path(filename, image_data)
                    
                    # Générer un ID unique pour éviter les doublons
                    if "id" in image_data:
                        # Utiliser l'ID existant mais le rendre unique avec le dataset
                        image_info.id = f"{dataset_name}_{image_data['id']}"
                    else:
                        # Générer un ID unique basé sur le chemin complet
                        image_info.id = f"{dataset_name}_{Path(filename).stem}"
                    
                    self.progress_updated.emit(f"DEBUG: Dataset = {dataset_name}, Path = {final_path}")
                    
                    if dataset_name and final_path:
                        # S'assurer que le chemin est bien un Path
                        if isinstance(final_path, str):
                            final_path = Path(final_path)
                        image_info.path = final_path
                        
                        # Ajouter au batch
                        batch_images.append((image_info, dataset_name))
                        self.progress_updated.emit(f"✅ Préparé: {filename} -> {dataset_name}")
                    else:
                        failed_images.append(filename)
                        self.progress_updated.emit(f"❌ Dataset/path vide pour: {filename}")
                
                except Exception as e:
                    failed_images.append(filename)
                    self.error_occurred.emit(f"Erreur préparation {filename}: {e}")
            
            # Insérer toutes les images en batch
            if batch_images:
                self.progress_updated.emit(f"Insertion batch de {len(batch_images)} images...")
                batch_success, batch_total = self.db.insert_images_batch(batch_images)
                success_count = batch_success
                
                self.progress_updated.emit(f"✅ Insertion batch terminée: {success_count}/{batch_total} images")
                
                # Afficher les détails
                for image_info, dataset_name in batch_images:
                    self.progress_updated.emit(f"✅ Succès: {image_info.id} -> {dataset_name}")
            
            # Afficher les erreurs
            for filename in failed_images:
                self.progress_updated.emit(f"❌ Échec: {filename}")
        
            self.progress_updated.emit(f"DEBUG: Final - {success_count}/{total_images} importées")
            self.finished.emit(success_count, total_images)
            
        except Exception as e:
            self.error_occurred.emit(f"Erreur générale: {e}")
    
    def _determine_dataset_and_path(
        self,
        filename: str,
        image_data: dict
    ) -> Tuple[Optional[str], Optional[Path]]:
        """Détermine le dataset et le chemin final selon le mode d'import"""

        def _validate_path(path_str: Optional[str], context: str) -> Optional[Path]:
            """Valide et retourne un Path propre"""
            if not path_str:
                print(f"DEBUG: chemin invalide ({context})")
                return None

            path = Path(path_str)

            if not path.exists():
                print(f"DEBUG: chemin inexistant ({context}): {path}")
                return None

            return path

        def _build_result(dataset_path: Path, filename: str) -> Tuple[str, Path]:
            """Construit le résultat final"""
            dataset_name = dataset_path.name
            final_path = dataset_path / filename

            print(f"DEBUG: dataset_name = {dataset_name}")
            print(f"DEBUG: final_path = {final_path}")

            return dataset_name, final_path

        # =========================
        # MODE 1 : WITH DATASET
        # =========================
        if self.import_mode == "with_dataset":
            dataset_name = image_data.get("dataset")

            if not isinstance(dataset_name, str) or not dataset_name:
                print("DEBUG: dataset invalide dans image_data")
                return None, None

            dataset_path = _validate_path(
                self.datasets_config.get(dataset_name),
                f"dataset '{dataset_name}'"
            )

            if not dataset_path:
                return None, None

            return _build_result(dataset_path, filename)

        # =========================
        # MODE 2 : MERGED
        # =========================
        elif self.import_mode == "without_dataset_merge":
            merged_folder = self.datasets_config.get("merged_folder")

            dataset_path = _validate_path(merged_folder, "merged_folder")
            if not dataset_path:
                return None, None

            print("DEBUG: mode merge actif")

            return _build_result(dataset_path, filename)

        # =========================
        # MODE 3 : SEPARATE
        # =========================
        elif self.import_mode == "without_dataset_separate":
            print(f"DEBUG: image_data keys = {list(image_data.keys())}")

            # --- CAS 1 : original_folder ---
            folder_name = image_data.get("original_folder")

            if isinstance(folder_name, str) and folder_name:
                print(f"DEBUG: original_folder = {folder_name}")

                dataset_path = _validate_path(
                    self.datasets_config.get(folder_name),
                    f"original_folder '{folder_name}'"
                )

                if dataset_path:
                    return _build_result(dataset_path, filename)

            else:
                print("DEBUG: original_folder absent ou invalide")

        # =========================
        # MODE INVALIDE
        # =========================
        else:
            print(f"DEBUG: import_mode invalide: {self.import_mode}")
            return None, None

class AdvancedImportDialog(QDialog):
    """Boîte de dialogue pour l'importation avancée"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Importation Avancée")
        self.setModal(True)
        self.resize(600, 500)
        
        self.file_path = None
        self.import_mode = None
        self.datasets_config = {}
        self.dynamic_config_layout = None  # Initialiser le layout dynamique
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout()
        
        # Sélection du fichier
        file_group = QGroupBox("1. Sélection du fichier JSON")
        file_layout = QHBoxLayout()
        
        self.file_label = QLabel("Aucun fichier sélectionné")
        self.browse_button = QPushButton("Parcourir...")
        self.browse_button.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.browse_button)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Mode d'importation
        mode_group = QGroupBox("2. Mode d'importation")
        mode_layout = QVBoxLayout()
        
        self.mode_group = QButtonGroup()
        
        self.with_dataset_radio = QRadioButton("Avec informations de dataset")
        self.without_dataset_radio = QRadioButton("Sans informations de dataset")
        self.with_dataset_radio.toggled.connect(self.on_mode_changed)
        self.without_dataset_radio.toggled.connect(self.on_mode_changed)
        
        mode_layout.addWidget(self.with_dataset_radio)
        mode_layout.addWidget(self.without_dataset_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Configuration des datasets (conteneur pour le widget actuel)
        self.config_group = QGroupBox("3. Configuration des datasets")
        self.config_layout = QVBoxLayout()
        self.config_group.setLayout(self.config_layout)
        self.config_group.setEnabled(False)
        layout.addWidget(self.config_group)
        
        # Zone de log
        log_group = QGroupBox("4. Progression")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Boutons
        button_layout = QHBoxLayout()
        
        self.import_button = QPushButton("Importer")
        self.import_button.clicked.connect(self.start_import)
        self.import_button.setEnabled(False)
        
        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def browse_file(self):
        """Parcourt pour sélectionner un fichier JSON"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner un fichier JSON", "", "Fichiers JSON (*.json)"
        )
        
        if file_path:
            self.file_path = file_path
            self.file_label.setText(Path(file_path).name)
            self.analyze_file()
    
    def analyze_file(self):
        """Analyse le fichier pour déterminer s'il contient des datasets"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Vérifier si les images ont des informations de dataset
            has_dataset_info = any(
                "dataset" in image_data 
                for filename, image_data in data.items() 
                if filename not in ["export_info", "metadata"]
            )
            
            if has_dataset_info:
                self.with_dataset_radio.setChecked(True)
                self.log_text.append("✅ Fichier détecté: contient des informations de dataset")
            else:
                self.without_dataset_radio.setChecked(True)
                self.log_text.append("ℹ️ Fichier détecté: ne contient pas d'informations de dataset")
            
            self.config_group.setEnabled(True)
            self.import_button.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'analyse du fichier: {e}")
    
    def on_mode_changed(self):
        """Gère le changement de mode d'importation"""
        if not self.file_path:
            return
        
        # Remplacer complètement le widget de configuration
        self.replace_config_widget()
    
    def replace_config_widget(self):
        """Remplace complètement le widget de configuration"""
        # Supprimer l'ancien widget s'il existe
        if hasattr(self, 'current_config_widget'):
            self.config_layout.removeWidget(self.current_config_widget)
            self.current_config_widget.deleteLater()
        
        # Créer le nouveau widget selon le mode
        if self.with_dataset_radio.isChecked():
            from .WithDatasetWidget import WithDatasetWidget
            self.current_config_widget = WithDatasetWidget(self.file_path, self)
            self.import_mode = "with_dataset"
        elif self.without_dataset_radio.isChecked():
            from .WithoutDatasetWidget import WithoutDatasetWidget
            self.current_config_widget = WithoutDatasetWidget(self)
            # Le mode sera déterminé par le widget lui-même
            self.import_mode = self.current_config_widget.get_import_mode()
        else:
            return
        
        # Connecter les signaux
        if hasattr(self.current_config_widget, 'dataset_config_changed'):
            self.current_config_widget.dataset_config_changed.connect(self.on_dataset_config_changed)
        if hasattr(self.current_config_widget, 'config_changed'):
            self.current_config_widget.config_changed.connect(self.on_config_changed)
        if hasattr(self.current_config_widget, 'validation_changed'):
            self.current_config_widget.validation_changed.connect(self.on_validation_changed)
        
        # Ajouter le nouveau widget
        self.config_layout.addWidget(self.current_config_widget)
    
    def on_dataset_config_changed(self, config):
        """Gère le changement de configuration de datasets"""
        self.datasets_config = config
    
    def on_config_changed(self, config):
        """Gère le changement de configuration"""
        self.datasets_config = config
    
    def on_validation_changed(self, is_valid):
        """Gère le changement de validation"""
        self.import_button.setEnabled(is_valid)
    
    def start_import(self):
        """Démarre l'importation"""
        if not self.validate_config():
            return
        
        # Récupérer le mode actuel depuis le widget
        if hasattr(self.current_config_widget, 'get_import_mode'):
            current_mode = self.current_config_widget.get_import_mode()
            print(f"DEBUG: Mode récupéré du widget: {current_mode}")
        else:
            current_mode = self.import_mode
            print(f"DEBUG: Mode par défaut: {current_mode}")
        
        # La configuration est déjà dans self.datasets_config grâce aux signaux
        
        # Désactiver les contrôles
        self.import_button.setEnabled(False)
        
        # Démarrer le thread d'importation
        self.worker = ImportWorkerThread(self.file_path, current_mode, self.datasets_config)
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.finished.connect(self.on_import_finished)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.start()
    
    def validate_config(self):
        """Valide la configuration actuelle"""
        if hasattr(self, 'current_config_widget'):
            return self.current_config_widget.is_valid()
        return False
    
    def on_progress_updated(self, message):
        """Met à jour la progression"""
        self.log_text.append(message)
    
    def on_import_finished(self, success_count, total_count):
        """Gère la fin de l'importation"""
        self.log_text.append(f"\n✅ Importation terminée: {success_count}/{total_count} images importées")
        
        QMessageBox.information(
            self, 
            "Importation terminée", 
            f"{success_count}/{total_count} images ont été importées avec succès."
        )
        
        self.accept()
    
    def on_error_occurred(self, error_message):
        """Gère les erreurs"""
        self.log_text.append(f"❌ {error_message}")

def show_advanced_import_dialog(parent=None) -> int:
    """Affiche la boîte de dialogue d'importation avancée"""
    dialog = AdvancedImportDialog(parent)
    return dialog.exec()
