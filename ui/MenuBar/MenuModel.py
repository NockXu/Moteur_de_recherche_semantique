import sys
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtCore import pyqtSignal


@dataclass
class MenuAction:
    """Configuration d'une action de menu"""
    name: str
    shortcut: Optional[str] = None
    tooltip: Optional[str] = None
    handler: Optional[callable] = None
    signal: Optional[pyqtSignal] = None
    separator_before: bool = False
    separator_after: bool = False


class MenuModel:
    """Modèle pour la structure du menu"""
    
    def __init__(self):
        self.menus: Dict[str, List[MenuAction]] = {
            "Fichier": [
                MenuAction(
                    name="Importer",
                    shortcut="Ctrl+I",
                    tooltip="Importer des images dans la base",
                    signal=None  # Sera défini par le contrôleur
                ),
                MenuAction(
                    name="Exporter...",
                    shortcut="Ctrl+E",
                    tooltip="Exporter les données de la base",
                    signal=None  # Sera défini par le contrôleur
                ),
                MenuAction(
                    name="Quitter",
                    shortcut="Ctrl+Q",
                    tooltip="Quitter l'application",
                    signal=None  # Sera défini par le contrôleur
                ),
            ],
            "Outils": [
                MenuAction(
                    name="Outil d'importation d'image",
                    shortcut="Ctrl+T",
                    tooltip="Afficher/Masquer le panneau d'import d'images",
                    signal=None  # Sera défini par le contrôleur
                ),
            ],
            "Styles": [
                MenuAction(
                    name="Selectionner un style",
                    shortcut="",
                    tooltip="Sélectionner un style pour l'application",
                    signal=None  # Sera défini par le contrôleur
                )
            ]
        }
    
    def add_menu(self, menu_name: str, actions: List[MenuAction]):
        """Ajoute un nouveau menu avec ses actions"""
        self.menus[menu_name] = actions
    
    def add_action(self, menu_name: str, action: MenuAction):
        """Ajoute une action à un menu existant"""
        if menu_name not in self.menus:
            self.menus[menu_name] = []
        self.menus[menu_name].append(action)
    
    def get_menus(self) -> Dict[str, List[MenuAction]]:
        """Retourne la structure complète des menus"""
        return self.menus
    
    def remove_menu(self, menu_name: str):
        """Supprime un menu entier"""
        if menu_name in self.menus:
            del self.menus[menu_name]
    
    def remove_action(self, menu_name: str, action_name: str):
        """Supprime une action spécifique d'un menu"""
        if menu_name in self.menus:
            self.menus[menu_name] = [
                action for action in self.menus[menu_name] 
                if action.name != action_name
            ]
    
    def clear(self):
        """Vide tous les menus"""
        self.menus.clear()
