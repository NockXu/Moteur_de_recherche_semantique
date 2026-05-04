import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QTextEdit, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

class ImportWorkerThread(QThread):
    """Thread pour l'import en arrière-plan"""
    progress_updated = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(int, str)  # total_imported, final_message
    
    def __init__(self, import_tool, file_path):
        super().__init__()
        self.import_tool = import_tool
        self.file_path = file_path
        self._running = True
    
    def run(self):
        """Exécute l'import dans un thread séparé"""
        try:
            # Charger les images depuis le fichier
            images = self.import_tool.import_from_file(self.file_path)
            total = len(images)
            
            if not self._running:
                return
            
            self.progress_updated.emit(0, total, f"Début de l'import de {total} images...")
            
            # Importer chaque image
            imported_count = 0
            for i, image in enumerate(images):
                if not self._running:
                    break
                
                try:
                    success = self.import_tool.db.insert_image(image)
                    if success:
                        imported_count += 1
                    
                    # Mettre à jour la progression
                    progress = i + 1
                    message = f"Import de {image.name} ({progress}/{total})"
                    self.progress_updated.emit(progress, total, message)
                    
                except Exception as e:
                    message = f"Erreur lors de l'import de {image.name}: {str(e)}"
                    self.progress_updated.emit(i, total, message)
            
            # Message final
            final_message = f"Import terminé: {imported_count}/{total} images importées avec succès"
            self.finished.emit(imported_count, final_message)
            
        except Exception as e:
            error_message = f"Erreur lors de l'import: {str(e)}"
            self.finished.emit(0, error_message)
    
    def stop(self):
        """Arrête le thread"""
        self._running = False

class ImportProgressDialog(QDialog):
    """Fenêtre de progression pour l'import"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import d'images")
        self.setFixedSize(500, 300)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # Thread d'import
        self.worker_thread = None
        
        # UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Titre
        title_label = QLabel("Import d'images")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Label de progression
        self.progress_label = QLabel("Préparation de l'import...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
        
        # Zone de texte pour les messages
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        layout.addWidget(self.log_text)
        
        # Boutons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("Fermer")
        self.close_button.clicked.connect(self.close)
        self.close_button.setEnabled(False)  # Désactivé au début
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def start_import(self, import_tool, file_path):
        """Démarre l'import"""
        # Créer et démarrer le thread
        self.worker_thread = ImportWorkerThread(import_tool, file_path)
        self.worker_thread.progress_updated.connect(self._on_progress_updated)
        self.worker_thread.finished.connect(self._on_import_finished)
        
        # Réinitialiser l'UI
        self.progress_bar.setValue(0)
        self.progress_label.setText("Préparation de l'import...")
        self.log_text.clear()
        self.cancel_button.setEnabled(True)
        self.close_button.setEnabled(False)
        
        # Démarrer le thread
        self.worker_thread.start()
    
    def _on_progress_updated(self, current, total, message):
        """Met à jour la progression"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
        
        self.progress_label.setText(f"{current}/{total} images")
        self.log_text.append(message)
        
        # Auto-scroll vers le bas
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_import_finished(self, total_imported, final_message):
        """Import terminé"""
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"Terminé: {total_imported} images importées")
        self.log_text.append(final_message)
        
        # Activer le bouton fermer, désactiver annuler
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        # Nettoyer le thread
        if self.worker_thread:
            self.worker_thread.deleteLater()
            self.worker_thread = None
    
    def _on_cancel_clicked(self):
        """Annule l'import"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.log_text.append("Import annulé par l'utilisateur")
            self.progress_label.setText("Import annulé")
            
            # Activer le bouton fermer
            self.cancel_button.setEnabled(False)
            self.close_button.setEnabled(True)
    
    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait()  # Attendre la fin du thread
        
        event.accept()
