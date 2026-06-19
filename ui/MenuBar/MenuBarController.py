import sys
import os
from typing import Dict, List, Optional
from collections.abc import Callable

from PyQt6.QtWidgets import QMenuBar, QMessageBox, QFileDialog
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QWidget
)
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup

from ui import load_from_config, save_in_config

from ui.utils.i18n import tr

from .MenuModel import MenuModel, MenuAction
from .MenuBarView import MenuBarView

from ui.widgets.Export.Export import Export, ExportDialog
from ui.widgets.Import.AdvancedImportDialog import AdvancedImportDialog

from qt_material import apply_stylesheet, list_themes


class MenuBarController(QObject):
    """Controller for the application's main menu bar.
    
    MVC Architecture:
    - Model: MenuModel (menu structures)
    - View: MenuBarView (widget rendering)
    - Controller: MenuBarController (business logic)
    
    Args:
        parent (QWidget, optional):
            The parent widget for the menu bar layout hierarchy. Defaults to None.

    """
    
    # Signaux pour les actions du menu
    file_import_requested = pyqtSignal()
    file_export_requested = pyqtSignal()
    file_quit_requested = pyqtSignal()
    toggle_import_tool = pyqtSignal()
    theme_changed = pyqtSignal(str)
    language_changed = pyqtSignal()
    
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
        
        self.translations_config = load_from_config("translations") or {}
        self.current_language = self.translations_config.get("current_language", "fr")
        
        self._setup_language_menu()
    
    def _setup_handlers(self) -> None:
        """Configure business handlers for menu action triggers."""
        self.handlers = {
            tr("Importer"): self.handle_import,
            f"{tr("Exporter")}...": self.handle_export,
            tr("Quitter"): lambda: self.file_quit_requested.emit(),
            tr("Outil d'importation d'image"): self.handle_toggle_import_tool,
            tr("Sélection du thème"): self.open_style_selector
        }
        
    def _setup_signals(self) -> None:
        """Bind underlying architecture signals to core module model actions."""
        for menu_name, actions in self.model.menus.items():
            for action in actions:
                if action.name == tr("Quitter"):
                    action.signal = self.file_quit_requested
                elif action.name == tr("Outil d'importation d'image"):
                    action.signal = self.toggle_import_tool
    
    def _setup_menu_bar(self) -> None:
        """Build the runtime window menu bar instance tracking components."""
        self.menu_bar = self.view.create_menu_bar(self.model.menus, self.handlers)
    
    # ─────────────────────────────────────────────
    # API PUBLIQUE
    # ─────────────────────────────────────────────
    
    def add_menu(self, menu_name: str, actions: list[MenuAction]) -> None:
        """Dynamically append a new categorical layout tab to the active structures.

        Args:
            menu_name (str):
                The unique identifier text label of the category.
            actions (list[MenuAction]):
                Collection of internal items to add down the column.

        """
        self.model.add_menu(menu_name, actions)
        self._setup_menu_bar()  # Recréer la barre
    
    def addAction(self, menu_name: str, action: MenuAction) -> None:
        """Dynamically inject an individual entry element directly onto a menu column.

        Args:
            menu_name (str):
                The target identifier category entry string.
            action (MenuAction):
                The precise structural properties defining the new action.

        """
        self.model.add_action(menu_name, action)
        self._setup_menu_bar()  # Recréer la barre
    
    def remove_menu(self, menu_name: str) -> None:
        """Purge an entire tab section from the live visual layouts.

        Args:
            menu_name (str):
                The identifier text key target to completely remove.

        """
        self.model.remove_menu(menu_name)
        self._setup_menu_bar()
    
    def remove_action(self, menu_name: str, action_name: str) -> None:
        """Erase a single action line configuration item from a structural category.

        Args:
            menu_name (str):
                The target parent column dictionary key.
            action_name (str):
                The specific entry display text identifier to purge.

        """
        self.model.remove_action(menu_name, action_name)
        self._setup_menu_bar()
    
    def get_menu_bar(self) -> QMenuBar:
        """Retrieve the primary structural menu bar visual widget element.

        Returns:
            The running operational QMenuBar instance object.

        """
        return self.menu_bar
    
    def get_model(self) -> MenuModel:
        """Retrieve the underlying dataset structure model for manual modifications.

        Returns:
            The raw data tracking MenuModel instance reference.

        """
        return self.model
    
    def get_view(self) -> MenuBarView:
        """Retrieve the rendering view abstraction instance frame.

        Returns:
            The layout generation MenuBarView instance handler.

        """
        return self.view
    
    # ─────────────────────────────────────────────
    # HANDLERS
    # ─────────────────────────────────────────────

    def open_style_selector(self) -> None:
        """Display an application dialogue window tracking available GUI skin themes."""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(tr("Sélection du thème"))

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

    def apply_theme(self, theme: str) -> None:
        """Apply a selected qt-material theme package across application boundaries.

        Args:
            theme (str):
                The string identification file properties target to parse.

        """
        if theme == "default":
            self.parent.setStyleSheet("")
            return

        apply_stylesheet(
            self.parent,
            theme=theme,
            invert_secondary=theme.startswith("light"),
        )

        self.theme_changed.emit(theme)
    
    def handle_import(self) -> None:
        """Trigger an advanced ingest pipeline view modal tracking local metadata files."""
        self.import_dialog = AdvancedImportDialog(self.parent)
        result = self.import_dialog.exec()
        
        if result == 1:
            self.file_import_requested.emit()
    
    def handle_export(self) -> None:
        """Launch an operational dialog box to export system catalog indices out."""
        export_dialog = ExportDialog(self.parent)
        export_dialog.exec()
    
    def handle_toggle_import_tool(self) -> None:
        """Toggle visibility bounds of the data-ingestion docking layout panels."""
        self.toggle_import_tool.emit()
    
    def cleanup(self) -> None:
        """Safely destroy processing resources and drop hanging dialog context references."""
        if self.import_dialog:
            self.import_dialog.close()
            self.import_dialog = None
            
    # ─────────────────────────────────────────────
    # LANGUAGE MENU
    # ─────────────────────────────────────────────
    
    def open_language_dialog(self) -> None:
        """Launch a systematic modal dialog tracking localization dictionary bundles."""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(tr("Sélection de la langue"))
        dialog.resize(300, 400)

        layout = QVBoxLayout(dialog)

        list_widget = QListWidget(dialog)

        languages = self.translations_config.get("available_languages", [])
        current = self.current_language

        # remplir la liste
        for lang in languages:
            item = QListWidgetItem(lang)
            item.setData(0, lang)

            # marquer la langue actuelle
            if lang == current:
                item.setSelected(True)

            list_widget.addItem(item)

        layout.addWidget(list_widget)

        # double clic = validation
        def on_select(item: QListWidgetItem) -> None:
            lang_code = item.text()
            self.set_language(lang_code)
            dialog.accept()

        list_widget.itemDoubleClicked.connect(on_select)

        dialog.exec()

    def _setup_language_menu(self) -> None:
        """Inject translation settings shortcuts directly inside running layouts."""
        if not self.translations_config:
            return

        self.add_menu(tr("Langue"), [
            MenuAction(
                name=f"{tr('Changer la langue')}...",
                tooltip=f"{tr('Ouvrir le sélecteur de langue')}",
                handler=self.open_language_dialog
            )
        ])
        
    def set_language(self, lang_code: str) -> None:
        """Switch active localized indexing across core visual text elements.

        Args:
            lang_code (str):
                The standardized short format string name target (e.g., 'fr', 'en').

        """
        if lang_code not in self.translations_config.get("available_languages", []):
            return

        self.current_language = lang_code
        self.translations_config["current_language"] = lang_code

        save_in_config("translations", self.translations_config)

        self.language_changed.emit()
        
    def _on_language_changed(self) -> None:
        """Re-compile all active items to dynamically pick up context translations changes."""
        self._setup_handlers()   # ← recréer les clés avec les nouveaux tr()
        self.model = MenuModel() # ← recréer le modèle avec les nouveaux tr()
        self._setup_signals()
        self._setup_menu_bar()
        self._setup_language_menu()
        
# ─────────────────────────────────────────────
# EXEMPLES D'UTILISATION
# ─────────────────────────────────────────────

def add_preferences_action(controller: MenuBarController) -> None:
    """Example function showing how to append custom preferences actions dynamically.

    Args:
        controller (MenuBarController):
            The target menu management instance layer to modify.

    """
    prefs_action = MenuAction(
        name=f"{tr("Préférences")}...",
        tooltip=f"{tr("Ouvrir les préférences de l'application")}",
        handler=lambda: print("Ouvrir préférences"),
        separator_before=True
    )
    controller.addAction("Fichier", prefs_action)


def create_menu_bar(parent : Optional[QWidget] =None) -> MenuBarController:
    """Factory layout utility building a ready-configured MenuBar component pipeline.
    
    Args:
        parent (QWidget, optional):
            The parent layout host matching system constraints. Defaults to None.
        
    Returns:
        MenuBarController: Orchestration controller engine ready for main systems linking.

    """
    controller = MenuBarController(parent) 
    return controller
