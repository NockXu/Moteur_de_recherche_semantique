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
    """Decoupled serialization data service handling Image mapping conversions.

    Eliminates direct storage engine dependencies and console stream pollution
    to output normalized object dictionary transformations.
    """

    # ─────────────────────────────
    # CORE SERIALIZATION
    # ─────────────────────────────

    def image_to_dict(self, image: Image) -> dict[str, Any]:
        """Convert a standalone Image object tracking instance into a standard key-value map.

        Args:
            image (Image): Target entity model containing processing attributes.

        Returns:
            dict[str, Any]: Flat dictionary representation of the asset properties.

        """
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
        """Map a collection list of Image models into a nested dictionary indexed by unique file names.

        Args:
            images (list[Image]): Collection array containing model entries.

        Returns:
            dict[str, Any]: Map index tracking individual image data dictionaries.

        """
        return {
            img.name: self.image_to_dict(img)
            for img in images
        }

    # ─────────────────────────────
    # EXPORT JSON STRING
    # ─────────────────────────────

    def to_json(self, images: list[Image], indent: int = 2) -> str:
        """Serialize a collection list of Image tracks into an indented human-readable text string.

        Args:
            images (list[Image]): Array tracking active data objects.
            indent (int): Visual indentation space spacing format width.

        Returns:
            str: Normalized data structure block encoded as a JSON text string.

        """
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
        """Commit structural object configurations sequences down onto a targeted local storage file.

        Args:
            images (list[Image]): Payload array tracking model nodes.
            output_file (str): Absolute destination path matching local storage devices.

        Returns:
            dict[str, Any]: Execution validation metadata tracking completion parameters.

        """
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
        """Convert a solitary target image element into a standalone string block.

        Args:
            image (Image): Selected singular tracking reference block.

        Returns:
            str: Serialized image model string segment.

        """
        return json.dumps(
            self.image_to_dict(image),
            indent=2,
            ensure_ascii=False
        )


class ExportDialog(QDialog):
    """Modal UI selection pop-up wrapper letting users pick simple or full file layout extraction formulas."""

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
        """Construct static layout containers and format local text label strings descriptions."""
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
        """Map core interactive widget click signals straight into tracking handler callback logic pools."""
        self.export_button.clicked.connect(self._on_export_clicked)
        self.cancel_button.clicked.connect(self.reject)
    
    def _on_export_clicked(self):
        """Intercept validation clicks, launch folder file explorers, and trigger data writes pipelines."""
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
        """Import modular script plugins at runtime to dump file structures safely based on flags.

        Args:
            file_path (str): Targeted storage location string matching absolute directories.

        Returns:
            bool: True if writing pipelines finalize cleanly without raising core exceptions.

        """
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
        """Fetch the tracking string key defining the type of structural extraction selected.

        Returns:
            str | None: Active formulation key flag string ('simple', 'integral'), or None if aborted.

        """
        return self.selected_mode
        
    def _on_language_changed(self):
        """Refresh static localized dictionary context lookups upon tracking environment switches."""
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
    """Launch the modal layout selector window and retrieve user choice settings tokens.

    Args:
        parent (QWidget, optional): Layout container hosting dialog child view nodes.

    Returns:
        str | None: Mode flag string character arrays selected ('simple', 'integral') or None if cancelled.

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