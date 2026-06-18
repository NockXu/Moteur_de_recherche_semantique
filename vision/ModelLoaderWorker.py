from PyQt6.QtCore import QObject, QThread, pyqtSignal

class ModelLoaderWorker(QObject):
    """Worker thread responsible for asynchronous initialization of the SAM3 model.

    This class offloads the heavy model instantiation process into a separate execution 
    thread context to keep the user interface responsive.

    Signals:
        finished (object): 
            Emitted when model initialization completes, passing the constructed 
            SAM3BatchProcessor instance.
    """

    finished = pyqtSignal(object)

    def __init__(self, sam3_root, confidence, device):
        super().__init__()
        self.sam3_root = sam3_root
        self.confidence = confidence
        self.device = device

    def run(self):
        """Execute the model loading logic within the worker thread context.

        This method imports the batch processor lazily, instantiates the SAM3 heavy 
        backend configuration, and broadcasts the completed object via the finished signal.
        """
        from common.SAM3BatchProcessor import SAM3BatchProcessor

        model = SAM3BatchProcessor(
            self.sam3_root,
            self.confidence,
            self.device
        )

        self.finished.emit(model)