from dataclasses import dataclass, field
from typing import List


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)

    def add_error(self, error: str):
        self.errors.append(error)
        self.failed += 1