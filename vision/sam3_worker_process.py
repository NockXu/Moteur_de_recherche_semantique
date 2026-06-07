import os
import pickle
import struct
import sys
import traceback
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from common.SAM3BatchProcessor import SAM3BatchProcessor



def _write_message(message: dict):
    payload = pickle.dumps(message, protocol=pickle.HIGHEST_PROTOCOL)
    os.write(1, struct.pack(">I", len(payload)) + payload)


def _read_exact(size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = sys.stdin.buffer.read(size - len(data))
        if not chunk:
            raise EOFError
        data.extend(chunk)
    return bytes(data)


def _read_message() -> dict:
    header = _read_exact(4)
    size = struct.unpack(">I", header)[0]
    return pickle.loads(_read_exact(size))


def _to_cpu(value):
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


def main():
    # Keep stdout reserved for the binary protocol. Any normal print from SAM3
    # dependencies is redirected to stderr so it cannot corrupt frames.
    sys.stdout = sys.stderr

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

    while True:
        try:
            message = _read_message()
        except EOFError:
            return

        if message.get("type") == "shutdown":
            return

        if message.get("type") != "process":
            continue

        job_id = message["job_id"]
        image_path = message["image_path"]
        prompts = message["prompts"]

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


if __name__ == "__main__":
    main()
