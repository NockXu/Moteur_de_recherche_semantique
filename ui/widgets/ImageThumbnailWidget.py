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
    def __init__(self, image_path: Path, size: int, target: "ImageThumbnailWidget"):
        super().__init__()
        self.setAutoDelete(True)
        self.image_path = image_path
        self.size       = size
        self._target    = target
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @pyqtSlot()
    def run(self):
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
# Label cliquable — Dessine l'image ET le badge dynamiquement
# ─────────────────────────────────────────────────────────────────────────────

class _ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._source_pixmap: QPixmap | None = None
        self._results = None
        self._original_size = None

    def set_source_pixmap(self, pixmap: QPixmap):
        self._source_pixmap = pixmap
        self._refresh_display()

    def set_image(self, image: Image):
        self._original_size = QImageReader(str(image.path)).size()

    def set_results(self, results):
        self._results = results if results else None
        self.repaint()

    def clear_results(self):
        self._results = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_display()

    def _refresh_display(self):
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
    """Widget thumbnail unifié avec chargement asynchrone.

    show_status_badge=True  → ImportTool (carte carrée fixe, overlay statut)
    show_status_badge=False → Masonry (hauteur dynamique, pas d'overlay)
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
        if self._loader is not None:
            self._loader.cancel()
            self._loader = None

    def setParent(self, parent):
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
        if not self.image_path.exists():
            self._show_error()
            return
        self._loader = _ThumbnailLoader(self.image_path, self.col_width, self)
        self._pool.start(self._loader)

    @pyqtSlot(QPixmap)
    def _on_pixmap_loaded(self, thumb: QPixmap):
        self._loader = None
        self._source_pixmap = thumb

        self.image_label.setMinimumSize(0, 0)
        self.image_label.setMaximumSize(16777215, 16777215) # QWIDGETSIZE_MAX
        self.image_label.set_source_pixmap(self._source_pixmap)

    # ─────────────────────────────────────────────────────────────────────────
    # resizeEvent — ne touche PLUS à la pixmap du label
    # ─────────────────────────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Rien à faire : _ClickableLabel.resizeEvent s'en charge lui-même

    def _update_pixmap_to_label(self):
        """Stub de compatibilité pour JustifiedGalleryLayout.
        _ClickableLabel gère son propre scaling via resizeEvent — rien à faire ici.
        """
        self.image_label.update()

    @pyqtSlot()
    def _show_error(self):
        self._loader = None
        self.image_label.setText("⚠")
        self.image_label.setStyleSheet("QLabel { background: transparent; border-radius: 4px; }")
        if self.show_status_badge:
            self.image_label.setFixedSize(self.col_width, self.col_width)

    # ─────────────────────────────────────────────────────────────────────────
    # Style
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_card_style(self):
        if not self.show_status_badge:
            self.setStyleSheet("ImageThumbnailWidget { background: transparent; border-radius: 10px; }")
            return
        self.setStyleSheet("ImageThumbnailWidget { background: transparent; border: none; }")
        self.image_label.setStyleSheet("QLabel { background: transparent; border-radius: 4px; }")

    # ─────────────────────────────────────────────────────────────────────────
    # API publique
    # ─────────────────────────────────────────────────────────────────────────

    def set_status(self, status: ProcessingStatus):
        self.status = status

        if self._source_pixmap:
            if self.show_status_badge:
                px = _build_import_pixmap(
                    self._source_pixmap,
                    self.col_width,
                    self.status
                )
                self.image_label.setFixedSize(px.width(), px.height())
                self.image_label.set_source_pixmap(px)
            else:
                # Si le badge est désactivé, on libère le layout des contraintes de taille fixe
                self.image_label.setMinimumSize(0, 0)
                self.image_label.setMaximumSize(16777215, 16777215)
                self.image_label.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Expanding,
                )
                self.image_label.set_source_pixmap(self._source_pixmap)

    def get_status(self) -> ProcessingStatus:
        return self.status

    def get_image_path(self) -> str:
        return str(self.image_path)