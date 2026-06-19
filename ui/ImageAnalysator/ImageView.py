from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import QLabel, QRubberBand
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen

# Palette de couleurs pour les boîtes
BOX_COLORS = [
    QColor(255, 80,  80),   # rouge
    QColor(80,  200, 120),  # vert
    QColor(80,  160, 255),  # bleu
    QColor(255, 200, 50),   # jaune
    QColor(200, 100, 255),  # violet
    QColor(255, 140, 50),   # orange
    QColor(50,  220, 220),  # cyan
    QColor(255, 100, 180),  # rose
]


class ImageView(QLabel):
    """Canvas interactif gérant l'affichage d'images, le tracé de boîtes et la superposition de masques SAM3.

    Args:
        parent (QWidget | None): Widget parent de l'instance. Defaults to None.
        selectable (bool): Active l'interaction à la souris pour dessiner ou modifier des boîtes. Defaults to False.
    """
    selection_finished = pyqtSignal()
    box_changed = pyqtSignal(int, QRect)
    results_displayed = pyqtSignal(dict)

    def __init__(self, parent=None, selectable: bool = False):
        super().__init__(parent)

        self._display_rect = QRect()
        self._scaled_pixmap = None
        self._image_path: Path | None = None

        self._pixmap = None
        self._selectable = selectable

        # Sélection en cours (dessin à la souris)
        self._origin: QPoint | None = None
        self._current_rect: QRect | None = None
        self._is_drawing = False

        # Stockage des boîtes validées  {index: {"rect": QRect, "color": QColor}}
        self._boxes: dict[int, dict] = {}
        self._next_index: int = 0

        # Boîte en cours de redimensionnement
        self._resize_index: int | None = None
        self._resize_handle: str | None = None   # "br", "tr", "bl", "tl"
        self._resize_origin: QPoint | None = None
        self._resize_initial_rect: QRect | None = None
        HANDLE_SIZE = 10
        self._handle_size = HANDLE_SIZE

        # Résultats à afficher — liste de dicts émis par ResultsTable.result_selected
        # Chaque élément : {"prompt", "index", "score", "box": [x1,y1,x2,y2],
        #                   "color": QColor, "row": int, "type": "result"}
        self._active_results: list[dict] = []

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(1, 1)
        self.setStyleSheet("background-color: #111;")

        if selectable:
            self.setMouseTracking(True)

    # ------------------------------------------------------------------ #
    #  Propriété selectable                                                #
    # ------------------------------------------------------------------ #

    @property
    def selectable(self) -> bool:
        """Indique si le dessin et le redimensionnement interactifs sont actifs.

        Returns:
            bool:
        """
        return self._selectable

    @selectable.setter
    def selectable(self, value: bool):
        self._selectable = value
        self.setMouseTracking(value)
        self.update()

    # ------------------------------------------------------------------ #
    #  Chargement de l'image                                               #
    # ------------------------------------------------------------------ #

    def setImage(self, image_path: Path | str | None):
        """Met à jour le pixmap source à partir d'un chemin de fichier cible.

        Args:
            image_path (Path | str | None): Chemin système vers l'image.
        """
        if image_path is None:
            self._image_path = None
            self._pixmap = None
        else:
            self._image_path = image_path
            self._pixmap = QPixmap(str(image_path))
        self.updateScaledPixmap()
        self.update()

    # ------------------------------------------------------------------ #
    #  Redimensionnement du widget                                         #
    # ------------------------------------------------------------------ #

    def resizeEvent(self, event) -> None:
        """Intercepte les redimensionnements du widget pour mettre à l'échelle la texture.

        Args:
            event (QResizeEvent): Métadonnées de l'événement système.
        """
        super().resizeEvent(event)
        self.updateScaledPixmap()

    def updateScaledPixmap(self) -> None:
        """Calcule le ratio d'aspect de l'image et centre le rectangle de rendu."""
        if self._pixmap is None:
            return

        self._scaled_pixmap = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # Centrage de l'image dans le widget
        x = (self.width() - self._scaled_pixmap.width()) // 2
        y = (self.height() - self._scaled_pixmap.height()) // 2

        self._display_rect = QRect(
            x,
            y,
            self._scaled_pixmap.width(),
            self._scaled_pixmap.height(),
        )

        self.update()

    # ------------------------------------------------------------------ #
    #  Dessin des boîtes par-dessus l'image                              #
    # ------------------------------------------------------------------ #

    def image_to_widget_rect(self, rect: QRect) -> QRect:
        """Transpose les dimensions depuis le repère image vers le repère widget.

        Args:
            rect (QRect): Zone d'origine en pixels image.

        Returns:
            QRect:
        """
        sx = self._display_rect.width() / self._pixmap.width()
        sy = self._display_rect.height() / self._pixmap.height()

        x = rect.x() * sx + self._display_rect.x()
        y = rect.y() * sy + self._display_rect.y()
        w = rect.width() * sx
        h = rect.height() * sy

        return QRect(int(x), int(y), int(w), int(h))

    def widget_to_image_rect(self, rect: QRect) -> QRect:
        """Transpose les dimensions depuis le repère widget vers le repère image.

        Args:
            rect (QRect): Zone d'origine en pixels widget.

        Returns:
            QRect:
        """
        sx = self._pixmap.width() / self._display_rect.width()
        sy = self._pixmap.height() / self._display_rect.height()

        x = (rect.x() - self._display_rect.x()) * sx
        y = (rect.y() - self._display_rect.y()) * sy
        w = rect.width() * sx
        h = rect.height() * sy

        return QRect(int(x), int(y), int(w), int(h))

    def paintEvent(self, event) -> None:
        """Gère le rendu des couches d'images, des overlays utilisateur et des masques.

        Args:
            event (QPaintEvent): Événement de mise à jour graphique.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # image
        if self._scaled_pixmap:
            painter.drawPixmap(self._display_rect.topLeft(), self._scaled_pixmap)

        # boxes (toujours visibles)
        for idx, box in self._boxes.items():
            color = box["color"]
            rect = self.image_to_widget_rect(box["rect"])

            painter.fillRect(rect, QColor(color.red(), color.green(), color.blue(), 40))
            painter.setPen(QPen(color, 2))
            painter.drawRect(rect)

            # handles uniquement si selectable
            if self._selectable:
                for hx, hy in self._handle_positions(box["rect"]):
                    hx = self.image_to_widget_rect(QRect(hx, hy, 1, 1)).x()
                    hy = self.image_to_widget_rect(QRect(hx, hy, 1, 1)).y()

                    painter.fillRect(
                        hx - self._handle_size // 2,
                        hy - self._handle_size // 2,
                        self._handle_size,
                        self._handle_size,
                        color
                    )

        # preview selection
        if self._is_drawing and self._current_rect:
            rect = self._current_rect.normalized()
            color = self._next_box_color()

            painter.fillRect(rect, QColor(color.red(), color.green(), color.blue(), 30))
            painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
            painter.drawRect(rect)

        # ---------------------------------------------------------
        # RESULTS (depuis ResultsTable.result_selected)
        # ---------------------------------------------------------

        for entry in self._active_results:

            box = entry.get("box")
            score = entry.get("score")
            color: QColor = entry.get("color")
            mask = entry.get("mask")

            dot_color = color or QColor(80, 160, 255)

            if box is None:
                continue

            x1, y1, x2, y2 = box
            rect_img = QRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
            rect = self.image_to_widget_rect(rect_img)

            # =========================
            # MASK (remplace fillRect)
            # =========================
            if mask is not None:
                self._draw_mask(painter, mask, dot_color, rect)

            # =========================
            # BORDER (box contour)
            # =========================
            painter.setPen(QPen(dot_color, 2))
            painter.drawRect(rect)

            # =========================
            # LABEL
            # =========================
            if score is not None:
                prompt = entry.get("prompt", "")
                idx = entry.get("index", 0)
                text = f"{prompt} #{idx + 1}  {score * 100:.1f}%"

                fm = painter.fontMetrics()
                tw = fm.horizontalAdvance(text) + 10
                th = fm.height() + 4

                label_x = rect.x()
                label_y = rect.y() - th - 2

                if label_y < self._display_rect.top():
                    label_y = rect.y() + 2

                painter.fillRect(
                    label_x,
                    label_y,
                    tw,
                    th,
                    QColor(dot_color.red(), dot_color.green(), dot_color.blue(), 200),
                )

                painter.setPen(Qt.GlobalColor.white)
                painter.drawText(label_x + 5, label_y + th - 5, text)

    def _draw_mask(self, painter : QPainter, mask, color : QColor, rect) -> None:
        """Convertit un tenseur/matrice numpy de masque et le plaque sur le canevas."""
        m = mask
        if mask is None:
            return

        import numpy as np
        from PyQt6.QtGui import QImage

        # Squeeze toutes les dimensions inutiles -> (H, W)
        m = mask
        if hasattr(m, "detach"):
            m = m.detach().cpu()
        if hasattr(m, "numpy"):
            m = m.numpy()
        m = np.asarray(m)
        while m.ndim > 2:
            m = m.squeeze(0)
        m = (m > 0).astype(np.uint8)

        h, w = m.shape
        r, g, b = color.red(), color.green(), color.blue()

        # Construit RGBA vectorise (bien plus rapide que setPixelColor)
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[..., 0] = r
        rgba[..., 1] = g
        rgba[..., 2] = b
        rgba[..., 3] = m * 120

        # Garde la ref des bytes en vie pendant drawImage
        rgba_bytes = rgba.tobytes()
        img = QImage(rgba_bytes, w, h, 4 * w, QImage.Format.Format_RGBA8888)

        painter.drawImage(self._display_rect, img)

    # ------------------------------------------------------------------ #
    #  API publique — résultats ResultsTable                              #
    # ------------------------------------------------------------------ #

    def set_active_results(self, results: list[dict]) -> None:
        """Injecte les données de segmentation actives pour forcer la mise à jour visuelle.

        Args:
            results (list[dict]): Liste de dictionnaires contenant boîtes, scores et masques.
        """
        if results not in [None, False]:
            self._active_results = results or []
            self.update()
            image_result = {self._image_path: results}
            self.results_displayed.emit(image_result)

    def clear_results(self) -> None:
        """Réinitialise et efface l'affichage de tous les masques calculés."""
        self._active_results = []
        self.update()

    # ------------------------------------------------------------------ #
    #  Événements souris                                                 #
    # ------------------------------------------------------------------ #

    def mousePressEvent(self, event) -> None:
        """Gère l'initialisation des tracés utilisateur et la capture des poignées de redimensionnement.

        Args:
            event (QMouseEvent): Contient la position du curseur souris.
        """
        if not self._selectable:
            return super().mousePressEvent(event)

        pos = event.position().toPoint()

        if not self._display_rect.contains(pos):
            return

        # Vérifie si on clique sur une poignée
        for idx, box in self._boxes.items():
            for (hx, hy), handle_name in zip(
                self._handle_positions(box["rect"]),
                ("tl", "tr", "bl", "br"),
            ):
                handle_pt = self.image_to_widget_rect(QRect(hx, hy, 1, 1)).topLeft()

                hr = QRect(
                    handle_pt.x() - self._handle_size // 2,
                    handle_pt.y() - self._handle_size // 2,
                    self._handle_size,
                    self._handle_size,
                )

                if hr.contains(pos):
                    self._resize_index = idx
                    self._resize_handle = handle_name
                    self._resize_initial_rect = QRect(box["rect"])
                    return

        # Sinon, début d'une nouvelle sélection
        self._origin = pos
        self._current_rect = QRect(pos, QSize())
        self._is_drawing = True

    def mouseMoveEvent(self, event) -> None:
        """Met à jour dynamiquement les dimensions de la boîte ciblée (tracé ou étirement).

        Args:
            event (QMouseEvent): Position mise à jour du curseur.
        """
        if not self._selectable:
            return super().mouseMoveEvent(event)

        pos = event.position().toPoint()

        # Clamp dans l'image
        pos.setX(max(self._display_rect.left(),
                    min(pos.x(), self._display_rect.right())))

        pos.setY(max(self._display_rect.top(),
                    min(pos.y(), self._display_rect.bottom())))

        if self._resize_index is not None:
            self._stretch_box(pos)
            self.update()
            return

        if self._is_drawing and self._origin is not None:
            self._current_rect = QRect(self._origin, pos).normalized()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        """Clôture l'opération courante de mutation géométrique et émet les signaux de notification.

        Args:
            event (QMouseEvent): Événement de relâchement du bouton souris.
        """
        if not self._selectable:
            return super().mouseReleaseEvent(event)

        # Fin du redimensionnement
        if self._resize_index is not None:
            idx = self._resize_index

            self.box_changed.emit(
                idx,
                QRect(self._boxes[idx]["rect"])
            )

            self._resize_index = None
            self._resize_handle = None
            self._resize_origin = None
            self._resize_initial_rect = None
            return

        # Fin du dessin — la boîte n'est PAS validée automatiquement,
        # elle reste disponible via get_selection_rect()
        self._is_drawing = False
        self.update()
        self.selection_finished.emit()

    # ------------------------------------------------------------------ #
    #  API publique — sélection                                            #
    # ------------------------------------------------------------------ #

    def get_selection_rect(self) -> QRect | None:
        """Fournit le rectangle en cours de tracé dans le référentiel du widget.

        Returns:
            QRect | None:
        """
        if self._current_rect is None:
            return None
        return self._current_rect.normalized()

    def get_selection_rect_image_coords(self) -> QRect | None:
        """Fournit le rectangle courant converti dans le repère en pixels réels de l'image.

        Returns:
            QRect | None:
        """
        rect = self.get_selection_rect()

        if rect is None or self._pixmap is None:
            return None

        scale_x = self._pixmap.width() / self._display_rect.width()
        scale_y = self._pixmap.height() / self._display_rect.height()

        x = (rect.x() - self._display_rect.x()) * scale_x
        y = (rect.y() - self._display_rect.y()) * scale_y

        w = rect.width() * scale_x
        h = rect.height() * scale_y

        return QRect(
            int(x),
            int(y),
            int(w),
            int(h),
        )

    def apply_selection(self) -> int | None:
        """Valide la sélection pointillée courante et l'ajoute au catalogue interne.

        Returns:
            int | None:
        """
        rect = self.get_selection_rect()

        if rect is None:
            return None

        if rect.isNull() or rect.width() < 2 or rect.height() < 2:
            return None

        image_rect = self.widget_to_image_rect(rect)

        color = self._next_box_color()
        idx = self._next_index

        self._boxes[idx] = {
            "rect": QRect(image_rect),
            "color": color
        }

        self._next_index += 1
        self._current_rect = None
        self.update()

        return idx

    def _stretch_box(self, pos: QPoint) -> None:
        """Modifie les dimensions de la boîte sélectionnée à partir de la poignée saisie."""
        if self._resize_index is None or self._resize_initial_rect is None:
            return

        r = QRect(self._resize_initial_rect)
        handle = self._resize_handle

        if handle == "tl":
            r.setTopLeft(pos)
        elif handle == "tr":
            r.setTopRight(pos)
        elif handle == "bl":
            r.setBottomLeft(pos)
        elif handle == "br":
            r.setBottomRight(pos)

        r = r.normalized()

        self._boxes[self._resize_index]["rect"] = r
        self.box_changed.emit(self._resize_index, QRect(r))  # <-- IMPORTANT

    def delete_box(self, index: int) -> bool:
        """Supprime l'élément correspondant à l'index donné s'il existe.

        Args:
            index (int): Identifiant unique de la boîte.

        Returns:
            bool:
        """
        if index not in self._boxes:
            return False
        del self._boxes[index]
        self.update()
        return True

    def get_box_color(self, index: int) -> QColor | None:
        """Renvoie la couleur associée à un identifiant donné.

        Args:
            index (int): Clé de recherche de la boîte.

        Returns:
            QColor | None:
        """
        box = self._boxes.get(index)
        return QColor(box["color"]) if box else None

    def get_all_boxes(self) -> dict[int, dict]:
        """Génère un dictionnaire découplé de l'ensemble des boîtes enregistrées.

        Returns:
            dict[int, dict]:
        """
        return {
            idx: {"rect": QRect(b["rect"]), "color": QColor(b["color"])}
            for idx, b in self._boxes.items()
        }

    def load_boxes(self, boxes: list[list[int]] | None = None, labels : list[bool] | None = None, colors : list[QColor] | None = None) -> None:
        """Écrase la configuration actuelle et injecte de nouveaux lots de données externes.

        Args:
            boxes (list[list[int]] | None): Liste de coordonnées [x1, y1, x2, y2]. Defaults to None.
            labels (list[bool] | None): Polarités associées (Positif/Négatif). Defaults to None.
            colors (list[QColor] | None): Couleurs prédéfinies à affecter. Defaults to None.
        """
        self._boxes.clear()
        self._next_index = 0

        if not boxes:
            self.update()
            return

        for i, coords in enumerate(boxes):
            x1, y1, x2, y2 = coords

            rect = QRect(x1, y1, x2 - x1, y2 - y1)

            color = colors[i] if colors else self._next_box_color()

            self._boxes[i] = {
                "rect": rect,
                "color": color,
                "label": labels[i] if labels else True
            }

            self._next_index += 1

        self.update()

    # ------------------------------------------------------------------ #
    #  Helpers internes                                                    #
    # ------------------------------------------------------------------ #

    def _next_box_color(self) -> QColor:
        """Renvoie la couleur cyclique suivante basée sur l'index incrémental.

        Returns:
            QColor:
        """
        return BOX_COLORS[self._next_index % len(BOX_COLORS)]

    def _handle_positions(self, rect: QRect) -> list[tuple[int, int]]:
        """Calcule les 4 coins cardinaux d'une boîte normalisée.

        Args:
            rect (QRect): Rectangle source dans le repère image.

        Returns:
            list[tuple[int, int]]:
        """
        r = rect.normalized()
        return [
            (r.left(), r.top()),      # tl
            (r.right(), r.top()),     # tr
            (r.left(), r.bottom()),   # bl
            (r.right(), r.bottom()),  # br
        ]

    def _stretch_box(self, pos: QPoint):
        if self._resize_index is None or self._resize_initial_rect is None:
            return

        r = QRect(self._resize_initial_rect)

        # convert widget → image (UNE seule fois)
        pos_img = self.widget_to_image_rect(QRect(pos, QSize(1, 1))).topLeft()

        handle = self._resize_handle

        if handle == "tl":
            r.setTopLeft(pos_img)
        elif handle == "tr":
            r.setTopRight(pos_img)
        elif handle == "bl":
            r.setBottomLeft(pos_img)
        elif handle == "br":
            r.setBottomRight(pos_img)

        r = r.normalized()

        self._boxes[self._resize_index]["rect"] = r
        self.box_changed.emit(self._resize_index, QRect(r))
        self.update()