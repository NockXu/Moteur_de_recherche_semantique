from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List


@dataclass
class ImportImageData:
    filename: str
    path: Optional[Path]
    dataset: Optional[str]
    description: str = ""
    keywords: List[str] = None
    embedding: List[float] = None
    id: Optional[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.embedding is None:
            self.embedding = []