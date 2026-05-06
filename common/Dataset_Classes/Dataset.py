from dataclasses import dataclass

@dataclass(frozen=True)
class Dataset:
    id: int | None
    name: str

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }