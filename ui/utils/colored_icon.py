from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

def colored_icon(path: str, color: str, size: int = 24) -> QIcon:
    """Generate a dynamically tinted QIcon from a source SVG asset vector path.

    Utilizes source-in color composition constraints over a transparent rendering 
    surface canvas to apply a uniform fill layer mask onto the asset lines.

    Args:
        path (str): The physical storage disk path location of the target SVG vector file.
        color (str): A hex character sequence code string representation (e.g., "#2e7d32").
        size (int): Dimensions width and height scaling boundary metrics applied onto the pixel grid canvas surface.

    Returns:
        QIcon: A new icon wrapper instance containing the re-tinted vector bitmap canvas frame.
    """
    renderer = QSvgRenderer(path)

    # Initialize a transparent square canvas frame
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    # Paint raw vector geometry layers onto the layout canvas texture first
    painter = QPainter(pixmap)
    renderer.render(painter)

    # Impose clipping boundaries onto the image data pixels to apply a color overlay mask
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()

    return QIcon(pixmap)