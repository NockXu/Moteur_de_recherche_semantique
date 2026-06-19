import os
import pickle
import queue
import struct
import sys
import threading
import traceback
from collections import deque
from pathlib import Path
import msvcrt

from typing import Any, Dict, List, Optional
from collections.abc import Generator

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from common.SAM3BatchProcessor import SAM3BatchProcessor


def _write_message(message: dict) -> None:
    """Serialize a message dictionary using pickle and write it to standard output.

    The message is prefixed with a 4-byte big-endian unsigned integer indicating 
    the total size of the binary payload.

    Args:
        message (dict):
            The message payload dictionary to send.

    """
    payload = pickle.dumps(message, protocol=pickle.HIGHEST_PROTOCOL)
    os.write(1, struct.pack(">I", len(payload)) + payload)


def _read_exact(fd, size: int) -> bytes:
    """Read an exact number of bytes from a generic binary stream block.

    This function blocks and loops internally until the requested byte size 
    is successfully assembled.

    Args:
        fd (io.BufferedReader):
            The binary input stream source.
        size (int):
            The explicit number of bytes to retrieve.

    Returns:
        The exact sequence of requested bytes.

    """
    data = bytearray()
    while len(data) < size:
        chunk = fd.read(size - len(data))
        if not chunk:
            raise EOFError
        data.extend(chunk)
    return bytes(data)


def _reader_thread(fd, msg_queue: queue.Queue) -> None:
    """Dedicated background reader thread managing standard input streams.

    This worker monitors binary stream payloads natively across Windows and Unix 
    architectures, unpacks structural packets, and moves them safely into a shared queue.

    Args:
        fd (io.BufferedReader):
            The monitored standard input buffer frame stream.
        msg_queue (queue.Queue):
            The shared thread-safe queue holding processed inbound commands.

    """
    try:
        while True:
            header = _read_exact(fd, 4)
            size = struct.unpack(">I", header)[0]
            payload = _read_exact(fd, size)
            msg_queue.put(pickle.loads(payload))
    except EOFError:
        msg_queue.put(None)  # sentinelle de fin
    except Exception as exc:
        msg_queue.put({"type": "error", "_reader": str(exc)})


def _to_cpu(value: Any) -> Any:
    """Recursively move any layout nested PyTorch tensors back to standard CPU memory space.

    This utility method ensures multi-dimensional data arrays can be serialized 
    via pickle smoothly without hardware backend dependency errors.

    Args:
        value (Any):
            A generic composite collection wrapper or a standalone PyTorch tensor array.

    Returns:
        The detached CPU-mapped tensor equivalent or equivalent nested structures.

    """
    try:
        import torch
    except Exception:
        torch = None

    if torch is not None and isinstance(value, torch.Tensor):
        return value.detach().cpu()

    if isinstance(value, list):
        return [_to_cpu(item) for item in value]

    if isinstance(value, tuple):
        return tuple(_to_cpu(item) for item in value)

    if isinstance(value, dict):
        return {key: _to_cpu(item) for key, item in value.items()}

    return value


def main() -> None:
    """Main entry point managing sub-process communication and image batch processing.

    This method configures platform-specific binary stream endpoints, initializes 
    the underlying SAM3 processing context, and balances arriving job execution cycles 
    against cancellation requests.
    """
    # Keep stdout reserved for the binary protocol. Any normal print from SAM3
    # dependencies is redirected to stderr so it cannot corrupt frames.
    sys.stdout = sys.stderr

    # Sur Windows, stdin/stdout doivent être en mode binaire
    if sys.platform == "win32":
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(1, os.O_BINARY)  # stdout fd

    sam3_root = sys.argv[1]
    confidence = float(sys.argv[2])
    device = sys.argv[3]

    try:
        processor = SAM3BatchProcessor(sam3_root, confidence, device)
        _write_message({"type": "ready"})
    except Exception as exc:
        _write_message({
            "type": "load_error",
            "error": f"{exc}\n{traceback.format_exc()}",
        })
        return

    stdin_fd = sys.stdin.buffer
    msg_queue: queue.Queue = queue.Queue()
    t = threading.Thread(target=_reader_thread, args=(stdin_fd, msg_queue), daemon=True)
    t.start()

    job_queue: deque[dict] = deque()
    cancelled: set[str] = set()

    def drain_msg_queue() -> Generator[dict, None, bool]:
        """Drain all buffered stream commands from the message queue non-blockingly.

        Yields:
            Incoming query message dictionaries collected from the pipeline.

        Returns:
            False if an EOF sentinel block was matched, True otherwise.

        """
        while True:
            try:
                msg = msg_queue.get_nowait()
            except queue.Empty:
                break
            if msg is None:
                return False  # EOF
            yield msg
        return True

    while True:
        # ── Attendre au moins un message ────────────────────────────────────
        if not job_queue:
            # Pas de travail : attente bloquante
            msg = msg_queue.get()
            if msg is None:
                return  # EOF
            incoming = [msg]
        else:
            incoming = []

        # Drainer tout ce qui est déjà disponible
        while True:
            try:
                msg = msg_queue.get_nowait()
            except queue.Empty:
                break
            if msg is None:
                return  # EOF
            incoming.append(msg)

        for msg in incoming:
            t_msg = msg.get("type")
            if t_msg == "shutdown":
                return
            elif t_msg == "cancel_all":
                for queued_msg in job_queue:
                    cancelled.add(queued_msg["job_id"])
                job_queue.clear()
                _write_message({"type": "cancelled"})
            elif t_msg == "process":
                job_queue.append(msg)

        # ── Traiter le prochain job non-annulé ───────────────────────────────
        while job_queue:
            job = job_queue.popleft()
            job_id = job["job_id"]

            if job_id in cancelled:
                cancelled.discard(job_id)
                continue

            image_path = job["image_path"]
            prompts = job["prompts"]

            try:
                results = processor.process_prompt_dataset(image_path, prompts)
                _write_message({
                    "type": "result",
                    "job_id": job_id,
                    "image_path": image_path,
                    "results": _to_cpu(results),
                })
            except Exception as exc:
                _write_message({
                    "type": "error",
                    "job_id": job_id,
                    "error": f"{exc}\n{traceback.format_exc()}",
                })

            # Après chaque image, drainer les messages entrants
            # (notamment un cancel_all arrivé pendant l'inférence)
            while True:
                try:
                    msg = msg_queue.get_nowait()
                except queue.Empty:
                    break
                if msg is None:
                    return
                t_msg = msg.get("type")
                if t_msg == "shutdown":
                    return
                elif t_msg == "cancel_all":
                    for queued_msg in job_queue:
                        cancelled.add(queued_msg["job_id"])
                    job_queue.clear()
                    _write_message({"type": "cancelled"})
                elif t_msg == "process":
                    job_queue.append(msg)

            break  # Retour à la boucle principale


if __name__ == "__main__":
    main()