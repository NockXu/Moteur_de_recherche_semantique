from __future__ import annotations
from typing import List, Dict, Optional

from common.History_Classes.HistoryData import HistoryData

class Tree:
    """A generic tree structure tailored for tracking search history steps.

    This class provides tree-traversal and tree-manipulation methods to handle
    hierarchical search branches (parent-child-sibling relationships), serialization,
    and generation tracking.

    Args:
        node (HistoryData):
            The value or data encapsulation held by this specific tree node.
        parent (Optional[Tree]):
            The parent tree node. Defaults to None.
        children (Optional[list[Tree]]):
            The list of immediate child nodes. Defaults to None (empty list).

    """

    def __init__(
        self,
        node : HistoryData,
        parent: Tree | None = None,
        children: list[Tree] | None = None
    ):
        self.parent = parent
        self.children = children if children is not None else []
        self.node = node

    def add_child(self, child: Tree) -> None:
        """Add a child node to the current tree structure.

        If the child is identical to the current node, it updates its threshold
        instead of appending it as a child.

        Args:
            child (Tree):
                The child node to append or update.

        """
        if child != self:
            if child not in self.children:
                self.children.append(child)
                child.parent = self
                return
        
        self.node.threshold = child.node.threshold

    def add_brother(self, brother: Tree) -> None:
        """Add a sibling node to the current node's parent structure.

        Args:
            brother (Tree):
                The sibling node to be appended.

        """
        if self.parent is not None:
            self.parent.add_child(brother)

    def add_children(self, children: list[Tree]) -> None:
        """Add multiple child nodes to the current tree node.

        Args:
            children (list[Tree]):
                A list of tree nodes to add as children.

        """
        for child in children:
            self.add_child(child)

    def get_root(self) -> Tree:
        """Traverse upwards to retrieve the absolute root node of the tree.

        Returns:
            The root Tree instance.

        """
        if self.is_root:
            return self

        return self.parent.get_root()

    def get_all(self) -> dict:
        """Retrieve a nested dictionary structure starting from the root node.

        Returns:
            A dictionary containing the absolute root node and all its descendants.

        """
        return self.get_root().get_all_from_this_point()

    def get_all_from_this_point(self) -> dict:
        """Retrieve a nested dictionary structure starting from the current node downwards.

        Returns:
            A dictionary representation of the current node and its children.

        """
        return {
            "node": self,
            "children": [
                child.get_all_from_this_point()
                for child in self.children
            ]
        }

    def get_all_ancestors(self) -> list[Tree]:
        """Retrieve a list of all ancestor nodes leading down to the current node.

        Returns:
            A list of Tree nodes starting from the root up to the current node.

        """
        if self.parent is not None:
            return self.parent.get_all_ancestors() + [self]
        return [self]

    def get_from_here(self, n: int) -> Tree:
        """Traverse upwards by n generations.

        Args:
            n (int):
                The number of generations to traverse upwards.

        Returns:
            The ancestor node at the specified level, or the root if n exceeds depth.

        """
        if n == 0:
            return self
        elif self.parent is None:
            return self
        else:
            return self.parent.get_from_here(n - 1)

    def disconect(self) -> None:
        """Disconnect the current node from its parent, turning it into a new root.
        """
        if self.parent:
            self.parent.children.remove(self)
            self.parent = None

    def get_number_generation(self) -> int:
        """Calculate the generation depth index of the current node.

        Returns:
            The generation index integer (0 for root).

        """
        if self.is_root:
            return 0
        return self.parent.get_number_generation() + 1

    def get_all_tree_from_generation(self, n: int) -> list[Tree]:
        """Retrieve all tree nodes located at a specific relative generation depth down the tree.

        Args:
            n (int):
                The target relative depth layer (0 represents the current node level).

        Returns:
            A list of Tree nodes present at the given generation layer.

        """
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
        """Check if the current node has no parent.

        Returns:
            True if it is a root node, False otherwise.

        """
        return self.parent is None

    @property
    def is_leaf(self) -> bool:
        """Check if the current node has no children.

        Returns:
            True if it is a leaf node, False otherwise.

        """
        return len(self.children) == 0

    def to_dict(self) -> dict:
        """Serialize the tree and all its descendants into a dictionary.

        Returns:
            A dictionary containing serialized data of the current node and its children.

        """
        return {
            "node": self.node.to_dict(),
            "children": [
                child.to_dict()
                for child in self.children
            ]
        }

    @classmethod
    def from_dict(cls, data : dict, parent : Tree = None) -> Tree:
        """Create a Tree instance and rebuild all its children recursively from a dictionary structure.

        Args:
            data (dict):
                The serialized tree dictionary data.
            parent (Optional[Tree]):
                The parent node to link. Defaults to None.

        Returns:
            A fully reconstituted Tree instance.

        """
        node = HistoryData.from_dict(data.get("node", {}))
        tree = cls(node=node, children=None, parent=parent)
        tree.children = [cls.from_dict(child, parent=tree) for child in data.get("children", [])]
        return tree

    def __eq__(self, other: object) -> bool:
        """Compare two Tree nodes for equality based on their underlying data nodes.

        Returns:
            True if the other object is a Tree and shares equal node data, False otherwise.

        """
        if isinstance(other, Tree):
            return other.node == self.node
        return False

    def __str__(self) -> str:
        """Get a string representation of the tree node.

        Returns:
            A string containing the node data string representation.

        """
        return f"""node: {self.node}"""

    def __hash__(self) -> int:
        """Generate a unique hash for the tree instance based on its memory identity.

        Returns:
            An integer hash value.

        """
        return id(self)

if __name__ == "__main__":
    data1 = HistoryData("Un chat", 0.5)
    data2 = HistoryData.from_dict({"query": "Un chat", "threasold" : 0.5})
    tree1 = Tree(data1)
    tree2 = Tree(data2)

    print(tree1 == tree2)