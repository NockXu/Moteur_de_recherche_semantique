from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QSizePolicy
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from pathlib import Path

from ui.utils.i18n import tr


class SearchBarView(QWidget):
    """Visual input field component for typing queries and triggering semantic image searches.

    Signals:
        search_triggered (pyqtSignal[str]): Emitted with text content when a search is executed.
        search_text_changed (pyqtSignal[str]): Emitted instantly whenever the input text shifts.

    Args:
        parent (QWidget | None): Optional structural parent widget container. Defaults to None.
        placeholder_text (str): Transient indicator message for empty states. Defaults to translated text.
    """
    search_triggered = pyqtSignal(str)
    search_text_changed = pyqtSignal(str)

    def __init__(self, parent=None, placeholder_text: str = tr("Rechercher une image...")):
        super().__init__(parent)
        
        self.setMinimumHeight(48)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._setup_ui(placeholder_text)

    def _setup_ui(self, placeholder_text: str) -> None:
        """Builds structural inner fields and binds activation click shortcuts.

        Args:
            placeholder_text (str): Visual ghost tip text values for empty text boxes.
        """
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

    def _on_search_clicked(self) -> None:
        """Handles action prompts and broadcasts current query string parameters."""
        self.search_triggered.emit(self.search_input.text())
    
    def _on_text_changed(self) -> None:
        """Handles live input changes and fires intermediate text updates."""
        self.search_text_changed.emit(self.search_input.text())

    def get_text(self) -> str:
        """Retrieves raw content characters typed inside the active entry bar.

        Returns:
            The raw string text currently filled inside the inner text box.
        """
        return self.search_input.text()

    def set_text(self, text: str) -> None:
        """Updates the inner search text box display values.

        Args:
            text (str): Incoming characters or keywords data sequence.
        """
        self.search_input.setText(text)

    def clear(self) -> None:
        """Purges written query keywords out of the input widget view fields."""
        self.search_input.clear()

    def set_placeholder(self, placeholder: str) -> None:
        """Alters target descriptive tips displayed inside empty tracking fields.

        Args:
            placeholder (str): Temporary prompt message lines.
        """
        self.search_input.setPlaceholderText(placeholder)

    def set_enabled(self, enabled: bool) -> None:
        """Toggles interactive capability states across entry fields and submit buttons.

        Args:
            enabled (bool): Interaction block toggle flag configuration.
        """
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