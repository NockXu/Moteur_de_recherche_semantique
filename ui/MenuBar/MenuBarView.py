import sys
import os
from typing import Dict, List
from collections.abc import Callable

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import QMenuBar, QMenu
from PyQt6.QtGui import QFont, QAction

from .MenuModel import MenuAction


class MenuBarView:
    """View responsible for rendering and styling the main application menu bar.

    This class instantiates a QMenuBar instance and dynamically populates it 
    with menus and sub-actions based on a provided configuration map.

    Args:
        parent (QWidget, optional):
            The parent widget layout containing this top menu bar. Defaults to None.

    """
    
    def __init__(self, parent=None):
        self.parent = parent
        self.menu_bar = QMenuBar()
        self.menu_bar.setFont(QFont("Segoe UI", 10))
    
    def create_menu_bar(self, menu_structure: dict[str, list[MenuAction]], handlers: dict[str, Callable]) -> QMenuBar:
        """Populate and structure the window menu bar using configuration maps.

        This clears any existing menu tabs before compiling actions and 
        binding event triggers in their sequential layout.

        Args:
            menu_structure (dict[str, list[MenuAction]]):
                A map dictionary defining category names linked to item definitions.
            handlers (dict[str, Callable]):
                Fallback callback mappings referenced using action name strings.

        Returns:
            The fully built and connected QMenuBar instance framework.

        """
        self.menu_bar.clear()
        
        for menu_name, actions in menu_structure.items():
            menu = self.menu_bar.addMenu(menu_name)
            
            for action_config in actions:
                # Ajouter séparateur avant si nécessaire
                if action_config.separator_before:
                    menu.addSeparator()
                
                # Créer l'action
                action = QAction(action_config.name, self.parent)
                
                if action_config.shortcut:
                    action.setShortcut(action_config.shortcut)
                
                if action_config.tooltip:
                    action.setStatusTip(action_config.tooltip)
                
                if action_config.handler:
                    action.triggered.connect(action_config.handler)
                elif action_config.name in handlers:
                    action.triggered.connect(handlers[action_config.name])
                elif action_config.signal:
                    action.triggered.connect(action_config.signal)
                
                menu.addAction(action)
                
                # Ajouter séparateur après si nécessaire
                if action_config.separator_after:
                    menu.addSeparator()
        
        return self.menu_bar
    
    def get_menu_bar(self) -> QMenuBar:
        """Retrieve the primary menu bar visual widget element.

        Returns:
            The underlying QMenuBar object instance.

        """
        return self.menu_bar
    
    def clear(self) -> None:
        """Purge all active categories and action objects from the menu layouts."""
        self.menu_bar.clear()
    
    def set_font(self, font: QFont) -> None:
        """Apply a customized font typography configuration profile to the component.

        Args:
            font (QFont):
                The typography configuration description object to use.

        """
        self.menu_bar.setFont(font)
