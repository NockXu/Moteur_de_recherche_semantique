from typing import List, Dict, Optional
from common.ImageInfo import ImageInfo

class ImageSearchedContainerModel:
    """Modèle pour gérer les données des images recherchées"""
    
    def __init__(self, max_images_per_page: int = 12):
        self.images: List[ImageInfo] = []
        self.current_page: int = 1
        self.max_images_per_page: int = max_images_per_page
        self.total_pages: int = 1
        self.sort_by: str = "score"  # score, title, path
        self.sort_order: str = "desc"  # desc, asc
        self.filter_tags: List[str] = []
        
    def add_image(self, image_info: ImageInfo):
        """Ajoute une image à la liste"""
        self.images.append(image_info)
        self.update_pagination()
        
    def add_images(self, image_list: List[ImageInfo]):
        """Ajoute plusieurs images à la liste"""
        self.images.extend(image_list)
        self.update_pagination()
        
    def set_images(self, image_list: List[ImageInfo]):
        """Définit la liste complète des images"""
        self.images = image_list.copy()
        self.update_pagination()
        
    def get_images_for_page(self, page: int) -> List[ImageInfo]:
        """Retourne les images pour une page spécifique"""
        # Appliquer les filtres
        filtered_images = self.apply_filters()
        
        # Appliquer le tri
        sorted_images = self.apply_sorting(filtered_images)
        
        # Calculer les indices pour la page
        start_idx = (page - 1) * self.max_images_per_page
        end_idx = min(start_idx + self.max_images_per_page, len(sorted_images))
        
        return sorted_images[start_idx:end_idx]
        
    def get_current_page_images(self) -> List[ImageInfo]:
        """Retourne les images de la page actuelle"""
        return self.get_images_for_page(self.current_page)
        
    def update_pagination(self):
        """Met à jour le nombre total de pages"""
        filtered_count = len(self.apply_filters())
        self.total_pages = max(1, (filtered_count + self.max_images_per_page - 1) // self.max_images_per_page)
        
        # Ajuster la page actuelle si nécessaire
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
            
    def apply_filters(self) -> List[ImageInfo]:
        """Applique les filtres actuels aux images"""
        if not self.filter_tags:
            return self.images
            
        filtered = []
        for image_info in self.images:
            # Vérifier si l'image a au moins un des tags requis
            if any(tag in image_info.keywords for tag in self.filter_tags):
                filtered.append(image_info)
        return filtered
        
    def apply_sorting(self, image_list: List[ImageInfo]) -> List[ImageInfo]:
        """Applique le tri actuel aux images"""
        if not image_list:
            return image_list
            
        reverse = self.sort_order == "desc"
        
        if self.sort_by == "score":
            return sorted(image_list, key=lambda x: x.score, reverse=reverse)
        elif self.sort_by == "title":
            return sorted(image_list, key=lambda x: x.name.lower(), reverse=reverse)
        elif self.sort_by == "path":
            return sorted(image_list, key=lambda x: str(x.path).lower(), reverse=reverse)
        else:
            return image_list
            
    def set_current_page(self, page: int):
        """Définit la page actuelle"""
        if 1 <= page <= self.total_pages:
            self.current_page = page
            
    def set_max_images_per_page(self, max_images: int):
        """Définit le nombre maximum d'images par page"""
        self.max_images_per_page = max(1, max_images)
        self.update_pagination()
        
    def set_sorting(self, sort_by: str, sort_order: str = "desc"):
        """Définit le critère et l'ordre de tri"""
        if sort_by in ["score", "title", "path"]:
            self.sort_by = sort_by
        if sort_order in ["desc", "asc"]:
            self.sort_order = sort_order
            
    def set_filter_tags(self, tags: List[str]):
        """Définit les tags à filtrer"""
        self.filter_tags = tags.copy()
        self.update_pagination()
        
    def add_filter_tag(self, tag: str):
        """Ajoute un tag de filtre"""
        if tag not in self.filter_tags:
            self.filter_tags.append(tag)
            self.update_pagination()
            
    def remove_filter_tag(self, tag: str):
        """Retire un tag de filtre"""
        if tag in self.filter_tags:
            self.filter_tags.remove(tag)
            self.update_pagination()
            
    def clear_filters(self):
        """Efface tous les filtres"""
        self.filter_tags = []
        self.update_pagination()
        
    def get_image_by_path(self, path: str) -> Optional[ImageInfo]:
        """Retourne une image par son chemin"""
        for image_info in self.images:
            if str(image_info.path) == path:
                return image_info
        return None
        
    def remove_image(self, image_info: ImageInfo) -> bool:
        """Retire une image par son objet ImageInfo"""
        if image_info in self.images:
            self.images.remove(image_info)
            self.update_pagination()
            return True
        return False
        
    def get_all_tags(self) -> List[str]:
        """Retourne tous les tags uniques des images"""
        tags = set()
        for image_info in self.images:
            tags.update(image_info.keywords)
        return sorted(list(tags))
        
    def get_statistics(self) -> Dict:
        """Retourne des statistiques sur les images"""
        if not self.images:
            return {
                'total_images': 0,
                'total_pages': 0,
                'current_page': 0,
                'filtered_images': 0,
                'unique_tags': 0
            }
            
        return {
            'total_images': len(self.images),
            'total_pages': self.total_pages,
            'current_page': self.current_page,
            'filtered_images': len(self.apply_filters()),
            'unique_tags': len(self.get_all_tags()),
            'avg_score': sum(img_info.score for img_info in self.images) / len(self.images) if self.images else 0
        }
        
    def clear(self):
        """Efface toutes les images"""
        self.images.clear()
        self.current_page = 1
        self.total_pages = 1
        self.filter_tags.clear()
        
    def to_dict_list(self) -> List[Dict]:
        """Convertit les images en liste de dictionnaires pour la vue"""
        page_image_infos = self.get_current_page_images()
        return [
            {
                'path': str(image_info.path),
                'title': image_info.name,
                'description': image_info.description,
                'tags': image_info.keywords,
                'score': image_info.score
            }
            for image_info in page_image_infos
        ]
        
    def get_image_count(self) -> int:
        """Retourne le nombre total d'images"""
        return len(self.images)
        
    def get_filtered_count(self) -> int:
        """Retourne le nombre d'images après filtrage"""
        return len(self.apply_filters())
