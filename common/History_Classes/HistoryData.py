from __future__ import annotations
from typing import List, Optional
from common.WeightCalculator import WeightSystem

class HistoryData:

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
        return self.query == ""

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "threshold": self.threshold,
            "w_const": self.w_const,
            "w_expr": str(self.w_expr)
        }

    @classmethod
    def from_dict(cls, data: dict) -> HistoryData:
        return cls(
            query=data.get("query", ""),
            threshold=data.get("threshold", 0.5),
            w_const=data.get("w_const", 1.0),
            w_expr=WeightSystem(data.get("w_expr", "const"))
        )

    def __str__(self) -> str:
        return f"{self.query}, {self.threshold}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HistoryData):
            return False
        return (
            self.query == other.query
        )

if __name__ == "__main__":
    un = HistoryData("Un chat", 0.5)
    deux = HistoryData("Un chat", 0.5)
    print(un == deux)