import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.DatabaseManager import DatabaseManager
from common.ImageInfo import ImageInfo, ProcessingStatus

class Import:
    def __init__(self):
        self.db = DatabaseManager()
        # DatabaseManager se connecte automatiquement dans __init__
    
    def json_to_images(self, json_str: str) -> List[ImageInfo]:
        """
        Transforme un JSON en liste d'ImageInfo
        
        Args:
            json_str: JSON string avec la structure {filename: {data}}
            
        Returns:
            List[ImageInfo]: Liste des ImageInfo créées
        """
        try:
            data = json.loads(json_str)
            images = []
            
            for filename, image_data in data.items():
                # Ignorer les métadonnées si présentes
                if filename in ["export_info", "metadata"]:
                    continue
                
                # Créer l'ImageInfo
                image_info = ImageInfo(
                    path=image_data.get("path", filename),
                    status=ProcessingStatus.COMPLETED if image_data.get("description") else ProcessingStatus.NOT_STARTED,
                    description=image_data.get("description", ""),
                    keywords=image_data.get("keywords", []),
                    embedding=image_data.get("embedding", [])
                )
                
                # Ajouter l'ID s'il existe
                if "id" in image_data:
                    image_info.id = image_data["id"]
                
                # Ajouter la date d'indexation si présente
                if "indexed_at" in image_data:
                    image_info.indexed_at = image_data["indexed_at"]
                
                images.append(image_info)
            
            return images
            
        except json.JSONDecodeError as e:
            print(f"❌ Erreur de décodage JSON: {e}")
            return []
        except Exception as e:
            print(f"❌ Erreur lors de la conversion: {e}")
            return []
    
    def import_from_file(self, file_path: str) -> List[ImageInfo]:
        """
        Importe des images depuis un fichier JSON
        
        Args:
            file_path: Chemin du fichier JSON
            
        Returns:
            List[ImageInfo]: Liste des ImageInfo importées
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_str = f.read()
            
            images = self.json_to_images(json_str)
            print(f"✅ Importé {len(images)} images depuis {file_path}")
            
            return images
            
        except FileNotFoundError:
            print(f"❌ Fichier non trouvé: {file_path}")
            return []
        except Exception as e:
            print(f"❌ Erreur lors de l'import: {e}")
            return []
    
    def import_and_save(self, file_path: str) -> int:
        """
        Importe des images et les sauvegarde en base de données
        
        Args:
            file_path: Chemin du fichier JSON
            
        Returns:
            int: Nombre d'images sauvegardées
        """
        images = self.import_from_file(file_path)
        saved_count = 0
        
        for image in images:
            try:
                success = self.db.insert_image(image)
                if success:
                    saved_count += 1
            except Exception as e:
                print(f"❌ Erreur lors de la sauvegarde de {image.name}: {e}")
        
        print(f"{saved_count}/{len(images)} images sauvegardées en base de données")
        return saved_count
