from typing import Any, Dict, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QColorDialog,
    QGraphicsOpacityEffect,
)

from ui.utils.i18n import tr

class ColorDot(QPushButton):

    colorChanged = pyqtSignal()

    def __init__(self, color=None):
        super().__init__()

        self._color = color or QColor(80, 160, 255)

        self.setObjectName("ColorDot")

        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)

        self.clicked.connect(self._pick_color)

        self._refresh()

    def color(self) -> QColor:
        return self._color

    def _pick_color(self):

        color = QColorDialog.getColor(self._color, self)

        if color.isValid():
            self._color = color
            self._refresh()
            self.colorChanged.emit()

    def _refresh(self):
        self.setStyleSheet(f"""
            QPushButton#ColorDot {{
                background-color: {self._color.name()};
                border-radius: 9px;
                border: 1px solid #444;
            }}
        """)

class ResultsTable(QWidget):

    result_selected = pyqtSignal(list)

    # Couleurs de sélection
    SEL_BG_ALPHA   = 55   # fond teinté (0-255)
    SEL_LEFT_W     = 4    # épaisseur de la barre gauche en px
    PROMPT_SEL_BG  = QColor(60, 100, 180, 80)   # teinte groupe sélectionné

    def __init__(self):
        super().__init__()

        self.selected = []
        self._all_results_cache = []

        # row_index → dot widget (pour récupérer la couleur choisie)
        self._row_dot: dict[int, "ColorDot"] = {}

        self.table = QTableWidget()

        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            [tr("Résultat"), tr("Score"), tr("Boxe"), tr("Color")]
        )

        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )

        # Désactive la sélection native Qt (on gère la nôtre)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.table.cellClicked.connect(self._on_cell_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)

    # =========================
    # CLEARS
    # =========================

    def clear_selection(self):

        self.selected.clear()
        self.table.clearSelection()
        self._refresh_visuals()

        if __name__ == "__main__":
            print("CLEAR ALL")

    def clear(self):
        self.clear_selection()
        self._all_results_cache.clear()
        self._row_dot.clear()
        self.table.setRowCount(0)
        self.clear_selection()

    # =========================
    # LOAD DATA
    # =========================

    def load_results(self, processed_results: List[Dict[str, Any]]):
        from collections import defaultdict
        import torch # type: ignore

        merged = {}

        for result in processed_results:

            prompt = result.get("prompt")

            if prompt not in merged:
                merged[prompt] = {
                    "prompt": prompt,
                    "scores": [],
                    "boxes": [],
                    "masks": []
                }

            scores = result.get("scores")
            boxes = result.get("boxes")
            masks = result.get("masks")

            if scores is not None:
                merged[prompt]["scores"].extend(scores)

            if boxes is not None:
                merged[prompt]["boxes"].extend(boxes)

            if masks is not None:
                merged[prompt]["masks"].extend(masks)

        processed_results = []

        for data in merged.values():

            processed_results.append({
                "prompt": data["prompt"],
                "scores": torch.stack(data["scores"]) if data["scores"] else None,
                "boxes": torch.stack(data["boxes"]) if data["boxes"] else None,
                "masks": torch.stack(data["masks"]) if data["masks"] else None,
            })

        self.table.setRowCount(0)
        self._all_results_cache.clear()
        self._row_dot.clear()

        row = 0

        for result in processed_results:

            prompt = result.get("prompt", [])
            scores = result.get("scores", [])
            boxes = result.get("boxes", [])
            masks = result.get("masks", [])

            # =====================
            # PROMPT ROW
            # =====================

            self.table.insertRow(row)

            prompt_item = QTableWidgetItem(f"Prompt : {prompt}")

            prompt_item.setFlags(Qt.ItemFlag.ItemIsEnabled)

            prompt_item.setBackground(QColor("#2d3748"))
            prompt_item.setForeground(QColor("white"))

            font = QFont()
            font.setBold(True)
            prompt_item.setFont(font)

            prompt_item.setData(
                Qt.ItemDataRole.UserRole,
                {
                    "type": "prompt",
                    "prompt": prompt
                }
            )

            self.table.setItem(row, 0, prompt_item)
            self.table.setSpan(row, 0, 1, 4)

            row += 1

            # =====================
            # RESULT ROWS
            # =====================

            if scores is None:
                continue

            for i in range(len(scores)):

                self.table.insertRow(row)

                score = scores[i].item()

                box = boxes[i].tolist()

                mask = masks[i]

                result_data = {
                    "type": "result",
                    "prompt": prompt,
                    "index": i,
                    "score": score,
                    "box": box,
                    "color": QColor(80, 160, 255),
                    "row": row,
                    "mask": mask
                }

                self._all_results_cache.append(result_data)

                # Résultat
                it0 = QTableWidgetItem(f"{i+1}")
                it1 = QTableWidgetItem(f"{score:.3f}")
                it2 = QTableWidgetItem(str(box))

                for it in (it0, it1, it2):
                    it.setData(Qt.ItemDataRole.UserRole, result_data)
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.table.setItem(row, 0, it0)
                self.table.setItem(row, 1, it1)
                self.table.setItem(row, 2, it2)

                # Color dot
                dot = ColorDot()
                
                def sync_color(row=row, dot=dot):
                    for r in self._all_results_cache:
                        if r["row"] == row:
                            r["color"] = dot.color()
                    self._refresh_visuals()

                dot.colorChanged.connect(sync_color)

                self.table.setCellWidget(row, 3, dot)
                self._row_dot[row] = dot

                row += 1

        self.table.resizeRowsToContents()
        self.selected = [
                r for r in self._all_results_cache
            ]
        self._refresh_visuals()

    # =========================
    # CLICK HANDLER
    # =========================

    def _on_cell_clicked(self, row, col):

        item = self.table.item(row, 0)

        if not item:
            self.clear_selection()
            return

        data = item.data(Qt.ItemDataRole.UserRole)

        if not data:
            self.clear_selection()
            return

        if data["type"] == "prompt":
            self._toggle_prompt(data)

        elif data["type"] == "result":
            self._toggle_result(data)

    # =========================
    # TOGGLE RESULT
    # =========================

    def _toggle_result(self, data):

        exists = any(
            x["type"] == "result"
            and x["prompt"] == data["prompt"]
            and x["index"] == data["index"]
            for x in self.selected
        )

        if exists:

            self.selected = [
                x for x in self.selected
                if not (
                    x["type"] == "result"
                    and x["prompt"] == data["prompt"]
                    and x["index"] == data["index"]
                )
            ]

            if __name__ == "__main__":
                print("REMOVE", data)

        else:

            self.selected.append(data)

            if __name__ == "__main__":
                print("ADD", data)

        self._refresh_visuals()

    # =========================
    # TOGGLE PROMPT GROUP
    # =========================

    def _toggle_prompt(self, data):

        prompt = data["prompt"]

        group = [
            x for x in self._all_results_cache
            if x["type"] == "result" and x["prompt"] == prompt
        ]

        all_selected = all(
            any(
                s["type"] == "result"
                and s["prompt"] == r["prompt"]
                and s["index"] == r["index"]
                for s in self.selected
            )
            for r in group
        )

        if all_selected:

            self.selected = [
                x for x in self.selected
                if not (x["type"] == "result" and x["prompt"] == prompt)
            ]

            if __name__ == "__main__":
                print("REMOVE GROUP", prompt)

        else:

            for r in group:
                if r not in self.selected:
                    self.selected.append(r)

            if __name__ == "__main__":
                print("ADD GROUP", prompt)

        self._refresh_visuals()

    # =========================
    # VISUAL FEEDBACK
    # =========================

    def _refresh_visuals(self):
        """
        Colore les lignes selon leur état de sélection.

        Lignes résultat sélectionnées :
          - fond teinté avec la couleur du dot (alpha SEL_BG_ALPHA)
          - barre gauche (colonne 0) en couleur pleine du dot
          - texte en blanc gras
        Lignes résultat non sélectionnées → reset
        Lignes prompt → teinte bleue si au moins un enfant sélectionné,
                         teinte complète si tous sélectionnés.
        """

        # Index des résultats sélectionnés pour lookup rapide
        sel_keys = {
            (s["prompt"], s["index"])
            for s in self.selected
            if s["type"] == "result"
        }

        for row in range(self.table.rowCount()):
            item0 = self.table.item(row, 0)
            if item0 is None:
                continue

            data = item0.data(Qt.ItemDataRole.UserRole)

            # ── Ligne résultat ──────────────────────────────────────────
            if data and data["type"] == "result":
                key = (data["prompt"], data["index"])
                selected = key in sel_keys

                if selected:
                    bg = QColor(80, 160, 255)
                    bg.setAlpha(self.SEL_BG_ALPHA)

                    accent = QColor(80, 160, 255)
                    accent.setAlpha(220)

                    font = QFont()
                    font.setBold(True)
                else:
                    bg = QColor(0, 0, 0, 0)      # transparent → thème par défaut
                    accent = bg                # couleur par défaut
                    font = QFont()
                    font.setBold(False)

                for col in range(4):
                    it = self.table.item(row, col)
                    if it is None:
                        continue
                    it.setBackground(bg if col != 0 else accent)
                    it.setFont(font)

            # ── Ligne prompt ────────────────────────────────────────────
            elif data and data["type"] == "prompt":
                prompt = data["prompt"]

                group = [
                    r for r in self._all_results_cache
                    if r["prompt"] == prompt
                ]
                total = len(group)
                n_sel = sum(
                    1 for r in group
                    if (r["prompt"], r["index"]) in sel_keys
                )

                if n_sel == 0:
                    # rien de sélectionné → style par défaut (gris foncé)
                    item0.setBackground(QColor("#2d3748"))
                    item0.setForeground(QColor("white"))
                elif n_sel == total:
                    # tout sélectionné → bleu vif
                    item0.setBackground(QColor(45, 90, 200, 180))
                    item0.setForeground(QColor("white"))
                else:
                    # sélection partielle → bleu intermédiaire
                    item0.setBackground(QColor(40, 70, 150, 120))
                    item0.setForeground(QColor(200, 220, 255))

        for entry in self.selected:
            dot = self._row_dot.get(entry.get("row"))
            if dot:
                entry["color"] = dot.color()

        self.result_selected.emit(self.selected)

    # =========================
    # CLICK OUTSIDE TABLE
    # =========================

    def mousePressEvent(self, event):

        index = self.table.indexAt(event.pos())

        if not index.isValid():
            self.clear_selection()

        super().mousePressEvent(event)

    def get_results(self):
        from collections import defaultdict
        import torch # type: ignore

        grouped = defaultdict(
            lambda: {
                "scores": [],
                "boxes": [],
                "masks": []
            }
        )

        for r in self._all_results_cache:
            grouped[r["prompt"]]["scores"].append(r["score"])
            grouped[r["prompt"]]["boxes"].append(r["box"])
            grouped[r["prompt"]]["masks"].append(r["mask"])

        return [
            {
                "prompt": prompt,
                "scores": torch.tensor(data["scores"]),
                "boxes": torch.tensor(data["boxes"]),
                "masks": torch.stack(data["masks"])
            }
            for prompt, data in grouped.items()
        ]
        
    def refresh_ui_language(self):
        """Met à jour tous les textes de l'UI après changement de langue"""

        # -------------------------
        # Header table
        # -------------------------
        self.table.setHorizontalHeaderLabels(
            [tr("Résultat"), tr("Score"), tr("Boxe"), tr("Color")]
        )

        # -------------------------
        # Prompt rows (colonne fusionnée)
        # -------------------------
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if not item:
                continue

            data = item.data(Qt.ItemDataRole.UserRole)
            if not data:
                continue

            # Prompt rows
            if data.get("type") == "prompt":
                prompt = data.get("prompt", "")
                item.setText(f"{tr('Prompt')} : {prompt}")

        # -------------------------
        # Optionnel: refresh tooltips / futurs labels custom
        # -------------------------
        self.table.viewport().update()

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    import torch # type: ignore

    data = [
        {
            "prompt": "chat",
            "scores": torch.tensor([0.641, 0.504]),
            "boxes": torch.tensor([
                [10, 20, 100, 120],
                [15, 30, 110, 130],
            ])
        },
        {
            "prompt": "chien",
            "scores": torch.tensor([0.912, 0.755, 0.622]),
            "boxes": torch.tensor([
                [50, 60, 150, 180],
                [55, 65, 160, 190],
                [70, 80, 170, 200],
            ])
        }
    ]
    
    app = QApplication(sys.argv)
    
    table = ResultsTable()
    table.show()

    table.load_results(data)

    table.result_selected.connect(lambda result: print("Result selected:", result))
    
    sys.exit(app.exec())