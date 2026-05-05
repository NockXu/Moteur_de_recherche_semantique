import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ajouter la racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.Image_Classes.Image import Image, ProcessingStatus


class Export:
    """
    Service d'export des images (clean version)
    - pas de DB coupling direct
    - pas de print
    - output structuré
    """

    # ─────────────────────────────
    # CORE SERIALIZATION
    # ─────────────────────────────

    def image_to_dict(self, image: Image) -> Dict[str, Any]:
        return {
            "id": getattr(image, "id", None),
            "path": str(image.path),
            "name": image.name,
            "status": image.status.value if image.status else ProcessingStatus.NOT_STARTED.value,
            "description": image.description or "",
            "keywords": image.keywords or [],
            "embedding": image.embedding or [],
            "indexed_at": getattr(image, "indexed_at", ""),
            "error_message": getattr(image, "error_message", "")
        }

    def images_to_dict(self, images: List[Image]) -> Dict[str, Any]:
        return {
            img.name: self.image_to_dict(img)
            for img in images
        }

    # ─────────────────────────────
    # EXPORT JSON STRING
    # ─────────────────────────────

    def to_json(self, images: List[Image], indent: int = 2) -> str:
        data = self.images_to_dict(images)
        return json.dumps(data, indent=indent, ensure_ascii=False)

    # ─────────────────────────────
    # EXPORT FILE
    # ─────────────────────────────

    def export_to_file(
        self,
        images: List[Image],
        output_file: str
    ) -> Dict[str, Any]:

        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            json_data = self.to_json(images)

            output_path.write_text(json_data, encoding="utf-8")

            return {
                "success": True,
                "count": len(images),
                "path": str(output_path)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # ─────────────────────────────
    # HELPERS (OPTIONAL)
    # ─────────────────────────────

    def export_single(self, image: Image) -> str:
        return json.dumps(
            self.image_to_dict(image),
            indent=2,
            ensure_ascii=False
        )