from typing import List

from .WithDatasetModel import WithDatasetModel
from .DatasetType import DatasetConfig
from .WithDatasetView import WithDatasetView
from ui.widgets.Import.DatasetConfigDataType import DatasetConfigData

class WithDatasetController:
    """Controller orchestrating configuration workflows when importing pre-partitioned dataset catalogs.

    Coordinates path matching, updates presence cache lookups via model layers, and performs validation 
    checks before packaging configured items for background processors.
    """
    
    def __init__(self):
        self.model = WithDatasetModel()
        self.view = WithDatasetView()
        
        self.view.dataset_path_changed.connect(self.on_dataset_path_changed)
        
    def on_dataset_path_changed(self, config: DatasetConfig, name: str):
        """Update interface validation components when individual folder path definitions change.

        Args:
            config (DatasetConfig): Dictionary mapping GUI row entry line inputs and status indicators.
            name (str): Alphanumeric identification key of the target dataset group.

        """
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
        """Compile and format all configured layout row options into structured schema payloads.

        Returns:
            list[DatasetConfigData]: Explicit mappings tracking names, absolute disk directories, and statuses.

        """
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
        """Verify form execution requirements by ensuring every displayed entry field contains text input.

        Returns:
            bool: True if validation assertions clear across all assigned components.

        """
        for name, config in self.view.datasets_config.items():
            if config["line_edit"].text() == "":
                return False
        return True

    def get_mode(self) -> str:
        """Fetch the designated structural file classification mode keyword.

        Returns:
            str: Identity string specifying the data processing workflow context.

        """
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