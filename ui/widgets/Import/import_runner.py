import threading
from typing import Callable, Optional

from ui.widgets.Import.import_service import ImportService
from common.Image_Classes.Image import Image


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
                data = self.service.load_file(file_path)
                images = data["images"]
                total_images = len(images)
                success_images = 0

                datasets = self.service.configs
                total_datasets = len(datasets)
                success_datasets = 0

                on_progress(f"Start import: {total_datasets} datasets")

                for dataset in datasets:
                    if not self._running:
                        on_progress("Import cancelled")
                        return

                    try:
                        # Sauvegarder le dataset
                        dataset_obj = self.service.dataset_repo.create(dataset["name"])

                        if dataset_obj is not None:
                            success_datasets += 1

                        on_progress(f"{success_datasets}/{total_datasets} - {dataset['name']}")

                    except Exception as e:
                        on_error(str(e))

                on_progress(f"Start import: {total_images} images")

                for i, image in enumerate(images):
                    if not self._running:
                        on_progress("Import cancelled")
                        return

                    try:
                        # Résoudre le chemin de l'image
                        final_path = self.service.resolve_path(image)

                        if not final_path:
                            on_progress(f"Skip {image.name}")
                            continue

                        # Mettre à jour le chemin de l'image
                        image.path = final_path

                        # Mettre à joue le Dataset
                        dataset = self.service.dataset_repo.get_by_name(image.dataset_name)
                        image.dataset_id = dataset.id

                        # Sauvegarder l'image
                        ok = self.service.image_repo.save_image(image)

                        if ok:
                            success_images += 1

                        on_progress(f"{i+1}/{total_images} - {image.name}")

                    except Exception as e:
                        on_error(str(e))

                on_done(success_images, total_images)

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