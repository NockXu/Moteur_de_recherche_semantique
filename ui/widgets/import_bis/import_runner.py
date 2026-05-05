import threading
from typing import Callable, Optional

from ui.widgets.import_bis.import_service import ImportService


class ImportRunner:
    """
    Wrapper async propre autour de ImportService
    (aucune dépendance PyQt ici)
    """

    def __init__(self, service: ImportService):
        self.service = service
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # -----------------------
    # RUN ASYNC
    # -----------------------
    def run(
        self,
        file_path: str,
        on_progress: Callable[[str], None],
        on_done: Callable[[int, int], None],
        on_error: Callable[[str], None]
    ):
        if self._running:
            on_error("Import already running")
            return

        self._running = True

        def task():
            try:
                images = self.service.load_file(file_path)
                total = len(images)
                success = 0

                on_progress(f"Start import: {total} images")

                for i, img in enumerate(images):
                    if not self._running:
                        on_progress("Import cancelled")
                        return

                    try:
                        dataset, path = self.service.strategy.resolve(
                            img.filename,
                            img.__dict__
                        )

                        if not dataset or not path:
                            on_progress(f"Skip {img.filename}")
                            continue

                        image = self.service._build_image(img, dataset, path)
                        ok = self.service.repo.save_image(image)

                        if ok:
                            success += 1

                        on_progress(f"{i+1}/{total} - {img.filename}")

                    except Exception as e:
                        on_error(str(e))

                on_done(success, total)

            except Exception as e:
                on_error(str(e))

            finally:
                self._running = False

        self._thread = threading.Thread(target=task, daemon=True)
        self._thread.start()

    # -----------------------
    # CANCEL
    # -----------------------
    def cancel(self):
        self._running = False