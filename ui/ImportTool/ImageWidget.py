import os
import sys

# Ajouter la racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ui.widgets.ImageThumbnailWidget import ImageThumbnailWidget
from common.Image_Classes.Image import ProcessingStatus
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QFont


class ImageWidget(ImageThumbnailWidget):
    """
    Carte image pour la grille ImportTool.

    Hérite de ImageThumbnailWidget (show_status_badge=True).
    L'overlay coloré + icône sont gérés par _build_import_pixmap()
    dans le widget parent — aucune logique dupliquée ici.
    """

    # Alias pour compatibilité avec le code existant (ImportToolView, Controller)
    image_clicked = ImageThumbnailWidget.clicked

    CARD_WIDTH  = 120
    CARD_HEIGHT = 160   # 120 image + 40 nom fichier

    def __init__(
        self,
        image_path: str,
        status: ProcessingStatus = ProcessingStatus.NOT_STARTED,
        status_icon: str = None,   # conservé pour compatibilité, ignoré
        parent=None,
    ):
        super().__init__(
            image_path=image_path,
            title=None,
            status=status,
            col_width=self.CARD_WIDTH,
            show_status_badge=True,
            parent=parent,
        )
        self.setFixedWidth(self.CARD_WIDTH)
        self._add_filename_label()

    def _add_filename_label(self):
        name    = self.image_path.name
        display = name[:16] + "…" if len(name) > 16 else name

        self.filename_label = QLabel(display)
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filename_label.setFont(QFont("Segoe UI", 8))
        self.filename_label.setStyleSheet("QLabel { background: transparent; }")
        self.filename_label.setContentsMargins(4, 2, 4, 4)
        self.filename_label.setToolTip(name)
        self.layout().addWidget(self.filename_label)

    def set_status(self, status: ProcessingStatus, status_icon: str = None):
        """Compatibilité avec l'ancienne interface du Controller."""
        super().set_status(status)