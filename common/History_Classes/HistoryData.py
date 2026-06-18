from __future__ import annotations
from typing import List, Optional
from common.WeightCalculator import WeightSystem

class HistoryData:
    """Data class representing a search history entry with associated parameters.

    This class encapsulates search configuration data, including the text query,
    similarity threshold, and weight system configurations. It provides utility
    methods for serialization and comparison.

    Args:
        query (str):
            The search query text. Defaults to an empty string.
        threshold (float):
            The similarity threshold for filtering results. Defaults to 0.5.
        w_const (float):
            A constant weight parameter. Defaults to 1.0.
        w_expr (WeightSystem):
            The weight system configuration. Defaults to WeightSystem("const").

    """

    def __init__(
        self,
        query: str = "",
        threshold: float = 0.5,
        w_const: float = 1,
        w_expr: WeightSystem = WeightSystem("const")
    ) -> None:
        self.query = query
        self.threshold = threshold
        self.w_const = w_const
        self.w_expr = w_expr

    @property
    def is_empty(self) -> bool:
        """Check if the history entry has an empty query.

        Returns:
            True if the query is an empty string, False otherwise.

        """
        return self.query == ""

    def to_dict(self) -> dict:
        """Serialize the history data into a dictionary.

        Returns:
            A dictionary representation of the history entry, with the weight
            system serialized as a string.

        """
        return {
            "query": self.query,
            "threshold": self.threshold,
            "w_const": self.w_const,
            "w_expr": str(self.w_expr)
        }

    @classmethod
    def from_dict(cls, data: dict) -> HistoryData:
        """Create a HistoryData instance from a dictionary.

        Args:
            data (dict):
                A dictionary containing the history entry parameters.

        Returns:
            A new HistoryData instance populated with the dictionary values.

        """
        return cls(
            query=data.get("query", ""),
            threshold=data.get("threshold", 0.5),
            w_const=data.get("w_const", 1.0),
            w_expr=WeightSystem(data.get("w_expr", "const"))
        )

    def __str__(self) -> str:
        """Get a string representation of the history entry.

        Returns:
            A string combining the query and the threshold.

        """
        return f"{self.query}, {self.threshold}"

    def __eq__(self, other: object) -> bool:
        """Compare two HistoryData instances for equality based on their query.

        Returns:
            True if the other object is a HistoryData instance and has the
            same query, False otherwise.

        """
        if not isinstance(other, HistoryData):
            return False
        return (
            self.query == other.query
        )

if __name__ == "__main__":
    un = HistoryData("Un chat", 0.5)
    deux = HistoryData("Un chat", 0.5)
    print(un == deux)