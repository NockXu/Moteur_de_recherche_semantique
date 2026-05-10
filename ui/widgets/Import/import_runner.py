import threading
from typing import Callable, Optional, List

from ui.widgets.Import.import_service import ImportService
from common.Image_Classes.Image import Image
from common.Dataset_Classes.Dataset import Dataset
from common.Dataset_Classes.DatasetRepository import DatasetRepository


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

            datasets: List[Dataset] = self.service.dataset_repo.get_all()
            images_to_save: List[Image] = []

            for i, image in enumerate(images):
                if not self._running:
                    on_progress("Import cancelled")
                    return

                # Résoudre le chemin de l'image
                final_path = self.service.resolve_path(image)

                if not final_path:
                    on_progress(f"Skip {image.name}")
                    continue

                # Mettre à jour le chemin de l'image
                image.path = final_path

                # Mettre à jour le Dataset (recherche dans la liste pré-chargée)
                dataset = next((d for d in datasets if d.name == image.dataset_name), None)
                if dataset:
                    image.dataset_id = dataset.id

                images_to_save.append(image)

            on_progress(f"Traitement fini passage à la sauvegarde en bdd")

            # Sauvegarder l'image
            BATCH_SIZE = 1000
            for i in range(0, len(images_to_save), BATCH_SIZE):
                batch = images_to_save[i:i+BATCH_SIZE]
                success_images += self.service.image_repo.save_many_images(batch)
                on_progress(f"{success_images}/{total_images}")

            on_done(success_images, total_images)

            self._running = False

        self._thread = threading.Thread(target=task, daemon=True)
        self._thread.start()

    # -----------------------
    # CANCEL
    # -----------------------
    def cancel(self):
        self._running = False