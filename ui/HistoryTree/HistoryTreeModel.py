from common.History_Classes import Tree, history

class HistoryTreeModel:
    """Data model wrapper acting as an abstraction layer over the global history tree structure."""
    
    @property
    def tree(self) -> Tree:
        """Retrieves the global history tree instance.

        Returns:
            Tree:
        """
        return history.history_tree

    def save(self) -> None:
        """Persists the current history state into persistent storage."""
        history.save()
        
    def load(self) -> None:
        """Loads the history tree state from persistent storage."""
        history.load()