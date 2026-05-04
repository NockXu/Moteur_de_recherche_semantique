from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional, Union
from datetime import datetime
from enum import Enum
import os

import json


class ProcessingStatus(Enum):
    """Statuts de traitement possibles pour une image"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


class ImageInfo:
    """
    Classe unifiée pour stocker les informations sur une image.
    Utilisable dans ImportTool et ImageSearchedContainer.
    """
    
    def __init__(self, 
                 path: Union[str, Path],
                 score: float = 0.0,
                 status: ProcessingStatus = ProcessingStatus.NOT_STARTED,
                 description: str = "Aucune description disponible",
                 keywords: List[str] = None,
                 embedding: List[float] = None,
                 error_message: str = "",
                 processing_start_time: Optional[datetime] = None,
                 processing_end_time: Optional[datetime] = None,
                 image_id: str = None):
        """
        Initialise une ImageInfo.
        
        Args:
            path: Chemin vers le fichier image
            score: Score de pertinence (pour les résultats de recherche)
            status: Statut de traitement
            description: Description générée par l'IA
            keywords: Liste de mots-clés
            embedding: Vecteur d'embedding
            error_message: Message d'erreur si traitement échoué
            processing_start_time: Heure de début de traitement
            processing_end_time: Heure de fin de traitement
            image_id: ID unique de l'image
        """
        self.path = Path(path)
        self.score = float(score)
        self.status = status
        self.description = description
        self.keywords = keywords or []
        self.embedding = embedding or []
        self.error_message = error_message
        self.processing_start_time = processing_start_time
        self.processing_end_time = processing_end_time
        
        # Générer un ID si non fourni
        if image_id:
            self.id = image_id
        else:
            # Utiliser le chemin comme base pour l'ID pour garantir l'unicité
            import hashlib
            path_str = str(self.path.resolve())
            hash_obj = hashlib.md5(path_str.encode('utf-8'))
            self.id = f"img_{hash_obj.hexdigest()[:16]}"
        
        # Attributs dérivés
        self.name = self.path.name
        self.stem = self.path.stem
        self.suffix = self.path.suffix.lower()
        self.size = self.path.stat().st_size if self.path.exists() else 0
    
    @property
    def is_processed(self) -> bool:
        """Vérifie si l'image a été traitée avec succès"""
        return self.status == ProcessingStatus.COMPLETED
    
    @property
    def has_error(self) -> bool:
        """Vérifie si l'image a une erreur"""
        return self.status == ProcessingStatus.ERROR
    
    @property
    def is_processing(self) -> bool:
        """Vérifie si l'image est en cours de traitement"""
        return self.status == ProcessingStatus.IN_PROGRESS
    
    @property
    def processing_duration(self) -> Optional[float]:
        """Retourne la durée de traitement en secondes"""
        if self.processing_start_time and self.processing_end_time:
            delta = self.processing_end_time - self.processing_start_time
            return delta.total_seconds()
        return None
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour la sérialisation"""
        return {
            "id": self.id,
            "path": str(self.path),
            "name": self.name,
            "stem": self.stem,
            "suffix": self.suffix,
            "size": self.size,
            "score": self.score,
            "status": self.status.value,
            "description": self.description,
            "keywords": self.keywords,
            "embedding": self.embedding,
            "error_message": self.error_message,
            "processing_start_time": self.processing_start_time.isoformat() if self.processing_start_time else None,
            "processing_end_time": self.processing_end_time.isoformat() if self.processing_end_time else None,
            "processing_duration": self.processing_duration
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ImageInfo':
        """Crée une instance depuis un dictionnaire"""
        path = data["path"]
        
        # Parser les timestamps
        start_time = None
        end_time = None
        if data.get("processing_start_time"):
            start_time = datetime.fromisoformat(data["processing_start_time"])
        if data.get("processing_end_time"):
            end_time = datetime.fromisoformat(data["processing_end_time"])
        
        return cls(
            path=path,
            score=data.get("score", 0.0),
            status=ProcessingStatus(data.get("status", ProcessingStatus.NOT_STARTED.value)),
            description=data.get("description", ""),
            keywords=data.get("keywords", []),
            embedding=data.get("embedding", []),
            error_message=data.get("error_message", ""),
            processing_start_time=start_time,
            processing_end_time=end_time,
            image_id=data.get("id")
        )
    
    def to_search_dict(self) -> dict:
        """Convertit en dictionnaire pour les résultats de recherche"""
        return {
            'path': str(self.path),
            'title': self.name,
            'description': self.description,
            'tags': self.keywords,
            'score': self.score,
            'status': self.status.value
        }
    
    def update_status(self, 
                     status: ProcessingStatus, 
                     description: str = None, 
                     keywords: List[str] = None,
                     embedding: List[float] = None, 
                     error_message: str = None):
        """
        Met à jour le statut et les informations de traitement.
        
        Args:
            status: Nouveau statut
            description: Nouvelle description (optionnel)
            keywords: Nouveaux mots-clés (optionnel)
            embedding: Nouvel embedding (optionnel)
            error_message: Message d'erreur (optionnel)
        """
        self.status = status
        
        # Mettre à jour les timestamps
        now = datetime.now()
        if status == ProcessingStatus.IN_PROGRESS and not self.processing_start_time:
            self.processing_start_time = now
        elif status in [ProcessingStatus.COMPLETED, ProcessingStatus.ERROR]:
            self.processing_end_time = now
        
        # Mettre à jour les autres champs
        if description is not None:
            self.description = description
        if keywords is not None:
            self.keywords = keywords
        if embedding is not None:
            self.embedding = embedding
        if error_message is not None:
            self.error_message = error_message
    
    def reset_processing(self):
        """Réinitialise les informations de traitement"""
        self.status = ProcessingStatus.NOT_STARTED
        self.description = ""
        self.keywords = []
        self.embedding = []
        self.error_message = ""
        self.processing_start_time = None
        self.processing_end_time = None
    
    def matches_tags(self, tags: List[str]) -> bool:
        """Vérifie si l'image correspond à au moins un des tags"""
        if not tags:
            return True
        return any(tag.lower() in [kw.lower() for kw in self.keywords] for tag in tags)
    
    def get_file_info(self) -> dict:
        """Retourne les informations sur le fichier"""
        return {
            "name": self.name,
            "stem": self.stem,
            "suffix": self.suffix,
            "size": self.size,
            "size_mb": round(self.size / (1024 * 1024), 2),
            "path": str(self.path),
            "exists": self.path.exists(),
            "is_readable": self.path.exists() and os.access(self.path, os.R_OK)
        }
    
    def __str__(self) -> str:
        """Représentation textuelle de l'objet ImageInfo."""
        status_emoji = {
            ProcessingStatus.NOT_STARTED: "-",
            ProcessingStatus.IN_PROGRESS: "...", 
            ProcessingStatus.COMPLETED: "OK",
            ProcessingStatus.ERROR: "ERR"
        }
        
        emoji = status_emoji.get(self.status, "?")
        
        return f"{emoji} ImageInfo(name='{self.name}', score={self.score:.3f}, status={self.status.value})"
    
    def __repr__(self) -> str:
        """Représentation détaillée de l'objet."""
        return (f"ImageInfo(id='{self.id}', path='{self.path}', score={self.score}, "
                f"status={self.status.value}, keywords={len(self.keywords)}, "
                f"embedding={len(self.embedding)}, description='{self.description}')")
    
    def __eq__(self, other) -> bool:
        """Comparaison basée sur le chemin du fichier."""
        if isinstance(other, ImageInfo):
            return self.path.resolve() == other.path.resolve()
        return False
    
    def __hash__(self) -> int:
        """Hash basé sur le chemin du fichier."""
        return hash(str(self.path.resolve()))
    
    def copy(self) -> 'ImageInfo':
        """Crée une copie de l'objet."""
        return ImageInfo(
            path=self.path,
            score=self.score,
            status=self.status,
            description=self.description,
            keywords=self.keywords.copy(),
            embedding=self.embedding.copy(),
            error_message=self.error_message,
            processing_start_time=self.processing_start_time,
            processing_end_time=self.processing_end_time,
            image_id=self.id
        )
    
    def save_as_json(self, file_path: str):
        """Fonction désactivée - plus de sauvegarde JSON cache"""
        pass
