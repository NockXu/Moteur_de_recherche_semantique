from typing import Optional, List, Dict, Any
from common.ImageInfo import ImageInfo, ProcessingStatus
from pathlib import Path
import json
from datetime import datetime


class ImagePreviewModel:
    """Modèle de données pour la prévisualisation d'images"""
    
    def __init__(self):
        self.current_image: Optional[ImageInfo] = None
        self.history: List[ImageInfo] = []
        self.max_history_size = 50
        self.auto_save_enabled = True
        self.last_error: Optional[str] = None
        
        # État de l'interface
        self.display_mode = "full"  # full, compact, minimal
        self.show_technical_info = True
        self.show_processing_info = True
        self.auto_refresh = False
    
    def set_image(self, image_info: ImageInfo) -> bool:
        """
        Définit l'image actuelle à prévisualiser.
        
        Args:
            image_info: Informations de l'image à afficher
            
        Returns:
            bool: True si l'image a été définie avec succès
        """
        try:
            # Valider l'image
            if not self._validate_image_info(image_info):
                return False
            
            # Ajouter à l'historique si différent de l'actuelle
            if self.current_image and self.current_image.path != image_info.path:
                self._add_to_history(self.current_image)
            
            # Définir la nouvelle image actuelle
            self.current_image = image_info
            self.last_error = None
            
            # Auto-sauvegarde si activée
            if self.auto_save_enabled:
                self._auto_save_current_image()
            
            return True
            
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def get_current_image(self) -> Optional[ImageInfo]:
        """Retourne l'image actuellement affichée"""
        return self.current_image
    
    def clear_current_image(self):
        """Efface l'image actuelle"""
        if self.current_image:
            self._add_to_history(self.current_image)
        self.current_image = None
        self.last_error = None
    
    def _validate_image_info(self, image_info: ImageInfo) -> bool:
        """Valide les informations de l'image"""
        if not image_info:
            self.last_error = "ImageInfo est None"
            return False
        
        # S'assurer que path est un objet Path
        from pathlib import Path
        if not isinstance(image_info.path, Path):
            image_info.path = Path(image_info.path)
            
        if not image_info.path.exists():
            self.last_error = f"Le fichier n'existe pas: {image_info.path}"
            return False
        
        if not image_info.path.is_file():
            self.last_error = f"Le chemin n'est pas un fichier: {image_info.path}"
            return False
        
        # Vérifier que c'est une image valide (par extension)
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        if image_info.path.suffix.lower() not in valid_extensions:
            self.last_error = f"Format d'image non supporté: {image_info.path.suffix}"
            return False
        
        return True
    
    def _add_to_history(self, image_info: ImageInfo):
        """Ajoute une image à l'historique"""
        # Éviter les doublons
        for i, existing in enumerate(self.history):
            if existing.path == image_info.path:
                # Déplacer vers le début
                self.history.pop(i)
                break
        
        # Ajouter au début
        self.history.insert(0, image_info)
        
        # Limiter la taille de l'historique
        if len(self.history) > self.max_history_size:
            self.history = self.history[:self.max_history_size]
    
    def get_history(self, limit: int = 10) -> List[ImageInfo]:
        """
        Retourne l'historique des images.
        
        Args:
            limit: Nombre maximum d'images à retourner
            
        Returns:
            List[ImageInfo]: Liste des images récemment visualisées
        """
        return self.history[:limit]
    
    def get_history_by_path(self, path: Path) -> Optional[ImageInfo]:
        """Retourne une image de l'historique par son chemin"""
        path = Path(path).resolve()
        for image_info in self.history:
            if image_info.path.resolve() == path:
                return image_info
        return None
    
    def remove_from_history(self, image_info: ImageInfo) -> bool:
        """
        Supprime une image de l'historique.
        
        Args:
            image_info: Image à supprimer
            
        Returns:
            bool: True si l'image a été supprimée
        """
        try:
            self.history.remove(image_info)
            return True
        except ValueError:
            return False
    
    def clear_history(self):
        """Efface tout l'historique"""
        self.history.clear()
    
    def set_image_by_path(self, image_path: str) -> bool:
        """
        Définit une image par son chemin.
        
        Args:
            image_path: Chemin vers l'image
            
        Returns:
            bool: True si l'image a été chargée avec succès
        """
        try:
            path = Path(image_path)
            
            # Vérifier si l'image existe dans l'historique
            existing_image = self.get_history_by_path(path)
            if existing_image:
                return self.set_image(existing_image)
            
            # Créer une nouvelle ImageInfo
            image_info = ImageInfo(path)
            return self.set_image(image_info)
            
        except Exception as e:
            self.last_error = f"Erreur lors du chargement: {str(e)}"
            return False
    
    def update_current_image_info(self, **kwargs) -> bool:
        """
        Met à jour les informations de l'image actuelle.
        
        Args:
            **kwargs: Paramètres à mettre à jour (description, keywords, score, etc.)
            
        Returns:
            bool: True si la mise à jour a réussi
        """
        if not self.current_image:
            self.last_error = "Aucune image actuelle à mettre à jour"
            return False
        
        try:
            # Mettre à jour les champs
            for key, value in kwargs.items():
                if hasattr(self.current_image, key):
                    setattr(self.current_image, key, value)
            
            # Auto-sauvegarde si activée
            if self.auto_save_enabled:
                self._auto_save_current_image()
            
            return True
            
        except Exception as e:
            self.last_error = f"Erreur lors de la mise à jour: {str(e)}"
            return False
    
    def _auto_save_current_image(self):
        """Sauvegarde automatiquement l'image actuelle"""
        if not self.current_image:
            return
        
        try:
            # Créer un dossier de cache si nécessaire
            cache_dir = Path("storage/preview_cache")
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Nom de fichier basé sur le chemin et l'ID
            cache_file = cache_dir / f"{self.current_image.path.stem}_{self.current_image.id}.json"
            
            # Sauvegarder les métadonnées
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_image.to_dict(), f, indent=2, ensure_ascii=False)
                
        except Exception:
            # Ignorer les erreurs de sauvegarde automatique
            pass
    
    def load_from_cache(self, image_path: Path) -> Optional[ImageInfo]:
        """
        Charge une image depuis le cache.
        
        Args:
            image_path: Chemin de l'image originale
            
        Returns:
            Optional[ImageInfo]: Image chargée depuis le cache ou None
        """
        try:
            cache_dir = Path("storage/preview_cache")
            if not cache_dir.exists():
                return None
            
            # Chercher les fichiers de cache correspondants
            cache_files = list(cache_dir.glob(f"{image_path.stem}_*.json"))
            
            if not cache_files:
                return None
            
            # Prendre le plus récent
            cache_file = max(cache_files, key=lambda f: f.stat().st_mtime)
            
            # Charger les données
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Vérifier que le fichier original existe toujours
            original_path = Path(data["path"])
            if not original_path.exists():
                return None
            
            # Créer l'ImageInfo
            return ImageInfo.from_dict(data)
            
        except Exception:
            return None
    
    def get_display_settings(self) -> Dict[str, Any]:
        """Retourne les paramètres d'affichage actuels"""
        return {
            "display_mode": self.display_mode,
            "show_technical_info": self.show_technical_info,
            "show_processing_info": self.show_processing_info,
            "auto_refresh": self.auto_refresh,
            "auto_save_enabled": self.auto_save_enabled
        }
    
    def set_display_settings(self, **settings):
        """
        Définit les paramètres d'affichage.
        
        Args:
            **settings: Paramètres à définir
        """
        for key, value in settings.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne des statistiques sur l'utilisation"""
        return {
            "current_image": {
                "path": str(self.current_image.path) if self.current_image else None,
                "name": self.current_image.name if self.current_image else None,
                "status": self.current_image.status.value if self.current_image else None
            },
            "history_size": len(self.history),
            "max_history_size": self.max_history_size,
            "last_error": self.last_error,
            "display_settings": self.get_display_settings()
        }
    
    def export_history(self, file_path: str) -> bool:
        """
        Exporte l'historique vers un fichier JSON.
        
        Args:
            file_path: Chemin du fichier d'export
            
        Returns:
            bool: True si l'export a réussi
        """
        try:
            export_data = {
                "export_date": datetime.now().isoformat(),
                "total_images": len(self.history),
                "images": [img.to_dict() for img in self.history]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            self.last_error = f"Erreur lors de l'export: {str(e)}"
            return False
    
    def import_history(self, file_path: str) -> bool:
        """
        Importe l'historique depuis un fichier JSON.
        
        Args:
            file_path: Chemin du fichier à importer
            
        Returns:
            bool: True si l'import a réussi
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Importer les images
            imported_images = []
            for img_data in data.get("images", []):
                try:
                    image_info = ImageInfo.from_dict(img_data)
                    if image_info.path.exists():  # Ne garder que les images existantes
                        imported_images.append(image_info)
                except Exception:
                    continue  # Ignorer les images invalides
            
            # Ajouter à l'historique
            for image_info in imported_images:
                self._add_to_history(image_info)
            
            return True
            
        except Exception as e:
            self.last_error = f"Erreur lors de l'import: {str(e)}"
            return False
    
    def cleanup_cache(self, max_age_days: int = 30) -> int:
        """
        Nettoie le cache des anciens fichiers.
        
        Args:
            max_age_days: Âge maximum des fichiers en jours
            
        Returns:
            int: Nombre de fichiers supprimés
        """
        try:
            cache_dir = Path("storage/preview_cache")
            if not cache_dir.exists():
                return 0
            
            cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
            deleted_count = 0
            
            for cache_file in cache_dir.glob("*.json"):
                if cache_file.stat().st_mtime < cutoff_time:
                    cache_file.unlink()
                    deleted_count += 1
            
            return deleted_count
            
        except Exception:
            return 0
