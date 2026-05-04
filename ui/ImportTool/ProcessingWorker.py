from PyQt6.QtCore import QThread, pyqtSignal
from typing import List, Callable, Optional
import sys
import os

# Ajouter le chemin racine du projet au sys.path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from vision.ollama_wrapper import OllamaWrapper
from vision.ImageProcessor import ImageProcessor
from database.DatabaseManager import insert_image
from common.ImageInfo import ProcessingStatus, ImageInfo


class ProcessingWorker(QThread):
    """Worker thread pour traiter les images en arrière-plan"""
    
    # Signaux
    progress_updated = pyqtSignal(str, ProcessingStatus)  # image_path, status
    image_processed = pyqtSignal(str, str, list)  # image_path, description, embedding
    image_error = pyqtSignal(str, str)  # image_path, error_message
    processing_complete = pyqtSignal()
    processing_stopped = pyqtSignal()  # Nouveau : émis quand on arrête manuellement
    
    def __init__(self, images: List[ImageInfo], ollama_wrapper: OllamaWrapper = None, model: str = "qwen2.5vl:7b"):
        super().__init__()
        self.images = images
        self.ollama_wrapper = ollama_wrapper
        self.model = model
        self._is_running = False
        self._current_index = 0
        
        # Initialiser l'ImageProcessor si le wrapper est disponible
        self.image_processor = None
        if self.ollama_wrapper:
            self.image_processor = ImageProcessor(self.ollama_wrapper, self.model)
    
    def run(self):
        """Traite toutes les images"""
        self._is_running = True
        self._current_index = 0
        stopped_manually = False
        
        try:
            for i, image_info in enumerate(self.images):
                # Vérifier fréquemment si on doit arrêter
                if not self._is_running:
                    print("ProcessingWorker interrompu")
                    stopped_manually = True
                    break
                
                self._current_index = i
                
                try:
                    self._process_single_image(image_info)
                except Exception as e:
                    print(f"Erreur traitement image {image_info.path.name}: {e}")
                    # Continuer avec les autres images même si une échoue
                    continue
            
        except Exception as e:
            print(f"Erreur globale dans ProcessingWorker: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self._is_running = False
            print("🏁 ProcessingWorker terminé")
            # Émettre le bon signal selon comment on a terminé
            if stopped_manually:
                self.processing_stopped.emit()
            else:
                self.processing_complete.emit()
    
    def _process_single_image(self, image_info: ImageInfo):
        """Traite une seule image en utilisant ImageProcessor"""
        try:
            # Vérifier si l'image est déjà traitée
            if image_info.status == ProcessingStatus.COMPLETED and "Déjà traitée" in image_info.description:
                print(f"⏭️  Image {image_info.name} déjà traitée, saut")
                return
            
            # Signaler le début du traitement
            image_info.status = ProcessingStatus.IN_PROGRESS
            self.progress_updated.emit(str(image_info.path), ProcessingStatus.IN_PROGRESS)
            
            if not self.image_processor:
                raise RuntimeError("ImageProcessor non initialisé - wrapper Ollama manquant")
            
            # Étape 1: Générer description et keywords avec ImageProcessor
            if not self._is_running:
                return
            
            self.image_processor.ImageToData(image_info)
            
            if not self._is_running:
                print("Arret demandé après génération description")
                return
            
            if not image_info.description:
                raise RuntimeError("Impossible de générer une description pour l'image")
            
            # Étape 2: Créer l'embedding à partir de la description
            if not self._is_running:
                print("Arret demandé avant création embedding")
                return
            
            self.image_processor.TextToEmbedding(image_info)
            
            if not self._is_running:
                print("Arret demandé après création embedding")
                return
            
            if not image_info.embedding:
                raise RuntimeError("Impossible de créer l'embedding")
            
            # Étape 3: Enregistrer en base de données
            try:
                success = insert_image(image_info)
                if success:
                    print(f"✅ Image {image_info.name} enregistrée en BDD")
                else:
                    print(f"❌ Erreur enregistrement BDD pour {image_info.name}")
            except Exception as e:
                print(f"❌ Erreur BDD pour {image_info.name}: {e}")
            
            # Signaler le succès
            self.progress_updated.emit(str(image_info.path), ProcessingStatus.COMPLETED)
            self.image_processed.emit(str(image_info.path), image_info.description, image_info.embedding)
            
        except Exception as e:
            # Signaler l'erreur
            error_msg = str(e)
            image_info.status = ProcessingStatus.ERROR
            image_info.error_message = error_msg
            self.progress_updated.emit(str(image_info.path), ProcessingStatus.ERROR)
            self.image_error.emit(str(image_info.path), error_msg)
    
    def stop(self):
        """Arrêt brutal du thread (plus rapide)"""
        print("Arrêt forcé du ProcessingWorker...")
        self._is_running = False
        self.terminate()   # Arrêt immédiat
        self.wait()        # Attendre la terminaison
        print("Thread terminé")
        # NE PAS émettre ici - run() va émettre le signal
    
    def is_running(self) -> bool:
        """Vérifie si le traitement est en cours"""
        return self._is_running
    
    def get_progress(self) -> float:
        """Retourne la progression actuelle (0.0 à 1.0)"""
        if not self.images:
            return 1.0
        
        return self._current_index / len(self.images)
    
    def get_current_image(self) -> Optional[str]:
        """Retourne le chemin de l'image actuellement traitée"""
        if 0 <= self._current_index < len(self.images):
            return str(self.images[self._current_index].path)
        return None


class BatchProcessingManager:
    """Gestionnaire pour traiter plusieurs lots d'images"""
    
    def __init__(self, ollama_wrapper: OllamaWrapper = None):
        self.ollama_wrapper = ollama_wrapper
        self.current_worker = None
    
    def start_batch_processing(self, images: List[ImageInfo], 
                             on_progress: Callable = None,
                             on_image_processed: Callable = None,
                             on_image_error: Callable = None,
                             on_complete: Callable = None,
                             on_stopped: Callable = None,
                             model: str = "qwen2.5vl:7b") -> ProcessingWorker:
        """Démarre le traitement par lot"""
        
        if self.current_worker and self.current_worker.isRunning():
            raise RuntimeError("Un traitement est déjà en cours")
        
        # Créer et configurer le worker avec toutes les images
        self.current_worker = ProcessingWorker(images, self.ollama_wrapper, model)
        
        # Connecter les signaux
        if on_progress:
            self.current_worker.progress_updated.connect(on_progress)
        if on_image_processed:
            self.current_worker.image_processed.connect(on_image_processed)
        if on_image_error:
            self.current_worker.image_error.connect(on_image_error)
        if on_complete:
            self.current_worker.processing_complete.connect(on_complete)
        if on_stopped:
            self.current_worker.processing_stopped.connect(on_stopped)
        
        # Démarrer le worker
        self.current_worker.start()
        
        return self.current_worker
    
    def stop_current_processing(self):
        """Arrête le traitement immédiatement (terminate + wait)"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.stop()  # terminate() + wait() + emit processing_stopped
    
    def is_processing(self) -> bool:
        """Vérifie si un traitement est en cours"""
        return (self.current_worker is not None and 
                self.current_worker.isRunning())
    
    def get_current_progress(self) -> float:
        """Retourne la progression du traitement actuel"""
        if self.current_worker:
            return self.current_worker.get_progress()
        return 1.0