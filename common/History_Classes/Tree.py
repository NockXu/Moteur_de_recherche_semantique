from __future__ import annotations
from typing import List, Dict, Optional

from common.History_Classes.HistoryData import HistoryData

class Tree:

    def __init__(
        self,
        node : HistoryData,
        parent: Optional[Tree] = None,
        children: Optional[list[Tree]] = None
    ):
        self.parent = parent
        self.children = children if children is not None else []
        self.node = node

    def add_child(self, child: Tree):
        if child != self:
            if child not in self.children:
                self.children.append(child)
                child.parent = self
                return
        
        self.node.threshold = child.node.threshold

    def add_brother(self, brother: Tree):
        if self.parent is not None:
            self.parent.add_child(brother)

    def add_children(self, children: list[Tree]):
        for child in children:
            self.add_child(child)

    def get_root(self) -> Tree:
        if self.is_root:
            return self

        return self.parent.get_root()

    def get_all(self) -> dict:
        return self.get_root().get_all_from_this_point()

    def get_all_from_this_point(self) -> dict:
        return {
            "node": self,
            "children": [
                child.get_all_from_this_point()
                for child in self.children
            ]
        }

    def get_all_ancestors(self) -> list[Tree]:
        if self.parent is not None:
            return self.parent.get_all_ancestors() + [self]
        return [self]

    def get_from_here(self, n: int) -> Tree:
        if n == 0:
            return self
        elif self.parent is None:
            return self
        else:
            return self.parent.get_from_here(n - 1)

    def disconect(self) -> None:
        if self.parent:
            self.parent.children.remove(self)
            self.parent = None

    def get_number_generation(self) -> int:
        if self.is_root:
            return 0
        return self.parent.get_number_generation() + 1

    def get_all_tree_from_generation(self, n: int) -> list[Tree]:
        if n == 0:
            return [self]

        elif self.is_leaf:
            return []
        
        else:
            result = []
            for child in self.children:
                result.extend(child.get_all_tree_from_generation(n - 1))

            return result

    @property
    def is_root(self) -> bool:
        return self.parent is None

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def to_dict(self) -> dict:
        return {
            "node": self.node.to_dict(),
            "children": [
                child.to_dict()
                for child in self.children
            ]
        }

    @classmethod
    def from_dict(cls, data : dict, parent : Tree = None) -> Tree:
        node = HistoryData.from_dict(data.get("node", {}))
        tree = cls(node=node, children=None, parent=parent)
        tree.children = [cls.from_dict(child, parent=tree) for child in data.get("children", [])]
        return tree

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Tree):
            return other.node == self.node
        return False

    def __str__(self) -> str:
        return f"""node: {self.node}"""

    def __hash__(self):
        return id(self)

if __name__ == "__main__":
    data1 = HistoryData("Un chat", 0.5)
    data2 = HistoryData.from_dict({"query": "Un chat", "threasold" : 0.5})
    tree1 = Tree(data1)
    tree2 = Tree(data2)

    print(tree1 == tree2)