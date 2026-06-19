import sys
import os

from ui.utils.i18n import tr

# Ajouter le chemin racine du projet au sys.path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor
from ui.ImportTool.widget.ConnectionVerificator.ConnectionVerificatorModel import State


class ConnectionVerificatorView(QWidget):
    """View component displaying the visual connection status of the backend service.

    Renders vector status icons, status descriptions, and retrieved software engine versions 
    using customized styles and localization translation mechanisms.

    Args:
        parent (QWidget):
            Optional parent widget container mapping the layout hierarchy. Defaults to None.

    """
    
    # Signaux
    status_info_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(40)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # Chemins des icônes SVG
        self.icon_paths = {
            'checking': 'ui/Icon/change_circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg',
            'connected': 'ui/Icon/check_circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg',
            'disconnected': 'ui/Icon/circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg',
            'error': 'ui/Icon/x_circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg'
        }
        
        # Couleurs pour chaque état
        self.icon_colors = {
            'checking': '#17a2b8',  # Bleu
            'connected': '#28a745',  # Vert
            'disconnected': '#dc3545',  # Rouge
            'error': '#ffc107'  # Orange
        }
        
        self._setup_ui()

    def _setup_ui(self):
        """Construct the structural child layout tree and instantiate view presentation subcomponents."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Indicateur de statut
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(16, 16)
        self.status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icône par défaut (même style que les labels)
        default_icon = self.recolor_svg(self.icon_paths['disconnected'], '#6c757d')
        self.status_indicator.setPixmap(default_icon.pixmap(16, 16))

        # Label de statut
        self.status_label = QLabel(tr("Non connecté"))
        self.status_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 11px;
                font-weight: 500;
                background: transparent;
            }
        """)
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        # Label de version (masqué par défaut)
        self.version_label = QLabel("")
        self.version_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 11px;
                font-weight: 500;
                background: transparent;
            }
        """)
        self.version_label.setFont(QFont("Segoe UI", 8))

        # Ajouter les widgets au layout
        layout.addWidget(self.status_indicator)
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.version_label)

    def recolor_svg(self, svg_path: str, color: str) -> QIcon:
        """Parse vector content to swap base element fill parameters and return a recolored QIcon object.

        Args:
            svg_path (str):
                The local file directory location pointing to the targeted SVG source.
            color (str):
                The target hexadecimal color token sequence applied onto the asset paths.

        Returns:
            QIcon: A painted pixmap object container tracking the modified vector layout.

        """
        # Essayer de charger le SVG
        try:
            # Utiliser QSvgRenderer pour une meilleure qualité
            from PyQt6.QtSvg import QSvgRenderer
            from PyQt6.QtCore import QByteArray
            
            # Lire le fichier SVG
            with open(svg_path, encoding='utf-8') as f:
                svg_content = f.read()
            
            # Remplacer les couleurs dans le SVG
            # Remplacer fill="#E3E3E3" par fill="{color}"
            svg_content = svg_content.replace('fill="#E3E3E3"', f'fill="{color}"')
            
            # Créer le renderer
            renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
            
            # Créer le pixmap
            pixmap = QPixmap(24, 24)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            # Créer et retourner le QIcon
            return QIcon(pixmap)
            
        except Exception:
            # Fallback : utiliser un cercle coloré si le SVG n'est pas trouvé ou en cas d'erreur
            pixmap = QPixmap(24, 24)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(4, 4, 16, 16)
            painter.end()
            return QIcon(pixmap)

    def update_status(self, state: State, version: str = "", error_message: str = ""):
        """Repaint vector indicators and switch descriptive text definitions to match pipeline states.

        Args:
            state (State):
                The verified lifecycle connection state configuration flag target.
            version (str):
                The build version string identifier returned by the backend node infrastructure. Defaults to "".
            error_message (str):
                The precise exceptional tracking trace logged during processing errors. Defaults to "".

        """
        if state == State.CONNECTED:
            self.status_indicator.setPixmap(self.recolor_svg(self.icon_paths['connected'], self.icon_colors['connected']).pixmap(16, 16))
            self.status_label.setText(f"{tr('Connecté')}")
            self.version_label.setText(f"v{version}")
            self.version_label.show()
            
        elif state == State.DISCONNECTED:
            self.status_indicator.setPixmap(self.recolor_svg(self.icon_paths['disconnected'], self.icon_colors['disconnected']).pixmap(16, 16))
            self.status_label.setText(f"{tr('Non connecté')}")
            self.version_label.hide()
            
        elif state == State.ERROR:
            self.status_indicator.setPixmap(self.recolor_svg(self.icon_paths['error'], self.icon_colors['error']).pixmap(16, 16))
            self.status_label.setText(f"{tr('Erreur')}")
            self.version_label.hide()

    def set_checking(self, is_checking: bool):
        """Toggle processing state graphics indicators and description labels during network queries.

        Args:
            is_checking (bool):
                If True, triggers pending status updates across matching view layers.

        """
        if is_checking:
            self.status_indicator.setPixmap(self.recolor_svg(self.icon_paths['checking'], self.icon_colors['checking']).pixmap(16, 16))
            self.status_label.setText(f"{tr('Vérification')}...")
            self.version_label.hide()
        else:
            # L'état sera mis à jour par update_status
            pass

    def get_view(self) -> QWidget:
        """Fetch the self context widget node coordinate system layout reference.

        Returns:
            QWidget: The current view instance frame context pointer.

        """
        return self
    
    def _on_language_changed(self):
        """Re-translate string resources across display items dynamically when runtime languages switch."""
        # Texte selon l'état actuel (on doit les recalculer proprement)
        current_text = self.status_label.text()

        # Mapping simple basé sur l'état visible actuel
        # (on ne stocke pas l'état -> on déduit via texte ou mieux: variable state si tu l'as)
        
        if current_text.startswith("Connecté") or current_text.startswith("Connected"):
            self.status_label.setText(tr("Connecté"))
            self.version_label.show()

        elif current_text.startswith("Erreur") or current_text.startswith("Error"):
            self.status_label.setText(tr("Erreur"))
            self.version_label.hide()

        elif current_text.startswith("Vérification") or current_text.startswith("Checking"):
            self.status_label.setText(tr("Vérification") + "...")

        else:
            self.status_label.setText(tr("Non connecté"))
            self.version_label.hide()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Test de la vue
    view = ConnectionVerificatorView()
    view.setWindowTitle("Test ConnectionVerificatorView")
    view.resize(400, 100)
    
    # Test des états
    from PyQt6.QtCore import QTimer
    
    def test_states():
        view.set_checking(True)
        QTimer.singleShot(2000, lambda: view.update_status(State.CONNECTED, "0.13.5"))
        QTimer.singleShot(4000, lambda: view.update_status(State.DISCONNECTED, "", "Serveur inaccessible"))
        QTimer.singleShot(6000, lambda: view.update_status(State.ERROR, "", "Erreur de connexion"))
        QTimer.singleShot(8000, lambda: view.set_checking(True))
    
    QTimer.singleShot(1000, test_states)
    
    view.show()
    sys.exit(app.exec())