from PIL import Image
from PyQt6.QtWidgets import QWidget, QToolButton, QSizePolicy ,QHBoxLayout, QVBoxLayout, QPushButton, QFileDialog
from PyQt6.QtCore import QPropertyAnimation, Qt
from .Sam3Widget import Sam3Widget
from .ImageView import ImageView

from common.Image_Classes.Image import Image
from common.Dataset_Classes.Dataset import Dataset

class ImageAnalysator(QWidget):
    def __init__(self, image: Image = None, theme_changed=None):
        super().__init__()

        self.image_path = image.path if image else None
        if self.image_path is None:
            self.show_loader_bar = True
        else:
            self.show_loader_bar = False

        self._init_ui()

        if self.image_path and self.image_path != "none":
            self.set_image(image)
        else:
            if __name__ == "__main__":
                image = Image("../Test_SAM/saber_high_resolution.jpg", Dataset(0, "test"))
                self.set_image(image)

        self.sam3_widget.prompt_selected.connect(self.on_prompt_selected)
        self.sam3_widget.results_displayed.connect(self.image_view.set_active_results)

    def set_image(self, image: Image):
        self.image_path = image.path
        self.image_view.setImage(image.path)
        self.image_view.updateScaledPixmap()
        self.sam3_widget.set_image(image)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.setMinimumWidth(400)

        # IMAGE (fixe)
        self.image_view = ImageView()
        self.image_view.setFixedHeight(200)
        self.layout.addWidget(self.image_view, stretch=0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # bouton toggle
        self.sam3_btn = QPushButton("Afficher SAM3 ▼")
        self.sam3_btn.setCheckable(True)
        self.sam3_btn.clicked.connect(self.toggle_sam3)
        self.layout.addWidget(self.sam3_btn)

        # SAM3 (créé mais pas ajouté)
        self.sam3_widget = Sam3Widget()
        self.sam3_visible = False

    def toggle_sam3(self):
        if not self.sam3_visible:
            self.layout.addWidget(self.sam3_widget, stretch=1)
            self.sam3_btn.setText("Masquer SAM3 ▲")
            self.sam3_visible = True
        else:
            self.layout.removeWidget(self.sam3_widget)
            self.sam3_widget.setParent(None)
            self.sam3_btn.setText("Afficher SAM3 ▼")
            self.sam3_visible = False

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir une image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)"
        )

        if path:
            self.set_image(Image(path, Dataset(0, "default")))

    def on_prompt_selected(self, data):
        boxes = data.get("boxes", [])
        labels = data.get("labels", [])

        self.image_view.load_boxes(boxes, labels)

    def clear(self):
        self.image_view.clear_results()
        self.image_view.set_active_results([{}])
        self.sam3_widget._clear_local_results()

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = ImageAnalysator()
    window.show()
    sys.exit(app.exec())
