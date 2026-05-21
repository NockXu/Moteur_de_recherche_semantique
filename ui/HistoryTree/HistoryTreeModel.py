from common.History_Classes import Tree, history

class HistoryTreeModel:
    @property
    def tree(self):
        return history.history_tree

    def save(self):
        history.save()