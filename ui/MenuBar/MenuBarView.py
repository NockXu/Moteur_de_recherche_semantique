import sys
import os
from typing import Dict, List
from collections.abc import Callable

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import QMenuBar, QMenu
from PyQt6.QtGui import QFont, QAction

from .MenuModel import MenuAction


class MenuBarView:
    """Vue pour la barre de menu"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.menu_bar = QMenuBar()
        self.menu_bar.setFont(QFont("Segoe UI", 10))
    
    def create_menu_bar(self, menu_structure: dict[str, list[MenuAction]], handlers: dict[str, Callable]):
        """Crée la barre de menu à partir de la structure et des handlers"""
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
    
    def get_menu_bar(self):
        """Retourne la barre de menu créée"""
        return self.menu_bar
    
    def clear(self):
        """Vide la barre de menu"""
        self.menu_bar.clear()
    
    def set_font(self, font: QFont):
        """Définit la police de la barre de menu"""
        self.menu_bar.setFont(font)
