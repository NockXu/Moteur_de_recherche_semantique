from PyQt6.QtWidgets import QLayout, QLayoutItem
from PyQt6.QtCore import QRect, QSize, Qt


class JustifiedGalleryLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=8):
        super().__init__(parent)

        self._item_list = []
        self._spacing = spacing

        self.setContentsMargins(margin, margin, margin, margin)

    # ----------------------------
    # BASIC REQUIRED METHODS
    # ----------------------------

    def addItem(self, item: QLayoutItem):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def sizeHint(self):
        return QSize(800, 600)

    def minimumSize(self):
        return QSize(200, 200)

    # ----------------------------
    # CORE JUSTIFIED LAYOUT
    # ----------------------------

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)

        if not self._item_list:
            return

        TARGET_HEIGHT = 180
        SPACING = self._spacing

        x0 = rect.x()
        y = rect.y()
        max_width = rect.width()

        row = []
        row_width = 0

        i = 0
        while i < len(self._item_list):
            item = self._item_list[i]
            widget = item.widget()

            if widget is None:
                i += 1
                continue

            ratio = getattr(widget, "aspect_ratio", 1.0)

            # largeur théorique à hauteur fixe
            w = TARGET_HEIGHT * ratio

            # si la ligne dépasse -> flush
            if row and (row_width + w + SPACING * len(row)) > max_width:

                self._layout_row(
                    row=row,
                    row_width=row_width,
                    rect_x=x0,
                    y=y,
                    max_width=max_width,
                    target_height=TARGET_HEIGHT,
                    spacing=SPACING
                )

                # avance en Y
                scale = self._compute_scale(row_width, max_width, len(row), SPACING)
                y += TARGET_HEIGHT * scale + SPACING

                row = []
                row_width = 0

            row.append((item, ratio))
            row_width += w
            i += 1

        # dernière ligne (non justifiée)
        x = x0
        for item, ratio in row:
            w = TARGET_HEIGHT * ratio
            h = TARGET_HEIGHT

            widget = item.widget()
            if widget:
                widget.setGeometry(int(x), int(y), int(w), int(h))
                widget._update_pixmap_to_label()

            x += w + SPACING

        # hauteur totale calculée
        total_height = y + TARGET_HEIGHT

        parent = self.parentWidget()
        if parent is not None:
            parent.setMinimumHeight(int(total_height))
            parent.resize(parent.width(), int(total_height))

    # ----------------------------
    # ROW LAYOUT HELPERS
    # ----------------------------

    def _layout_row(self, row, row_width, rect_x, y, max_width, target_height, spacing):
        """
        Étire une ligne pour remplir toute la largeur.
        """
        if not row:
            return

        scale = self._compute_scale(row_width, max_width, len(row), spacing)

        x = rect_x
        h = target_height * scale

        for item, ratio in row:
            w = target_height * ratio * scale

            widget = item.widget()
            if widget:
                widget.setGeometry(
                    int(x),
                    int(y),
                    int(w),
                    int(h)
                )
                widget._update_pixmap_to_label()

            x += w + spacing

    def _compute_scale(self, row_width, max_width, n_items, spacing):
        """
        Calcule le facteur d'étirement pour remplir la ligne.
        """
        total_spacing = spacing * (n_items - 1)
        if row_width + total_spacing == 0:
            return 1.0

        return (max_width - total_spacing) / row_width

    # ----------------------------
    # OPTIONAL CLEANUP
    # ----------------------------

    def clear(self):
        while self._item_list:
            item = self._item_list.pop()
            if item.widget():
                item.widget().setParent(None)