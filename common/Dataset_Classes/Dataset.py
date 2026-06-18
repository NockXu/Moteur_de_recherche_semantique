from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass(frozen=True)
class Dataset:
    """Represents a dataset entity.

    This class is used to store dataset data.

    Args:
        id: Dataset id
        name: Dataset name

    """

    id: int | None
    name: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the Dataset instance to a dictionary representation.

        Returns:
            Dictionary containing dataset fields (id and name).

        """
        return {
            "id": self.id,
            "name": self.name
        }