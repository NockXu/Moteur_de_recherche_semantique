from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QDoubleSpinBox, QSlider, QSizePolicy,
    QMessageBox, QColorDialog, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QPainter, QColor
from typing import Optional

from .PromptBuilderDialog import PromptBuilderDialog
from vision.SAM3AsyncManager import get_sam3_manager
from .ResultWidget import ResultsTable

from common.Image_Classes.Image import Image

from ui.utils.i18n import tr

# ------------------------------------------------------------------ #
#  Helpers                                                           #
# ------------------------------------------------------------------ #

class AutoElideLabel(QLabel):
    """Text label component that automatically cuts and elides long paths or text inputs."""
    
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setToolTip(text)

    def setFullText(self, text: str) -> None:
        """Assigns the complete string sequence and updates structural text metrics.

        Args:
            text (str): Incoming raw sentence characters.
        """
        self._full_text = text
        self.setToolTip(text)
        self.update()

    def paintEvent(self, event) -> None:
        """Intercepts paint routines to squeeze matching text blocks inside borders."""
        metrics = QFontMetrics(self.font())
        width = self.contentsRect().width()
        if width <= 0:
            return
        elided = metrics.elidedText(
            self._full_text,
            Qt.TextElideMode.ElideRight,
            width
        )
        painter = QPainter(self)
        painter.drawText(self.rect(), self.alignment(), elided)


class ClickableRow(QWidget):
    """Custom wrapper row container allowing direct layout click event captures."""
    clicked = pyqtSignal()

    def mousePressEvent(self, event) -> None:
        """Captures press gestures to fire custom interaction signals."""
        self.clicked.emit()
        super().mousePressEvent(event)


# ------------------------------------------------------------------ #
#  Sam3Widget                                                        #
# ------------------------------------------------------------------ #

