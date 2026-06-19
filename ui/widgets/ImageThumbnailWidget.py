import sys
import os
import hashlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import (
    Qt, QSize, pyqtSignal, QRect, QRunnable, QThreadPool,
    QObject, pyqtSlot, QMetaObject, Q_ARG,
)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QBrush, QPainterPath, QMouseEvent, QImageReader
from pathlib import Path
from common.Image_Classes.Image import Image, ProcessingStatus
from ui.utils.result_painter import draw_results


# ─────────────────────────────────────────────────────────────────────────────
# Cache disque de thumbnails
# ─────────────────────────────────────────────────────────────────────────────

_CACHE_DIR = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")) / "img_search_thumbs"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(image_path: Path, size: int) -> Path:
    """Generate a unique deterministic hashed JPEG file path for storage caching.

    Args:
        image_path (Path):
            The local system disk location pointing to the original media file.
        size (int):
            Target width dimension metric constraint.

    Returns:
        Path: The absolute cache directory location mapping the output asset.

    """
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
# Chargement asynchrone — worker annulable (inchangé)
# ─────────────────────────────────────────────────────────────────────────────

class _ThumbnailLoader(QRunnable):
    """Runnable worker task loading image files from disk inside a separate background thread.

    Supports on-demand cancellation protocols to safely ignore outdated streaming requests.

    Args:
        image_path (Path):
            The local file location directory tracking the resource asset.
        size (int):
            Standardized bounding dimensions requested for execution.
        target (ImageThumbnailWidget):
            The destination UI widget object receiving completed pixel streams.

    """
    
    def __init__(self, image_path: Path, size: int, target: "ImageThumbnailWidget"):
        super().__init__()
        self.setAutoDelete(True)
        self.image_path = image_path
        self.size       = size
        self._target    = target
        self._cancelled = False

    def cancel(self):
        """Raise internal execution flags to cleanly ignore final signal delivery calls."""
        self._cancelled = True

    @pyqtSlot()
    def run(self):
        """Execute the asynchronous background file reading and thumbnail caching sequence."""
        if self._cancelled:
            return
        try:
            px = QPixmap(str(self.image_path))
            if px.isNull():
                if not self._cancelled:
                    self._deliver_error()
                return

            if self._cancelled:
                return

            cp = _cache_path(self.image_path, self.size)
            if not cp.exists():
                thumb = px.scaled(QSize(self.size, self.size),
                                  Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
                thumb.save(str(cp), "JPEG", 85)

            if not self._cancelled:
                self._deliver(px)

        except Exception:
            if not self._cancelled:
                self._deliver_error()

    def _deliver(self, px: QPixmap):
        """Safely invoke completion callback signals on the target GUI thread instance.

        Args:
            px (QPixmap):
                The valid image pixel matrices loaded from disk.

        """
        if self._cancelled:
            return
        QMetaObject.invokeMethod(
            self._target,
            "_on_pixmap_loaded",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(QPixmap, px),
        )

    def _deliver_error(self):
        """Safely invoke exceptional fallback handlers on the target GUI thread instance."""
        if self._cancelled:
            return
        QMetaObject.invokeMethod(
            self._target,
            "_show_error",
            Qt.ConnectionType.QueuedConnection,
        )

# ─────────────────────────────────────────────────────────────────────────────
# Label cliquable — Dessine l'image ET le badge dynamiquement
# ─────────────────────────────────────────────────────────────────────────────

class _ClickableLabel(QLabel):
    """Custom interactive display frame layer built on standard QLabel components.

    Dynamically overlays analytical evaluation contours alongside status tracking shapes 
    precisely targeted over visible picture box geometry boundaries.

    """
    
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._source_pixmap: QPixmap | None = None
        self._results = None
        self._original_size = None

    def set_source_pixmap(self, pixmap: QPixmap):
        """Update internal resource references and refresh structural component layout frames.

        Args:
            pixmap (QPixmap):
                The raw source pixel block to render.

        """
        self._source_pixmap = pixmap
        self._refresh_display()

    def set_image(self, image: Image):
        """Read original unscaled resolution metrics metadata safely from disk locations.

        Args:
            image (Image):
                The custom target data image tracking structure.

        """
        self._original_size = QImageReader(str(image.path)).size()

    def set_results(self, results):
        """Assign segmented pipeline prediction nodes to draw bounding boxes on the canvas.

        Args:
            results (Any):
                The custom segmented visual data tracking collections.

        """
        self._results = results if results else None
        self.repaint()

    def clear_results(self):
        """Purge evaluation contexts and wipe tracking paths from layout display layers."""
        self._results = None
        self.update()

    def mousePressEvent(self, event):
        """Intercept mouse press instances to broadcast interactive selection signals outward.

        Args:
            event (QMouseEvent):
                The hardware cursor interaction context packet.

        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def resizeEvent(self, event):
        """Recalculate canvas boundaries dynamically during window configuration modifications.

        Args:
            event (QResizeEvent):
                The component geometry modification event tracking package.

        """
        super().resizeEvent(event)
        self._refresh_display()

    def _refresh_display(self):
        """Scale and render internal pixmap matrices to fit bounding box layouts smoothly."""
        if self._source_pixmap is None or self._source_pixmap.isNull():
            return

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        scaled = self._source_pixmap.scaled(
            QSize(w, h),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        super().setPixmap(scaled)

    def paintEvent(self, event):
        """Paint media contents, visual evaluation arrays, and lifecycle status shapes.

        Args:
            event (QPaintEvent):
                The underlying structural update region instruction context.

        """
        # 1. Laisse le QLabel afficher la Pixmap normalement
        super().paintEvent(event)

        current = self.pixmap()
        if not current or current.isNull():
            return

        # Récupération du contexte du parent
        parent_widget = self.parent()
        if not parent_widget:
            return

        show_badge = getattr(parent_widget, "show_status_badge", False)
        status = getattr(parent_widget, "status", ProcessingStatus.NOT_STARTED)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # ─── CALCUL DU RECTANGLE REEL DE L'IMAGE ───
        # Qt centre l'image dans le label. On calcule exactement où elle s'affiche
        # pour éviter que l'overlay bave ou s'arrête trop tôt sur le bord droit.
        label_w = self.width()
        label_h = self.height()
        img_w = current.width()
        img_h = current.height()

        x_offset = (label_w - img_w) // 2
        y_offset = (label_h - img_h) // 2
        visible_image_rect = QRect(x_offset, y_offset, img_w, img_h)

        # 3. Dessin des résultats SAM (si présents)
        if self._results and self._original_size:
            draw_results(painter, self._results, visible_image_rect, current.size())

        # 4. Rendu dynamique du Badge et de l'Overlay de Statut
        if show_badge:
            overlay_color = STATUS_OVERLAY.get(status, QColor(0, 0, 0, 0))
            if overlay_color.alpha() > 0:
                # L'overlay épouse désormais PARFAITEMENT les bords visibles de l'image
                clip = QPainterPath()
                clip.addRect(x_offset, y_offset, img_w, img_h)
                painter.setClipPath(clip)
                painter.fillPath(clip, QBrush(overlay_color))
                painter.setClipping(False)

                icon_path = STATUS_ICON.get(status, "")
                icon_color = STATUS_BORDER.get(status, QColor(150, 150, 150))

                if icon_path:
                    icon = QPixmap(icon_path)
                    if not icon.isNull():
                        icon_size = 28
                        icon = icon.scaled(icon_size, icon_size,
                                           Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)

                        colored_icon = QPixmap(icon.size())
                        colored_icon.fill(Qt.GlobalColor.transparent)
                        painter_icon = QPainter(colored_icon)
                        painter_icon.setRenderHint(QPainter.RenderHint.Antialiasing)
                        painter_icon.drawPixmap(0, 0, icon)
                        painter_icon.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                        painter_icon.fillRect(colored_icon.rect(), icon_color)
                        painter_icon.end()

                        # Centrage dynamique au milieu de l'image visible
                        cx = visible_image_rect.x() + visible_image_rect.width() // 2
                        cy = visible_image_rect.y() + visible_image_rect.height() // 2
                        r = icon_size // 2 + 6
                        painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
                        painter.setPen(QPen(icon_color, 2))
                        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
                        painter.drawPixmap(cx - icon_size // 2, cy - icon_size // 2, colored_icon)

        painter.end()

# ─────────────────────────────────────────────────────────────────────────────
# Widget principal — ne touche plus à la pixmap du label
# ─────────────────────────────────────────────────────────────────────────────

class ImageThumbnailWidget(QWidget):
    """Unified grid display thumbnail dashboard component backing asynchronous asset loading.

    Supports dual rendering profiles across modular views:
    show_status_badge=True  -> Static uniform dimension square aspect overlays (ImportTool).
    show_status_badge=False -> Fluid variable height structural layouts (Masonry).

    Args:
        image_path (str):
            The file path directory location pointing to the original media source.
        title (str):
            Descriptive asset string title text. Defaults to None.
        status (ProcessingStatus):
            Initial pipeline lifecycle state configuration map token. Defaults to None.
        col_width (int):
            Standardized presentation column target size scale. Defaults to 200.
        show_status_badge (bool):
            Toggle rendering state color overlays and indicators. Defaults to True.
        parent (QWidget):
            Optional corporate parent container framework. Defaults to None.
        show_title (bool):
            Toggle text description field rendering properties. Defaults to True.

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
        show_title=True
    ):
        super().__init__(parent)

        self.image_path        = Path(image_path)
        self.title             = title or self.image_path.name
        self.status            = status or ProcessingStatus.NOT_STARTED
        self.col_width         = col_width
        self.show_status_badge = show_status_badge
        self._source_pixmap: QPixmap | None = None
        self._loader: _ThumbnailLoader | None = None
        self.show_title = show_title

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._setup_ui()
        self._apply_card_style()
        self._start_async_load()

    # ─────────────────────────────────────────────────────────────────────────
    # Annulation propre avant destruction
    # ─────────────────────────────────────────────────────────────────────────

    def cancel_load(self):
        """Safely disconnect or halt active concurrent processing thread workers."""
        if self._loader is not None:
            self._loader.cancel()
            self._loader = None

    def setParent(self, parent):
        """Interprets parental context changes to disconnect processing pipelines safely.

        Args:
            parent (QWidget):
                The targeted hierarchical parent view frame container.

        """
        self.cancel_load()
        super().setParent(parent)

    # ─────────────────────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        """Construct child presentation elements and connect layout interaction lines."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = _ClickableLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.image_label.clicked.connect(lambda: self.clicked.emit(str(self.image_path)))
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        layout.addWidget(self.image_label)

        if self.title and self.show_title and not self.show_status_badge:
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
        """Instantiate tracking workers and stream file contents onto thread pools."""
        if not self.image_path.exists():
            self._show_error()
            return
        self._loader = _ThumbnailLoader(self.image_path, self.col_width, self)
        self._pool.start(self._loader)

    @pyqtSlot(QPixmap)
    def _on_pixmap_loaded(self, thumb: QPixmap):
        """Receive processed background image assets and adapt rendering scales.

        Args:
            thumb (QPixmap):
                The valid image pixel matrices loaded from background operations.

        """
        self._loader = None
        self._source_pixmap = thumb
        self._apply_pixmap_geometry()

        self.image_label.setMinimumSize(0, 0)
        self.image_label.setMaximumSize(16777215, 16777215) # QWIDGETSIZE_MAX
        self.image_label.set_source_pixmap(self._source_pixmap)

    # ─────────────────────────────────────────────────────────────────────────
    # resizeEvent — ne touche PLUS à la pixmap du label
    # ─────────────────────────────────────────────────────────────────────────

    def resizeEvent(self, event):
        """Forward structural dimensional notifications to subcomponents automatically.

        Args:
            event (QResizeEvent):
                The operational metric modifications configuration tracking context.

        """
        super().resizeEvent(event)
        # Rien à faire : _ClickableLabel.resizeEvent s'en charge lui-même

    def _update_pixmap_to_label(self):
        """Provide layout stability stub overrides for JustifiedGalleryLayout configurations.

        Sizing scales are managed autonomously internally by internal subcomponent layers.
        """
        self.image_label.update()

    @pyqtSlot()
    def _show_error(self):
        """Enforce visibility error indicators when underlying disk streaming actions fail."""
        self._loader = None
        self.image_label.setText("⚠")
        self.image_label.setStyleSheet("QLabel { background: transparent; border-radius: 4px; }")
        if self.show_status_badge:
            self.image_label.setFixedSize(self.col_width, self.col_width)

    # ─────────────────────────────────────────────────────────────────────────
    # Style
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_card_style(self):
        """Inject customized background CSS properties matching active mode badges."""
        if not self.show_status_badge:
            self.setStyleSheet("ImageThumbnailWidget { background: transparent; border-radius: 10px; }")
            return
        self.setStyleSheet("ImageThumbnailWidget { background: transparent; border: none; }")
        self.image_label.setStyleSheet("QLabel { background: transparent; border-radius: 4px; }")

    # ─────────────────────────────────────────────────────────────────────────
    # API publique
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_pixmap_geometry(self):
        """Configure widget bounding scale boundaries based on active loaded dimensions and profile constraints.

        Must only execute on initial file loader callbacks; never call during status updates.
        """
        if not self._source_pixmap:
            return

        if self.show_status_badge:
            px = self._source_pixmap
            self.image_label.setFixedSize(px.width(), px.height())
        else:
            self.image_label.setMinimumSize(0, 0)
            self.image_label.setMaximumSize(16777215, 16777215)
            self.image_label.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )

    def set_source_pixmap(self, pixmap: QPixmap):
        """Manually map raw pixel asset fields and update structural grid dimensions once.

        Args:
            pixmap (QPixmap):
                The loaded picture matrix block instance configuration target.

        """
        self._source_pixmap = pixmap
        self._apply_pixmap_geometry()      # géométrie calculée UNE FOIS ici
        self.image_label.set_source_pixmap(pixmap)

    def set_status(self, status: ProcessingStatus):
        """Apply an updated pipeline status flag and request repainting routines over overlays.

        Args:
            status (ProcessingStatus):
                The targets updated pipeline validation enum tracker state.

        """
        self.status = status
        # uniquement le rendu du badge, plus aucun appel à setFixedSize/setSizePolicy
        self.image_label.update()

    def get_status(self) -> ProcessingStatus:
        """Fetch the current lifecycle processing state registered within the element.

        Returns:
            ProcessingStatus: The active pipeline state configuration token.

        """
        return self.status

    def get_image_path(self) -> str:
        """Fetch the absolute file disk system directory location tracking the media asset.

        Returns:
            str: The string file path representation.

        """
        return str(self.image_path)