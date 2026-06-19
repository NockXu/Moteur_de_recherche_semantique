from __future__ import annotations
from typing import Optional

from PyQt6.QtCore import (
    Qt, 
    QPointF, 
    pyqtSignal,
    QPropertyAnimation,
    QRect,
    QEasingCurve
)
from PyQt6.QtGui import (
    QPainter, 
    QPainterPath, 
    QPen, 
    QColor, 
    QBrush,
    QTextOption
)
from PyQt6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsTextItem,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsPathItem,
    QWidget,
    QVBoxLayout,
    QFrame
)

from common.History_Classes import Tree, history

from .HistoryPreview import HistoryPreview

import os

class EdgeItem(QGraphicsPathItem):
    """Graphic item representing a cubic Bezier curve link between a parent node and a child node."""
    
    def __init__(self, parent_item, child_item) -> None:
        super().__init__()

        self.parent_item = parent_item
        self.child_item = child_item

        pen = QPen(QColor("#808080"))
        pen.setWidth(2)

        self.setPen(pen)

        self.setZValue(-1)

        self.update_position()

    def update_position(self) -> None:
        """Recalculates the curve geometry based on the bounded boxes positions of both connected nodes."""
        parent_rect = self.parent_item.sceneBoundingRect()
        child_rect = self.child_item.sceneBoundingRect()

        start = QPointF(
            parent_rect.center().x(),
            parent_rect.bottom()
        )

        end = QPointF(
            child_rect.center().x(),
            child_rect.top()
        )

        dy = (end.y() - start.y()) * 0.5

        ctrl1 = QPointF(start.x(), start.y() + dy)
        ctrl2 = QPointF(end.x(), end.y() - dy)

        path = QPainterPath(start)
        path.cubicTo(ctrl1, ctrl2, end)

        self.setPath(path)

class TreeNodeItem(QGraphicsRectItem):
    """Visual bounding box item displaying an abstracted search query representation inside the graph scene."""
    WIDTH = 120
    HEIGHT = 50

    def __init__(self, node: Tree):
        super().__init__(0, 0, self.WIDTH, self.HEIGHT)

        self.node = node

        text = "Empty"
        if node.node and hasattr(node.node, "query"):
            text = node.node.query or "Empty"

        if len(text) > 15:
            text = text[:13] + "…"

        self.text = QGraphicsTextItem(text, self)
        self.text.setDefaultTextColor(Qt.GlobalColor.white)

        self.text.setTextWidth(self.WIDTH)

        option = self.text.document().defaultTextOption()
        option.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)

        self.text.document().setDefaultTextOption(option)

        self.text.setPos(0, 10)

        self.setBrush(QBrush(QColor("#2b2b2b")))
        self.setPen(QPen(QColor("#5a5a5a"), 2))

    def center(self) -> QPointF:
        """Returns the absolute center point coordinate of this node inside the scene.

        Returns:
            QPointF: The center coordinates.
        """
        return self.scenePos() + self.boundingRect().center()

    def mousePressEvent(self, event) -> None:
        """Intercepts the selection click event and re-routes the internal node reference to the scene."""
        scene = self.scene()

        event.ignore()

        if isinstance(scene, HistoryTreeScene):
            if scene and hasattr(scene, "node_clicked"):
                scene.node_clicked.emit(self.node)

    def set_selected(self) -> None:
        """Highlights the item's border using the primary material theme accent color."""
        self.setPen(QPen(QColor(os.environ["QTMATERIAL_PRIMARYCOLOR"]), 2))

    def set_unselected(self) -> None:
        """Resets the item's border using the secondary material theme color."""
        self.setPen(QPen(QColor(os.environ["QTMATERIAL_SECONDARYCOLOR"]), 2))

