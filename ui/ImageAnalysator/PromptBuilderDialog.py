from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QScrollArea,
    QWidget, QFrame, QSplitter, QLineEdit,
    QMessageBox, QSlider, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor

from .ImageView import ImageView

from ui.utils.i18n import tr

class BoxRow(QWidget):
    """
    Widget représentant une boîte dans le scroll.
    Affiche : [couleur] [coords] [bouton +/-] [supprimer]
    """

    def __init__(self, box_index: int, coords: list[float], color: QColor, parent=None):
        super().__init__(parent)

        self.box_index = box_index
        self.coords = coords      # [x1, y1, x2, y2]
        self.label: bool = True   # True = positif, False = négatif
        self.threshold_value = 0.5

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # Pastille de couleur
        self.color_dot = QLabel()
        self.color_dot.setFixedSize(16, 16)
        self.color_dot.setStyleSheet(
            f"background-color: {color.name()}; border-radius: 8px;"
        )
        layout.addWidget(self.color_dot)

        # Index + coordonnées
        x1, y1, x2, y2 = [int(v) for v in coords]
        self.coords_label = QLabel(f"#{box_index}  [{x1}, {y1}, {x2}, {y2}]")
        self.coords_label.setStyleSheet("font-family: monospace; font-size: 12px;")
        layout.addWidget(self.coords_label, stretch=1)

        # Bouton toggle True / False
        self.toggle_btn = QPushButton()
        self.toggle_btn.clicked.connect(self._toggle_label)
        self._refresh_toggle()
        layout.addWidget(self.toggle_btn)

        # Bouton supprimer
        self.delete_btn = QPushButton("✕")
        self.delete_btn.setFixedWidth(28)
        self.delete_btn.setStyleSheet(
            "color: #e05c5c; font-weight: bold; border: none; background: transparent;"
        )
        layout.addWidget(self.delete_btn)

        self.setStyleSheet("BoxRow { border-bottom: 1px solid #2a2a2a; }")

    def _toggle_label(self):
        self.label = not self.label
        self._refresh_toggle()

    def _refresh_toggle(self):
        if self.label:
            self.toggle_btn.setText("✔")
            self.toggle_btn.setStyleSheet(
                "background-color: #2d6a4f; color: #b7e4c7; "
                "border-radius: 4px; font-size: 12px; padding: 2px 6px;"
            )
        else:
            self.toggle_btn.setText("✖")
            self.toggle_btn.setStyleSheet(
                "background-color: #6a2d2d; color: #e4b7b7; "
                "border-radius: 4px; font-size: 12px; padding: 2px 6px;"
            )

    def update_coords(self, coords: list[float]):
        self.coords = coords

        x1, y1, x2, y2 = [int(v) for v in coords]
        self.coords_label.setText(f"#{self.box_index}  [{x1}, {y1}, {x2}, {y2}]")

