from typing import Dict, List, Optional, Union
from dataclasses import dataclass

from PyQt6.QtCore import pyqtSignal

from ui.utils.i18n import tr

@dataclass
class MenuAction:
    """Configuration data for a menu action item.

    Attributes:
        name (str):
            The display text or label of the menu action.
        shortcut (str, optional):
            Keyboard shortcut string (e.g., 'Ctrl+I'). Defaults to None.
        tooltip (str, optional):
            Status bar or hover description text. Defaults to None.
        handler (callable, optional):
            The callback function triggered on execution. Defaults to None.
        signal (pyqtSignal, optional):
            Qt signal instance associated with the action. Defaults to None.
        separator_before (bool):
            Whether to place a separator visual bar before this item. Defaults to False.
        separator_after (bool):
            Whether to place a separator visual bar after this item. Defaults to False.

    """

    name: str
    shortcut: Union[str, None] = None
    tooltip: Union[str, None] = None
    handler: Union[callable, None] = None
    signal: Union[pyqtSignal, None] = None
    separator_before: bool = False
    separator_after: bool = False


class MenuModel:
    """Model responsible for maintaining the application menu bar structure.

    This class serves as a structured repository holding categorized 
    collections of MenuAction elements representing the UI layout.

    """
    
    def __init__(self):
        self.menus: dict[str, list[MenuAction]] = {
            tr("Fichier"): [
                MenuAction(
                    name=tr("Importer"),
                    shortcut="Ctrl+I",
                    tooltip=tr("Importer des images dans la base"),
                    signal=None  # Will be defined by the controller
                ),
                MenuAction(
                    name=f"{tr("Exporter")}...",
                    shortcut="Ctrl+E",
                    tooltip=tr("Exporter les données de la base"),
                    signal=None  # Will be defined by the controller
                ),
                MenuAction(
                    name=tr("Quitter"),
                    shortcut="Ctrl+Q",
                    tooltip=tr("Quitter l'application"),
                    signal=None  # Will be defined by the controller
                ),
            ],
            tr("Outils"): [
                MenuAction(
                    name=tr("Outil d'importation d'image"),
                    shortcut="Ctrl+T",
                    tooltip=tr("Afficher/Masquer le panneau d'import d'images"),
                    signal=None  # Will be defined by the controller
                ),
            ],
            tr("Styles"): [
                MenuAction(
                    name=tr("Sélection du thème"),
                    tooltip=tr("Sélectionner un thème pour l'application"),
                    signal=None  # Will be defined by the controller
                ),
            ]
        }
    
    def add_menu(self, menu_name: str, actions: list[MenuAction]) -> None:
        """Add a completely new menu section with its initial actions.

        Args:
            menu_name (str):
                The unique identifier name of the menu category.
            actions (list[MenuAction]):
                Collection of structural configuration items to populate under the key.

        """
        self.menus[menu_name] = actions
    
    def add_action(self, menu_name: str, action: MenuAction) -> None:
        """Append an individual menu action to an existing category list.

        Creates the structural category list on-the-fly if it does not yet exist.

        Args:
            menu_name (str):
                The identifier target category to attach the actions to.
            action (MenuAction):
                The individual action entry model configurations.

        """
        if menu_name not in self.menus:
            self.menus[menu_name] = []
        self.menus[menu_name].append(action)
    
    def get_menus(self) -> dict[str, list[MenuAction]]:
        """Retrieve the absolute map reference structure of all configured menus.

        Returns:
            Dictionary containing category names mapping to lists of MenuAction items.

        """
        return self.menus
    
    def remove_menu(self, menu_name: str) -> None:
        """Delete an entire category menu along with its underlying actions from the collection.

        Args:
            menu_name (str):
                The structural dictionary entry key name to purge.

        """
        if menu_name in self.menus:
            del self.menus[menu_name]
    
    def remove_action(self, menu_name: str, action_name: str) -> None:
        """Filter out a single unique action item out of a categorical list sequence.

        Args:
            menu_name (str):
                The dictionary map layer category section.
            action_name (str):
                The text target label property value to match and delete.

        """
        if menu_name in self.menus:
            self.menus[menu_name] = [
                action for action in self.menus[menu_name] 
                if action.name != action_name
            ]
    
    def clear(self):
        """Purge and reset the absolute collection mapping contents entirely."""
        self.menus.clear()