class HistoryTreeScene(QGraphicsScene):
    """Custom 2D graphics workspace managing the structural computing hierarchy layout and connections visualization."""
    H_SPACING = 180
    V_SPACING = 120

    node_clicked = pyqtSignal(object)

    def __init__(self):
        super().__init__()

        self.node_items: dict[Tree, TreeNodeItem] = {}
        self.edges: list[EdgeItem] = []

        self.tree = None

    # ---------------- TREE ----------------

    def set_tree(self, tree: Optional[Tree]) -> None:
        """Clears the previous architecture canvas and recalculates the new graph projection layout.

        Args:
            tree (Tree | None): The new global history tree data instance.
        """
        self.clear()
        self.node_items.clear()
        self.tree = tree

        if not tree:
            return

        positions = {}
        self._layout(tree, 0, 0, positions)
        self._center(positions)
        self._build(tree, positions)

        rect = self.itemsBoundingRect()

        margin = max(rect.width(), rect.height()) * 0.1  # marge proportionnelle globale

        self.setSceneRect(rect.adjusted(
            -margin, -margin,
            margin, margin
        ))

    # ---------------- LAYOUT ----------------

    def _layout(self, node: Tree, depth: int, x: float, positions : dict[Tree, tuple[float, float]]) -> float:
        """Recursive bottom-up layout processing that computes intermediate relative nodes spacing metrics."""
        if node.is_leaf:
            positions[node] = (x, depth * self.V_SPACING)
            return x + self.H_SPACING

        child_x = x
        centers = []

        for c in node.children:
            child_x = self._layout(c, depth + 1, child_x, positions)
            centers.append(positions[c][0])

        center_x = (min(centers) + max(centers)) / 2
        positions[node] = (center_x, depth * self.V_SPACING)

        return child_x

    def _center(self, positions) -> None:
        """Applies a global vertical offset modifier to ensure the graph configuration is perfectly centered around the origin."""
        ys = [y for _, y in positions.values()]
        offset_y = - (min(ys) + max(ys)) / 2

        for k in positions:
            x, y = positions[k]
            positions[k] = (x, y + offset_y)

    # ---------------- BUILD GRAPH ----------------

    def _build(self, node : Tree, positions : dict[Tree, tuple[float, float]]) -> None:
        """Instantiates and registers the graphical items and their visual edge curves inside the scene hierarchy."""
        x, y = positions[node]

        item = TreeNodeItem(node)
        self.addItem(item)
        item.setPos(x, y)

        self.node_items[node] = item

        for c in node.children:
            self._build(c, positions)

            edge = EdgeItem(self.node_items[node], self.node_items[c])
            self.addItem(edge)
            self.edges.append(edge)

    def update_edges(self) -> None:
        """Forces all instantiated edge linking components to refresh their path curves geometry."""
        for e in self.edges:
            e.update_position()

    def _draw_edge(self, parent: Tree, child: Tree) -> None:
        """Draws a straight line fallback edge between a parent and a child node.

        Args:
            parent (Tree): The parent history node.
            child (Tree): The child history node.
        """
        pen = QPen(QColor("#808080"))
        pen.setWidth(2)

        p1 = self.node_items[parent].center()
        p2 = self.node_items[child].center()

        self.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)

    def mousePressEvent(self, event) -> None:
        """Catches empty background click inputs to request side panel retraction workflows."""
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return

        item = self.itemAt(event.scenePos(), self.views()[0].transform())

        if item is None:
            self.node_clicked.emit(None)

        event.ignore()

# -------------------- VIEW --------------------

