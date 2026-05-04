import sys
import os
from PyQt6.QtCore import QObject, QThread, pyqtSignal

# Ajouter le chemin racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Import direct en utilisant le chemin racine déjà configuré
from ui.ImageSearchedContainer.AutoResearch import AutoResearch


class EmbeddingWorker(QObject):
    """Worker pour effectuer la recherche sémantique dans un thread séparé"""
    finished = pyqtSignal(list)  # Signal émis quand la recherche est terminée
    error = pyqtSignal(str)     # Signal émis en cas d'erreur
    
    def __init__(self, query, auto_research=None):
        super().__init__()
        self.query = query
        self.auto_research = auto_research or AutoResearch()
    
    def run(self):
        """Effectue la recherche sémantique de manière synchrone dans ce thread"""
        try:
            # Utiliser AutoResearch pour faire la recherche
            results = self.auto_research.find(query=self.query)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(f"Erreur lors de la recherche: {str(e)}")


class AsyncEmbeddingManager:
    """Gestionnaire pour lancer des recherches sémantiques asynchrones"""
    
    def __init__(self):
        self.current_worker = None
        self.current_thread = None
    
    def start_search(self, query, auto_research=None, on_finished=None, on_error=None):
        """Démarre une recherche sémantique asynchrone"""
        # Nettoyer le thread précédent s'il existe
        if self.current_thread:
            if self.current_thread.isRunning():
                self.current_thread.quit()
                self.current_thread.wait()
            self.current_thread = None
            self.current_worker = None
        
        # Créer le worker et le thread
        self.current_worker = EmbeddingWorker(query, auto_research)
        self.current_thread = QThread()
        
        # Déplacer le worker vers le thread
        self.current_worker.moveToThread(self.current_thread)
        
        # Connecter les signaux
        self.current_thread.started.connect(self.current_worker.run)
        
        # Nettoyer automatiquement quand terminé
        self.current_worker.finished.connect(self._cleanup_thread)
        
        # Connecter les callbacks personnalisés
        if on_finished:
            self.current_worker.finished.connect(on_finished)
        if on_error:
            self.current_worker.error.connect(on_error)
        
        # Démarrer le thread
        self.current_thread.start()
        
        return self.current_worker, self.current_thread
    
    def _cleanup_thread(self):
        """Nettoie le thread et le worker après exécution"""
        if self.current_thread:
            if self.current_thread.isRunning():
                self.current_thread.quit()
                self.current_thread.wait(1000)  # Attendre max 1 seconde
            self.current_thread.deleteLater()
            self.current_thread = None
        if self.current_worker:
            self.current_worker.deleteLater()
            self.current_worker = None
    
    def is_running(self):
        """Vérifie si une recherche est en cours"""
        return self.current_thread and self.current_thread.isRunning()
    
    def stop_search(self):
        """Arrête la recherche en cours"""
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.quit()
            self.current_thread.wait()
    
    # Méthode pour compatibilité avec l'ancien code
    def start_embedding(self, model, text, wrapper=None, on_finished=None, on_error=None):
        """Méthode de compatibilité - utilise start_search à la place"""
        return self.start_search(text, on_finished=on_finished, on_error=on_error)
