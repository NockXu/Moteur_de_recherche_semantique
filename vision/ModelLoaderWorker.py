from PyQt6.QtCore import QObject, QThread, pyqtSignal

class ModelLoaderWorker(QObject):
    finished = pyqtSignal(object)

    def __init__(self, sam3_root, confidence, device):
        super().__init__()
        self.sam3_root = sam3_root
        self.confidence = confidence
        self.device = device

    def run(self):
        from common.SAM3BatchProcessor import SAM3BatchProcessor

        model = SAM3BatchProcessor(
            self.sam3_root,
            self.confidence,
            self.device
        )

        self.finished.emit(model)