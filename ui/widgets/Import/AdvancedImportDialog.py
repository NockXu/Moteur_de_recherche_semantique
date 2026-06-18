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

from ui.utils.i18n import tr
from ui.widgets.Import.import_service import ImportService
from ui.widgets.Import.import_runner import ImportRunner
from ui.widgets.Import.WithDataset.WithDatasetController import WithDatasetController
from ui.widgets.Import.WithoutDataset.WithoutDatasetController import WithoutDatasetController

from common.Image_Classes.ImageRepository import ImageRepository
from database.DbService import DbService


class AdvancedImportDialog(QDialog):
    """Boîte de dialogue d'import propre (UI + orchestration uniquement)"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.image_repository = ImageRepository(DbService().sqlite, DbService().faiss)
        self.file_path = None
        self.current_config_widget = None
        self.runner = None
        self.detected_datasets = set()

        self.with_dataset_controller : WithDatasetController = None
        self.without_dataset_controller : WithoutDatasetController = None

        self.setWindowTitle(tr("Importation Avancée"))
        self.setModal(True)
        self.resize(600, 500)

        self.setup_ui()

    # -------------------------
    # UI
    # -------------------------
    def setup_ui(self):
        layout = QVBoxLayout()

        # FILE
        file_group = QGroupBox(tr("1. Fichier JSON"))
        file_layout = QHBoxLayout()

        self.file_label = QLabel(tr("Aucun fichier sélectionné"))
        self.browse_button = QPushButton(tr("Parcourir..."))
        self.browse_button.clicked.connect(self.browse_file)

        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.browse_button)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # MODE
        mode_group = QGroupBox(tr("2. Mode"))
        mode_layout = QVBoxLayout()

        self.mode_group = QButtonGroup()

        self.with_dataset_radio = QRadioButton(tr("Avec dataset"))
        self.without_dataset_radio = QRadioButton(tr("Sans dataset"))

        self.with_dataset_radio.toggled.connect(self.on_mode_changed)
        self.without_dataset_radio.toggled.connect(self.on_mode_changed)

        mode_layout.addWidget(self.with_dataset_radio)
        mode_layout.addWidget(self.without_dataset_radio)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # CONFIG AREA (widget dynamique)
        self.config_group = QGroupBox(tr("3. Configuration"))
        self.config_layout = QVBoxLayout()
        self.config_group.setLayout(self.config_layout)
        self.config_group.setEnabled(False)
        layout.addWidget(self.config_group)

        # LOG
        log_group = QGroupBox(tr("4. Log"))
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # BUTTONS
        btn_layout = QHBoxLayout()

        self.import_btn = QPushButton(tr("Importer"))
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.start_import)

        self.cancel_btn = QPushButton(tr("Annuler"))
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
            tr("Sélectionner un fichier JSON"),
            "",
            "JSON (*.json)"
        )

        if file_path:
            self.file_path = file_path
            self.file_label.setText(Path(file_path).name)
            self.analyze_file()

    def analyze_file(self):
        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)

            # Extraire les noms de datasets uniques
            self.detected_datasets = set()
            for k, img in data.items():
                if k not in ["metadata", "export_info", "datasets"] and "dataset" in img:
                    self.detected_datasets.add(img["dataset"])

            has_dataset = bool(self.detected_datasets)

            if has_dataset:
                self.with_dataset_radio.setChecked(True)
                self.log(f"{tr("Datasets détectés")}: {', '.join(self.detected_datasets)}")
            else:
                self.without_dataset_radio.setChecked(True)
                self.log(f"{tr("Sans dataset détecté")}")

            self.config_group.setEnabled(True)
            self.import_btn.setEnabled(True)

        except Exception as e:
            self.log(f"{tr("Erreur analyse")}: {e}")

    # -------------------------
    # MODE / WIDGET
    # -------------------------
    def on_mode_changed(self):
        if not self.file_path:
            return

        self.replace_config_widget()

    def replace_config_widget(self):
        # cleanup ancien widget
        if self.current_config_widget:
            self.config_layout.removeWidget(self.current_config_widget)
            self.current_config_widget.deleteLater()
            self.current_config_widget = None
            self.with_dataset_controller = None
            self.without_dataset_controller = None

        # créer nouveau widget selon mode
        if self.with_dataset_radio.isChecked():
            self.with_dataset_controller = WithDatasetController()
            # Ajouter les champs pour chaque dataset détecté
            for dataset_name in self.detected_datasets:
                self.with_dataset_controller.view.add_dataset_field(dataset_name)
            self.current_config_widget = self.with_dataset_controller.view
            self.current_controller = self.with_dataset_controller

        elif self.without_dataset_radio.isChecked():
            self.without_dataset_controller = WithoutDatasetController()
            self.current_config_widget = self.without_dataset_controller.view
            self.current_controller = self.without_dataset_controller

        else:
            return

        # AJOUT correct
        self.config_layout.addWidget(self.current_config_widget)

    # -------------------------
    # IMPORT
    # -------------------------
    def start_import(self):
        if not self.validate():
            return

        if not self.current_config_widget:
            return
            
        valid = self.current_controller.is_valid()
        config = self.current_controller.get_all()
        mode = self.current_controller.get_mode()

        if not valid:
            self.log(f"{tr("Configuration invalide")}")
            return

        service = ImportService(config, mode)
        self.runner = ImportRunner(service)

        self.log_text.clear()
        self.import_btn.setEnabled(False)

        self.runner.run(
            file_path=self.file_path,
            on_progress=self.log,
            on_done=self.on_done,
            on_error=self.log
        )

    # -------------------------
    # VALIDATION
    # -------------------------
    def validate(self):
        return (
            self.file_path is not None
            and self.current_controller is not None
            and self.current_controller.is_valid()
        )

    # -------------------------
    # CALLBACKS
    # -------------------------
    def log(self, msg):
        self.log_text.append(str(msg))

    def on_done(self, success, total):
        self.log(f"{tr("Terminé")}: {success}/{total}")
        self.import_btn.setEnabled(True)

    def cancel_import(self):
        if self.runner:
            self.runner.cancel()
            self.log(f"{tr("annulé")}")
            
    def _on_language_changed(self, lang_code: str = None) -> None:
        # --- STATIC UI ---
        self.setWindowTitle(tr("Importation Avancée"))

        self.file_group.setTitle(tr("1. Fichier JSON"))
        self.mode_group.setTitle(tr("2. Mode"))
        self.config_group.setTitle(tr("3. Configuration"))
        self.log_group.setTitle(tr("4. Log"))

        self.file_label.setText(tr("Aucun fichier sélectionné"))
        self.browse_button.setText(tr("Parcourir..."))
        self.import_btn.setText(tr("Importer"))
        self.cancel_btn.setText(tr("Annuler"))

        # --- LOG TEXT (optionnel) ---
        self.log_text.setPlaceholderText(tr("Log en cours..."))

        # --- DYNAMIC UI ---
        if self.with_dataset_controller:
            self.with_dataset_controller.on_language_changed()

        if self.without_dataset_controller:
            self.without_dataset_controller.on_language_changed()


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = AdvancedImportDialog()
    dialog.show()
    sys.exit(app.exec())
