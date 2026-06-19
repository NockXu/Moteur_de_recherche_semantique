from PyQt6.QtWidgets import QLineEdit, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QFileDialog
from pathlib import Path
from typing import List

from .WithoutDatasetModel import WithoutDatasetModel
from .WithoutDatasetView import WithoutDatasetView
from .WithoutDatasetType import WithoutDatasetData, WithoutDatasetStatus
from ui.widgets.Import.DatasetConfigDataType import DatasetConfigData


class WithoutDatasetController:
    """Controller orchestrating datasets configuration when parsing manifests missing partition schemas.

    Manages dynamic form configurations, directory mapping synchronization loops, and tracks view
    state integrity flags before committing values onto model layers.
    """
    
    def __init__(self):
        self.view = WithoutDatasetView()
        self.model = WithoutDatasetModel()

        self.valid : bool = False

        # connexions
        self.view.mode_changed.connect(self.on_mode_changed)
        self.view.config_changed.connect(self.sync_model)

        # init
        self.on_mode_changed(self.view.get_mode())

    def get_all(self) -> list[DatasetConfigData]:
        """Compile and format all active directory parameters into structured config records.

        Returns:
            list[DatasetConfigData]: Explicit mappings tracking names, paths, and existence statuses.

        """
        datas : list[DatasetConfigData] = []
        for config in self.view.config:
            if config["name"].text() == "" or config["path"].text() == "":
                continue
            
            if config["status"].text() != "":
                if config["status"].text() == "✔ Dataset trouvé (fusion automatique)":
                    status = True
                else:
                    status = False
            else:
                status = False

            datas.append(DatasetConfigData(
                name=config["name"].text(),
                path=config["path"].text(),
                status=status
            ))

        return datas

    def is_valid(self) -> bool:
        """Fetch the current form completeness validation state.

        Returns:
            bool: True if input properties resolve matching layout rules correctly.

        """
        return self.valid

    def get_mode(self) -> str:
        """Fetch the tracking processing distribution mode set inside the model.

        Returns:
            str: Active operation structural mapping keyword.

        """
        return self.model.mode

    # ---------------- MODE ----------------

    def on_mode_changed(self, mode: str):
        """Update system processing schemas when targeting separate or nested dataset targets.

        Args:
            mode (str):
                View component classification tracking keyword string.

        """
        self.model.mode = "merge" if mode == "without_dataset_merge" else "separate"

        if self.model.mode == "merge":
            self.view.build_merge()
        else:
            self.view.build_separate()

    # ---------------- SYNC MODEL ----------------

    def sync_model(self):
        """Extract configurations from reactive view states and refresh tracked backend model metrics."""
        configs = self.view.config
        datas = []
        valid_configs = []
        
        # Si pas de configs, ne rien faire
        if not configs:
            return
        
        # Filtrer les configs valides et créer les données
        for config in configs:
            if config["name"].text() == "" or config["path"].text() == "":
                config["status"].setText("")
                config["status"].hide()
                self.valid = False
            try:
                name = config["name"].text().strip()
                path = config["path"].text().strip()
                
                # Ne créer des données que si nom et path sont valides
                if name and path:
                    data = WithoutDatasetData(
                        name=name,
                        path=path,
                        status=None
                    )
                    datas.append(data)
                    valid_configs.append(config)
            except RuntimeError:
                # Ignorer les configs dont les widgets ont été supprimés
                continue
            
        if datas:  # Ne mettre à jour que s'il y a des données valides
            self.model.update(datas)

            # Mettre à jour uniquement les configs valides
            for i, data in enumerate(datas):
                config = valid_configs[i]
                try:
                    if data["status"] == WithoutDatasetStatus.EXISTS:
                        config["status"].setText("✔ Dataset trouvé (fusion automatique)")
                        config["status"].setStyleSheet("color: #2e7d32; font-size: 11px;")  # vert propre
                        config["status"].show()
                    elif data["status"] == WithoutDatasetStatus.NOT_EXISTS:
                        config["status"].setText("✖ Dataset inexistant (création automatique)")
                        config["status"].setStyleSheet("color: #ed6c02; font-size: 11px;")  # orange lisible
                        config["status"].show()
                except RuntimeError:
                    # Ignorer si le widget a été supprimé entre temps
                    continue
            
            self.valid = True
        else:
            self.valid = False
            

    # ---------------- MERGE ----------------

    def browse_single(self, line_edit: QLineEdit):
        """Launch directory search prompts and push selected paths into input lines targets.

        Args:
            line_edit (QLineEdit):
                The interactive input field widget target instance being configured.

        """
        folder = QFileDialog.getExistingDirectory(self.view, "Choisir dossier")
        if folder:
            line_edit.setText(folder)
            self.sync_model()

    # ---------------- SEPARATE ----------------

    def add_folder(self):
        """Trigger row element append sequences inside the interactive viewport."""
        self.view.add_folder()

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    controller = WithoutDatasetController()
    controller.view.show()
    sys.exit(app.exec())
