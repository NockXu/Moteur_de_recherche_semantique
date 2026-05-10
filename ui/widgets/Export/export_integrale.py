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
from common.Dataset_Classes.Dataset import Dataset
from database.DbService import DbService


class ExportIntegrale:
    """
    Export intégral des données au format JSON avec datasets et images
    Structure:
    {
        "datasets": [
            {"id": <id>, "name": <name>},
            ...
        ],
        "images": [
            "<name>": {
                "id": <name>,
                "path": <path>,
                "description": <description>,
                "keywords": [<keyword>, ...],
                "embedding": [<float>, ...]
            },
            ...
        ]
    }
    """

    def __init__(self):
        """Initialise le service d'export intégral"""
        self.db_service = DbService()

    def export_all_data(self, file_path: str) -> Dict[str, Any]:
        """
        Exporte toutes les données (datasets + images) vers un fichier JSON
        
        Args:
            file_path: Chemin du fichier de sortie
            
        Returns:
            Dict: Les données exportées
        """
        try:
            # Récupérer tous les datasets
            datasets = self._get_all_datasets()
            
            # Récupérer toutes les images
            images = self._get_all_images()
            
            # Construire la structure de données
            export_data = {
                "datasets": datasets,
                "images": images
            }
            
            # Écrire dans le fichier
            self._write_json_file(file_path, export_data)
            
            return export_data
            
        except Exception as e:
            print(f"Erreur lors de l'export: {e}")
            raise

    def _get_all_datasets(self) -> List[Dict[str, Any]]:
        """Récupère tous les datasets de la base de données"""
        try:
            from common.Dataset_Classes.DatasetRepository import DatasetRepository
            dataset_repo = DatasetRepository(DbService().sqlite)
            raw_datasets = dataset_repo.get_all()
            print(f"Raw datasets: {raw_datasets}")
            
            datasets = []
            for dataset in raw_datasets:
                datasets.append({
                    "id": dataset.id,
                    "name": dataset.name
                })
            
            return datasets
            
        except Exception as e:
            print(f"Erreur lors de la récupération des datasets: {e}")
            return []

    def _get_all_images(self) -> Dict[str, Any]:
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
            print(f"Erreur lors de la récupération des images: {e}")
            return {}

    def _write_json_file(self, file_path: str, data: Dict[str, Any]) -> None:
        """Écrit les données dans un fichier JSON"""
        try:
            # Créer le répertoire si nécessaire
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Écrire le fichier JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"Données exportées avec succès dans: {file_path}")
            
        except Exception as e:
            print(f"Erreur lors de l'écriture du fichier: {e}")
            raise

    def export_to_string(self) -> str:
        """
        Exporte toutes les données vers une chaîne JSON
        
        Returns:
            str: Les données au format JSON
        """
        try:
            # Récupérer tous les datasets
            datasets = self._get_all_datasets()
            
            # Récupérer toutes les images
            images = self._get_all_images()
            
            # Construire la structure de données
            export_data = {
                "datasets": datasets,
                "images": images
            }
            
            # Convertir en JSON string
            return json.dumps(export_data, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"Erreur lors de l'export en string: {e}")
            raise


# ─────────────────────────────────────────────
# FONCTION UTILITAIRE POUR UTILISATION RAPIDE
# ─────────────────────────────────────────────

def export_integral_file(file_path: str) -> Dict[str, Any]:
    """
    Fonction utilitaire pour exporter rapidement toutes les données
    
    Args:
        file_path: Chemin du fichier de sortie
        
    Returns:
        Dict: Les données exportées
    """
    exporter = ExportIntegrale()
    return exporter.export_all_data(file_path)


def export_integral_string() -> str:
    """
    Fonction utilitaire pour exporter rapidement les données en string
    
    Returns:
        str: Les données au format JSON
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
        print(f"Export réussi! {len(data['datasets'])} datasets et {len(data['images'])} images exportés.")
    except Exception as e:
        print(f"Erreur: {e}")
    
    # Exemple 2: Exporter en string
    try:
        json_string = export_integral_string()
        print("Export JSON string généré avec succès!")
        # print(json_string)  # Décommenter pour voir le JSON
    except Exception as e:
        print(f"Erreur: {e}")
