"""ConnectionVerificator Widget

Widget PyQt6 pour vérifier l'état de connexion au serveur Ollama.
Architecture MVC avec Model-View-Controller.
"""

from .ConnectionVerificatorModel import ConnectionVerificatorModel, State
from .ConnectionVerificatorView import ConnectionVerificatorView
from .ConnectionVerificatorController import ConnectionVerificatorController, create_connection_verificator

__all__ = [
    'ConnectionVerificatorController',
    'ConnectionVerificatorModel',
    'ConnectionVerificatorView',
    'State',
    'create_connection_verificator'
]
