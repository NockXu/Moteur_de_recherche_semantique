from PyQt6.QtCore import pyqtSignal
from .HistoryTreeModel import HistoryTreeModel
from .HistoryTreeView import HistoryTreeView
from common.History_Classes import Tree
from ui import load_from_config
from common.History_Classes import history

from PyQt6.QtWidgets import QApplication


class HistoryTreeController:
    """Controller orchestrating the history tree logic by bridging HistoryTreeModel and HistoryTreeView.

    Args:
        theme_changed (pyqtSignal): Global signal emitted when the application theme changes.
    """
    def __init__(self, theme_changed : pyqtSignal) -> None:
        self.model = HistoryTreeModel()
        self.view = HistoryTreeView()

        self.theme_changed = theme_changed

        self._connect_signal()

    def _connect_signal(self) -> None:
        """Establishes signal-slot connections between the view, model, and global history events."""
        self.theme_changed.connect(self.view._on_theme_changed)
        self.view.preview.action_done.connect(self._on_action_done)
        history.current_search_updated.connect(self.update_view)
        history.history_changed.connect(self.update_view)

    def _on_action_done(self) -> None:
        """Handles post-action verification by flushing the model state to storage and refreshing the UI."""
        self.model.save()
        self.update_view()

    def _on_close_clicked(self) -> None:
        """Slots connected to the view closing request."""
        self.view.close()

    def update_view(self) -> None:
        """Synchronizes the tree visual structure and updates nodes selection/preview states."""
        self.view.set_tree(self.model.tree)
        if history.current_search is not None:
            self.view.preview.set_node(history.current_search)

            for node, item in self.view.tree_scene.node_items.items():
                if node == history.current_search:
                    item.set_selected()
                else:
                    item.set_unselected()
            

    def load(self) -> None:
        """Initializes data state loading procedures and triggers the first view rendering cycle."""
        self.update_view()
        