class Sam3Widget(QWidget):
    """Interactive control dock managing multi-prompt segmentation setups powered by SAM3 AI models.

    Signals:
        prompt_selected (pyqtSignal[dict]): Broadcasts parameters of the active configured prompt.
        results_displayed (pyqtSignal[object]): Fires details about selected output mask layers.
        results_cleared (pyqtSignal[list]): Announces manual purge events targeting localized image logs.
        multi_prompts_send (pyqtSignal[list]): Transfers clean text queries across global project scopes.

    Args:
        sam3_root (str): Execution root directory for runtime model assets. Defaults to target path.
        device (str): Compute layer architecture hardware binding flag. Defaults to "cuda".
    """
    prompt_selected   = pyqtSignal(dict)
    results_displayed = pyqtSignal(object)
    results_cleared = pyqtSignal(list)
    multi_prompts_send = pyqtSignal(list)

    def __init__(self, sam3_root: str = "./vision/sam3/sam3", device: str = "cuda"):
        super().__init__()

        self.sam3_root = sam3_root
        self.confidence_threshold = 0.5
        self.device = device
        self.image_path = None

        self._sam3_manager = get_sam3_manager(
            self.sam3_root, self.confidence_threshold, self.device
        )
        self._current_job_id: str | None = None
        self.prompt_list: list[tuple[dict, QWidget]] = []

        self._init_ui()
        self._connect_signals()
        self._connect_sam3_manager()

    # ------------------------------------------------------------------ #
    #  Modèle                                                             #
    # ------------------------------------------------------------------ #

    def _connect_sam3_manager(self) -> None:
        """Binds localized thread processors to global background async response managers."""
        self._sam3_manager.ready.connect(self._on_model_ready)
        self._sam3_manager.result.connect(self._on_sam3_result)
        self._sam3_manager.error.connect(self._on_sam3_error)

        if self._sam3_manager.is_ready:
            self._on_model_ready()

    def _on_model_ready(self) -> None:
        """Unlocks submission UI pathways once core model weights are fully mapped."""
        self.send_btn.setEnabled(True)
        self.send_btn.setText(tr("RECHERCHER"))

    # ------------------------------------------------------------------ #
    #  UI                                                                 #
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        """Initializes internal segmentation dock dimensions and builds widget frames."""
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.setMinimumWidth(300)
        self.setMinimumHeight(400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._init_header()
        self._init_prompt_entry()
        self._init_footer()

    def _init_header(self) -> None:
        """Builds regional layouts reserved for handling top-aligned parameters."""
        self.header_layout = QVBoxLayout()
        self.main_layout.addLayout(self.header_layout)

    def _init_prompt_entry(self) -> None:
        """Assembles prompt tracking scroll structures and operational add/reset toggles."""
        self.prompt_layout = QVBoxLayout()
        self.main_layout.addLayout(self.prompt_layout)

        self.prompt_label = QLabel(tr("Détails à analyser :"))
        self.prompt_layout.addWidget(self.prompt_label)

        self.prompt_button_layout = QHBoxLayout()
        self.add_btn   = QPushButton(tr("Ajouter"))
        self.reset_btn = QPushButton(tr("Réinitialiser"))
        self.prompt_button_layout.addWidget(self.add_btn)
        self.prompt_button_layout.addWidget(self.reset_btn)
        self.prompt_layout.addLayout(self.prompt_button_layout)

        self.prompt_entry_scroll_area = QScrollArea()
        self.prompt_entry_scroll_area.setMinimumHeight(200)
        self.prompt_entry_scroll_area.setWidgetResizable(True)

        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(2, 2, 2, 2)
        self.scroll_layout.setSpacing(2)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.prompt_entry_scroll_area.setWidget(self.scroll_widget)
        self.prompt_layout.addWidget(self.prompt_entry_scroll_area)

    def _init_footer(self) -> None:
        """Initializes processing triggers, multi-mode drop menus, and the masking results view."""
        self.footer_layout = QVBoxLayout()
        self.footer_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.main_layout.addLayout(self.footer_layout)

        self.send_btn = QPushButton(tr("RECHERCHER"))
        self.send_btn.setEnabled(False)

        menu = QMenu(self)

        action_signal1 = menu.addAction(tr("Seul"))
        action_signal2 = menu.addAction(tr("Tous"))

        action_signal1.triggered.connect(self._send_prompts)
        action_signal2.triggered.connect(self._send_to_all)

        self.send_btn.setMenu(menu)

        self.footer_layout.addWidget(self.send_btn)

        # --- En-tête résultats ---
        results_header = QHBoxLayout()
        self.results_label = QLabel(tr("Résultats fusionnés :"))
        self.results_label.setStyleSheet("font-weight: bold;")
        results_header.addWidget(self.results_label)
        results_header.addStretch()

        self.clear_result_btn = QPushButton(tr("Effacer tout"))
        self.clear_result_btn.setFixedHeight(22)
        self.clear_result_btn.setStyleSheet("font-size: 11px; padding: 0 6px;")
        self.clear_result_btn.clicked.connect(self.clear_results)
        results_header.addWidget(self.clear_result_btn)

        self.clear_sel_btn = QPushButton(tr("Désélectionner"))
        self.clear_sel_btn.setFixedHeight(22)
        self.clear_sel_btn.setStyleSheet("font-size: 11px; padding: 0 6px;")
        self.clear_sel_btn.clicked.connect(self._deselect_all_results)
        results_header.addWidget(self.clear_sel_btn)

        self.footer_layout.addLayout(results_header)

        # --- Scroll résultats ---
        self.results_widget = ResultsTable()

        self.footer_layout.addWidget(self.results_widget)

    def _connect_signals(self) -> None:
        """Binds interface button clicks and row selection outputs directly to slot callbacks."""
        self.add_btn.clicked.connect(self._add_prompt)
        self.reset_btn.clicked.connect(self._reset_prompts)
        self.results_widget.result_selected.connect(self.on_result_row_selected)

    # ------------------------------------------------------------------ #
    #  Prompts                                                            #
    # ------------------------------------------------------------------ #

    def mousePressEvent(self, event) -> None:
        """Tracks open clicks outside rows to easily clear highlighted configurations."""
        child = self.childAt(event.pos())
        if child:
            parent = child
            while parent is not None:
                if isinstance(parent, ClickableRow):
                    return super().mousePressEvent(event)
                parent = parent.parent()
        self.prompt_selected.emit({})
        return super().mousePressEvent(event)

    def _add_prompt(self, data: dict | bool | None = None) -> None:
        """Launches editing wizard dialogues and creates a summary row tracking prompts inside lists.

        Args:
            data (dict | bool | None): Existing configurations to load, fallback, or replace.
        """
        
        # Their was instance were data wad a bool and was crashing the app so this is a countermesure
        if isinstance(data, bool):
            data = None
        if data is None:
            data = {}

            if not self.image_path:
                QMessageBox.warning(self, "Erreur", "Veuillez d'abord sélectionner une image.")
                return

            dialog = PromptBuilderDialog(self, self.image_path)
            if not dialog.exec():
                return

            data.update(dialog.result)

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(2, 2, 2, 2)

        label    = AutoElideLabel()
        edit_btn = QPushButton(tr("Modifier"))
        del_btn  = QPushButton(tr("Supprimer"))

        row_layout.addWidget(label, stretch=1)
        row_layout.addWidget(edit_btn)
        row_layout.addWidget(del_btn)

        container = ClickableRow()
        container.clicked.connect(lambda d=data: self.prompt_selected.emit(d))
        container.setLayout(row_layout)
        self.scroll_layout.addWidget(container)

        self.prompt_list.append((data, container))
        self._refresh_label(label, data)

        def edit():
            dlg = PromptBuilderDialog(self, self.image_path)

            # -----------------------------
            # Init prompt + threshold
            # -----------------------------
            dlg._prompt_edit.setText(data.get("prompt", ""))
            dlg.threshold_slider.setValue(int(data.get("threshold", 0.5) * 100))

            # -----------------------------
            # Load boxes (avec labels)
            # -----------------------------
            dlg._image_view.load_boxes(
                boxes=data.get("boxes", []),
                labels=data.get("labels", []),
                colors=data.get("colors", [])
            )

            # IMPORTANT: on reconstruit depuis _boxes pour garder label + color
            dlg._clear_rows()

            for idx, box in dlg._image_view._boxes.items():

                rect = box["rect"]

                coords = [
                    rect.x(),
                    rect.y(),
                    rect.x() + rect.width(),
                    rect.y() + rect.height(),
                ]

                color = box.get("color")
                label_bool = box.get("label", None)

                dlg._add_row_from_image_box(
                    idx,
                    coords,
                    color,
                    label_bool
                )

            # -----------------------------
            # Validation dialog
            # -----------------------------
            if dlg.exec():
                data.update(dlg.result)
                self._refresh_label(label, data)
                self.prompt_selected.emit(data)
            else:
                self.prompt_selected.emit({})

        def remove():
            self._remove_prompt(data, container)
            self.prompt_selected.emit({})

        edit_btn.clicked.connect(edit)
        del_btn.clicked.connect(remove)

    def _refresh_label(self, label: AutoElideLabel, data: dict) -> None:
        """Formats the text block inside prompt rows summarizing parameters and box scores.

        Args:
            label (AutoElideLabel): Target row visual label text.
            data (dict): Query dictionary holding parameter variables.
        """
        boxes     = data.get("boxes", [])
        labels    = data.get("labels", [])
        prompt    = data.get("prompt", "")
        threshold = data.get("threshold", 0.0)
        pos = sum(1 for l in labels if l)
        neg = len(labels) - pos
        label.setFullText(
            f"{threshold * 100:.0f}% | {prompt} {len(boxes)} boîte(s)  ✔{pos} ✖{neg}"
        )

    def _remove_prompt(self, data: dict, container: QWidget) -> None:
        """Purges a single tracked query block and cleans up associated UI row sub-elements.

        Args:
            data (dict): Reference prompt item being deleted.
            container_row (QWidget): Visual layout wrapper hosting the targets.
        """
        self.prompt_list = [(d, w) for d, w in self.prompt_list if d is not data]
        self.scroll_layout.removeWidget(container)
        container.deleteLater()

    def _reset_prompts(self) -> None:
        """Clears out all existing summary tracking elements out of prompt display docks."""
        for _, widget in self.prompt_list:
            self.scroll_layout.removeWidget(widget)
            widget.deleteLater()
        self.prompt_list.clear()

    # ------------------------------------------------------------------ #
    #  Envoi & résultats                                                  #
    # ------------------------------------------------------------------ #

    def _send_prompts(self) -> None:
        """Packages localized parameter structures and offloads computation requests to background queues."""
        if self._current_job_id is not None:
            return

        if not self.image_path:
            QMessageBox.warning(self, tr("Erreur"), tr("Veuillez d'abord sélectionner une image."))
            return

        prompts = self.get_prompts()
        if not prompts:
            return

        self.image.set_prompts(self.get_prompts_for_all())

        self.send_btn.setEnabled(False)
        self.send_btn.setText("Recherche...")
        self._current_job_id = self._sam3_manager.process_image(
            str(self.image_path), prompts
        )

    def _on_sam3_result(self, job_id: str, image_path: str, results: list) -> None:
        """Applies received model segmentation overlays on database entries when IDs line up.

        Args:
            job_id (str): Background tracking ID token generated at launch.
            image_path (str): Target filesystem image location string.
            results (list): Parsed model response overlay coordinates.
        """
        if job_id != self._current_job_id:
            return

        self._current_job_id = None
        self.send_btn.setEnabled(True)
        self.send_btn.setText(tr("RECHERCHER"))
        self.results_widget.load_results(results)

        self.image.set_SAM3_results(self.results_widget.get_results())

    def _on_sam3_error(self, job_id: str, error: str) -> None:
        """Catches job task runtime failures and reverts lock buttons to matching base states.

        Args:
            job_id (str): Unique processing execution identification hash.
            error (str): System message detailing reasons for task execution failures.
        """
        if job_id and job_id != self._current_job_id:
            return

        self._current_job_id = None
        self.send_btn.setEnabled(self._sam3_manager.is_ready)
        self.send_btn.setText(tr("RECHERCHER"))
        QMessageBox.warning(self, tr("Erreur SAM3"), error)

    def _send_to_all(self) -> None:
        """Broadcasts current prompt configurations over global data pipes."""
        self.multi_prompts_send.emit(self.get_prompts_for_all())

    def get_prompts_for_all(self) -> list[dict]:
        """Filters complex graphical coordinates down to basic search text data items.

        Returns:
            A clean list containing keyword phrases paired with accuracy margins.
        """
        prompts: list[dict] = []

        for prompt in self.get_prompts():
            text = prompt.get("prompt", "visual")
            threshold = prompt.get("threshold", 0.5)

            prompts.append({"prompt": text, "threshold": threshold})
        
        return prompts

    def _deselect_all_results(self) -> None:
        """Clears highlighted row references out of table displays."""
        self.results_widget.clear_selection()

    def on_result_row_selected(self, result: dict) -> None:
        """Dispatches parameters matching selected tabular entries back out to listeners.

        Args:
            result (dict): Data slice identifying the selected segment row properties.
        """
        self.results_displayed.emit(result)

    # ------------------------------------------------------------------ #
    #  API                                                               #
    # ------------------------------------------------------------------ #

    def get_prompts(self) -> list[dict]:
        """Extracts data dictionaries out of currently tracked input rows.

        Returns:
            The complete list of query parameter specifications.
        """
        return [data for data, _ in self.prompt_list]

    def set_image(self, image: Image) -> None:
        """Binds a fresh image object and re-populates preexisting analysis rows.

        Args:
            image (Image): The new target tracking asset model to show.
        """
        self.image = image
        self.image_path = image.path
        results = self.image.get_SAM3_results()
        if results is not None:
            self.set_results(results)
        else:
            self._clear_local_results()
            self._reset_prompts()

    def set_results(self, results: list[dict]) -> None:
        """Loads cached analytical outputs into result boxes and reconstructs prompt rows.

        Args:
            results (list[dict]): Saved segment coordinates metadata.
        """
        if not results:
            self._clear_local_results()
            return

        # Recharge le tableau des résultats
        self.results_widget.load_results(results)

        # Reconstruit les prompts
        self._reset_prompts()

        for result in results:
            text = result.get("prompt", "")

            prompt_data = {
                "prompt": text,
                "boxes": [],
                "labels": [],
                "colors": [],
                "threshold": self.image.prompts.get(text, 0.5),
            }

            self._add_prompt(prompt_data)

    def clear_results(self) -> None:
        """Purges active display data lists and broadcasts local path deletion keys."""
        self._clear_local_results()
        self.results_cleared.emit([str(self.image_path)])

    def _clear_local_results(self) -> None:
        """Resets the core results matrix layout frame."""
        self.results_widget.clear()
        
    def _on_language_changed(self, lang_code: str | None = None) -> None:
        """Refreshes all displayed interface text lines whenever active system translation keys change.

        Args:
            lang_code (str | None): Target language code abbreviation string. Defaults to None.
        """
        # ----------------------------
        # Labels principaux UI
        # ----------------------------
        self.prompt_label.setText(tr("Détails à analyser :"))
        self.add_btn.setText(tr("Ajouter"))
        self.reset_btn.setText(tr("Réinitialiser"))
        self.results_label.setText(tr("Résultats fusionnés :"))

        # bouton principal (attention: il a un menu, donc on update aussi ses actions)
        self.send_btn.setText(tr("RECHERCHER"))

        # ----------------------------
        # Menu du bouton send_btn
        # ----------------------------
        menu = self.send_btn.menu()
        if menu:
            actions = menu.actions()
            if len(actions) >= 2:
                actions[0].setText(tr("Seul"))
                actions[1].setText(tr("Tous"))

        # ----------------------------
        # Refresh prompts affichés
        # ----------------------------
        for data, widget in self.prompt_list:
            label = widget.layout().itemAt(0).widget()
            self._refresh_label(label, data)

        # ----------------------------
        # Refresh résultats (si besoin de labels traduits)
        # ----------------------------
        self.results_widget.refresh_ui_language()
        
        self.clear_result_btn.setText(tr("Effacer tout"))
        self.clear_sel_btn.setText(tr("Désélectionner"))

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = Sam3Widget()
    widget.show()
    sys.exit(app.exec())
