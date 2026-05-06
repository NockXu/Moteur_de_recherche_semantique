import sys
import os

# Ajouter le chemin racine du projet au sys.path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor
from ui.ImportTool.widget.ConnectionVerificator.ConnectionVerificatorModel import State


class ConnectionVerificatorView(QWidget):
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
        """Configure l'interface utilisateur"""
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
        self.status_label = QLabel("Non connecté")
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
        """Recolorise un SVG en une couleur spécifique et retourne un QIcon"""
        # Essayer de charger le SVG
        try:
            # Utiliser QSvgRenderer pour une meilleure qualité
            from PyQt6.QtSvg import QSvgRenderer
            from PyQt6.QtCore import QByteArray
            
            # Lire le fichier SVG
            with open(svg_path, 'r', encoding='utf-8') as f:
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
        """Met à jour l'affichage du statut"""
        if state == State.CONNECTED:
            self.status_indicator.setPixmap(self.recolor_svg(self.icon_paths['connected'], self.icon_colors['connected']).pixmap(16, 16))
            self.status_label.setText("Connecté")
            self.version_label.setText(f"v{version}")
            self.version_label.show()
            
        elif state == State.DISCONNECTED:
            self.status_indicator.setPixmap(self.recolor_svg(self.icon_paths['disconnected'], self.icon_colors['disconnected']).pixmap(16, 16))
            self.status_label.setText("Non connecté")
            self.version_label.hide()
            
        elif state == State.ERROR:
            self.status_indicator.setPixmap(self.recolor_svg(self.icon_paths['error'], self.icon_colors['error']).pixmap(16, 16))
            self.status_label.setText("Erreur")
            self.version_label.hide()

    def set_checking(self, is_checking: bool):
        """Met à jour l'interface pendant la vérification"""
        if is_checking:
            self.status_indicator.setPixmap(self.recolor_svg(self.icon_paths['checking'], self.icon_colors['checking']).pixmap(16, 16))
            self.status_label.setText("Vérification...")
            self.version_label.hide()
        else:
            # L'état sera mis à jour par update_status
            pass

    def get_view(self) -> QWidget:
        """Retourne le widget vue"""
        return self


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