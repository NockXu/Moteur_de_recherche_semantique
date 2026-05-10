import sys
import os
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import QMenuBar, QMenu, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QFont, QAction
from pathlib import Path

from ui.widgets.Export import Export
from ui.widgets.Import.AdvancedImportDialog import AdvancedImportDialog


@dataclass
class MenuAction:
    """Configuration d'une action de menu"""
    name: str
    shortcut: Optional[str] = None
    tooltip: Optional[str] = None
    handler: Optional[Callable] = None
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


class MenuBarView:
    """Vue pour la barre de menu"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.menu_bar = QMenuBar()
        self.menu_bar.setFont(QFont("Segoe UI", 10))
    
    def create_menu_bar(self, menu_structure: Dict[str, List[MenuAction]], handlers: Dict[str, Callable]):
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
                
                # Connecter le handler ou le signal
                if action_config.handler and action_config.name in handlers:
                    action.triggered.connect(handlers[action_config.name])
                elif action_config.signal:
                    action.triggered.connect(action_config.signal)
                
                menu.addAction(action)
                
                # Ajouter séparateur après si nécessaire
                if action_config.separator_after:
                    menu.addSeparator()
        
        return self.menu_bar
    
    def get_menu_bar(self) -> QMenuBar:
        """Retourne la barre de menu créée"""
        return self.menu_bar


class MenuBarController(QObject):
    """
    Contrôleur pour la barre de menu principale de l'application.
    
    Architecture MVC :
    - Model : MenuModel (structure des menus)
    - View : MenuBarView (création des widgets)
    - Controller : MenuBarController (logique métier)
    """
    
    # Signaux pour les actions du menu
    file_import_requested = pyqtSignal()
    file_export_requested = pyqtSignal()
    file_quit_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.export_tool = Export()
        self.import_dialog = None
        
        # Initialisation MVC
        self.model = MenuModel()
        self.view = MenuBarView(parent)
        
        # Configuration des handlers
        self._setup_handlers()
        
        # Configuration des signaux dans le modèle
        self._setup_signals()
        
        # Création de la barre de menu
        self._setup_menu_bar()
    
    def _setup_handlers(self):
        """Configure les handlers pour les actions"""
        self.handlers = {
            "Importer": self.handle_import,
            "Exporter...": self.handle_export,
            "Quitter": lambda: self.file_quit_requested.emit(),
        }
    
    def _setup_signals(self):
        """Configure les signaux dans le modèle"""
        # Associer les signaux aux actions du modèle
        for menu_name, actions in self.model.menus.items():
            for action in actions:
                if action.name == "Importer":
                    action.signal = self.file_import_requested
                elif action.name == "Exporter...":
                    action.signal = self.file_export_requested
                elif action.name == "Quitter":
                    action.signal = self.file_quit_requested
    
    def _setup_menu_bar(self):
        """Crée la barre de menu avec le système MVC"""
        self.menu_bar = self.view.create_menu_bar(self.model.menus, self.handlers)
    
    def add_menu(self, menu_name: str, actions: List[MenuAction]):
        """Ajoute dynamiquement un nouveau menu"""
        self.model.add_menu(menu_name, actions)
        self._setup_menu_bar()  # Recréer la barre
    
    def add_action(self, menu_name: str, action: MenuAction):
        """Ajoute dynamiquement une action à un menu"""
        self.model.add_action(menu_name, action)
        self._setup_menu_bar()  # Recréer la barre
    
        
    def get_menu_bar(self) -> QMenuBar:
        """Retourne la barre de menu créée."""
        return self.menu_bar
    
    def handle_import(self):
        """Gère l'import depuis un fichier JSON."""
        # Utiliser le nouveau dialogue d'importation avancée
        self.import_dialog = AdvancedImportDialog(self.parent)
        result = self.import_dialog.exec()
        
        if result == 1:  # QDialog.Accepted
            # L'importation a été effectuée, rafraîchir l'interface
            self.file_import_requested.emit()
    
    def handle_export(self):
        """Gère l'export vers un fichier JSON."""
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Exporter les images",
            "images_export.json",
            "Fichiers JSON (*.json);;Tous les fichiers (*.*)"
        )
        
        if file_path:
            try:
                json_data = self.export_tool.export_all_images(file_path)
                if json_data and json_data != "{}":
                    QMessageBox.information(
                        self.parent,
                        "Export réussi",
                        f"Les images ont été exportées vers :\n{file_path}"
                    )
                else:
                    QMessageBox.warning(
                        self.parent,
                        "Export vide",
                        "Aucune image à exporter."
                    )
                self.file_export_requested.emit()
            except Exception as e:
                QMessageBox.critical(
                    self.parent,
                    "Erreur d'export",
                    f"Une erreur est survenue lors de l'export :\n{str(e)}"
                )
    
    def cleanup(self):
        """Nettoie les ressources."""
        if self.import_dialog:
            self.import_dialog.close()
            self.import_dialog = None


# ─────────────────────────────────────────────
# EXEMPLE D'UTILISATION
# ─────────────────────────────────────────────

# Exemple 1: Ajouter un nouveau menu dynamiquement
def add_edit_menu(controller):
    """Exemple d'ajout d'un menu Édition"""
    edit_actions = [
        MenuAction(
            name="Copier",
            shortcut="Ctrl+C",
            tooltip="Copier l'élément sélectionné",
            handler=lambda: print("Copier")
        ),
        MenuAction(
            name="Coller",
            shortcut="Ctrl+V", 
            tooltip="Coller depuis le presse-papiers",
            handler=lambda: print("Coller"),
            separator_before=True
        ),
        MenuAction(
            name="Supprimer",
            shortcut="Suppr",
            tooltip="Supprimer l'élément sélectionné",
            handler=lambda: print("Supprimer"),
            separator_before=True
        )
    ]
    controller.add_menu("Édition", edit_actions)

# Exemple 2: Ajouter une seule action à un menu existant
def add_preferences_action(controller):
    """Exemple d'ajout d'une action Préférences"""
    prefs_action = MenuAction(
        name="Préférences...",
        tooltip="Ouvrir les préférences de l'application",
        handler=lambda: print("Ouvrir préférences"),
        separator_before=True
    )
    controller.add_action("Fichier", prefs_action)


def create_menu_bar(parent=None) -> MenuBarController:
    """
    Fonction factory pour créer une barre de menu.
    
    Args:
        parent: Widget parent de la barre de menu
        
    Returns:
        MenuBarController: Contrôleur de la barre de menu
    """
    controller = MenuBarController(parent)
    
    # Exemple d'utilisation:
    # add_edit_menu(controller)
    # add_preferences_action(controller)
    
    return controller
