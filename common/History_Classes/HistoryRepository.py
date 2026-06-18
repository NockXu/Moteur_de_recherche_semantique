from __future__ import annotations

from PyQt6.QtWidgets import QWidget
from .Tree import Tree
from .HistoryData import HistoryData
from ui import save_in_config, load_from_config
from pathlib import Path
from typing import Optional
import json
import os

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal


class HistoryRepository(QWidget):
    """Repository responsible for managing the search history tree and its configuration.

    This class provides an abstraction layer to load, save, and track the persistent 
    state of searches using a custom tree structure. It integrates with PyQt6 signals 
    to trigger saving operations when changes occur.

    Signals:
        history_changed: Emitted when the history requires saving.
        current_search_updated: Emitted when the active search node changes.
    """

    history_changed = pyqtSignal()
    current_search_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.history_path = None
        self.history_tree = None
        self.current_search : Tree | None = None

        self.history_changed.connect(self.save)

    def set_current_search(self, node: Tree) -> None:
        """Set the currently active search tree node and notify listeners.

        Args:
            node (Tree):
                The tree node representing the current search.

        """
        self.current_search = node
        self.current_search_updated.emit()

    def load_history(self) -> None:
        """Load the history tree from a local JSON file.

        If the history file directory or file does not exist, or if the file 
        is corrupted/empty, a default tree structure is created and initialized.
        """
        if self.history_path is None:
            return

        history_dir = Path(self.history_path)
        history_dir.mkdir(parents=True, exist_ok=True)

        history_file = history_dir / "history_tree.json"

        # Création automatique du fichier
        if not history_file.exists():
            self.history_tree = Tree(HistoryData("DEFAULT"))
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(self.history_tree.to_dict(), f, ensure_ascii=False, indent=4)
            return

        with open(history_file, encoding="utf-8") as f:
            data = json.load(f)

        # Fichier vide ou JSON invalide
        if not data:
            self.history_tree = Tree(HistoryData("DEFAULT"))
            return

        self.history_tree = Tree.from_dict(data)


    def save_history(self) -> bool:
        """Serialize and save the current history tree structure to a JSON file.

        Returns:
            True if the history was successfully saved, False if history_path is not set.

        """
        if self.history_path is None:
            return False

        history_dir = Path(self.history_path)
        history_dir.mkdir(parents=True, exist_ok=True)

        history_file = history_dir / "history_tree.json"

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(
                self.history_tree.to_dict(),
                f,
                ensure_ascii=False,
                indent=4
            )

        return True

    def load(self) -> None:
        """Load global configurations, trigger history loading, and restore the active search state.

        This method reads the history path and last known search node parameters 
        from the application configuration, then looks up the correct tree node 
        based on generation and index indices.
        """
        self.history_path = load_from_config("history_path")

        self.load_history()

        current_search = load_from_config("current_search")

        if self.history_tree is None:
            self.history_tree = Tree(HistoryData("DEFAULT"))

        if not current_search:
            return

        current_search_data = HistoryData.from_dict(current_search)

        if current_search_data.is_empty:
            return

        generation = current_search.get("generation", 0)
        index = current_search.get("index", 0)

        potential_trees = self.history_tree.get_all_tree_from_generation(generation)

        if index < 0 or index >= len(potential_trees):
            return

        self.current_search = potential_trees[index]

    def save(self) -> bool:
        """Save the current state of the history path and current search data into the application configuration.

        This method calculates the context indices (generation and sibling index) 
        of the current search node and stores them before saving the tree data.

        Returns:
            True if the structural history file was successfully updated, False otherwise.

        """
        if self.current_search is None:
            self.current_search = self.history_tree

        save_in_config("history_path", self.history_path)

        save_in_config("current_search", {
            "query": self.current_search.node.query,
            "threashold": self.current_search.node.threshold,
            "generation": self.current_search.get_number_generation(),
            "index": (
                self.current_search.parent.children.index(self.current_search)
                if self.current_search.parent else 0
            )
        })

        return self.save_history()