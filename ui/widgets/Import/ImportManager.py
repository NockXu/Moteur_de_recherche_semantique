import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal

from ui.widgets.Import.AdvancedImport import AdvancedImportDialog
from ui.widgets.Import.Import import Import

class ImportManager(QObject):
    """Gestionnaire central pour les importations"""
    
    import_completed = pyqtSignal(int, int)  # success_count, total_count
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
    
    def show_import_dialog(self):
        """Affiche la boîte de dialogue d'importation avancée"""
        dialog = AdvancedImportDialog(self.parent)
        dialog.finished.connect(self.on_import_finished)
        return dialog.exec()
    
    def on_import_finished(self, result):
        """Gère la fin de l'importation"""
        if result == 1:  # QDialog.Accepted
            # L'importation a été effectuée avec succès
            # Le signal sera émis par le dialogue lui-même
            pass
        else:
            # L'importation a été annulée
            pass
    
    def quick_import(self, file_path=None):
        """Importation rapide depuis un fichier spécifique"""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self.parent,
                "Sélectionner un fichier JSON",
                str(Path.home()),
                "Fichiers JSON (*.json);;Tous les fichiers (*.*)"
            )
            
            if not file_path:
                return 0
        
        try:
            # Utiliser l'importation simple existante
            import_tool = Import()
            return import_tool.import_and_save(file_path)
            
        except Exception as e:
            QMessageBox.critical(
                self.parent, 
                "Erreur d'importation", 
                f"Une erreur est survenue lors de l'importation: {e}"
            )
            return 0

def get_import_manager(parent=None):
    """Crée et retourne une instance de ImportManager"""
    return ImportManager(parent)
