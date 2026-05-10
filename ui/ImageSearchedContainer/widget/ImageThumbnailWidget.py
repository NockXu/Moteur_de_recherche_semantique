from ui.widgets.ImageThumbnailWidget import ImageThumbnailWidget as BaseImageThumbnailWidget
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, pyqtSignal


class ImageThumbnailWidget(BaseImageThumbnailWidget):
    """
    Miniature d'image avec titre, hauteur dynamique (style Pinterest).
    Avec support lazy loading
    """
    
    # Signal émis quand l'image est chargée et la taille change
    image_loaded = pyqtSignal()

    def __init__(
        self, 
        image_path: str, 
        title: str = "", 
        col_width: int = 200,
        lazy: bool = False  # NOUVEAU paramètre
    ):
        # État lazy loading AVANT super().__init__
        self._lazy_mode = lazy
        self._is_loaded = not lazy  # Si pas lazy, considérer comme chargé
        self._original_image_path = image_path
        
        # Si lazy, passer un placeholder temporaire au parent
        if lazy:
            placeholder_path = self._create_placeholder()
            super().__init__(
                image_path=placeholder_path,
                title=title,
                status=None,
                col_width=col_width,
                show_status_badge=False,
            )
        else:
            # Mode normal : chargement immédiat
            super().__init__(
                image_path=image_path,
                title=title,
                status=None,
                col_width=col_width,
                show_status_badge=False,
            )
    
    def _create_placeholder(self) -> str:
        """
        Crée un placeholder gris et retourne son chemin
        (ou None si le widget parent gère déjà les pixmaps vides)
        """
        # Si BaseImageThumbnailWidget gère bien les chemins invalides,
        # on peut juste retourner un chemin vide
        return ""
    
    def load_image(self):
        """
        ✅ Méthode appelée par le lazy loader pour charger l'image réelle
        """
        if self._is_loaded or not self._lazy_mode:
            return
        
        try:
            # Charger l'image depuis le chemin original
            pixmap = QPixmap(self._original_image_path)
            
            if not pixmap.isNull():
                # Redimensionner pour optimisation RAM
                scaled = pixmap.scaled(
                    self.col_width * 2,  # 2x pour retina
                    4000,  # Hauteur max
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Mettre à jour le pixmap dans le widget parent
                # (selon l'implémentation de BaseImageThumbnailWidget)
                if hasattr(self, 'image_label'):
                    self.image_label.setPixmap(scaled)
                elif hasattr(self, 'set_image'):
                    self.set_image(scaled)
                
                self._is_loaded = True
                
                # Notifier que l'image a changé de taille
                self.image_loaded.emit()
                
        except Exception as e:
            print(f"[LAZY] Failed to load {self._original_image_path}: {e}")
            self._show_error()
    
    def _show_error(self):
        """Affiche un indicateur d'erreur"""
        if hasattr(self, 'image_label'):
            error_pixmap = QPixmap(200, 200)
            error_pixmap.fill(QColor(255, 200, 200))
            
            painter = QPainter(error_pixmap)
            painter.setPen(QColor(200, 0, 0))
            painter.drawText(
                error_pixmap.rect(), 
                Qt.AlignmentFlag.AlignCenter, 
                "❌ Erreur"
            )
            painter.end()
            
            self.image_label.setPixmap(error_pixmap)
    
    def unload_image(self):
        """
        ✅ Décharge l'image pour libérer RAM (optionnel)
        Utile pour très grandes collections
        """
        if self._is_loaded and self._lazy_mode:
            # Remettre le placeholder
            placeholder_pixmap = QPixmap(self.col_width, self.col_width)
            placeholder_pixmap.fill(QColor(240, 240, 240))
            
            if hasattr(self, 'image_label'):
                self.image_label.setPixmap(placeholder_pixmap)
            
            self._is_loaded = False
    
    @property
    def is_loaded(self):
        """Pour que le lazy loader puisse vérifier l'état"""
        return self._is_loaded