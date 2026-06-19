import sys
import os

from PyQt6.QtWidgets import (
    QGridLayout, QWidget, QVBoxLayout, QLabel, QScrollArea,
    QFrame, QHBoxLayout, QSizePolicy, QLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap
from matplotlib import container

from common.Image_Classes.Image import Image
from common.Dataset_Classes.Dataset import Dataset

from ui.utils.FlowLayout import FlowLayout
from ui.utils.ResponsiveImageLabel import ResponsiveImageLabel
from ui.ImageAnalysator.ImageAnalysator import ImageAnalysator
from ui.utils.i18n import tr

class ImagePreviewView(QWidget):
    """Side inspector panel view displaying details, metadata, and tags for a selected image.

    Signals:
        image_clicked (pyqtSignal): Emitted when the user interacts with the preview image area.
        reload_requested (pyqtSignal): Emitted when an explicit preview reload event is requested.
    """

    image_clicked = pyqtSignal()
    reload_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._setup_ui()

    # ─────────────────────────────
    # UI
    # ─────────────────────────────

    def _setup_ui(self) -> None:
        """Initializes structural sidebar components and binds layout scroll boundaries."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.setMinimumWidth(450)

        # SCROLL AREA GLOBALE
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        container = QWidget()
        container.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )

        main_layout = QVBoxLayout(container)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)

        # ═════════════════════════════════════
        # SECTION IMAGE
        # ═════════════════════════════════════

        image_section = QWidget()
        image_section.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding
        )

        image_layout = QVBoxLayout(image_section)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        image_layout.setSpacing(12)

        # Image display
        self.image_analysator = ImageAnalysator()
        self.image_analysator.show_loader_bar = False
        self.image_analysator.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        image_layout.addWidget(self.image_analysator)

        # Title
        self.title = QLabel()
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.title.setWordWrap(True)
        self.title.setStyleSheet("QLabel { background: transparent; }")
        image_layout.addWidget(self.title)

        main_layout.addWidget(image_section)

        # Separator
        self.separator1 = QFrame()
        self.separator1.setFrameShape(QFrame.Shape.HLine)
        self.separator1.setFixedHeight(1)
        self.separator1.setStyleSheet(
            f"QFrame {{ background: transparent; border: none; border-top: 1px solid {os.environ['QTMATERIAL_SECONDARYLIGHTCOLOR']}; }}"
        )
        main_layout.addSpacing(12)
        main_layout.addWidget(self.separator1)
        main_layout.addSpacing(12)

        # ═════════════════════════════════════
        # SECTION INFORMATIONS
        # ═════════════════════════════════════

        self.info_section = QWidget()
        self.info_section.setStyleSheet(
            f"QWidget {{ background: {os.environ['QTMATERIAL_SECONDARYLIGHTCOLOR']}; padding: 10px; }}"
        )

        info_layout = QVBoxLayout(self.info_section)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(20)

        # Path
        self.path_group, self.path_title = self._create_info_group(tr("Emplacement"))
        self.path_label = QLabel()
        self.path_label.setFont(QFont("Segoe UI", 9))
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_group.layout().addWidget(self.path_label)
        info_layout.addWidget(self.path_group)

        # Description
        self.desc_group, self.desc_title = self._create_info_group(tr("Description"))
        self.desc_label = QLabel()
        self.desc_label.setFont(QFont("Segoe UI", 9))
        self.desc_label.setWordWrap(True)
        self.desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignJustify)
        self.desc_group.layout().addWidget(self.desc_label)
        info_layout.addWidget(self.desc_group)

        # Tags
        self.tags_group, self.tags_title = self._create_info_group(tr("Mots-clés"))
        self.tags_group.layout().setContentsMargins(0, 0, 0, 10)

        self.tags_container = QWidget()
        self.tags_layout = FlowLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(8)
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        self.tags_group.layout().addWidget(self.tags_container)
        info_layout.addWidget(self.tags_group)

        main_layout.addWidget(self.info_section)

        # EMPTY STATE
        self.empty = QLabel(
            tr("Aucune image sélectionnée\n\nSélectionne une image dans la galerie\npour voir ses détails")
        )
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setFont(QFont("Segoe UI", 10))
        self.empty.setStyleSheet("QLabel { background: transparent; color: rgba(0,0,0,0.4); }")

        main_layout.addWidget(self.empty)

        # FINALIZE
        root.addWidget(self.scroll)
        QTimer.singleShot(0, lambda: self._attach_scroll(container))

        container.setMinimumWidth(0)

        self.path_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.desc_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        main_layout.addStretch()
        
    def _attach_scroll(self, container) -> None:
        """Binds the main container widget instance inside the global scroll viewport view.

        Args:
            container (QWidget): The inner scroll wrapper layout widget.
        """
        self.scroll.setWidget(container)

    def _create_info_group(self, title: str) -> tuple[QWidget, QLabel]:
        """Creates a labelled container block used to isolate unified structural details rows.

        Args:
            title (str): Bold uppercase row header descriptor text.

        Returns:
            A tuple pairing the wrapping widget with its descriptive label header.
        """
        group = QWidget()
        group.setStyleSheet("QWidget { background: transparent; }")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        title_label = QLabel(title.upper())
        title_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        title_label.setProperty("class", "title")
        title_label.setStyleSheet(f"QLabel[class='title'] {{ background: transparent; color: {os.environ["QTMATERIAL_PRIMARYCOLOR"]}; letter-spacing: 1px; }}")
        layout.addWidget(title_label)
        
        return (group, title_label)

    # ─────────────────────────────
    # API
    # ─────────────────────────────

    def display_image(self, image: Image | None) -> None:
        """Pushes data properties from an image file structure directly onto panel displays.

        Args:
            image (Image | None): Selected database image asset entity.
        """
        self._current_image = image

        # Masquer l'empty state
        self.empty.hide()
        
        # Afficher les sections d'info
        self.path_group.show()
        self.desc_group.show()
        self.tags_group.show()
        

        # ═══════════════════════════════════════════════════════════
        # IMAGE
        # ═══════════════════════════════════════════════════════════
        
        self.image_analysator.set_image(image)

        # ═══════════════════════════════════════════════════════════
        # TITRE
        # ═══════════════════════════════════════════════════════════
        
        self.title.setText(image.name)

        # ═══════════════════════════════════════════════════════════
        # CHEMIN
        # ═══════════════════════════════════════════════════════════
        
        self.path_label.setText(str(image.path).replace('\\', '/'))

        # ═══════════════════════════════════════════════════════════
        # DESCRIPTION
        # ═══════════════════════════════════════════════════════════
        
        if image.description:
            self.desc_label.setText(image.description)
            self.desc_group.show()
        else:
            self.desc_label.setText(tr("Aucune description"))
            self.desc_label.setStyleSheet("QLabel { background: transparent; padding: 8px; color: rgba(0,0,0,0.4); font-style: italic; }")

        # ═══════════════════════════════════════════════════════════
        # TAGS (BADGES)
        # ═══════════════════════════════════════════════════════════
        
        # Nettoyer les anciens tags
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tags = image.keywords or []
        if tags:
            # Créer un flow layout pour les badges
            for tag in tags:
                tag_badge = QLabel(tag)
                tag_badge.setFont(QFont("Segoe UI", 8))
                tag_badge.setStyleSheet(f"""
                    QLabel {{
                        background: {os.environ["QTMATERIAL_SECONDARYDARKCOLOR"]};
                        border: 1px solid {os.environ["QTMATERIAL_PRIMARYCOLOR"]};
                        border-radius: 12px;
                        padding: 4px 12px;
                    }}
                """)
                tag_badge.setFixedHeight(24)
                self.tags_layout.addWidget(tag_badge)
            
            # Spacer pour pousser à gauche
            self.tags_group.show()
        else:
            no_tags = QLabel(tr("Aucun mot-clé"))
            no_tags.setFont(QFont("Segoe UI", 9))
            no_tags.setStyleSheet("QLabel { background: transparent; color: rgba(0,0,0,0.4); font-style: italic; }")
            self.tags_layout.addWidget(no_tags)

    def _clear(self) -> None:
        """Blanks all context properties and shows the fallback unselected message prompt."""
        # Afficher l'empty state
        self.empty.show()
        
        # Masquer les sections d'info
        self.path_group.hide()
        self.desc_group.hide()
        self.tags_group.hide()

        # Réinitialiser l'image
        self.image_analysator.clear()
        
        # Réinitialiser le titre
        self.title.setText("")

    # ═══════════════════════════════════════════════════════════
    # THEME
    # ═══════════════════════════════════════════════════════════

    def _on_theme_changed(self) -> None:
        """Refreshes structural color styling rules matching system environment updates."""
        self.separator1.setStyleSheet(f"QFrame {{ background: transparent; border: none; border-top: 1px solid {os.environ["QTMATERIAL_SECONDARYLIGHTCOLOR"]}; }}")
        self.info_section.setStyleSheet(f"QWidget {{ background: {os.environ["QTMATERIAL_SECONDARYLIGHTCOLOR"]}; padding: 10px 10px 10px 10px; }}")
        self.path_title.setStyleSheet(f"QLabel[class='title'] {{ background: transparent; color: {os.environ["QTMATERIAL_PRIMARYCOLOR"]}; letter-spacing: 1px; }}")
        self.desc_title.setStyleSheet(f"QLabel[class='title'] {{ background: transparent; color: {os.environ["QTMATERIAL_PRIMARYCOLOR"]}; letter-spacing: 1px; }}")
        self.tags_title.setStyleSheet(f"QLabel[class='title'] {{ background: transparent; color: {os.environ["QTMATERIAL_PRIMARYCOLOR"]}; letter-spacing: 1px; }}")
        if hasattr(self, '_current_image'):
            self.display_image(self._current_image)
            
    # ═══════════════════════════════════════════════════════════
    # LANGUAGE
    # ═══════════════════════════════════════════════════════════

    def _on_language_changed(self, lang_code: str | None = None) -> None:
        """Forces complete translations updates across static framework interface strings.

        Args:
            lang_code (str | None): Target localization shorthand code parameter. Defaults to None.
        """
        # -----------------------------
        # Labels statiques (UI fixe)
        # -----------------------------
        self.path_title.setText(tr("Emplacement"))
        self.desc_title.setText(tr("Description"))
        self.tags_title.setText(tr("Mots-clés"))

        self.empty.setText(
            tr("Aucune image sélectionnée\n\nSélectionne une image dans la galerie\npour voir ses détails")
        )

        # -----------------------------
        # Bouton / titres dynamiques
        # -----------------------------
        if hasattr(self, "_current_image") and self._current_image:
            self._refresh_image_texts()

        # -----------------------------
        # Force repaint propre
        # -----------------------------
        self.update()
        
    def _refresh_image_texts(self) -> None:
        """Updates dictionary text attributes relying exclusively on live image fields."""
        image = self._current_image
        
        # Image analysator
        self.image_analysator._on_language_changed()

        # titre
        self.title.setText(image.name)

        # path
        self.path_label.setText(str(image.path).replace("\\", "/"))

        # description
        if image.description:
            self.desc_label.setText(image.description)
            self.desc_label.setStyleSheet("QLabel { background: transparent; }")
        else:
            self.desc_label.setText(tr("Aucune description"))
            self.desc_label.setStyleSheet(
                "QLabel { background: transparent; color: rgba(0,0,0,0.4); font-style: italic; }"
            )

        # tags texte conditionnel
        if not image.keywords:
            # on ne touche pas aux widgets, juste texte "aucun mot-clé"
            if self.tags_layout.count() == 1:
                w = self.tags_layout.itemAt(0).widget()
                if isinstance(w, QLabel):
                    w.setText(tr("Aucun mot-clé"))