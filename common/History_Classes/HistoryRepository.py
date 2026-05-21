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
    history_changed = pyqtSignal()
    current_search_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.history_path = None
        self.history_tree = None
        self.current_search : Optional[Tree] = None

        self.history_changed.connect(self.save)

    def set_current_search(self, node: Tree) -> None:
        self.current_search = node
        self.current_search_updated.emit()

    def load_history(self) -> None:
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

        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Fichier vide ou JSON invalide
        if not data:
            self.history_tree = Tree(HistoryData("DEFAULT"))
            return

        self.history_tree = Tree.from_dict(data)


    def save_history(self) -> bool:
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