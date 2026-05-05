from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple


class BaseImportStrategy(ABC):

    @abstractmethod
    def resolve(self, filename: str, data: dict) -> Tuple[Optional[str], Optional[Path]]:
        """
        Retourne (dataset_name, final_path)
        """
        pass