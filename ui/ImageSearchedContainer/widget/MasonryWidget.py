from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize


class MasonryLayout(QWidget):
    """
    Layout masonry (Pinterest) : colonnes de largeur fixe,
    hauteur de chaque carte dictée par le ratio réel de l'image.

    Les widgets enfants sont positionnés manuellement via resizeEvent
    pour éviter les contraintes des QLayout standards.
    """

    image_clicked = pyqtSignal(str)

    # Largeur cible d'une colonne (px). Ajuster selon le design.
    COLUMN_WIDTH = 210
    GAP = 14  # espacement horizontal et vertical

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[QWidget] = []

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def set_cards(self, cards: list[QWidget]):
        """Remplace toutes les cartes actuelles par une nouvelle liste."""
        # Supprimer les anciennes
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards = cards

        for card in self._cards:
            card.setParent(self)
            card.show()

        self._relayout()

    def clear(self):
        self.set_cards([])

    # ------------------------------------------------------------------
    # Positionnement
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self):
        """Calcule la position de chaque carte selon l'algorithme masonry."""
        if not self._cards:
            self.setMinimumHeight(0)
            return

        available_width = self.width()
        col_count = max(1, (available_width + self.GAP) // (self.COLUMN_WIDTH + self.GAP))
        col_width = (available_width - (col_count - 1) * self.GAP) // col_count

        # Hauteur courante de chaque colonne
        col_heights = [self.GAP] * col_count

        for card in self._cards:
            # La carte doit se redimensionner à col_width pour calculer sa hauteur
            card.setFixedWidth(col_width)
            card.adjustSize()
            card_height = card.sizeHint().height()

            # Choisir la colonne la moins haute
            min_col = col_heights.index(min(col_heights))
            x = min_col * (col_width + self.GAP)
            y = col_heights[min_col]

            card.setGeometry(QRect(x, y, col_width, card_height))
            col_heights[min_col] += card_height + self.GAP

        total_height = max(col_heights) + self.GAP
        self.setMinimumHeight(total_height)