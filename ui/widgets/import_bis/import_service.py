import json
from pathlib import Path
from typing import List

from ui.widget.import_bis.import_models import ImportImageData
from ui.widget.import_bis.import_result import ImportResult
from ui.widget.import_bis.strategies.base_strategy import BaseImportStrategy

from common.Image_Classes.Image import Image, ProcessingStatus
from database.repositories.image_repository import ImageRepository  # ton repo existant


class ImportService:

    def __init__(self, image_repository: ImageRepository, strategy: BaseImportStrategy):
        self.repo = image_repository
        self.strategy = strategy

    # -------------------------
    # LOAD JSON
    # -------------------------
    def load_file(self, file_path: str) -> List[ImportImageData]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        images = []

        for filename, image_data in data.items():
            if filename in ["export_info", "metadata"]:
                continue

            images.append(
                ImportImageData(
                    filename=filename,
                    path=None,
                    dataset=image_data.get("dataset"),
                    description=image_data.get("description", ""),
                    keywords=image_data.get("keywords", []),
                    embedding=image_data.get("embedding", []),
                    id=image_data.get("id")
                )
            )

        return images

    # -------------------------
    # MAIN IMPORT PIPELINE
    # -------------------------
    def import_file(self, file_path: str) -> ImportResult:
        result = ImportResult()
        images = self.load_file(file_path)

        for img in images:
            try:
                dataset_name, final_path = self.strategy.resolve(
                    img.filename,
                    img.__dict__
                )

                if not dataset_name or not final_path:
                    result.add_error(f"Mapping failed: {img.filename}")
                    continue

                image = Image(
                    path=final_path,
                    dataset=dataset_name,  # IMPORTANT: ton repo attend un Dataset object → on adapte après
                    description=img.description,
                    keywords=img.keywords,
                    embedding=img.embedding
                )

                if img.id:
                    image.id = img.id

                # 🔥 UNIQUE CHANGEMENT : on passe par TON repository
                success = self.repo.save_image(image)

                if success is None:
                    result.add_error(f"DB insert failed: {img.filename}")
                else:
                    result.success += 1

            except Exception as e:
                result.add_error(f"{img.filename}: {str(e)}")

        return result

    def _build_image(self, img, dataset, path):
        from common.Image_Classes.Image import Image, ProcessingStatus

        return Image(
            path=path,
            dataset=dataset,
            description=img.description,
            keywords=img.keywords,
            embedding=img.embedding,
            image_id=img.id
        )