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
    """Export simple des images au format JSON
    Structure:
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
        """Initialise le service d'export simple"""
        self.db_service = DbService()

    def export_images(self, file_path: str) -> dict[str, Any]:
        """Exporte toutes les images vers un fichier JSON
        
        Args:
            file_path: Chemin du fichier de sortie
            
        Returns:
            Dict: Les images exportées

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
        """Récupère toutes les images et les formate selon la structure demandée"""
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
        """Écrit les données dans un fichier JSON"""
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
        """Exporte toutes les images vers une chaîne JSON
        
        Returns:
            str: Les images au format JSON

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
    """Fonction utilitaire pour exporter rapidement toutes les images
    
    Args:
        file_path: Chemin du fichier de sortie
        
    Returns:
        Dict: Les images exportées

    """
    exporter = ExportSimple()
    return exporter.export_images(file_path)


def export_images_string() -> str:
    """Fonction utilitaire pour exporter rapidement les images en string
    
    Returns:
        str: Les images au format JSON

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
