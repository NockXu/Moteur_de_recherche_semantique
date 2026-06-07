from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import QRect

import numpy as np
import cv2
from PyQt6.QtGui import QImage

def draw_results(painter: QPainter, results: list[dict], display_rect: QRect, pixmap_size):
    """
    Dessine les résultats SAM3 sur n'importe quel painter.
    Extrait de ImageView.paintEvent — réutilisable partout.
    """
    for entry in results:
        mask = entry.get("mask")

        color: QColor = entry.get("color") or QColor(80, 160, 255)

        painter.setPen(QPen(color, 2))

        if mask is not None:
            mask_np = mask.squeeze(0).detach().cpu().numpy().astype(np.uint8)

            # Redimensionnement du masque à la taille du pixmap affiché
            mask_np = cv2.resize(
                mask_np,
                (pixmap_size.width(), pixmap_size.height()),
                interpolation=cv2.INTER_NEAREST
            )

            rgba = np.zeros(
                (pixmap_size.height(), pixmap_size.width(), 4),
                dtype=np.uint8
            )

            rgba[..., 0] = color.red()
            rgba[..., 1] = color.green()
            rgba[..., 2] = color.blue()
            rgba[..., 3] = mask_np * 100  # transparence

            qimg = QImage(
                rgba.data,
                pixmap_size.width(),
                pixmap_size.height(),
                rgba.strides[0],
                QImage.Format.Format_RGBA8888
            ).copy()

            painter.drawImage(display_rect, qimg)