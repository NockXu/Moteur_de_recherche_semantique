from typing import List

from .WithDatasetModel import WithDatasetModel
from .DatasetType import DatasetConfig
from .WithDatasetView import WithDatasetView
from ui.widgets.Import.DatasetConfigDataType import DatasetConfigData

class WithDatasetController:
    def __init__(self):
        self.model = WithDatasetModel()
        self.view = WithDatasetView()
        
        self.view.dataset_path_changed.connect(self.on_dataset_path_changed)
        
    def on_dataset_path_changed(self, config: DatasetConfig, name: str):
        """Gère le changement de chemin d'un dataset"""
        if config["line_edit"].text() == "":
            config["status_label"].setText("")
            config["status_label"].hide()
            return

        data = self.model.update(name)
        if data:
            self.view.exist(name, data["status"])

        if __name__ == "__main__":
            print(self.get_all())

    def get_all(self) -> list[DatasetConfigData]:
        datasets_data = []

        for name, config in self.view.datasets_config.items():
            if name in self.model.datasets_data:
                status = self.model.datasets_data[name]["status"]
            else:
                status = "NOT_EXISTS"

            path = config["line_edit"].text()
            if path:
                datasets_data.append(DatasetConfigData(path=path, name=name, status=status))

        return datasets_data

    def is_valid(self) -> bool:
        for name, config in self.view.datasets_config.items():
            if config["line_edit"].text() == "":
                return False
        return True

    def get_mode(self) -> str:
        return "with_dataset"


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    controller = WithDatasetController()
    controller.view.show()
    controller.view.add_dataset_field("dataset1")
    controller.view.add_dataset_field("dataset2")
    sys.exit(app.exec())