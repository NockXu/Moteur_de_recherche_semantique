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
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setToolTip(text)

    def setFullText(self, text: str):
        self._full_text = text
        self.setToolTip(text)
        self.update()

    def paintEvent(self, event):
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
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


# ------------------------------------------------------------------ #
#  Sam3Widget                                                         #
# ------------------------------------------------------------------ #

class Sam3Widget(QWidget):
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

    def _connect_sam3_manager(self):
        self._sam3_manager.ready.connect(self._on_model_ready)
        self._sam3_manager.result.connect(self._on_sam3_result)
        self._sam3_manager.error.connect(self._on_sam3_error)

        if self._sam3_manager.is_ready:
            self._on_model_ready()

    def _on_model_ready(self):
        self.send_btn.setEnabled(True)
        self.send_btn.setText(tr("RECHERCHER"))

    # ------------------------------------------------------------------ #
    #  UI                                                                 #
    # ------------------------------------------------------------------ #

    def _init_ui(self):
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.setMinimumWidth(300)
        self.setMinimumHeight(400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._init_header()
        self._init_prompt_entry()
        self._init_footer()

    def _init_header(self):
        self.header_layout = QVBoxLayout()
        self.main_layout.addLayout(self.header_layout)

    def _init_prompt_entry(self):
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

    def _init_footer(self):
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

    def _connect_signals(self):
        self.add_btn.clicked.connect(self._add_prompt)
        self.reset_btn.clicked.connect(self._reset_prompts)
        self.results_widget.result_selected.connect(self.on_result_row_selected)

    # ------------------------------------------------------------------ #
    #  Prompts                                                            #
    # ------------------------------------------------------------------ #

    def mousePressEvent(self, event):
        child = self.childAt(event.pos())
        if child:
            parent = child
            while parent is not None:
                if isinstance(parent, ClickableRow):
                    return super().mousePressEvent(event)
                parent = parent.parent()
        self.prompt_selected.emit({})
        return super().mousePressEvent(event)

    def _add_prompt(self, data: dict = None):
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

    def _refresh_label(self, label: AutoElideLabel, data: dict):
        boxes     = data.get("boxes", [])
        labels    = data.get("labels", [])
        prompt    = data.get("prompt", "")
        threshold = data.get("threshold", 0.0)
        pos = sum(1 for l in labels if l)
        neg = len(labels) - pos
        label.setFullText(
            f"{threshold * 100:.0f}% | {prompt} {len(boxes)} boîte(s)  ✔{pos} ✖{neg}"
        )

    def _remove_prompt(self, data: dict, container: QWidget):
        self.prompt_list = [(d, w) for d, w in self.prompt_list if d is not data]
        self.scroll_layout.removeWidget(container)
        container.deleteLater()

    def _reset_prompts(self):
        for _, widget in self.prompt_list:
            self.scroll_layout.removeWidget(widget)
            widget.deleteLater()
        self.prompt_list.clear()

    # ------------------------------------------------------------------ #
    #  Envoi & résultats                                                  #
    # ------------------------------------------------------------------ #

    def _send_prompts(self):
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

    def _on_sam3_result(self, job_id: str, image_path: str, results):
        if job_id != self._current_job_id:
            return

        self._current_job_id = None
        self.send_btn.setEnabled(True)
        self.send_btn.setText(tr("RECHERCHER"))
        self.results_widget.load_results(results)

        self.image.set_SAM3_results(self.results_widget.get_results())

    def _on_sam3_error(self, job_id: str, error: str):
        if job_id and job_id != self._current_job_id:
            return

        self._current_job_id = None
        self.send_btn.setEnabled(self._sam3_manager.is_ready)
        self.send_btn.setText(tr("RECHERCHER"))
        QMessageBox.warning(self, tr("Erreur SAM3"), error)

    def _send_to_all(self):
        self.multi_prompts_send.emit(self.get_prompts_for_all())

    def get_prompts_for_all(self):
        prompts: list[dict] = []

        for prompt in self.get_prompts():
            text = prompt.get("prompt", "visual")
            threshold = prompt.get("threshold", 0.5)

            prompts.append({"prompt": text, "threshold": threshold})
        
        return prompts

    def _deselect_all_results(self):
        self.results_widget.clear_selection()

    def on_result_row_selected(self, result):
        self.results_displayed.emit(result)

    # ------------------------------------------------------------------ #
    #  API                                                               #
    # ------------------------------------------------------------------ #

    def get_prompts(self) -> list[dict]:
        return [data for data, _ in self.prompt_list]

    def set_image(self, image: Image) -> None:
        self.image = image
        self.image_path = image.path
        results = self.image.get_SAM3_results()
        if results is not None:
            self.set_results(results)
        else:
            self._clear_local_results()
            self._reset_prompts()

    def set_results(self, results: list[dict]):
        """Results = résultat de image.get_SAM3_results()
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

    def clear_results(self):
        self._clear_local_results()
        self.results_cleared.emit([str(self.image_path)])

    def _clear_local_results(self):
        self.results_widget.clear()
        
    def _on_language_changed(self, lang_code: str = None) -> None:
        """Met à jour toute l'UI quand la langue change"""
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
