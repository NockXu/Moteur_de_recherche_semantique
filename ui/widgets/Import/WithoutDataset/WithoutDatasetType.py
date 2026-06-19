from typing import Optional, TypedDict
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

class WithoutDatasetStatus:
    """Status enumeration constants tracking dataset presence within the data layer.

    Attributes:
        EXISTS (bool): Indicates the target dataset already exists (enables automatic merging).
        NOT_EXISTS (bool): Indicates a missing dataset entry (triggers automatic initialization).
    """
    EXISTS = True
    NOT_EXISTS = False

class WithoutDatasetData(TypedDict):
    """Data dictionary container structure storing clean alphanumeric data properties.

    Attributes:
        name (str): The logical catalog identification designation.
        path (str): The structural storage folder absolute path context string.
        status (WithoutDatasetStatus | None): Calculated presence flag state tracking cache.
    """
    name: str
    path: str
    status: WithoutDatasetStatus | None

class WithoutDatasetConfig(TypedDict):
    """Interface widget container structure tracking active input elements per collection row.

    Attributes:
        name (QLineEdit): Input text row targeting user tracking label entries.
        path (QLineEdit): Path text string presentation line component.
        status (QLabel): Reactive contextual metadata notification label object.
    """
    name: QLineEdit
    path: QLineEdit
    status: QLabel