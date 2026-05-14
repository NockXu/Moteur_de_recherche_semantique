import sys

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QWidget, QLabel
from ui.ImportTool.widget.ConnectionVerificator.ConnectionVerificatorView import ConnectionVerificatorView
from ui.ImportTool.widget.ConnectionVerificator.ConnectionVerificatorModel import ConnectionVerificatorModel, State
from threading import Thread
import time


class ConnectionWorker(QThread):
    """Worker thread pour la vérification de connexion asynchrone"""
    
    # Signaux
    check_completed = pyqtSignal(State, str, str)  # state, version, error_message
    check_error = pyqtSignal(str)  # error_message
    
    def __init__(self, model: ConnectionVerificatorModel):
        super().__init__()
        self.model = model
        self._should_stop = False
        
    def run(self):
        """Exécute la vérification de connexion"""
        try:
            if self._should_stop:
                return
                
            # Vérifier la connexion
            state = self.model.check_connection()
            
            if self._should_stop:
                return
                
            # Émettre le résultat
            self.check_completed.emit(
                state,
                self.model.version,
                self.model.error_message
            )
            
        except Exception as e:
            if not self._should_stop:
                self.check_error.emit(str(e))
    
    def stop(self):
        """Arrête le worker"""
        self._should_stop = True


class ConnectionVerificatorController(QObject):
    """Contrôleur pour le vérificateur de connexion"""
    
    # Signaux
    connection_status_changed = pyqtSignal(State, str, str)  # state, version, error_message
    
    def __init__(self, base_url: str = None, timeout_s: float = 10.0, check_interval_s: int = 30, parent=None):
        super().__init__(parent)
        
        # Initialiser le modèle et la vue
        self.model = ConnectionVerificatorModel(base_url, timeout_s)
        self.view = ConnectionVerificatorView()
        
        # Worker pour les vérifications asynchrones
        self.worker = None
        self.is_checking = False
        
        # Timer pour la vérification automatique (démarré après la 1ère vérification)
        self.auto_check_timer = QTimer()
        self.auto_check_timer.timeout.connect(self.check_connection)
        self.auto_check_timer.setInterval(check_interval_s * 1000)  # Convertir en millisecondes
        
        # Première vérification immédiate (le timer auto démarre après dans _on_check_completed)
        QTimer.singleShot(100, self.check_connection)
    
    def check_connection(self):
        """Démarre une vérification de connexion"""
        if self.is_checking:
            # Si déjà en cours, ignorer la demande
            return
        
        # Démarrer une nouvelle vérification
        self._start_checking()
    
    def _start_checking(self):
        """Démarre le processus de vérification"""
        self.is_checking = True
        self.view.set_checking(True)
        
        # Créer et démarrer le worker
        self.worker = ConnectionWorker(self.model)
        self.worker.check_completed.connect(self._on_check_completed)
        self.worker.check_error.connect(self._on_check_error)
        self.worker.start()
    
    def _stop_checking(self):
        """Arrête le processus de vérification"""
        if self.worker:
            self.worker.stop()
            self.worker.wait(1000)  # Attendre max 1 seconde
            self.worker = None
        
        self.is_checking = False
        self.view.set_checking(False)
    
    def _on_check_completed(self, state: State, version: str, error_message: str):
        """Gère la fin de la vérification"""
        self.is_checking = False
        self.worker = None
        
        # Mettre à jour la vue
        self.view.update_status(state, version, error_message)
        
        # Émettre le signal
        self.connection_status_changed.emit(state, version, error_message)
        
        # Démarrer le timer automatique si pas déjà actif
        if not self.auto_check_timer.isActive():
            self.auto_check_timer.start()
    
    def _on_check_error(self, error_message: str):
        """Gère les erreurs de vérification"""
        self.is_checking = False
        self.worker = None
        
        # Mettre à jour la vue avec l'erreur
        self.view.update_status(State.ERROR, "", error_message)
        
        # Émettre le signal
        self.connection_status_changed.emit(State.ERROR, "", error_message)
        
        # Démarrer le timer automatique si pas déjà actif
        if not self.auto_check_timer.isActive():
            self.auto_check_timer.start()
    
    def get_current_state(self) -> State:
        """Retourne l'état actuel de la connexion"""
        return self.model.state
    
    def is_connected(self) -> bool:
        """Retourne True si la connexion est active"""
        return self.model.is_connected()
    
    def get_status_info(self) -> dict:
        """Retourne toutes les informations de statut"""
        return self.model.get_status_info()
    
    def get_view(self) -> QWidget:
        """Retourne la vue"""
        return self.view
    
    def cleanup(self):
        """Nettoie les ressources"""
        self._stop_checking()
        self.auto_check_timer.stop()


# Fonction utilitaire pour créer une instance complète
def create_connection_verificator(base_url: str = None, timeout_s: float = 10.0) -> ConnectionVerificatorController:
    """Crée une instance complète du vérificateur de connexion"""
    return ConnectionVerificatorController(base_url, timeout_s)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Test ConnectionVerificatorController")
            self.setGeometry(100, 100, 500, 200)
            
            # Créer le contrôleur
            self.controller = ConnectionVerificatorController()
            
            # Connecter les signaux pour le test
            self.controller.connection_status_changed.connect(self._on_status_changed)
            
            # Créer le widget principal
            central_widget = QWidget()
            layout = QVBoxLayout(central_widget)
            
            # Ajouter la vue du vérificateur
            layout.addWidget(self.controller.get_view())
            
            # Label pour afficher les informations
            self.info_label = QLabel("En attente...")
            self.info_label.setWordWrap(True)
            layout.addWidget(self.info_label)
            
            self.setCentralWidget(central_widget)
        
        def _on_status_changed(self, state: State, version: str, error_message: str):
            """Gère les changements de statut"""
            info = f"État: {state.value}\n"
            if version:
                info += f"Version: {version}\n"
            if error_message:
                info += f"Erreur: {error_message}"
            self.info_label.setText(info)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())