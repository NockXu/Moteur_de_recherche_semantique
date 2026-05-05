from typing import List

from .WithDatasetModel import WithDatasetModel
from .DatasetType import DatasetConfig, DatasetsData
from .WithDatasetView import WithDatasetView

class WithDatasetController:
    def __init__(self):
        self.model = WithDatasetModel()
        self.view = WithDatasetView()
        
        self.view.dataset_path_changed.connect(self.on_dataset_path_changed)
        
    def on_dataset_path_changed(self, config: DatasetConfig, name: str):
        """Gère le changement de chemin d'un dataset"""
        
        data = self.model.update(name)
        if data:
            self.view.exist(name, data["status"])

        if __name__ == "__main__":
            print(self.get_all())

    def get_all(self) -> List[DatasetsData]:
        datasets_data = []

        for name, config in self.view.datasets_config.items():
            if name in self.model.datasets_data:
                status = self.model.datasets_data[name]["status"]
            else:
                status = "NOT_EXISTS"

            path = config["line_edit"].text()
            if path:
                datasets_data.append(DatasetsData(path=path, name=name, status=status))

        return datasets_data


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    controller = WithDatasetController()
    controller.view.show()
    controller.view.add_dataset_field("dataset1")
    controller.view.add_dataset_field("dataset2")
    sys.exit(app.exec())