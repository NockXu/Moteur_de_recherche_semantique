from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class SAM3ProgressWindow(QWidget):
    """
    Fenêtre flottante non-bloquante affichant la progression du traitement SAM3 multi-images.
    """

    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Traitement SAM3")
        self.setMinimumWidth(350)
        self.setFixedHeight(120)
        self._total = 0
        self._done = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.status_label = QLabel("Initialisation...")
        self.status_label.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        footer = QHBoxLayout()
        self.count_label = QLabel("0 / 0")
        self.count_label.setFont(QFont("Segoe UI", 8))
        footer.addWidget(self.count_label)
        footer.addStretch()

        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.setFixedHeight(24)
        self.cancel_btn.clicked.connect(self._on_cancel)
        footer.addWidget(self.cancel_btn)

        layout.addLayout(footer)

    def start(self, total: int):
        self._total = total
        self._done = 0
        self.progress_bar.setValue(0)
        self.count_label.setText(f"0 / {total}")
        self.status_label.setText(f"Traitement de {total} image(s)...")
        self.cancel_btn.setEnabled(True)
        self.show()
        self.raise_()

    def update_progress(self, done: int, image_name: str = ""):
        self._done = done
        pct = int(done / self._total * 100) if self._total > 0 else 0
        self.progress_bar.setValue(pct)
        self.count_label.setText(f"{done} / {self._total}")
        if image_name:
            self.status_label.setText(f"✓ {image_name}")

    def finish(self):
        self.progress_bar.setValue(100)
        self.count_label.setText(f"{self._total} / {self._total}")
        self.status_label.setText("Traitement terminé.")
        self.cancel_btn.setEnabled(False)

    def _on_cancel(self):
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Annulation en cours...")
        self.cancelled.emit()

    def reset(self):
        self.hide()
        self._total = 0
        self._done = 0
        self.progress_bar.setValue(0)
        self.count_label.setText("0 / 0")
        self.status_label.setText("")
        self.cancel_btn.setEnabled(True)
