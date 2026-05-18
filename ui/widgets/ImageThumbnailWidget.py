import sys
import os
import hashlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import (
    Qt, QSize, pyqtSignal, QRect, QRunnable, QThreadPool,
    QObject, pyqtSlot, QMetaObject, Q_ARG,
)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QBrush, QPainterPath, QMouseEvent
from pathlib import Path
from common.Image_Classes.Image import Image, ProcessingStatus


# ─────────────────────────────────────────────────────────────────────────────
# Cache disque de thumbnails
# ─────────────────────────────────────────────────────────────────────────────

_CACHE_DIR = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")) / "img_search_thumbs"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(image_path: Path, size: int) -> Path:
    key = f"{image_path}:{size}:{image_path.stat().st_mtime_ns}"
    h   = hashlib.md5(key.encode()).hexdigest()
    return _CACHE_DIR / f"{h}.jpg"


# ─────────────────────────────────────────────────────────────────────────────
# Palette des statuts
# ─────────────────────────────────────────────────────────────────────────────

STATUS_OVERLAY: dict[ProcessingStatus, QColor] = {
    ProcessingStatus.NOT_STARTED: QColor(0,   0,   0,   0),
    ProcessingStatus.IN_PROGRESS: QColor(255, 193,  7, 160),
    ProcessingStatus.COMPLETED:   QColor( 40, 167, 69, 140),
    ProcessingStatus.ERROR:       QColor(220,  53, 69, 160),
}

STATUS_BORDER: dict[ProcessingStatus, QColor] = {
    ProcessingStatus.NOT_STARTED: QColor(210, 214, 220),
    ProcessingStatus.IN_PROGRESS: QColor(255, 193,   7),
    ProcessingStatus.COMPLETED:   QColor( 40, 167,  69),
    ProcessingStatus.ERROR:       QColor(220,  53,  69),
}

STATUS_ICON: dict[ProcessingStatus, str] = {
    ProcessingStatus.NOT_STARTED: "",
    ProcessingStatus.IN_PROGRESS: "./ui/icon/hourglass.svg",
    ProcessingStatus.COMPLETED:   "./ui/icon/check.svg",
    ProcessingStatus.ERROR:       "./ui/icon/error.svg",
}


# ─────────────────────────────────────────────────────────────────────────────
# Pixmap composite (image + overlay + icône)
# ─────────────────────────────────────────────────────────────────────────────

