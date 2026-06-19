from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import QRect

import numpy as np
import cv2
from PyQt6.QtGui import QImage

def draw_results(painter: QPainter, results: list[dict], display_rect: QRect, pixmap_size):
    """Render SAM3 segmentation masks and bounding boxes onto a targeted canvas surface.

    Extracted from ImageView.paintEvent for cross-component modular reuse across
    different canvas overlays.

    Args:
        painter (QPainter): The target active render surface context.
        results (list[dict]): A collection of dictionaries tracking prediction results, 
            containing keys such as 'mask', 'box', and 'color'.
        display_rect (QRect): Bounding viewport layout matching the target canvas location.
        pixmap_size (QSize): Scale metrics of the texture map layer currently displayed.
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
        
        box = entry.get("box")
        if box:
            x1, y1, x2, y2 = box

            scale_x = pixmap_size.width() / mask.shape[-1]
            scale_y = pixmap_size.height() / mask.shape[-2]

            x1 *= scale_x
            x2 *= scale_x
            y1 *= scale_y
            y2 *= scale_y

            painter.drawRect(
                int(display_rect.x() + x1),
                int(display_rect.y() + y1),
                int(x2 - x1),
                int(y2 - y1)
            )