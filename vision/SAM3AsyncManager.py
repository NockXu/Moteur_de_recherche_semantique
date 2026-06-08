import os
import pickle
import struct
import sys
from uuid import uuid4

from PyQt6.QtCore import QObject, QProcess, pyqtSignal


class SharedSAM3Manager(QObject):
    ready = pyqtSignal()
    result = pyqtSignal(str, str, object)
    error = pyqtSignal(str, str)

    def __init__(
        self,
        sam3_root: str = "./vision/sam3/sam3",
        confidence: float = 0.5,
        device: str = "cuda",
    ):
        super().__init__()
        self.sam3_root = sam3_root
        self.confidence = confidence
        self.device = device
        self._is_ready = False
        self._out_buffer = bytearray()
        self._pending_jobs: dict[str, str] = {}

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._process.readyReadStandardOutput.connect(self._read_stdout)
        self._process.readyReadStandardError.connect(self._read_stderr)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_process_error)
        self._process.setWorkingDirectory(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        self._start_process()

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    def process_image(self, image_path: str, prompts: list[dict]) -> str:
        job_id = uuid4().hex
        self._pending_jobs[job_id] = str(image_path)

        if self._process.state() == QProcess.ProcessState.NotRunning:
            self._start_process()

        if not self._is_ready:
            self.error.emit(job_id, "Le modèle SAM3 n'est pas encore prêt.")
            self._pending_jobs.pop(job_id, None)
            return job_id

        self._write_message({
            "type": "process",
            "job_id": job_id,
            "image_path": str(image_path),
            "prompts": prompts,
        })
        return job_id

    def cancel_all(self):
        """Annule tous les jobs en cours en killant et relançant le process."""
        jobs = list(self._pending_jobs.keys())
        self._pending_jobs.clear()
        self._is_ready = False

        if self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
            self._process.waitForFinished(500)

        for job_id in jobs:
            self.error.emit(job_id, "Annulé")

        self._out_buffer.clear()
        self._start_process()

    def shutdown(self):
        if self._process.state() == QProcess.ProcessState.NotRunning:
            return

        self._write_message({"type": "shutdown"})
        self._process.waitForFinished(1000)
        if self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()

    def _start_process(self):
        worker_path = os.path.join(os.path.dirname(__file__), "sam3_worker_process.py")
        self._process.start(
            sys.executable,
            [worker_path, self.sam3_root, str(self.confidence), self.device],
        )

    def _write_message(self, message: dict):
        payload = pickle.dumps(message, protocol=pickle.HIGHEST_PROTOCOL)
        frame = struct.pack(">I", len(payload)) + payload
        self._process.write(frame)

    def _read_stdout(self):
        self._out_buffer.extend(bytes(self._process.readAllStandardOutput()))

        while len(self._out_buffer) >= 4:
            size = struct.unpack(">I", self._out_buffer[:4])[0]
            if len(self._out_buffer) < 4 + size:
                return

            payload = bytes(self._out_buffer[4:4 + size])
            del self._out_buffer[:4 + size]

            try:
                message = pickle.loads(payload)
            except Exception as exc:
                self.error.emit("", f"Réponse SAM3 illisible: {exc}")
                continue

            self._handle_message(message)

    def _read_stderr(self):
        data = bytes(self._process.readAllStandardError()).decode(
            "utf-8", errors="replace"
        )
        if data.strip():
            print(f"[SAM3 worker] {data}", end="")

    def _handle_message(self, message: dict):
        message_type = message.get("type")

        if message_type == "ready":
            self._is_ready = True
            self.ready.emit()
            return

        if message_type == "load_error":
            self.error.emit("", message.get("error", "Chargement SAM3 impossible."))
            return

        if message_type == "result":
            job_id = message.get("job_id", "")
            self._pending_jobs.pop(job_id, None)
            self.result.emit(
                job_id,
                message.get("image_path", ""),
                message.get("results"),
            )
            return

        if message_type == "error":
            job_id = message.get("job_id", "")
            self._pending_jobs.pop(job_id, None)
            self.error.emit(job_id, message.get("error", "Erreur SAM3 inconnue."))

    def _on_process_error(self, process_error):
        self._is_ready = False
        message = f"Processus SAM3 indisponible: {process_error.name}"
        for job_id in list(self._pending_jobs):
            self.error.emit(job_id, message)
        self._pending_jobs.clear()

    def _on_finished(self, exit_code: int, exit_status):
        was_ready = self._is_ready
        self._is_ready = False

        if not was_ready and not self._pending_jobs:
            return

        message = (
            f"Le processus SAM3 s'est arrêté "
            f"(code={exit_code}, status={exit_status.name})."
        )
        for job_id in list(self._pending_jobs):
            self.error.emit(job_id, message)
        self._pending_jobs.clear()


_shared_sam3_manager: SharedSAM3Manager | None = None


def get_sam3_manager(
    sam3_root: str = "./vision/sam3/sam3",
    confidence: float = 0.5,
    device: str = "cuda",
) -> SharedSAM3Manager:
    global _shared_sam3_manager

    if _shared_sam3_manager is None:
        _shared_sam3_manager = SharedSAM3Manager(sam3_root, confidence, device)

    return _shared_sam3_manager