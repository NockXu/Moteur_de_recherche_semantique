from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QSizePolicy
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from pathlib import Path

from ui.utils.i18n import tr


class SearchBarView(QWidget):
    search_triggered = pyqtSignal(str)
    search_text_changed = pyqtSignal(str)

    def __init__(self, parent=None, placeholder_text: str = tr("Rechercher une image...")):
        super().__init__(parent)
        
        self.setMinimumHeight(48)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._setup_ui(placeholder_text)

    def _setup_ui(self, placeholder_text: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Champ de texte
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(placeholder_text)
        self.search_input.setMinimumHeight(48)
        self.search_input.setFont(QFont("Segoe UI", 11))
        self.search_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        # Bouton loupe avec icône SVG
        icon_path = Path(__file__).parent.parent.parent.parent / "Icon" / "search_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
        self.search_button = QPushButton()
        self.search_button.setIcon(QIcon(str(icon_path)))
        self.search_button.setIconSize(QSize(52//2, 48//2))
        self.search_button.setFixedSize(52, 48)
        self.search_button.setFont(QFont("Segoe UI", 14))
        self.search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_button.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed
        )

        # Signaux
        self.search_button.clicked.connect(self._on_search_clicked)
        self.search_input.returnPressed.connect(self._on_search_clicked)
        self.search_input.textChanged.connect(self._on_text_changed)

        layout.addWidget(self.search_input)
        layout.addWidget(self.search_button)

    def _on_search_clicked(self):
        self.search_triggered.emit(self.search_input.text())
    
    def _on_text_changed(self):
        self.search_text_changed.emit(self.search_input.text())

    def get_text(self) -> str:
        return self.search_input.text()

    def set_text(self, text: str):
        self.search_input.setText(text)

    def clear(self):
        self.search_input.clear()

    def set_placeholder(self, placeholder: str):
        self.search_input.setPlaceholderText(placeholder)

    def set_enabled(self, enabled: bool):
        self.search_input.setEnabled(enabled)
        self.search_button.setEnabled(enabled)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout
    import sys

    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Search Bar Demo")
    window.setMinimumSize(700, 120)

    central = QWidget()
    window.setCentralWidget(central)
    layout = QVBoxLayout(central)
    layout.setContentsMargins(40, 30, 40, 30)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    bar = SearchBarView()
    bar.search_triggered.connect(lambda enabled: print(f"Recherche activée : {enabled}"))
    bar.search_text_changed.connect(lambda text: print(f"Texte de recherche : {text}"))
    layout.addWidget(bar)

    window.show()
    sys.exit(app.exec())