def _build_import_pixmap(source: QPixmap, max_width: int, status: ProcessingStatus) -> QPixmap:
    """
    Construit un pixmap avec overlay de statut, en préservant les proportions de l'image.
    
    Args:
        source: L'image source à afficher
        max_width: Largeur maximale de la carte
        status: Statut de traitement pour l'overlay
    
    Returns:
        Un QPixmap aux dimensions de l'image scalée (pas forcément carré)
    """
    # Scaler l'image en gardant les proportions
    scaled = source.scaled(QSize(max_width, max_width),
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
    
    # Créer un pixmap aux dimensions exactes de l'image scalée
    result = QPixmap(scaled.width(), scaled.height())
    result.fill(Qt.GlobalColor.transparent)

    p = QPainter(result)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    # Dessiner l'image (pas de centrage nécessaire, taille exacte)
    p.drawPixmap(0, 0, scaled)

    overlay_color = STATUS_OVERLAY.get(status, QColor(0, 0, 0, 0))
    if overlay_color.alpha() > 0:
        clip = QPainterPath()
        clip.addRect(0, 0, scaled.width(), scaled.height())
        p.setClipPath(clip)
        p.fillPath(clip, QBrush(overlay_color))
        p.setClipping(False)

        icon_path = STATUS_ICON.get(status, "")
        icon_color = STATUS_BORDER.get(status, QColor(150, 150, 150))

        if icon_path:
            icon = QPixmap(icon_path)

            if not icon.isNull():
                icon_size = 28

                icon = icon.scaled(
                    icon_size,
                    icon_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                # ───── recolorisation ─────
                colored_icon = QPixmap(icon.size())
                colored_icon.fill(Qt.GlobalColor.transparent)

                painter_icon = QPainter(colored_icon)
                painter_icon.setRenderHint(QPainter.RenderHint.Antialiasing)

                painter_icon.drawPixmap(0, 0, icon)

                painter_icon.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter_icon.fillRect(colored_icon.rect(), icon_color)

                painter_icon.end()

                # ───── position ─────
                cx = scaled.width() // 2
                cy = scaled.height() // 2

                r = icon_size // 2 + 6

                p.setBrush(QBrush(QColor(255, 255, 255, 230)))
                p.setPen(QPen(icon_color, 2))
                p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

                p.drawPixmap(
                    cx - icon_size // 2,
                    cy - icon_size // 2,
                    colored_icon
                )
    p.end()
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Chargement asynchrone — worker annulable
# ─────────────────────────────────────────────────────────────────────────────

class _ThumbnailLoader(QRunnable):
    """
    Worker de décodage image.

    Correction fenêtres fantômes :
    - Le worker garde une référence faible vers le widget cible via son id().
    - Avant d'émettre quoi que ce soit, il vérifie `_cancelled`.
    - Le widget positionne `_cancelled = True` dans sa méthode cancel(),
      appelée AVANT setParent(None) / deleteLater().
    - Le résultat est livré via QMetaObject.invokeMethod (thread-safe, pas de
      connexion persistante qui pourrait déclencher après destruction).
    """

    def __init__(self, image_path: Path, size: int, target: "ImageThumbnailWidget"):
        super().__init__()
        self.setAutoDelete(True)
        self.image_path = image_path
        self.size       = size
        self._target    = target   # référence directe — on ne va jamais la déréférencer
                                   # dans le thread (lecture seule de _cancelled)
        self._cancelled = False    # alias vers target._loader_cancelled

    def cancel(self):
        self._cancelled = True

    @pyqtSlot()
    def run(self):
        if self._cancelled:
            return
        try:
            cp = _cache_path(self.image_path, self.size)

            if cp.exists():
                px = QPixmap(str(cp))
                if not px.isNull() and not self._cancelled:
                    self._deliver(px)
                    return

            if self._cancelled:
                return

            px = QPixmap(str(self.image_path))
            if px.isNull():
                if not self._cancelled:
                    self._deliver_error()
                return

            if self._cancelled:
                return

            thumb = px.scaled(QSize(self.size, self.size),
                               Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
            thumb.save(str(cp), "JPEG", 85)

            if not self._cancelled:
                self._deliver(thumb)

        except Exception:
            if not self._cancelled:
                self._deliver_error()

    def _deliver(self, px: QPixmap):
        """Invocation thread-safe vers le slot du widget (Qt::QueuedConnection implicite)."""
        if self._cancelled:
            return
        QMetaObject.invokeMethod(
            self._target,
            "_on_pixmap_loaded",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(QPixmap, px),
        )

    def _deliver_error(self):
        if self._cancelled:
            return
        QMetaObject.invokeMethod(
            self._target,
            "_show_error",
            Qt.ConnectionType.QueuedConnection,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Label cliquable
# ─────────────────────────────────────────────────────────────────────────────

class _ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


# ─────────────────────────────────────────────────────────────────────────────
# Widget principal
# ─────────────────────────────────────────────────────────────────────────────

class ImageThumbnailWidget(QWidget):
    """
    Widget thumbnail unifié avec chargement asynchrone.

    show_status_badge=True  → ImportTool (carte carrée fixe, overlay statut)
    show_status_badge=False → Masonry (hauteur dynamique, pas d'overlay)

    Corrections v3 :
    - Le loader est annulé (cancel()) avant que le widget soit détruit →
      plus de fenêtres fantômes.
    - La livraison du pixmap passe par QMetaObject.invokeMethod (pas de
      signal persistant qui pourrait tirer après destruction).
    """

    clicked = pyqtSignal(str)

    _pool = QThreadPool.globalInstance()
    _pool.setMaxThreadCount(max(4, os.cpu_count() or 4))

    def __init__(
        self,
        image_path: str,
        title: str = None,
        status: ProcessingStatus = None,
        col_width: int = 200,
        show_status_badge: bool = True,
        parent=None,
    ):
        super().__init__(parent)

        self.image_path        = Path(image_path)
        self.title             = title or self.image_path.name
        self.status            = status or ProcessingStatus.NOT_STARTED
        self.col_width         = col_width
        self.show_status_badge = show_status_badge
        self._source_pixmap: QPixmap | None = None
        self._loader: _ThumbnailLoader | None = None   # référence pour annulation

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._setup_ui()
        self._apply_card_style()
        self._start_async_load()

    # ─────────────────────────────────────────────────────────────────────────
    # Annulation propre avant destruction
    # ─────────────────────────────────────────────────────────────────────────

    def cancel_load(self):
        """
        À appeler AVANT setParent(None) ou deleteLater().
        Empêche le worker d'invoquer quoi que ce soit sur ce widget.
        """
        if self._loader is not None:
            self._loader.cancel()
            self._loader = None

    def setParent(self, parent):
        """Override : annule le loader dès qu'on détache le widget de son parent."""
        self.cancel_load()
        super().setParent(parent)

    # ─────────────────────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = _ClickableLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.image_label.clicked.connect(lambda: self.clicked.emit(str(self.image_path)))

        # Placeholder transparent immédiat
        placeholder = QPixmap(self.col_width, self.col_width)
        placeholder.fill(Qt.GlobalColor.transparent)
        self.image_label.setPixmap(placeholder)

        # Les deux modes utilisent maintenant une taille dynamique basée sur l'image
        self.image_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout.addWidget(self.image_label)

        if self.title and not self.show_status_badge:
            self.title_label = QLabel(self.title)
            self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.title_label.setWordWrap(True)
            self.title_label.setFont(QFont("Segoe UI", 9))
            self.title_label.setContentsMargins(8, 4, 8, 8)
            layout.addWidget(self.title_label)

    # ─────────────────────────────────────────────────────────────────────────
    # Chargement asynchrone
    # ─────────────────────────────────────────────────────────────────────────

    def _start_async_load(self):
        if not self.image_path.exists():
            self._show_error()
            return
        self._loader = _ThumbnailLoader(self.image_path, self.col_width, self)
        self._pool.start(self._loader)

    @pyqtSlot(QPixmap)
    def _on_pixmap_loaded(self, thumb: QPixmap):
        self._loader = None
        self._source_pixmap = thumb
        self._render_pixmap()

    # ─────────────────────────────────────────────────────────────────────────
    # Rendu
    # ─────────────────────────────────────────────────────────────────────────

    def _render_pixmap(self):
        if self._source_pixmap is None:
            return
        if self.show_status_badge:
            # Utiliser les dimensions proportionnelles de l'image
            px = _build_import_pixmap(self._source_pixmap, self.col_width, self.status)
            self.image_label.setFixedSize(px.width(), px.height())
            self.image_label.setPixmap(px)
        else:
            scaled = self._source_pixmap.scaledToWidth(
                self.col_width, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setFixedSize(scaled.width(), scaled.height())
            self.image_label.setPixmap(scaled)

    @pyqtSlot()
    def _show_error(self):
        self._loader = None
        self.image_label.setText("⚠")
        self.image_label.setStyleSheet("QLabel { background: transparent; border-radius: 4px; }")
        # Garder le placeholder à la largeur demandée, mais adapter la hauteur
        if self.show_status_badge:
            self.image_label.setFixedSize(self.col_width, self.col_width)

    # ─────────────────────────────────────────────────────────────────────────
    # Style
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_card_style(self):
        if not self.show_status_badge:
            self.setStyleSheet("ImageThumbnailWidget { background: transparent; border-radius: 10px; }")
            return
        self.setStyleSheet(f"ImageThumbnailWidget {{ background: transparent; border: none; }}")
        self.image_label.setStyleSheet("QLabel { background: transparent; border-radius: 4px; }")

    # ─────────────────────────────────────────────────────────────────────────
    # API publique
    # ─────────────────────────────────────────────────────────────────────────

    def set_status(self, status: ProcessingStatus):
        self.status = status
        if self.show_status_badge:
            self._render_pixmap()
            self._apply_card_style()

    def get_status(self) -> ProcessingStatus:
        return self.status

    def get_image_path(self) -> str:
        return str(self.image_path)