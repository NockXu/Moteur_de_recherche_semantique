from typing import Optional, TypedDict
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

class WithoutDatasetStatus:
    EXISTS = True
    NOT_EXISTS = False

class WithoutDatasetData(TypedDict):
    name: str
    path: str
    status: WithoutDatasetStatus | None

class WithoutDatasetConfig(TypedDict):
    name: QLineEdit
    path: QLineEdit
    status: QLabel