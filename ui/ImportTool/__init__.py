"""
ImportTool - Widget PyQt6 pour le traitement d'images

Ce package fournit un outil complet pour traiter des images par lot avec:
- Sélection de dossier
- Affichage des images avec badges de statut
- Traitement asynchrone des images
- Barre de progression globale
- Architecture MVC propre

Classes principales:
- ImportToolController: Contrôleur principal
- ImportToolView: Interface utilisateur
- ImportToolModel: Modèle de données
- ImageWidget: Widget individuel pour une image
- ProcessingWorker: Worker thread pour le traitement
"""

from .ImportToolController import ImportToolController, create_import_tool
from .ImportToolView import ImportToolView
from .ImportToolModel import ImportToolModel
from .ImageWidget import ImageWidget, ProcessingStatus
from .ProcessingWorker import ProcessingWorker, BatchProcessingManager
from common.ImageInfo import ImageInfo

__all__ = [
    "ImportToolController",
    "ImportToolView", 
    "ImportToolModel",
    "ImageWidget",
    "ProcessingWorker",
    "BatchProcessingManager",
    "ImageInfo",
    "ProcessingStatus",
    "create_import_tool"
]
