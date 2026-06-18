from __future__ import annotations

"""PySide6 port of the widgets/layouts/flowlayout example from Qt v6.x"""

import sys
from PyQt6.QtCore import Qt, QMargins, QPoint, QRect, QSize
from PyQt6.QtWidgets import QApplication, QLayout, QPushButton, QSizePolicy, QWidget

class FlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(QMargins(0, 0, 0, 0))

        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
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

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        line_items = []      # 🔥 items de la ligne courante
        line_start_x = x     # début de ligne

        for item in self._item_list:
            style = item.widget().style()

            layout_spacing_x = style.layoutSpacing(
                QSizePolicy.ControlType.PushButton,
                QSizePolicy.ControlType.PushButton,
                Qt.Orientation.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                QSizePolicy.ControlType.PushButton,
                QSizePolicy.ControlType.PushButton,
                Qt.Orientation.Vertical
            )

            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y

            item_w = item.sizeHint().width()
            item_h = item.sizeHint().height()

            next_x = x + item_w + space_x

            # ─────────────────────────────
            # WRAP
            # ─────────────────────────────
            if next_x - space_x > rect.right() and line_height > 0:

                # 🔥 CENTRAGE DE LA LIGNE
                line_width = (x - line_start_x) - space_x

                offset = (rect.width() - line_width) // 2

                if not test_only:
                    for i in line_items:
                        geo = i.geometry()
                        i.setGeometry(
                            QRect(
                                QPoint(geo.x() + offset, geo.y()),
                                i.sizeHint()
                            )
                        )

                # reset ligne
                x = rect.x()
                y = y + line_height + space_y
                line_height = 0
                line_items = []
                line_start_x = x

                next_x = x + item_w + space_x

            # placement normal
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            line_items.append(item)

            x = next_x
            line_height = max(line_height, item_h)

        # ─────────────────────────────
        # DERNIÈRE LIGNE (centrage aussi)
        # ─────────────────────────────
        if line_items:
            line_width = (x - line_start_x) - space_x
            offset = (rect.width() - line_width) // 2

            if not test_only:
                for i in line_items:
                    geo = i.geometry()
                    i.setGeometry(
                        QRect(
                            QPoint(geo.x() + offset, geo.y()),
                            i.sizeHint()
                        )
                    )

        return y + line_height - rect.y()

    def minimumSize(self):
        return QSize(0, 0)