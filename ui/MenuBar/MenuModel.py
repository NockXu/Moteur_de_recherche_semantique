from typing import Dict, List, Optional, Union
from dataclasses import dataclass

from PyQt6.QtCore import pyqtSignal

from ui.utils.i18n import tr

@dataclass
class MenuAction:
    """Configuration d'une action de menu"""

    name: str
    shortcut: Union[str, None] = None
    tooltip: Union[str, None] = None
    handler: Union[callable, None] = None
    signal: Union[pyqtSignal, None] = None
    separator_before: bool = False
    separator_after: bool = False


class MenuModel:
    """Modèle pour la structure du menu"""
    
    def __init__(self):
        self.menus: dict[str, list[MenuAction]] = {
            tr("Fichier"): [
                MenuAction(
                    name=tr("Importer"),
                    shortcut="Ctrl+I",
                    tooltip=tr("Importer des images dans la base"),
                    signal=None  # Sera défini par le contrôleur
                ),
                MenuAction(
                    name=f"{tr("Exporter")}...",
                    shortcut="Ctrl+E",
                    tooltip=tr("Exporter les données de la base"),
                    signal=None  # Sera défini par le contrôleur
                ),
                MenuAction(
                    name=tr("Quitter"),
                    shortcut="Ctrl+Q",
                    tooltip=tr("Quitter l'application"),
                    signal=None  # Sera défini par le contrôleur
                ),
            ],
            tr("Outils"): [
                MenuAction(
                    name=tr("Outil d'importation d'image"),
                    shortcut="Ctrl+T",
                    tooltip=tr("Afficher/Masquer le panneau d'import d'images"),
                    signal=None  # Sera défini par le contrôleur
                ),
            ],
            tr("Styles"): [
                MenuAction(
                    name=tr("Sélection du thème"),
                    tooltip=tr("Sélectionner un thème pour l'application"),
                    signal=None  # Sera défini par le contrôleur
                ),
            ]
        }
    
    def add_menu(self, menu_name: str, actions: list[MenuAction]):
        """Ajoute un nouveau menu avec ses actions"""
        self.menus[menu_name] = actions
    
    def add_action(self, menu_name: str, action: MenuAction):
        """Ajoute une action à un menu existant"""
        if menu_name not in self.menus:
            self.menus[menu_name] = []
        self.menus[menu_name].append(action)
    
    def get_menus(self) -> dict[str, list[MenuAction]]:
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
