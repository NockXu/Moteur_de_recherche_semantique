import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QRadioButton, QButtonGroup, QGroupBox,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from common.Image_Classes.Image import Image, ProcessingStatus
from ui.utils.i18n import tr


class Export:
    """Service d'export des images (clean version)
    - pas de DB coupling direct
    - pas de print
    - output structuré
    """

    # ─────────────────────────────
    # CORE SERIALIZATION
    # ─────────────────────────────

    def image_to_dict(self, image: Image) -> dict[str, Any]:
        return {
            "id": getattr(image, "id", None),
            "path": str(image.path),
            "name": image.name,
            "status": image.status.value if image.status else ProcessingStatus.NOT_STARTED.value,
            "description": image.description or "",
            "keywords": image.keywords or [],
            "embedding": image.embedding or [],
            "indexed_at": getattr(image, "indexed_at", ""),
            "error_message": getattr(image, "error_message", "")
        }

    def images_to_dict(self, images: list[Image]) -> dict[str, Any]:
        return {
            img.name: self.image_to_dict(img)
            for img in images
        }

    # ─────────────────────────────
    # EXPORT JSON STRING
    # ─────────────────────────────

    def to_json(self, images: list[Image], indent: int = 2) -> str:
        data = self.images_to_dict(images)
        return json.dumps(data, indent=indent, ensure_ascii=False)

    # ─────────────────────────────
    # EXPORT FILE
    # ─────────────────────────────

    def export_to_file(
        self,
        images: list[Image],
        output_file: str
    ) -> dict[str, Any]:

        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            json_data = self.to_json(images)

            output_path.write_text(json_data, encoding="utf-8")

            return {
                "success": True,
                "count": len(images),
                "path": str(output_path)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # ─────────────────────────────
    # HELPERS (OPTIONAL)
    # ─────────────────────────────

    def export_single(self, image: Image) -> str:
        return json.dumps(
            self.image_to_dict(image),
            indent=2,
            ensure_ascii=False
        )


class ExportDialog(QDialog):
    """Boîte de dialogue d'export avec choix du mode
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exporter les données")
        self.setMinimumSize(400, 300)
        self.setModal(True)
        
        # Mode sélectionné
        self.selected_mode = None
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Titre
        title = QLabel(f"{tr("Choisir le mode d'export")}")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Groupe de choix
        choice_group = QGroupBox(f"{tr("Mode d'export")}")
        choice_layout = QVBoxLayout(choice_group)
        
        # Boutons radio
        self.radio_simple = QRadioButton(f"{tr("Export simple (images uniquement)")}")
        self.radio_simple.setChecked(True)  # Sélectionné par défaut
        
        simple_desc = QLabel(f"{tr("Exporte uniquement les images avec leurs métadonnées")}.")
        simple_desc.setStyleSheet("color: #666; font-size: 10px; margin-left: 20px;")
        simple_desc.setWordWrap(True)
        
        self.radio_integral = QRadioButton(f"{tr("Export intégral (datasets + images)")}")
        
        integral_desc = QLabel(f"{tr("Exporte les datasets et les images dans un fichier complet")}.")
        integral_desc.setStyleSheet("color: #666; font-size: 10px; margin-left: 20px;")
        integral_desc.setWordWrap(True)
        
        choice_layout.addWidget(self.radio_simple)
        choice_layout.addWidget(simple_desc)
        choice_layout.addWidget(self.radio_integral)
        choice_layout.addWidget(integral_desc)
        
        layout.addWidget(choice_group)
        
        # Boutons
        button_layout = QHBoxLayout()
        
        self.export_button = QPushButton(f"{tr("Exporter")}...")
        self.export_button.setDefault(True)
        
        self.cancel_button = QPushButton(f"{tr("Annuler")}")
        
        button_layout.addStretch()
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
    
    def _setup_connections(self):
        """Configure les connexions des signaux"""
        self.export_button.clicked.connect(self._on_export_clicked)
        self.cancel_button.clicked.connect(self.reject)
    
    def _on_export_clicked(self):
        """Gère le clic sur le bouton Exporter"""
        # Déterminer le mode sélectionné
        if self.radio_simple.isChecked():
            self.selected_mode = "simple"
        elif self.radio_integral.isChecked():
            self.selected_mode = "integral"
        else:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un mode d'export.")
            return
        
        # Choisir le fichier de destination
        default_name = "export_simple.json" if self.selected_mode == "simple" else "export_integral.json"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Choisir le fichier d'export",
            default_name,
            "Fichiers JSON (*.json);;Tous les fichiers (*.*)"
        )
        
        if file_path:
            # Effectuer l'export
            success = self._perform_export(file_path)
            
            if success:
                QMessageBox.information(
                    self, 
                    f"{tr("Export réussi")}", 
                    f"{tr("Les données ont été exportées avec succès dans")}:\n{file_path}"
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self, 
                    f"{tr("Erreur d'export")}", 
                    f"{tr("Une erreur est survenue lors de l'export")}."
                )
    
    def _perform_export(self, file_path: str) -> bool:
        """Effectue l'export selon le mode sélectionné"""
        try:
            if self.selected_mode == "simple":
                from .export_simple import export_images_file
                export_images_file(file_path)
            elif self.selected_mode == "integral":
                from .export_integrale import export_integral_file
                export_integral_file(file_path)
            else:
                return False
            
            return True
            
        except Exception as e:
            print(f"{tr("Erreur lors de l'export")}: {e}")
            return False
    
    def get_selected_mode(self) -> str | None:
        """Retourne le mode sélectionné"""
        return self.selected_mode
        
    def _on_language_changed(self):
        self.setWindowTitle(tr("Exporter les données"))

        self.findChild(QLabel).setText(tr("Choisir le mode d'export"))

        self.radio_simple.setText(tr("Export simple (images uniquement)"))
        self.radio_integral.setText(tr("Export intégral (datasets + images)"))

        self.radio_simple.setToolTip(tr("Exporte uniquement les images avec leurs métadonnées"))
        self.radio_integral.setToolTip(tr("Exporte les datasets et les images dans un fichier complet"))

        self.export_button.setText(tr("Exporter") + "...")
        self.cancel_button.setText(tr("Annuler"))

# ─────────────────────────────────────────────
# FONCTION UTILITAIRE POUR UTILISATION RAPIDE
# ─────────────────────────────────────────────

def show_export_dialog(parent=None) -> str | None:
    """Affiche la boîte de dialogue d'export
    
    Args:
        parent: Widget parent
        
    Returns:
        str: Mode sélectionné ('simple', 'integral') ou None si annulé

    """
    dialog = ExportDialog(parent)
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        return dialog.get_selected_mode()
    
    return None


# ─────────────────────────────────────────────
# EXEMPLE D'UTILISATION
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Test de la boîte de dialogue
    mode = show_export_dialog()
    
    if mode:
        print(f"Mode sélectionné: {mode}")
    else:
        print("Export annulé")
    
    sys.exit()