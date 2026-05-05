import sys
import os
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QRadioButton,
    QButtonGroup, QGroupBox, QTextEdit
)
from PyQt6.QtCore import Qt

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ui.widget.import_bis.import_service import ImportService
from ui.widget.import_bis.import_runner import ImportRunner
from ui.widget.import_bis.strategies.merge_strategy import MergeStrategy
from ui.widget.import_bis.strategies.separate_strategy import SeparateStrategy
from ui.widget.import_bis.strategies.with_dataset_strategy import WithDatasetStrategy


class AdvancedImportDialog(QDialog):
    """Boîte de dialogue d'import propre (UI + orchestration uniquement)"""

    def __init__(self, image_repository, parent=None):
        super().__init__(parent)

        self.image_repository = image_repository
        self.file_path = None
        self.current_config_widget = None
        self.runner = None

        self.setWindowTitle("Importation Avancée")
        self.setModal(True)
        self.resize(600, 500)

        self.setup_ui()

    # -------------------------
    # UI
    # -------------------------
    def setup_ui(self):
        layout = QVBoxLayout()

        # FILE
        file_group = QGroupBox("1. Fichier JSON")
        file_layout = QHBoxLayout()

        self.file_label = QLabel("Aucun fichier sélectionné")
        self.browse_button = QPushButton("Parcourir...")
        self.browse_button.clicked.connect(self.browse_file)

        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.browse_button)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # MODE
        mode_group = QGroupBox("2. Mode")
        mode_layout = QVBoxLayout()

        self.mode_group = QButtonGroup()

        self.with_dataset_radio = QRadioButton("Avec dataset")
        self.without_dataset_radio = QRadioButton("Sans dataset")

        self.with_dataset_radio.toggled.connect(self.on_mode_changed)
        self.without_dataset_radio.toggled.connect(self.on_mode_changed)

        mode_layout.addWidget(self.with_dataset_radio)
        mode_layout.addWidget(self.without_dataset_radio)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # CONFIG AREA (widget dynamique)
        self.config_group = QGroupBox("3. Configuration")
        self.config_layout = QVBoxLayout()
        self.config_group.setLayout(self.config_layout)
        self.config_group.setEnabled(False)
        layout.addWidget(self.config_group)

        # LOG
        log_group = QGroupBox("4. Log")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # BUTTONS
        btn_layout = QHBoxLayout()

        self.import_btn = QPushButton("Importer")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.start_import)

        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    # -------------------------
    # FILE
    # -------------------------
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier JSON",
            "",
            "JSON (*.json)"
        )

        if file_path:
            self.file_path = file_path
            self.file_label.setText(Path(file_path).name)
            self.analyze_file()

    def analyze_file(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            has_dataset = any(
                "dataset" in img
                for k, img in data.items()
                if k not in ["metadata", "export_info"]
            )

            if has_dataset:
                self.with_dataset_radio.setChecked(True)
                self.log("Dataset détecté")
            else:
                self.without_dataset_radio.setChecked(True)
                self.log("Sans dataset détecté")

            self.config_group.setEnabled(True)
            self.import_btn.setEnabled(True)

        except Exception as e:
            self.log(f"Erreur analyse: {e}")

    # -------------------------
    # MODE / WIDGET
    # -------------------------
    def on_mode_changed(self):
        if not self.file_path:
            return

        self.replace_config_widget()

    def replace_config_widget(self):
        if self.current_config_widget:
            self.config_layout.removeWidget(self.current_config_widget)
            self.current_config_widget.deleteLater()
            self.current_config_widget = None

        if self.with_dataset_radio.isChecked():
            from .WithDatasetWidget import WithDatasetWidget
            self.current_config_widget = WithDatasetWidget(self.file_path)

        elif self.without_dataset_radio.isChecked():
            from .WithoutDatasetWidget import WithoutDatasetWidget
            self.current_config_widget = WithoutDatasetWidget()

        else:
            return

        self.config_layout.addWidget(self.current_config_widget)

    # -------------------------
    # IMPORT
    # -------------------------
    def start_import(self):
        if not self.validate():
            return

        mode = self.current_config_widget.get_import_mode()
        config = self.current_config_widget.get_config()

        strategy = self.build_strategy(mode, config)
        if not strategy:
            self.log("❌ Stratégie invalide")
            return

        service = ImportService(self.image_repository, strategy)
        self.runner = ImportRunner(service)

        self.log_text.clear()
        self.import_btn.setEnabled(False)

        self.runner.run(
            file_path=self.file_path,
            on_progress=self.log,
            on_done=self.on_done,
            on_error=self.log
        )

    def build_strategy(self, mode, config):
        if mode == "with_dataset":
            return WithDatasetStrategy(config)

        if mode == "without_dataset_merge":
            return MergeStrategy(config.get("merged_folder"))

        if mode == "without_dataset_separate":
            return SeparateStrategy(config)

        return None

    # -------------------------
    # VALIDATION
    # -------------------------
    def validate(self):
        return (
            self.file_path is not None
            and self.current_config_widget is not None
            and self.current_config_widget.is_valid()
        )

    # -------------------------
    # CALLBACKS
    # -------------------------
    def log(self, msg):
        self.log_text.append(str(msg))

    def on_done(self, success, total):
        self.log(f"✅ Terminé: {success}/{total}")
        self.import_btn.setEnabled(True)

    def cancel_import(self):
        if self.runner:
            self.runner.cancel()
            self.log("⛔ annulé")