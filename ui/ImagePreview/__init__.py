"""
ImagePreview - Widget PyQt6 pour la prévisualisation d'images avec métadonnées

Ce package fournit un widget complet pour afficher une image et ses informations associées
avec une architecture MVC propre et réutilisable.

Classes principales:
- ImagePreviewController: Contrôleur principal
- ImagePreviewView: Interface utilisateur
- ImagePreviewModel: Modèle de données

Utilisation:
    from ui.ImagePreview import create_image_preview
    
    controller = create_image_preview()
    controller.set_image_by_path("path/to/image.jpg")
    layout.addWidget(controller.get_view())
"""

from .ImagePreviewController import ImagePreviewController, create_image_preview
from .ImagePreviewView import ImagePreviewView
from .ImagePreviewModel import ImagePreviewModel

__version__ = "1.0.0"
__author__ = "Semantic Search Engine Team"

__all__ = [
    "ImagePreviewController",
    "ImagePreviewView", 
    "ImagePreviewModel",
    "create_image_preview"
]
