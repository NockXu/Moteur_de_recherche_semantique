from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from ui.utils.i18n import tr


class SAM3ProgressWindow(QWidget):
    """Floating non-blocking progress dialog monitoring multi-image SAM3 prediction pipelines.

    Maintains visual trackers, processing percentages, and handles interactive execution 
    aborts using custom asynchronous signals.
    """

    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle(f"{tr('Traitement SAM3')}")
        self.setMinimumWidth(350)
        self.setFixedHeight(120)
        self._total = 0
        self._done = 0
        self._setup_ui()

    def _setup_ui(self):
        """Construct structural container boxes and instantiate layout visualization nodes."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.status_label = QLabel(f"{tr('Initialisation')}...")
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

        self.cancel_btn = QPushButton(f"{tr('Annuler')}")
        self.cancel_btn.setFixedHeight(24)
        self.cancel_btn.clicked.connect(self._on_cancel)
        footer.addWidget(self.cancel_btn)

        layout.addLayout(footer)

    def start(self, total: int, initial_done: int = 0):
        """Initialize pipeline constraints parameters and bring the view container overlay to top.

        Args:
            total (int): Total number of targeted file assets to parse.
            initial_done (int): Number of items already completed before this invocation baseline.

        """
        self._total = total
        self._done = initial_done
        pct = int(initial_done / total * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.count_label.setText(f"{initial_done} / {total}")
        self.status_label.setText(f"{tr('Traitement de')} {total} {tr('image(s)')}...")
        self.cancel_btn.setEnabled(True)
        self.show()
        self.raise_()

    def update_progress(self, done: int, image_name: str = ""):
        """Increment current milestones progress indicators and refresh the text overlay layout properties.

        Args:
            done (int): Cumulative count of finalized records.
            image_name (str, optional): Target file identifier token that completed processing.

        """
        self._done = done
        pct = int(done / self._total * 100) if self._total > 0 else 0
        self.progress_bar.setValue(pct)
        self.count_label.setText(f"{done} / {self._total}")
        if image_name:
            self.status_label.setText(f"✓ {image_name}")

    def finish(self):
        """Transition interface variables towards completed states and schedule an automated window hide."""
        self.progress_bar.setValue(100)
        self.count_label.setText(f"{self._total} / {self._total}")
        self.status_label.setText(f"{tr('Traitement terminé')}.")
        self.cancel_btn.setEnabled(False)
        QTimer.singleShot(1500, self.hide)

    def _on_cancel(self):
        """Intercept user abort execution interactions and broadcast termination requests signals."""
        self.cancel_btn.setEnabled(False)
        self.status_label.setText(f"{tr('Annulation en cours')}...")
        self.cancelled.emit()

    def reset(self):
        """Purge stored trackers metric layers data to restore base initialization profiles states."""
        self.hide()
        self._total = 0
        self._done = 0
        self.progress_bar.setValue(0)
        self.count_label.setText("0 / 0")
        self.status_label.setText("")
        self.cancel_btn.setEnabled(True)
        
    def _on_language_changed(self, lang_code: str = None) -> None:
        """Refresh structural dictionary context lookups upon tracking system localization switches.

        Args:
            lang_code (str, optional): Target environment localization shorthand symbol token.

        """
        # -----------------------------
        # TITRE DE FENÊTRE
        # -----------------------------
        self.setWindowTitle(tr("Traitement SAM3"))

        # -----------------------------
        # STATUS LABEL (états dynamiques possibles)
        # -----------------------------
        if self.progress_bar.value() == 0:
            self.status_label.setText(tr("Initialisation") + "...")
        elif self.progress_bar.value() >= 100:
            self.status_label.setText(tr("Traitement terminé") + ".")

        # -----------------------------
        # FOOTER BUTTON
        # -----------------------------
        self.cancel_btn.setText(tr("Annuler"))

        # -----------------------------
        # COUNT LABEL (inchangé structurellement, mais on garde format)
        # -----------------------------
        self.count_label.setText(f"{self._done} / {self._total}")

        # -----------------------------
        # CONTEXT STATUS UPDATE (si en cours)
        # -----------------------------
        if 0 < self._done < self._total:
            self.status_label.setText(
                f"{tr('Traitement de')} {self._total} {tr('image(s)')}..."
            )

        # -----------------------------
        # FORCE REFRESH UI
        # -----------------------------
        self.update()