from ui.widgets.ImageThumbnailWidget import ImageThumbnailWidget as BaseImageThumbnailWidget

class ImageThumbnailWidget(BaseImageThumbnailWidget):
    """Miniature d'image avec titre, hauteur dynamique (style Pinterest)."""

    def __init__(self, image_path: str, title: str = "", col_width: int = 200):
        # Utiliser le widget unifié avec mode Pinterest (pas de badge)
        super().__init__(
            image_path=image_path,
            title=title,
            status=None,  # Pas de statut pour les résultats de recherche
            col_width=col_width,
            show_status_badge=False,  # Mode Pinterest
        )