from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ui.utils.i18n import tr


class PaginationWidget(QWidget):
    """Pagination bar layout with back, next, and target page input fields.

    Signals:
        page_changed (pyqtSignal[int]): Emitted when the active display page updates.

    Args:
        current_page (int): Initial active layout index screen. Defaults to 1.
        total_pages (int): Complete depth length of available pages. Defaults to 1.
    """

    page_changed = pyqtSignal(int)

    def __init__(self, current_page: int = 1, total_pages: int = 1):
        super().__init__()
        self.current_page = current_page
        self.total_pages = total_pages
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        """Initializes structural display items and links event callbacks."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        font = QFont("Segoe UI", 10)

        self.prev_button = QPushButton(tr("← Précédent"))
        self.prev_button.setFont(font)
        self.prev_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_button.clicked.connect(self._go_previous)

        self.page_input = QLineEdit(str(self.current_page))
        self.page_input.setFixedWidth(48)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.setFont(font)
        self.page_input.returnPressed.connect(self._go_to_page)

        self.total_label = QLabel(f"/ {self.total_pages}")
        self.total_label.setFont(font)

        self.next_button = QPushButton(tr("Suivant →"))
        self.next_button.setFont(font)
        self.next_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_button.clicked.connect(self._go_next)

        layout.addWidget(self.prev_button)
        layout.addStretch()
        layout.addWidget(QLabel(tr("Page")))
        layout.addWidget(self.page_input)
        layout.addWidget(self.total_label)
        layout.addStretch()
        layout.addWidget(self.next_button)

        self._refresh_buttons()

    def _apply_styles(self):
        """Applies local QSS style sheets to the pagination components."""
        self.setStyleSheet("""
            PaginationWidget {
                border-top: 1px solid;
            }
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QLineEdit {
                border: 1.5px solid;
                border-radius: 6px;
                padding: 4px;
            }
            QLineEdit:focus { border-color: #4361ee; }
            QLabel { color: #495057; }
        """)

    # ------------------------------------------------------------------
    def _go_previous(self):
        """Decrements the current active page counter if possible."""
        if self.current_page > 1:
            self._emit(self.current_page - 1)

    def _go_next(self):
        """Increments the current active page counter if possible."""
        if self.current_page < self.total_pages:
            self._emit(self.current_page + 1)

    def _go_to_page(self):
        """Validates numerical text entry and moves directly to the requested page."""
        try:
            page = int(self.page_input.text())
            if 1 <= page <= self.total_pages:
                self._emit(page)
            else:
                self.page_input.setText(str(self.current_page))
        except ValueError:
            self.page_input.setText(str(self.current_page))

    def _emit(self, page: int):
        """Saves target index values and notifies external controller observers.

        Args:
            page (int): Target page index configuration state tracker.
        """
        self.current_page = page
        self._refresh_buttons()
        self.page_changed.emit(page)

    def _refresh_buttons(self):
        """Refreshes status tracking properties and sets button interaction modes."""
        self.page_input.setText(str(self.current_page))
        self.total_label.setText(f"/ {self.total_pages}")
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)

    def set_page(self, page: int):
        """Updates internal navigation tracking states to a specific page index number.

        Args:
            page (int): Selected page number index destination.
        """
        self.current_page = max(1, min(page, self.total_pages))
        self._refresh_buttons()

    def set_total_pages(self, total: int):
        """Resets the total page capacity and prevents indexes from scaling out of bounds.

        Args:
            total (int): Maximum layout limits depth integer length value.
        """
        self.total_pages = max(1, total)
        self.current_page = min(self.current_page, self.total_pages)
        self._refresh_buttons()