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
# Pixmap composite (image + overlay + icône) — inchangé
# ─────────────────────────────────────────────────────────────────────────────

def _build_import_pixmap(source: QPixmap, max_width: int, status: ProcessingStatus) -> QPixmap:
    scaled = source.scaled(QSize(max_width, max_width),
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)

    result = QPixmap(scaled.width(), scaled.height())
    result.fill(Qt.GlobalColor.transparent)

    p = QPainter(result)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
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

                cx = scaled.width() // 2
                cy = scaled.height() // 2
                r = icon_size // 2 + 6
                p.setBrush(QBrush(QColor(255, 255, 255, 230)))
                p.setPen(QPen(icon_color, 2))
                p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
                p.drawPixmap(cx - icon_size // 2, cy - icon_size // 2, colored_icon)
    p.end()
    return result


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
# Label cliquable — gère sa propre pixmap et son propre scaling
# ─────────────────────────────────────────────────────────────────────────────

class _ClickableLabel(QLabel):
    """
    Label qui :
    - détient la pixmap originale (_source_pixmap)
    - se scale lui-même dans resizeEvent
    - dessine les résultats SAM dans paintEvent
    - personne d'autre ne touche à sa pixmap
    """
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._source_pixmap: QPixmap | None = None  # pixmap originale, jamais scalée
        self._results = None
        self._original_size = None  # taille réelle de l'image source (QSize)

    def set_source_pixmap(self, pixmap: QPixmap):
        """Seule méthode pour donner une pixmap au label. Jamais setPixmap() directement."""
        self._source_pixmap = pixmap
        self._refresh_display()

    def set_image(self, image: Image):
        """Stocke la taille originale de l'image pour le calcul du ratio des résultats."""
        self._original_size = QImageReader(str(image.path)).size()

    def set_results(self, results):
        if results not in [None, []]:
            self._results = results
        self.update()

    def clear_results(self):
        self._results = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def resizeEvent(self, event):
        """Le label se redimensionne lui-même — le widget parent n'a rien à faire."""
        super().resizeEvent(event)
        self._refresh_display()

    def _refresh_display(self):
        """Recalcule et affiche la pixmap scalée à la taille actuelle du label."""
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
        # On appelle setPixmap de QLabel ici — c'est le seul endroit autorisé
        super().setPixmap(scaled)

    def paintEvent(self, event):
        super().paintEvent(event)

        if not self._results or not self._original_size:
            return

        current = self.pixmap()
        if not current or current.isNull():
            return

        sx = current.width() / self._original_size.width()
        sy = current.height() / self._original_size.height()

        scaled_results = []
        for entry in self._results:
            box = entry.get("box")
            if box:
                x1, y1, x2, y2 = box
                entry = dict(entry)
                entry["box"] = [x1 * sx, y1 * sy, x2 * sx, y2 * sy]
            scaled_results.append(entry)

        painter = QPainter(self)
        label_rect = QRect(0, 0, self.width(), self.height())
        draw_results(painter, scaled_results, label_rect, current.size())
        painter.end()


# ─────────────────────────────────────────────────────────────────────────────
# Widget principal — ne touche plus à la pixmap du label
# ─────────────────────────────────────────────────────────────────────────────

class ImageThumbnailWidget(QWidget):
    """
    Widget thumbnail unifié avec chargement asynchrone.

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

        if self.show_status_badge:
            # Mode badge : le composite est déjà final (taille fixe, overlay inclus)
            # On bypasse set_source_pixmap et on donne le composite directement à QLabel
            px = _build_import_pixmap(self._source_pixmap, self.col_width, self.status)
            self.image_label.setFixedSize(px.width(), px.height())
            QLabel.setPixmap(self.image_label, px)
        else:
            # Mode masonry : le label gère le scaling tout seul
            self.image_label.set_source_pixmap(self._source_pixmap)

    # ─────────────────────────────────────────────────────────────────────────
    # resizeEvent — ne touche PLUS à la pixmap du label
    # ─────────────────────────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Rien à faire : _ClickableLabel.resizeEvent s'en charge lui-même

    def _update_pixmap_to_label(self):
        """
        Stub de compatibilité pour JustifiedGalleryLayout.
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
        if self.show_status_badge and self._source_pixmap:
            px = _build_import_pixmap(self._source_pixmap, self.col_width, self.status)
            self.image_label.setFixedSize(px.width(), px.height())
            QLabel.setPixmap(self.image_label, px)

    def get_status(self) -> ProcessingStatus:
        return self.status

    def get_image_path(self) -> str:
        return str(self.image_path)