from PyQt6.QtWidgets import QLineEdit, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QFileDialog
from pathlib import Path
from typing import List

from .WithoutDatasetModel import WithoutDatasetModel
from .WithoutDatasetView import WithoutDatasetView
from .WithoutDatasetType import WithoutDatasetData, WithoutDatasetConfig, WithoutDatasetStatus


class WithoutDatasetController:
    def __init__(self):
        self.view = WithoutDatasetView()
        self.model = WithoutDatasetModel()

        self.folder_configs = []  # uniquement côté UI (widgets Qt)

        # connexions
        self.view.mode_changed.connect(self.on_mode_changed)
        self.view.config_changed.connect(self.sync_model)

        # init
        self.on_mode_changed(self.view.get_mode())

    # ---------------- MODE ----------------

    def on_mode_changed(self, mode: str):
        self.model.mode = "merge" if mode == "without_dataset_merge" else "separate"

        if self.model.mode == "merge":
            self.view.build_merge()
        else:
            self.view.build_separate()

    # ---------------- SYNC MODEL ----------------

    def sync_model(self):
        """Met à jour le model depuis la vue"""
        configs = self.view.config
        datas = []
        valid_configs = []
        
        # Si pas de configs, ne rien faire
        if not configs:
            return
        
        # Filtrer les configs valides et créer les données
        for config in configs:
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
                    elif data["status"] == WithoutDatasetStatus.NOT_EXISTS:
                        config["status"].setText("✖ Dataset inexistant (création automatique)")
                        config["status"].setStyleSheet("color: #ed6c02; font-size: 11px;")  # orange lisible
                except RuntimeError:
                    # Ignorer si le widget a été supprimé entre temps
                    continue
            

    # ---------------- MERGE ----------------

    def browse_single(self, line_edit: QLineEdit):
        folder = QFileDialog.getExistingDirectory(self.view, "Choisir dossier")
        if folder:
            line_edit.setText(folder)
            self.sync_model()

    # ---------------- SEPARATE ----------------

    def add_folder(self):
        self.view.add_folder()

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    controller = WithoutDatasetController()
    controller.view.show()
    sys.exit(app.exec())