class PromptBuilderDialog(QDialog):
    """
    Dialog pour construire un visual_prompt SAM3.
    Contient un ImageView intégré pour dessiner des boîtes à la souris.

    result : {
        "type": "visual",
        "boxes": [[x1,y1,x2,y2], ...],
        "labels": [True/False, ...]
    }
    """

    def __init__(self, parent=None, image_path: str | None = None):
        super().__init__(parent)

        self.setWindowTitle(tr("Créer un prompt SAM3"))
        self.setMinimumWidth(700)
        self.setMinimumHeight(520)

        self.result = None
        self._rows: list[BoxRow] = []

        self._init_ui()

        if image_path:
            self.load_image(image_path)

    # ------------------------------------------------------------------ #
    #  Construction de l'UI                                              #
    # ------------------------------------------------------------------ #

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        # ---- Prompt texte ----
        prompt_label = QLabel(tr("Prompt"))
        prompt_label.setStyleSheet("font-weight: bold;")

        self._prompt_edit = QLineEdit()
        self._prompt_edit.setPlaceholderText(
            tr("Décrivez ce que SAM doit segmenter...")
        )

        root.addWidget(prompt_label)
        root.addWidget(self._prompt_edit)

        # Splitter horizontal : ImageView à gauche, liste à droite
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---- Panneau gauche : ImageView + boutons de sélection ----
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(6)

        self._image_view = ImageView(selectable=True)
        self._image_view.setMinimumSize(300, 300)
        left_layout.addWidget(self._image_view, stretch=1)

        self._image_view.selection_finished.connect(self._apply_selection)
        self._image_view.box_changed.connect(self._on_box_changed)

        splitter.addWidget(left_panel)

        # ---- Panneau droit : liste des boîtes ----
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(6)

        list_header = QLabel(tr("Boîtes de sélection"))
        list_header.setStyleSheet("font-weight: bold; font-size: 13px;")
        right_layout.addWidget(list_header)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.StyledPanel)

        self._scroll_content = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_content)
        self._scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll_layout.setSpacing(0)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)

        self._empty_label = QLabel(tr("Dessinez une zone sur l'image."))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: #666; font-style: italic; padding: 20px;"
        )
        self._scroll_layout.addWidget(self._empty_label)

        self._scroll_area.setWidget(self._scroll_content)
        right_layout.addWidget(self._scroll_area, stretch=1)

        # Bouton « Tout effacer »
        clear_btn = QPushButton(f"{tr('Tout effacer')}")
        clear_btn.clicked.connect(self._clear_all)
        right_layout.addWidget(clear_btn)

        splitter.addWidget(right_panel)
        splitter.setSizes([420, 280])

        root.addWidget(splitter, stretch=1)

        # ---- FOOTER (threshold bar en bas du widget) ----
        self.footer_layout = QVBoxLayout()

        self.threshold_label = QLabel(tr("Seuil de confiance :"))
        self.threshold_label.setStyleSheet("font-weight: bold;")

        self.footer_layout.addWidget(self.threshold_label)

        self.threshold_layout = QHBoxLayout()

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(50)

        self.threshold = QDoubleSpinBox()
        self.threshold.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.threshold.setRange(0.0, 1.0)
        self.threshold.setSingleStep(0.01)
        self.threshold.setValue(0.5)
        self.footer_layout.setContentsMargins(0, 10, 0, 0)
        self.footer_layout.setSpacing(4)

        self.threshold_layout.addWidget(self.threshold_slider)
        self.threshold_layout.addWidget(self.threshold)

        self.footer_layout.addLayout(self.threshold_layout)

        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold.setValue(v / 100.0)
        )

        self.threshold.valueChanged.connect(
            lambda v: self.threshold_slider.setValue(int(v * 100))
        )

        root.addLayout(self.footer_layout)

        # ---- Boutons OK / Annuler ----
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton(tr("OK"))
        ok_btn.setDefault(True)
        cancel_btn = QPushButton(tr("Annuler"))

        ok_btn.clicked.connect(self._build_result)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        root.addLayout(btn_layout)

    # ------------------------------------------------------------------ #
    #  API publique                                                      #
    # ------------------------------------------------------------------ #

    def load_image(self, image_path: str):
        """Charge une image dans l'ImageView intégré."""
        self._image_view.setImage(image_path)

    def add_box(self, box_index: int, coords: list[float], color: QColor | None = None):
        """
        Ajoute manuellement une boîte dans la liste (sans passer par l'ImageView).
        """
        if color is None:
            color = self._image_view._next_box_color()

        row = BoxRow(box_index, coords, color, parent=self._scroll_content)
        row.delete_btn.clicked.connect(lambda _, r=row: self._remove_row(r))

        self._rows.append(row)
        self._scroll_layout.addWidget(row)
        self._refresh_empty()

    def add_boxes_from_view(self, image_view: ImageView):
        """
        Importe toutes les boîtes validées depuis un ImageView externe.
        Vide la liste existante et synchronise l'ImageView interne.
        """
        self._clear_rows()
        for idx, box in image_view.get_all_boxes().items():
            self._image_view._boxes[idx] = {
                "rect": box["rect"],
                "color": box["color"],
            }
            self._image_view._next_index = max(
                self._image_view._next_index, idx + 1
            )
            coords = [
                box["rect"].x(),
                box["rect"].y(),
                box["rect"].x() + box["rect"].width(),
                box["rect"].y() + box["rect"].height(),
            ]
            self._add_row_from_image_box(idx, coords, box["color"])

        self._image_view.update()

    # ------------------------------------------------------------------ #
    #  Sélection depuis l'ImageView interne                              #
    # ------------------------------------------------------------------ #

    def _apply_selection(self):
        """Valide la sélection courante de l'ImageView et l'ajoute à la liste."""

        rect = self._image_view.get_selection_rect_image_coords()
        idx = self._image_view.apply_selection()

        if idx is None:
            return

        # Coordonnées réelles image
        
        if rect is None:
            return

        coords = [
            rect.x(),
            rect.y(),
            rect.x() + rect.width(),
            rect.y() + rect.height(),
        ]

        # Couleur affichage
        color = self._image_view._boxes[idx]["color"]

        self._add_row_from_image_box(idx, coords, color)

    def _add_row_from_image_box(self, idx: int, coords: list[float], color: QColor, label : bool = True):
        row = BoxRow(idx, coords, color, parent=self._scroll_content)
        if not label:
            row._toggle_label()

        def on_delete(_, r=row, i=idx):
            self._image_view.delete_box(i)
            self._remove_row(r)

        row.delete_btn.clicked.connect(on_delete)

        self._rows.append(row)
        self._scroll_layout.addWidget(row)
        self._refresh_empty()

    # ------------------------------------------------------------------ #
    #  Redimensionnement des boîtes                                      #
    # ------------------------------------------------------------------ #

    def _on_box_changed(self, idx, rect):
        coords = [
            rect.x(),
            rect.y(),
            rect.x() + rect.width(),
            rect.y() + rect.height(),
        ]

        for row in self._rows:
            if row.box_index == idx:
                row.update_coords(coords)
                break

    # ------------------------------------------------------------------ #
    #  Chargement image via dialog fichier                               #
    # ------------------------------------------------------------------ #

    def _open_image_dialog(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, f"{tr('Ouvrir une image')}", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"
        )
        if path:
            self.load_image(path)

    # ------------------------------------------------------------------ #
    #  Logique interne                                                   #
    # ------------------------------------------------------------------ #

    def _remove_row(self, row: BoxRow):
        if row in self._rows:
            self._rows.remove(row)
        self._scroll_layout.removeWidget(row)
        row.deleteLater()
        self._refresh_empty()

    def _clear_rows(self):
        for row in list(self._rows):
            self._scroll_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()
        self._refresh_empty()

    def _clear_all(self):
        """Supprime toutes les boîtes (liste + ImageView)."""
        for row in list(self._rows):
            self._image_view.delete_box(row.box_index)
        self._clear_rows()

    def _refresh_empty(self):
        self._empty_label.setVisible(len(self._rows) == 0)

    def _build_result(self):
        prompt = self._prompt_edit.text().strip()

        if not prompt:
            prompt = "visual"

        if not self._rows:
            self._rows = []

        self.result = {
            "type": "visual",
            "prompt": prompt,
            "threshold": float(self.threshold.value()),
            "boxes": [row.coords for row in self._rows],
            "labels": [row.label for row in self._rows],
        }

        self.accept()