from pathlib import Path
from typing import Optional, Tuple

from .base_strategy import BaseImportStrategy


class MergeStrategy(BaseImportStrategy):

    def __init__(self, merged_folder: str):
        self.merged_folder = Path(merged_folder)

    def resolve(self, filename: str, data: dict) -> Tuple[Optional[str], Optional[Path]]:
        if not self.merged_folder:
            return None, None

        return "merged", self.merged_folder / filename