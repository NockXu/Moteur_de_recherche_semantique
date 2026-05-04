import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.DatabaseManager import DatabaseManager
from common.ImageInfo import ImageInfo, ProcessingStatus

class Export:
    def __init__(self):
        self.db = DatabaseManager()
        # DatabaseManager se connecte automatiquement dans __init__
    
    def images_to_json(self, images: List[ImageInfo], output_file: str = None) -> str:
        """
        Transforme une liste d'ImageInfo en JSON
        
        Args:
            images: Liste des ImageInfo à exporter
            output_file: Fichier de sortie (optionnel)
            
        Returns:
            str: JSON string des images
        """
        export_data = {}
        
        for image in images:
            # Utiliser le nom du fichier comme clé
            filename = image.name
            export_data[filename] = {
                "id": image.id,
                "path": str(image.path),
                "name": image.name,
                "status": image.status.value if image.status else ProcessingStatus.NOT_STARTED.value,
                "description": image.description or "",
                "keywords": image.keywords or [],
                "embedding": image.embedding or [],
                "indexed_at": image.indexed_at or "",
                "error_message": image.error_message or ""
            }
        
        # Convertir en JSON
        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        
        # Sauvegarder dans un fichier si spécifié
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"✅ Exporté {len(images)} images vers {output_file}")
        
        return json_str
    
    def export_all_images(self, output_file: str = None) -> str:
        """
        Exporte toutes les images de la base de données
        
        Args:
            output_file: Fichier de sortie (optionnel)
            
        Returns:
            str: JSON string de toutes les images
        """
        try:
            images = self.db.get_all_images()
            return self.images_to_json(images, output_file)
        except Exception as e:
            print(f"❌ Erreur lors de l'export: {e}")
            return "{}"