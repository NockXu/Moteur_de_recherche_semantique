from pathlib import Path
from typing import Optional, Tuple

from .base_strategy import BaseImportStrategy


class SeparateStrategy(BaseImportStrategy):

    def __init__(self, datasets_config: dict):
        self.datasets_config = {
            k: Path(v) for k, v in datasets_config.items()
        }

    def resolve(self, filename: str, data: dict) -> Tuple[Optional[str], Optional[Path]]:
        dataset_name = data.get("dataset") or data.get("original_folder")

        if not dataset_name:
            return None, None

        base_path = self.datasets_config.get(dataset_name)
        if not base_path:
            return None, None

        return dataset_name, base_path / filename