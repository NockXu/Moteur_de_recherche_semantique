import sys
import os
from typing import Dict, List, Callable

from PyQt6.QtWidgets import QMenuBar, QMessageBox, QFileDialog
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
)
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup

from .MenuModel import MenuModel, MenuAction
from .MenuBarView import MenuBarView

from ui.widgets.Export.Export import Export, ExportDialog
from ui.widgets.Import.AdvancedImportDialog import AdvancedImportDialog

from qt_material import apply_stylesheet, list_themes


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
    toggle_import_tool = pyqtSignal()
    theme_changed = pyqtSignal(str)
    
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
            "Outil d'importation d'image": self.handle_toggle_import_tool,
            "Sélection du thème": self.open_style_selector
        }
        
    def _setup_signals(self):
        """Configure les signaux dans le modèle"""
        # Associer les signaux aux actions du modèle (uniquement pour ceux qui n'ont pas de handler direct)
        for menu_name, actions in self.model.menus.items():
            for action in actions:
                if action.name == "Quitter":
                    action.signal = self.file_quit_requested
                elif action.name == "Outil d'importation d'image":
                    action.signal = self.toggle_import_tool
                # Importer et Exporter utilisent les handlers directs, pas besoin de signal
    
    def _setup_menu_bar(self):
        """Crée la barre de menu avec le système MVC"""
        self.menu_bar = self.view.create_menu_bar(self.model.menus, self.handlers)
    
    # ─────────────────────────────────────────────
    # API PUBLIQUE
    # ─────────────────────────────────────────────
    
    def add_menu(self, menu_name: str, actions: List[MenuAction]):
        """Ajoute dynamiquement un nouveau menu"""
        self.model.add_menu(menu_name, actions)
        self._setup_menu_bar()  # Recréer la barre
    
    def addAction(self, menu_name: str, action: MenuAction):
        """Ajoute dynamiquement une action à un menu"""
        self.model.add_action(menu_name, action)
        self._setup_menu_bar()  # Recréer la barre
    
    def remove_menu(self, menu_name: str):
        """Supprime un menu entier"""
        self.model.remove_menu(menu_name)
        self._setup_menu_bar()
    
    def remove_action(self, menu_name: str, action_name: str):
        """Supprime une action spécifique"""
        self.model.remove_action(menu_name, action_name)
        self._setup_menu_bar()
    
    def get_menu_bar(self) -> QMenuBar:
        """Retourne la barre de menu créée"""
        return self.menu_bar
    
    def get_model(self) -> MenuModel:
        """Retourne le modèle pour manipulation directe"""
        return self.model
    
    def get_view(self) -> MenuBarView:
        """Retourne la vue pour manipulation directe"""
        return self.view
    
    # ─────────────────────────────────────────────
    # HANDLERS
    # ─────────────────────────────────────────────

    def open_style_selector(self):
        """Affiche une boîte de dialogue de sélection des thèmes."""

        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Sélection du thème")

        # taille fixe raisonnable
        dialog.resize(300, 400)

        layout = QVBoxLayout(dialog)

        theme_list = QListWidget(dialog)

        themes = list_themes()

        for theme in themes:
            item = QListWidgetItem(theme)
            theme_list.addItem(item)

        # double clic → appliquer thème
        theme_list.itemDoubleClicked.connect(
            lambda item: self.apply_theme(item.text())
        )

        layout.addWidget(theme_list)

        dialog.exec()

    def apply_theme(self, theme: str):
        """Applique un thème qt-material."""

        if theme == "default":
            self.parent.setStyleSheet("")
            return

        apply_stylesheet(
            self.parent,
            theme=theme,
            invert_secondary=theme.startswith("light"),
        )

        self.theme_changed.emit(theme)
    
    def handle_import(self):
        """Gère l'import depuis un fichier JSON."""
        # Utiliser le nouveau dialogue d'importation avancée
        self.import_dialog = AdvancedImportDialog(self.parent)
        result = self.import_dialog.exec()
        
        if result == 1:  # QDialog.Accepted
            # L'importation a été effectuée, rafraîchir l'interface
            self.file_import_requested.emit()
    
    def handle_export(self):
        """Gère l'export avec choix du mode via la boîte de dialogue."""
        # Utiliser la nouvelle boîte de dialogue d'export
        export_dialog = ExportDialog(self.parent)
        export_dialog.exec()
    
    def handle_toggle_import_tool(self):
        """Gère l'affichage/masquage de l'Import Tool."""
        self.toggle_import_tool.emit()
    
    def cleanup(self):
        """Nettoie les ressources."""
        if self.import_dialog:
            self.import_dialog.close()
            self.import_dialog = None

# ─────────────────────────────────────────────
# EXEMPLES D'UTILISATION
# ─────────────────────────────────────────────

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

def add_preferences_action(controller):
    """Exemple d'ajout d'une action Préférences"""
    prefs_action = MenuAction(
        name="Préférences...",
        tooltip="Ouvrir les préférences de l'application",
        handler=lambda: print("Ouvrir préférences"),
        separator_before=True
    )
    controller.addAction("Fichier", prefs_action)


def create_menu_bar(parent=None):
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
