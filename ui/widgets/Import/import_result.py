from dataclasses import dataclass, field
from typing import List


@dataclass
class ImportResult:
    """Data container tracking execution performance metrics for data import operations.

    Tracks calculation run states, counting items processed successfully versus failures 
    while preserving exceptional historical trace logs.

    Attributes:
        success (int):
            Counter tracking records processed without runtime errors. Defaults to 0.
        failed (int):
            Counter tracking processing attempts that triggered failures. Defaults to 0.
        errors (list[str]):
            Historical text catalog preserving localized error logs. Defaults to an empty list factory.

    """
    success: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def add_error(self, error: str):
        """Register a runtime tracking error trace string and increment failure metrics.

        Args:
            error (str):
                The description or traceback text detailing the processing issue encountered.

        """
        self.errors.append(error)
        self.failed += 1