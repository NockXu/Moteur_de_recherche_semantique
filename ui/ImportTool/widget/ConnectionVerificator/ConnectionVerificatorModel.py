import sys
import os

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

from ui.utils.i18n import tr

class State(Enum):
    """États de connexion possibles"""
    DISCONNECTED = "non_connecté"
    CONNECTED = "connecté"
    ERROR = "erreur_connection"


class ConnectionVerificatorModel:
    def __init__(self, base_url: str = None, timeout_s: float = 10.0):
        # Utiliser la variable d'environnement si base_url n'est pas fourni
        if base_url is None:
            base_url = os.getenv('OLLAMA_BASE_URL', 'http://10.22.28.190:11434')
        
        self.base_url = base_url
        self.timeout_s = timeout_s
        self._state = State.DISCONNECTED
        self._error_message = ""
        self._version = ""
        
    @property
    def state(self) -> State:
        """Retourne l'état actuel de la connexion"""
        return self._state
    
    @property
    def error_message(self) -> str:
        """Retourne le message d'erreur si l'état est ERROR"""
        return self._error_message
    
    @property
    def version(self) -> str:
        """Retourne la version du serveur si connecté"""
        return self._version
    
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
                self._version = wrapper.get_version()
                self._state = State.CONNECTED
                self._error_message = ""
            else:
                self._state = State.DISCONNECTED
                self._error_message = tr("Serveur Ollama non démarré ou inaccessible")
                self._version = ""
                
        except OllamaConnectionError as e:
            self._state = State.ERROR
            self._error_message = f"{tr('Erreur de connexion')}: {str(e)}"
            self._version = ""
            
        except OllamaResponseError as e:
            self._state = State.ERROR
            self._error_message = f"{tr('Réponse invalide du serveur')}: {str(e)}"
            self._version = ""
            
        except Exception as e:
            self._state = State.ERROR
            self._error_message = f"{tr('Erreur inattendue')}: {str(e)}"
            self._version = ""
        
        return self._state
    
    def is_connected(self) -> bool:
        """Retourne True si la connexion est active"""
        return self._state == State.CONNECTED
    
    def has_error(self) -> bool:
        """Retourne True si il y a une erreur de connexion"""
        return self._state == State.ERROR
    
    def reset(self) -> None:
        """Réinitialise l'état à DISCONNECTED"""
        self._state = State.DISCONNECTED
        self._error_message = ""
        self._version = ""
    
    def get_status_info(self) -> dict:
        """
        Retourne un dictionnaire avec toutes les informations de statut
        
        Returns:
            dict: Informations sur l'état de connexion
        """
        return {
            "state": self._state.value,
            "is_connected": self.is_connected(),
            "has_error": self.has_error(),
            "error_message": self._error_message,
            "version": self._version,
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
        print(f"Erreur: {verifier.error_message}")
    else:
        print(f"Non connecté: {verifier.error_message}")
    
    # Afficher toutes les informations
    print("\nInformations complètes:")
    info = verifier.get_status_info()
    for key, value in info.items():
        print(f"  {key}: {value}")