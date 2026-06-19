
from typing import Optional, TypedDict
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

class DatasetStatus:
    """Status enumeration constants tracking dataset presence within the data storage layer.

    Attributes:
        EXISTS (bool): Indicates the target dataset already exists in the database.
        NOT_EXISTS (bool): Indicates a missing dataset entry that will require initialization.
    """
    EXISTS = True
    NOT_EXISTS = False

class DatasetData(TypedDict):
    """Data dictionary container structure storing dataset record configuration details.

    Attributes:
        dataset_name (str): The unique logical tracking label identifying the dataset group.
        status (DatasetStatus | None): Calculated presence flag state tracking cache.
    """
    dataset_name: str
    status: DatasetStatus | None

class DatasetConfig(TypedDict):
    """Interface widget container structure tracking active form input components per dataset row.

    Attributes:
        line_edit (QLineEdit): Input text box targeting file mapping locations.
        status_label (QLabel): Reactive text banner showing current processing state validations.
    """
    line_edit: QLineEdit
    status_label: QLabel
    