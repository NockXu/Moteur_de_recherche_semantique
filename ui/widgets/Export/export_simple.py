import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from ui.utils.i18n import tr

# Ajouter la racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.Image_Classes.Image import Image, ProcessingStatus
from database.DbService import DbService


class ExportSimple:
    """Handles basic image metadata records serialization into standard JSON format.

    Output Schema Structure:
    {
        "<name>": {
            "id": <name>,
            "path": <path>,
            "description": <description>,
            "keywords": [<keyword>, ...],
            "embedding": [<float>, ...]
        },
        ...
    }
    """

    def __init__(self):
        """Initialize the simplified metadata extraction export service layer."""
        self.db_service = DbService()

    def export_images(self, file_path: str) -> dict[str, Any]:
        """Serialize and save all image registry properties directly to a local JSON file.

        Args:
            file_path (str): The absolute or relative target path for the generated output file.

        Returns:
            dict[str, Any]: The fully compiled image data records written to disk.

        Raises:
            Exception: If an error occurs during data extraction or file system write routines.

        """
        try:
            # Récupérer toutes les images
            images = self._get_all_images()
            
            # Écrire dans le fichier
            self._write_json_file(file_path, images)
            
            return images
            
        except Exception as e:
            print(f"{tr("Erreur lors de l'export")}: {e}")
            raise

    def _get_all_images(self) -> dict[str, Any]:
        """Query data repositories to map all active image objects into the target dictionary schema.

        Returns:
            dict[str, Any]: Formatted data records mapped using unique image file names as keys.

        """
        try:
            # Récupérer toutes les images via ImageRepository
            from common.Image_Classes.ImageRepository import ImageRepository
            repo = ImageRepository(self.db_service.sqlite, self.db_service.faiss)
            
            all_images = repo.get_all()
            images_dict = {}
            
            for image in all_images:
                images_dict[image.name] = {
                    "id": image.name,
                    "path": str(image.path),
                    "description": image.description or "",
                    "keywords": image.keywords or [],
                    "embedding": image.embedding or []
                }
            
            return images_dict
            
        except Exception as e:
            print(f"{tr("Erreur lors de la récupération des images")}: {e}")
            return {}

    def _write_json_file(self, file_path: str, data: dict[str, Any]) -> None:
        """Write structured metadata dictionary payloads to a targeted physical disk file.

        Args:
            file_path (str): Destination path string on the filesystem.
            data (dict[str, Any]): Dictionary schema payload block to serialize.

        Raises:
            Exception: If structural directory creation fails or writing access is denied.

        """
        try:
            # Créer le répertoire si nécessaire
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Écrire le fichier JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"{tr("Images exportées avec succès dans")}: {file_path}")
            
        except Exception as e:
            print(f"{tr("Erreur lors de l'écriture du fichier")}: {e}")
            raise

    def export_to_string(self) -> str:
        """Compile image metadata logs and output them into a structured, serialized text string.

        Returns:
            str: Normalized human-readable image catalog parameters formatted as a JSON string.

        Raises:
            Exception: If system data formatting or memory serialization workflows fail.

        """
        try:
            # Récupérer toutes les images
            images = self._get_all_images()
            
            # Convertir en JSON string
            return json.dumps(images, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"{tr("Erreur lors de l'export en string")}: {e}")
            raise


# ─────────────────────────────────────────────
# FONCTION UTILITAIRE POUR UTILISATION RAPIDE
# ─────────────────────────────────────────────

def export_images_file(file_path: str) -> dict[str, Any]:
    """Utility wrapper to instantly serialize and output all active image metrics to a disk file.

    Args:
        file_path (str): Target physical disk storage path.

    Returns:
        dict[str, Any]: The finalized collection properties schema block written to storage.

    """
    exporter = ExportSimple()
    return exporter.export_images(file_path)


def export_images_string() -> str:
    """Utility wrapper to instantly dump all image registries properties directly into a text string.

    Returns:
        str: Serialized image database records translated into a JSON string block.

    """
    exporter = ExportSimple()
    return exporter.export_to_string()


# ─────────────────────────────────────────────
# EXEMPLE D'UTILISATION
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Exemple 1: Exporter dans un fichier
    try:
        data = export_images_file("export_images.json")
        print(f"{tr("Export réussi")}: {len(data)} {tr("images exportées")}.")
    except Exception as e:
        print(f"{tr("Erreur")}: {e}")
    
    # Exemple 2: Exporter en string
    try:
        json_string = export_images_string()
        print(f"{tr("Export JSON string généré avec succès")}")
        # print(json_string)  # Décommenter pour voir le JSON
    except Exception as e:
        print(f"{tr("Erreur")}: {e}")
