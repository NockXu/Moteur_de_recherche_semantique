import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import QMenuBar, QMenu, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QFont, QAction
from pathlib import Path

from ui.widgets.Export import Export
from ui.widgets.Import import Import
from ui.widgets.Import.ImportProgressDialog import ImportProgressDialog
from ui.widgets.Import.ImportManager import get_import_manager


class MenuBarController(QObject):
    """
    Contrôleur pour la barre de menu principale de l'application.
    
    Structure du menu :
    - Fichier : Importer, Exporter, Quitter
    """
    
    # Signaux pour les actions du menu
    file_import_requested = pyqtSignal()
    file_export_requested = pyqtSignal()
    file_quit_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.import_tool = Import()
        self.export_tool = Export()
        self.import_manager = get_import_manager(parent)
        self.menu_bar = QMenuBar()
        self.menu_bar.setFont(QFont("Segoe UI", 10))
        
        # Connecter le signal d'importation
        self.import_manager.import_completed.connect(self.on_import_completed)
        
        # Créer le menu
        self._setup_menu_bar()
    
    def _setup_menu_bar(self):
        """Crée la barre de menu avec tous les menus et actions."""
        self.menu_bar = QMenuBar()
        self.menu_bar.setFont(QFont("Segoe UI", 10))
        
        # Menu Fichier
        self._create_file_menu()
    
    def _create_file_menu(self):
        """Crée le menu Fichier."""
        file_menu = self.menu_bar.addMenu("Fichier")
        
        # Importer (avancé)
        import_action = QAction("Importer (Avancé)", self.parent)
        import_action.setShortcut("Ctrl+I")
        import_action.setStatusTip("Importer des images dans la base")
        import_action.triggered.connect(self.handle_import)
        file_menu.addAction(import_action)
        
        # Importer (simple)
        simple_import_action = QAction("Importer (Simple)", self.parent)
        simple_import_action.triggered.connect(self.handle_simple_import)
        file_menu.addAction(simple_import_action)
        
        # Exporter
        export_action = QAction("Exporter...", self.parent)
        export_action.setShortcut("Ctrl+E")
        export_action.setStatusTip("Exporter les données de la base")
        export_action.triggered.connect(self.handle_export)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # Quitter
        quit_action = QAction("Quitter", self.parent)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.setStatusTip("Quitter l'application")
        quit_action.triggered.connect(self.file_quit_requested)
        file_menu.addAction(quit_action)
    
        
    def get_menu_bar(self) -> QMenuBar:
        """Retourne la barre de menu créée."""
        return self.menu_bar
    
    def handle_import(self):
        """Gère l'import depuis un fichier JSON."""
        # Utiliser l'importation avancée
        result = self.import_manager.show_import_dialog()
        
        if result == 1:  # QDialog.Accepted
            # L'importation a été effectuée, le signal est déjà émis par ImportManager
            pass
    
    def on_import_completed(self, success_count, total_count):
        """Gère la fin de l'importation"""
        if success_count > 0:
            QMessageBox.information(
                self.parent,
                "Importation terminée",
                f"{success_count}/{total_count} images importées avec succès."
            )
            # Rafraîchir l'interface
            self.file_import_requested.emit()
        else:
            QMessageBox.warning(
                self.parent,
                "Importation échouée",
                "Aucune image n'a pu être importée."
            )
    
    def handle_simple_import(self):
        """Gère l'import simple (ancienne méthode)."""
        count = self.import_manager.quick_import()
        if count > 0:
            QMessageBox.information(
                self.parent,
                "Importation terminée",
                f"{count} images importées avec succès."
            )
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
        try:
            # DatabaseManager n'a pas de close_connection explicite
            # Les connexions sont fermées automatiquement à la destruction
            pass
        except:
            pass


def create_menu_bar(parent=None) -> MenuBarController:
    """
    Fonction factory pour créer une barre de menu.
    
    Args:
        parent: Widget parent de la barre de menu
        
    Returns:
        MenuBarController: Contrôleur de la barre de menu
    """
    return MenuBarController(parent)
