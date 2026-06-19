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
    """Enumeration mapping of all possible backend server communication connection states."""

    DISCONNECTED = "non_connecté"
    CONNECTED = "connecté"
    ERROR = "erreur_connection"


class ConnectionVerificatorModel:
    """Model tracking server communication parameters, response payloads, and exception state caches.

    Args:
        base_url (str):
            The targeted endpoint link network directory string. Defaults to None.
        timeout_s (float):
            Network verification expiration threshold limitation duration given in seconds. Defaults to 10.0.

    """
    
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
        """Fetch the active monitoring connection status tracking flag.

        Returns:
            The current communication enum State context tracker.

        """
        return self._state
    
    @property
    def error_message(self) -> str:
        """Fetch saved network diagnostic exception traces recorded if operational errors occurred.

        Returns:
            The raw error logging message content.

        """
        return self._error_message
    
    @property
    def version(self) -> str:
        """Fetch the firmware engine version string returned by successfully established server connections.

        Returns:
            The compiled build metadata sequence identifier.

        """
        return self._version
    
    def check_connection(self) -> State:
        """Query endpoints to update target status logs and record interface response versions.
        
        Returns:
            State: The newly verified lifecycle monitoring evaluation state.

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
            self._error_message = f"{tr('Erreur de connexion')}: {e!s}"
            self._version = ""
            
        except OllamaResponseError as e:
            self._state = State.ERROR
            self._error_message = f"{tr('Réponse invalide du serveur')}: {e!s}"
            self._version = ""
            
        except Exception as e:
            self._state = State.ERROR
            self._error_message = f"{tr('Erreur inattendue')}: {e!s}"
            self._version = ""
        
        return self._state
    
    def is_connected(self) -> bool:
        """Check if socket lines to remote backend listeners are open and active.

        Returns:
            True if variables register a completely successful connected property, otherwise False.

        """
        return self._state == State.CONNECTED
    
    def has_error(self) -> bool:
        """Check if operational failure traces have locked standard connection execution routes.

        Returns:
            True if variables match fault descriptions, otherwise False.

        """
        return self._state == State.ERROR
    
    def reset(self) -> None:
        """Revert local instance tracking metrics back to default uninitialized values."""
        self._state = State.DISCONNECTED
        self._error_message = ""
        self._version = ""
    
    def get_status_info(self) -> dict:
        """Compile an analytical metrics dictionary holding configuration values and trace information.
        
        Returns:
            dict: An information metadata mapping tracking model system state attributes.

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