class HistoryTreeView(QWidget):
    """Main view housing the interactive graph projection container alongside a smooth animated sliding overview sidebar."""
    
    def __init__(self):
        super().__init__()

        self._setup_ui()

        self._connect_signals()

        self._apply_stylesheets()

    def _connect_signals(self) -> None:
        """Binds intra-widget UI interactions and external models signals."""
        self.tree_scene.node_clicked.connect(self.on_node_clicked)

        self.preview.close_clicked.connect(self.on_node_closed)

    # ---------------- UI ----------------

    def _setup_ui(self) -> None:
        """Configures structural geometry layout alignments, scrolling behaviors, and animation constraints."""
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

        # ---------- GRAPH VIEW ----------

        self.graphics_view = QGraphicsView()
        self.graphics_view.setViewportMargins(0, 0, 0, 0)
        self.graphics_view.setFrameShape(QFrame.Shape.NoFrame)
        self.graphics_view.setStyleSheet("border: none;")
        self.graphics_view.setDragMode(
            QGraphicsView.DragMode.ScrollHandDrag
        )

        self.graphics_view.setInteractive(True)

        self.graphics_view.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        self.tree_scene = HistoryTreeScene()

        self.graphics_view.setScene(self.tree_scene)

        self.graphics_view.fitInView(
            self.tree_scene.sceneRect(),
            Qt.AspectRatioMode.KeepAspectRatio
        )

        layout.addWidget(self.graphics_view)

        # ---------- OVERLAY PANEL ----------

        self.preview = HistoryPreview(self)

        self.preview.setFixedWidth(350)

        ## ANIMATION

        self.preview_animation = QPropertyAnimation(
            self.preview,
            b"geometry"
        )

        self.preview_animation.setDuration(250)

        self.preview_animation.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )

        self.preview.raise_()

        self.preview.hide()

    # ---------------- RESIZE ----------------

    def resizeEvent(self, event) -> None:
        """Keeps the side-panel geometry properly attached to the right bounds during window scaling actions."""
        super().resizeEvent(event)

        margin = 0

        self.preview.setGeometry(
            self.width() - self.preview.width() - margin,
            margin,
            self.preview.width(),
            self.height() - margin * 2
        )

    # ---------------- TREE ----------------

    def set_tree(self, tree : Optional[Tree]) -> None:
        """Forwards the structural tree payload down to the visual scene layout processor."""
        self.tree_scene.set_tree(tree)

    # ---------------- PREVIEW ----------------

    def on_node_clicked(self, node : Optional[Tree]) -> None:
        """Triggered when a scene item or background selection update is intercepted.

        Args:
            node (Tree | None): The clicked history context entity.
        """
        if node is None:
            self.hide_preview()
            return

        self.show_preview()
        history.set_current_search(node)

    def on_node_closed(self) -> None:
        """Callback connected to the closure request signal emitted from the sliding sidebar panel."""
        self.hide_preview()

    def show_preview(self) -> None:
        """Computes current margins geometries and starts the sliding-in sidebar panel transition."""
        final_rect = QRect(
            self.width() - self.preview.width() - self.graphics_view.verticalScrollBar().sizeHint().width(),
            - self.graphics_view.horizontalScrollBar().sizeHint().height(),
            self.preview.width(),
            self.height()
        )

        start_rect = QRect(
            self.width(),
            - self.graphics_view.horizontalScrollBar().sizeHint().height(),
            self.preview.width(),
            self.height()
        )

        self.preview.show()

        self.preview_animation.stop()

        self.preview_animation.setStartValue(start_rect)
        self.preview_animation.setEndValue(final_rect)

        self.preview_animation.start()

    def hide_preview(self) -> None:
        """Starts the sliding-out sidebar retraction animation towards the right viewport boundaries."""

        self.graphics_view.setViewportMargins(0, 0, 0, 0)
        
        start_rect = self.preview.geometry()

        end_rect = QRect(
            self.width(),
            0,
            self.preview.width(),
            self.height(),
        )

        self.preview_animation.stop()

        self.preview_animation.setStartValue(start_rect)
        self.preview_animation.setEndValue(end_rect)

        self.preview_animation.start()

    def _on_theme_changed(self) -> None:
        """Propagates global runtime look-and-feel stylesheet changes down to all individual scene nodes."""
        self.preview._on_theme_changed()
        self._apply_stylesheets()
        
        if history.current_search is not None:
            for node, item in self.tree_scene.node_items.items():
                if node == history.current_search:
                    item.set_selected()
                else:
                    item.set_unselected()

    def _apply_stylesheets(self) -> None:
        """Injects updated variable evaluations compiled from the active material look-and-feel configuration."""
        self.graphics_view.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {os.environ["QTMATERIAL_SECONDARYLIGHTCOLOR"]};
                border: none;
            }}
        """)
        
    def _on_language_changed(self) -> None:
        """Forwards runtime internationalization locale translations reload flags to sub-components layers."""
        self.preview._on_language_changed()