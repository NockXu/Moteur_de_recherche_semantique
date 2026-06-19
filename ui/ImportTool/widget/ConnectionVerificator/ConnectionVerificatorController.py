import sys
import os

# Ajouter le chemin racine du projet au sys.path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QWidget, QLabel
from ui.ImportTool.widget.ConnectionVerificator.ConnectionVerificatorView import ConnectionVerificatorView
from ui.ImportTool.widget.ConnectionVerificator.ConnectionVerificatorModel import ConnectionVerificatorModel, State
from threading import Thread
import time


class ConnectionWorker(QThread):
    """Worker thread responsible for executing non-blocking asynchronous connection checks.

    Communicates lifecycle events and network responses back to the main GUI thread via Qt signals.

    Args:
        model (ConnectionVerificatorModel):
            The target data tracking structure used to process the endpoint ping check.

    """
    
    # Signaux
    check_completed = pyqtSignal(State, str, str)  # state, version, error_message
    check_error = pyqtSignal(str)  # error_message
    
    def __init__(self, model: ConnectionVerificatorModel):
        super().__init__()
        self.model = model
        self._should_stop = False
        
    def run(self):
        """Execute the target network verification logic loop inside the background thread context."""
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
        """Raise internal execution flags to gracefully abort ongoing connection task loops."""
        self._should_stop = True


class ConnectionVerificatorController(QObject):
    """Controller responsible for coordinating connection monitoring and state synchronization.

    Manages automated repetition polling, manages lifecycle scopes of concurrent background worker 
    threads, and forwards responses directly onto the matching layout components.

    Args:
        base_url (str):
            The API target address location to query. Defaults to None.
        timeout_s (float):
            Network expiration threshold restriction specified in seconds. Defaults to 10.0.
        check_interval_s (int):
            The delay interval duration between automated background tests. Defaults to 30.
        parent (QObject):
            Optional corporate Qt object scope container. Defaults to None.

    """
    
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
        """Initiate an asynchronous target connection state inspection routine if idle flags match."""
        if self.is_checking or (self.worker and self.worker.isRunning()):
            # Si déjà en cours, ignorer la demande
            return
        
        # Démarrer une nouvelle vérification
        self._start_checking()
    
    def _start_checking(self):
        """Instantiate tracking workers and configure dependent display layers for processing states."""
        self.is_checking = True
        self.view.set_checking(True)
        
        # Créer et démarrer le worker
        self.worker = ConnectionWorker(self.model)
        self.worker.check_completed.connect(self._on_check_completed)
        self.worker.check_error.connect(self._on_check_error)
        self.worker.finished.connect(lambda worker=self.worker: self._on_worker_finished(worker))
        self.worker.start()
    
    def _stop_checking(self):
        """Request active worker threads to halt processing routines and wait for thread termination."""
        if self.worker:
            self.worker.stop()
            if self.worker.isRunning():
                self.worker.wait()
        
        self.is_checking = False
        self.view.set_checking(False)
    
    def _on_check_completed(self, state: State, version: str, error_message: str):
        """Process verified responses, refresh layout views, and toggle recurrence timelines.

        Args:
            state (State):
                The verified lifecycle network state configuration target.
            version (str):
                The version string identifier retrieved from the remote backend service.
            error_message (str):
                The detailed trace data describing unexpected interface exceptions.

        """
        self.is_checking = False
        
        # Mettre à jour la vue
        self.view.update_status(state, version, error_message)
        
        # Émettre le signal
        self.connection_status_changed.emit(state, version, error_message)
        
        # Démarrer le timer automatique si pas déjà actif
        if not self.auto_check_timer.isActive():
            self.auto_check_timer.start()
    
    def _on_check_error(self, error_message: str):
        """Catch operational failures during evaluation routines and log exceptions onto layouts.

        Args:
            error_message (str):
                The diagnostic trace information string captured during evaluation.

        """
        self.is_checking = False
        
        # Mettre à jour la vue avec l'erreur
        self.view.update_status(State.ERROR, "", error_message)
        
        # Émettre le signal
        self.connection_status_changed.emit(State.ERROR, "", error_message)
        
        # Démarrer le timer automatique si pas déjà actif
        if not self.auto_check_timer.isActive():
            self.auto_check_timer.start()
    
    def get_current_state(self) -> State:
        """Fetch the current verification state registered inside the database model layer.

        Returns:
            The connection lifecycle enum tracker state representation.

        """
        return self.model.state
    
    def is_connected(self) -> bool:
        """Evaluate whether connection streams are active and communicating securely.

        Returns:
            True if the model status registers operational metrics, otherwise False.

        """
        return self.model.is_connected()
    
    def get_status_info(self) -> dict:
        """Compile a metadata dictionary map holding current state properties and exceptions.

        Returns:
            A metadata key-value mapping tracking active properties.

        """
        return self.model.get_status_info()
    
    def get_view(self) -> QWidget:
        """Fetch the visual status dashboard view display widget.

        Returns:
            The view layout widget container.

        """
        return self.view

    def _on_worker_finished(self, worker: ConnectionWorker):
        """Safely release pointer references only after the QThread context concludes execution.

        Args:
            worker (ConnectionWorker):
                The background worker thread object currently undergoing deallocation steps.

        """
        if self.worker is worker:
            self.worker = None
        worker.deleteLater()
    
    def cleanup(self):
        """Safely disconnect listening sockets, halt routine clocks, and abort active worker processes."""
        self._stop_checking()
        self.auto_check_timer.stop()


# Fonction utilitaire pour créer une instance complète
def create_connection_verificator(base_url: str = None, timeout_s: float = 10.0) -> ConnectionVerificatorController:
    """Helper factory routine initializing an isolated connection controller configuration.

    Args:
        base_url (str):
            The target link network directory value. Defaults to None.
        timeout_s (float):
            Network delay limits given in raw seconds format. Defaults to 10.0.

    Returns:
        A fully instantiated controller instance.

    """
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
