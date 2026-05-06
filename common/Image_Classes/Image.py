from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union
from datetime import datetime
from enum import Enum
import os
import sys
import hashlib

# Ajouter la racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.Dataset_Classes import Dataset


class ProcessingStatus(Enum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


class Image:
    """
    Modèle métier pur (aucune logique BDD ici)
    """

    def __init__(
        self,
        path: Union[str, Path],
        dataset: Dataset,
        name: str = None,
        score: float = 0.0,
        status: ProcessingStatus = ProcessingStatus.NOT_STARTED,
        description: str = "",
        keywords: Optional[List[str]] = None,
        embedding: Optional[List[float]] = None,
        error_message: str = "",
        processing_start_time: Optional[datetime] = None,
        processing_end_time: Optional[datetime] = None,
        image_id: Optional[str] = None,
    ):
        self.path = Path(path)

        # dataset = data simple, PAS objet DB
        self.dataset_id = dataset.id if dataset else None
        self.dataset_name = dataset.name if dataset else None

        self.score = float(score)
        self.status = status
        self.description = description
        self.keywords = keywords or []
        self.embedding = embedding or []
        self.error_message = error_message

        self.processing_start_time = processing_start_time
        self.processing_end_time = processing_end_time

        # ID stable
        if image_id:
            self.id = image_id
        else:
            self.id = "img_" + hashlib.md5(str(self.path).encode()).hexdigest()[:16]

        if name:
            self.name = name
        else:
            self.name = self.path.name
        self.stem = self.path.stem
        self.suffix = self.path.suffix.lower()

        try:
            self.size = self.path.stat().st_size
        except Exception:
            self.size = 0

    # =========================
    # SERIALIZATION
    # =========================

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "path": str(self.path),
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "name": self.name,
            "score": self.score,
            "status": self.status.value,
            "description": self.description,
            "keywords": self.keywords,
            "embedding": self.embedding,
            "error_message": self.error_message,
            "processing_start_time": self.processing_start_time.isoformat() if self.processing_start_time else None,
            "processing_end_time": self.processing_end_time.isoformat() if self.processing_end_time else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Image":
        start = datetime.fromisoformat(data["processing_start_time"]) if data.get("processing_start_time") else None
        end = datetime.fromisoformat(data["processing_end_time"]) if data.get("processing_end_time") else None

        return cls(
            path=data["path"],
            dataset_id=data["dataset_id"],
            dataset_name=data.get("dataset_name"),
            score=data.get("score", 0.0),
            status=ProcessingStatus(data.get("status", "not_started")),
            description=data.get("description", ""),
            keywords=data.get("keywords", []),
            embedding=data.get("embedding", []),
            error_message=data.get("error_message", ""),
            processing_start_time=start,
            processing_end_time=end,
            image_id=data.get("id"),
        )

    # =========================
    # DERIVED PROPS
    # =========================

    @property
    def is_processed(self) -> bool:
        return self.status == ProcessingStatus.COMPLETED

    @property
    def has_error(self) -> bool:
        return self.status == ProcessingStatus.ERROR

    @property
    def is_processing(self) -> bool:
        return self.status == ProcessingStatus.IN_PROGRESS

    # =========================
    # UTILS
    # =========================

    def copy(self) -> "Image":
        return Image(
            path=self.path,
            dataset_id=self.dataset_id,
            dataset_name=self.dataset_name,
            score=self.score,
            status=self.status,
            description=self.description,
            keywords=self.keywords.copy(),
            embedding=self.embedding.copy(),
            error_message=self.error_message,
            processing_start_time=self.processing_start_time,
            processing_end_time=self.processing_end_time,
            image_id=self.id,
        )

    def __eq__(self, other) -> bool:
        return isinstance(other, Image) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)