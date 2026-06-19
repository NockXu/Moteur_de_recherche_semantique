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
from common.Dataset_Classes.Dataset import Dataset
from database.DbService import DbService


class ExportIntegrale:
    """Full database data export engine translating image and dataset metadata records into JSON format.
    
    Output Schema Structure:
    {
        "<name>": {
            "id": <name>,
            "path": <path>,
            "description": <description>,
            "keywords": [<keyword>, ...],
            "dataset": <dataset_name>,
            "embedding": [<float>, ...]
        },
        ...
    }
    """

    def __init__(self):
        """Initialize the full comprehensive export database service layer."""
        self.db_service = DbService()

    def export_all_data(self, file_path: str) -> dict[str, Any]:
        """Serialize and save all catalog metrics (datasets + image rows) directly to a local JSON file.

        Args:
            file_path (str): The absolute or relative target path for the generated output file.

        Returns:
            dict[str, Any]: The fully compiled data dictionary structure that was written to disk.

        Raises:
            Exception: If an error occurs during extraction or file serialization steps.

        """
        try:
            # Récupérer toutes les images
            images = self._get_all_images()
            
            # Construire la structure de données
            export_data = images
            
            # Écrire dans le fichier
            self._write_json_file(file_path, export_data)
            
            return export_data
            
        except Exception as e:
            print(f"{tr("Erreur lors de l'export")}: {e}")
            raise

    def _get_all_images(self) -> dict[str, Any]:
        """Query tracking indexes to extract and format all image elements into the target schema payload.

        Returns:
            dict[str, Any]: A serialized image dictionary mapped via unique file names keys.

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
                    "dataset": image.dataset_name or "",
                    "embedding": image.embedding or []
                }
            
            return images_dict
            
        except Exception as e:
            print(f"{tr("Erreur lors de la récupération des images")}: {e}")
            return {}

    def _write_json_file(self, file_path: str, data: dict[str, Any]) -> None:
        """Commit data layout dictionaries payload structurally onto a target disk file path location.

        Args:
            file_path (str): Target physical destination path location on disk.
            data (dict[str, Any]): Catalog payload properties structured block to persist.

        Raises:
            Exception: If sub-directory instantiation fails or writing permissions are denied.

        """
        try:
            # Créer le répertoire si nécessaire
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Écrire le fichier JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"{tr("Données exportées avec succès dans")}: {file_path}")
            
        except Exception as e:
            print(f"{tr("Erreur lors de l'écriture du fichier")}: {e}")
            raise

    def export_to_string(self) -> str:
        """Compile catalog entries layer metrics and format into an explicit serialized JSON string block.

        Returns:
            str: The fully stringified human-readable dataset and image database records block.

        Raises:
            Exception: If individual structural records serialization workflows fail.

        """
        try:
            # Récupérer tous les datasets
            datasets = self._get_all_datasets()
            
            # Récupérer toutes les images
            images = self._get_all_images()
            
            # Construire la structure de données
            export_data = images
            
            # Convertir en JSON string
            return json.dumps(export_data, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"{tr("Erreur lors de l'export en string")}: {e}")
            raise


# ─────────────────────────────────────────────
# FONCTION UTILITAIRE POUR UTILISATION RAPIDE
# ─────────────────────────────────────────────

def export_integral_file(file_path: str) -> dict[str, Any]:
    """Utility shorthand wrapper function to instantly export all data metrics directly into a local file.

    Args:
        file_path (str): Target filesystem path location destination.

    Returns:
        dict[str, Any]: The finalized compiled dictionary schema data block committed to disk.

    """
    exporter = ExportIntegrale()
    return exporter.export_all_data(file_path)


def export_integral_string() -> str:
    """Utility shorthand wrapper function to instantly convert entire catalog models into a JSON string block.

    Returns:
        str: Serialized human-readable system configuration parameters text string block.

    """
    exporter = ExportIntegrale()
    return exporter.export_to_string()


# ─────────────────────────────────────────────
# EXEMPLE D'UTILISATION
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Exemple 1: Exporter dans un fichier
    try:
        data = export_integral_file("export_integral.json")
        print(f"{tr("Export réussi")}: {len(data['datasets'])} {tr("datasets")} et {len(data['images'])} {tr("images exportés")}.")
    except Exception as e:
        print(f"{tr("Erreur")}: {e}")
    
    # Exemple 2: Exporter en string
    try:
        json_string = export_integral_string()
        print(f"{tr("Export JSON string généré avec succès")}")
        # print(json_string)  # Décommenter pour voir le JSON
    except Exception as e:
        print(f"{tr("Erreur")}: {e}")
