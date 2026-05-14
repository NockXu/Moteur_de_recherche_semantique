import sys
import os
from pathlib import Path

# Ajouter le chemin racine du projet au sys.path pour les imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# On doit remonter d'un niveau supplémentaire pour arriver à la racine du projet
project_root = os.path.dirname(project_root)
sys.path.append(project_root)

# Charger les variables d'environnement depuis le fichier .env
from dotenv import load_dotenv
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path)

from enum import Enum
from vision.ollama_wrapper import OllamaWrapper, OllamaConnectionError, OllamaResponseError

class ConnectionStatus():
    def __init__(self, icon : Path, value : str, version : str = ""):
        self.icon = icon
        self.value = value
        self.version = version

class State(Enum):
    """États de connexion possibles"""
    DISCONNECTED = ConnectionStatus(Path("ui/Icon/circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"), "déconnecté")
    CONNECTED = ConnectionStatus(Path("ui/Icon/check_circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"), "connecté")
    CHECKING = ConnectionStatus(Path("ui/Icon/change_circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"), "en cours")
    ERROR = ConnectionStatus(Path("ui/Icon/x_circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"), "erreur")


class ConnectionVerificatorModel:
    def __init__(self, base_url: str = None, timeout_s: float = 10.0):
        # Utiliser la variable d'environnement si base_url n'est pas fourni
        if base_url is None:
            base_url = os.getenv('OLLAMA_BASE_URL', 'http://10.22.28.190:11434')
        
        self.base_url = base_url
        self.timeout_s = timeout_s
        self._connection_status = State.DISCONNECTED
        
    @property
    def state(self) -> State:
        """Retourne l'état actuel de la connexion"""
        return self._connection_status.value
    
    @property
    def version(self) -> str:
        """Retourne la version du serveur si connecté"""
        return self._connection_status.version
    
    def check_connection(self) -> State:
        """
        Vérifie la connexion au serveur Ollama et met à jour l'état
        
        Returns:
            State: Le nouvel état de connexion
        """
        try:
            # Créer un wrapper avec les paramètres actuels
            wrapper = OllamaWrapper(base_url=self.base_url, timeout_s=self.timeout_s)
            
            # Vérifier si le serveur est en cours d'exécution
            if wrapper.is_server_running():
                # Récupérer la version pour confirmation
                self._connection_status.version = wrapper.get_version()
                self._connection_status = State.CONNECTED
            else:
                self._connection_status.version = ""
                self._connection_status = State.DISCONNECTED
            
        except Exception as e:
            self._connection_status.version = ""
            self._connection_status = State.ERROR
        
        return self._connection_status
    
    def is_connected(self) -> bool:
        """Retourne True si la connexion est active"""
        return self._connection_status == State.CONNECTED
    
    def has_error(self) -> bool:
        """Retourne True si il y a une erreur de connexion"""
        return self._connection_status == State.ERROR
    
    def reset(self) -> None:
        """Réinitialise l'état à DISCONNECTED"""
        self._connection_status = State.DISCONNECTED
        self._connection_status.version = ""
    
    def get_status_info(self) -> dict:
        """
        Retourne un dictionnaire avec toutes les informations de statut
        
        Returns:
            dict: Informations sur l'état de connexion
        """
        return {
            "state": self.state,
            "is_connected": self.is_connected(),
            "has_error": self.has_error(),
            "version": self.version,
            "base_url": self.base_url,
            "timeout": self.timeout_s
        }


if __name__ == "__main__":
    # Test simple de la classe
    print("Test de ConnectionVerificatorModel")
    print(f"Variable d'environnement OLLAMA_BASE_URL: {os.getenv('OLLAMA_BASE_URL', 'Non définie')}")
    
    # Créer une instance
    verifier = ConnectionVerificatorModel()
    print(f"État initial: {verifier.state.value}")
    print(f"URL utilisée: {verifier.base_url}")
    
    # Vérifier la connexion
    print("\nVérification de la connexion...")
    state = verifier.check_connection()
    print(f"Nouvel état: {state.value}")
    
    if verifier.is_connected():
        print(f"Connecté - Version: {verifier.version}")
    elif verifier.has_error():
        print(f"Erreur: {verifier.state}")
    else:
        print(f"Non connecté: {verifier.state}")
    
    # Afficher toutes les informations
    print("\nInformations complètes:")
    info = verifier.get_status_info()
    for key, value in info.items():
        print(f"  {key}: {value}")