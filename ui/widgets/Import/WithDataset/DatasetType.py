
from typing import Optional, TypedDict
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

class DatasetStatus:
    EXISTS = True
    NOT_EXISTS = False

class DatasetData(TypedDict):
    dataset_name: str
    status: Optional[DatasetStatus]

class DatasetConfig(TypedDict):
    line_edit: QLineEdit
    status_label: QLabel
    