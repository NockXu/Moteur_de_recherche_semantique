from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
import os
import sys
import hashlib
from PIL import Image as PILImage

from common.Dataset_Classes.Dataset import Dataset

class ProcessingStatus(Enum):
    """
    Represents the status of a processing task.

    This enum is used to track the lifecycle state of a process,
    from not started to completion or failure.
    """

    NOT_STARTED = "not_started"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"

from typing import Optional, List, Union
from pathlib import Path
from datetime import datetime
import hashlib

class Image:
    """
    Class representing an image.

    This class does not contains database logic.
    It is used across the application for processing, indexing and analysis.

    Args:
        path (Union[str, Path]):
            Path to the image file.
        dataset (Dataset):
            Dataset to which the image belongs.
        name (Optional[str]):
            Name of the image.
        score (float):
            Score of the image.
        status (ProcessingStatus):
            Status of the image.
        description (str):
            Description of the image.
        keywords (Optional[List[str]]):
            Keywords of the image.
        embedding (Optional[List[float]]):
            Embedding of the image.
        error_message (str):
            Error message of the image.
        processing_start_time (Optional[datetime]):
            Processing start time of the image.
        processing_end_time (Optional[datetime]):
            Processing end time of the image.
        image_id (Optional[str]): 
            ID of the image.
    """

    def __init__(
        self,
        path: Union[str, Path],
        dataset: Dataset,
        name: Optional[str] = None,
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

        # Dataset reference
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

        # Stable ID (will not be used in bdd)
        self.id = image_id or (
            "img_" + hashlib.md5(str(self.path).encode()).hexdigest()[:16]
        )

        # File metadata
        self.name = name or self.path.name
        self.title = self.name
        self.stem = self.path.stem
        self.suffix = self.path.suffix.lower()

        try:
            self.size = self.path.stat().st_size
        except Exception:
            self.size = 0

        self._sam3_results = None
        self.prompts : Dict[str, float] = {}
        # Image dimensions (for layout system)
        self.width = 0
        self.height = 0
        self.aspect_ratio = 1.0

        self._load_image_metadata()

    def _load_image_metadata(self):
        try:
            with PILImage.open(self.path) as img:
                self.width, self.height = img.size
                self.aspect_ratio = (
                    self.width / self.height if self.height else 1.0
                )
        except Exception as e:
            self.width = 0
            self.height = 0
            self.aspect_ratio = 1.0

    # =========================
    # SERIALIZATION
    # =========================

    def to_dict(self) -> dict:
        """
        Convert the Image object into a JSON-serializable dictionary.

        Returns:
            Dictionary representation of the Image model.
        """
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
            "processing_start_time": (
                self.processing_start_time.isoformat()
                if self.processing_start_time else None
            ),
            "processing_end_time": (
                self.processing_end_time.isoformat()
                if self.processing_end_time else None
            ),
        }

    from typing import Any, Dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Image:
        """
        Create an Image instance from a dictionary representation.

        This method is used to reconstruct an Image object from serialized data
        (e.g., database row, JSON, or cache).

        Args:
            data (Dict[str, Any]):
                Dictionary containing image fields.

        Returns:
            Reconstructed Image instance.
        """
        start = (
            datetime.fromisoformat(data["processing_start_time"])
            if data.get("processing_start_time")
            else None
        )

        end = (
            datetime.fromisoformat(data["processing_end_time"])
            if data.get("processing_end_time")
            else None
        )

        dataset = Dataset(
            id=data.get("dataset_id", 0),
            name=data.get("dataset_name", "")
        )

        return cls(
            path=data["path"],
            dataset=dataset,
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

    from typing import Any

    def copy(self) -> Image:
        """
        Create a deep copy of the Image instance.

        Returns:
            A new Image instance with the same data but independent mutable fields.
        """
        dataset = Dataset(id=self.dataset_id, name=self.dataset_name)

        return Image(
            path=self.path,
            dataset=dataset,
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
        """
        Compare two Image objects based on their unique ID.

        Returns:
            True if both objects are Image instances with the same ID.
        """
        return isinstance(other, Image) and self.id == other.id


    def __hash__(self) -> int:
        """
        Return a hash based on the unique image ID.

        Returns:
            Hash value of the image ID.
        """
        return hash(self.id)

    def set_SAM3_results(self, results : Optional[List[Dict[str, Any]]]):
        """
        Set the SAM3 results for the image.
        
        Args:
            results: The SAM3 results to set.
        """
        self._sam3_results = results

    def get_SAM3_results(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get the SAM3 results for the image.
        
        Returns:
            The SAM3 results.
        """
        return self._sam3_results

    def set_prompts(self, prompts: List[dict]):
        """
        Set the prompts for the image.
        
        Args:
            prompts: The prompts to set.
        """
        for prompt in prompts:
            text = prompt.get("prompt", None)
            if not text:
                continue
            threshold = prompt.get("threshold", 0.5)
            self.prompts.update({text: threshold})

    def get_prompts(self) -> List[dict]:
        """
        Get the prompts for the image.
        
        Returns:
            The prompts.
        """
        return [{"prompt": prompt, "threshold": threshold} for prompt, threshold in self.prompts.items()]