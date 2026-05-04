from pathlib import Path
from typing import List, Dict, Optional, Set
from common.ImageInfo import ImageInfo, ProcessingStatus


class ImportToolModel:
    """
    Modèle de données pour l'outil d'import d'images.

    Optimisations vs version précédente :
    - Le scan du dossier ne crée PAS 41k ImageInfo immédiatement.
      On stocke seulement les Path bruts ; les ImageInfo sont instanciées
      à la demande via get_page() (lazy instantiation).
    - Un dict _cache évite de recréer les objets déjà utilisés.
    - La vérification BDD (get_all_images()) est séparée et peut être
      appelée en arrière-plan par le Controller (thread dédié).
    """

    PAGE_SIZE = 60   # widgets créés par batch dans la vue

    def __init__(self):
        self._all_paths: List[Path] = []          # chemins bruts — peu de mémoire
        self._cache: Dict[Path, ImageInfo] = {}   # ImageInfo déjà instanciées
        self._db_paths: Set[str] = set()          # chemins déjà en BDD (résolu)
        self.selected_folder: Optional[Path] = None
        self.supported_extensions = {
            '.jpg', '.jpeg', '.png', '.gif',
            '.bmp', '.tiff', '.webp',
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Scan dossier (rapide — pas de BDD, pas d'ImageInfo)
    # ─────────────────────────────────────────────────────────────────────────

    def set_folder(self, folder_path: str) -> bool:
        """
        Scanne le dossier et mémorise les Path.
        N'instancie AUCUN ImageInfo ici → retour quasi-immédiat même
        pour 40 000 fichiers.
        """
        try:
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                return False

            self.selected_folder = folder
            self._all_paths.clear()
            self._cache.clear()
            # self._db_paths est rempli séparément (voir load_db_status)

            ext = self.supported_extensions
            self._all_paths = [
                p for p in folder.rglob('*')
                if p.is_file() and p.suffix.lower() in ext
            ]
            print(f"📂 {len(self._all_paths)} images trouvées dans {folder.name}")
            return True

        except Exception as e:
            print(f"Erreur set_folder: {e}")
            return False

    def load_db_status(self):
        """
        Charge les chemins déjà présents en BDD.
        À appeler dans un QThread séparé (peut être lent sur grande BDD).
        """
        try:
            from database.DatabaseManager import DatabaseManager
            db = DatabaseManager()
            existing = db.get_all_images()
            self._db_paths = {str(img.path.resolve()) for img in existing}
            db.close_connection()
            print(f"🗄️  {len(self._db_paths)} images en BDD")
        except Exception as e:
            print(f"Erreur load_db_status: {e}")
            self._db_paths = set()

    # ─────────────────────────────────────────────────────────────────────────
    # Accès paginé (lazy)
    # ─────────────────────────────────────────────────────────────────────────

    def get_page(self, page: int) -> List[ImageInfo]:
        """
        Retourne les ImageInfo de la page `page` (0-indexé).
        Instancie et met en cache uniquement les objets de cette page.
        """
        start = page * self.PAGE_SIZE
        end   = start + self.PAGE_SIZE
        paths = self._all_paths[start:end]

        result = []
        for p in paths:
            if p not in self._cache:
                info = ImageInfo(str(p))
                if str(p.resolve()) in self._db_paths:
                    info.status      = ProcessingStatus.COMPLETED
                    info.description = "Déjà traitée (présente en base de données)"
                self._cache[p] = info
            result.append(self._cache[p])
        return result

    def get_page_count(self) -> int:
        import math
        return math.ceil(len(self._all_paths) / self.PAGE_SIZE) if self._all_paths else 0

    def get_loaded_images(self) -> List[ImageInfo]:
        """Retourne uniquement les ImageInfo déjà instanciées (pour le traitement)."""
        return list(self._cache.values())

    def get_all_images(self) -> List[ImageInfo]:
        """
        Instancie TOUTES les ImageInfo (utilisé par le ProcessingWorker).
        À n'appeler que quand l'utilisateur démarre le traitement,
        pas au chargement du dossier.
        """
        for p in self._all_paths:
            if p not in self._cache:
                info = ImageInfo(str(p))
                if str(p.resolve()) in self._db_paths:
                    info.status      = ProcessingStatus.COMPLETED
                    info.description = "Déjà traitée (présente en base de données)"
                self._cache[p] = info
        return list(self._cache.values())

    # ─────────────────────────────────────────────────────────────────────────
    # Stats (travaillent sur _all_paths + _cache)
    # ─────────────────────────────────────────────────────────────────────────

    def get_images_count(self) -> int:
        return len(self._all_paths)

    def get_images_by_status(self) -> Dict[ProcessingStatus, int]:
        counts = {s: 0 for s in ProcessingStatus}
        # Compter les images en cache (les autres sont NOT_STARTED implicitement)
        for info in self._cache.values():
            counts[info.status] += 1
        # Les non-cachées non-BDD sont toutes NOT_STARTED
        uncached_non_db = len(self._all_paths) - len(self._cache)
        counts[ProcessingStatus.NOT_STARTED] += uncached_non_db
        return counts

    def get_processed_count(self) -> int:
        done = sum(
            1 for info in self._cache.values()
            if info.status in (ProcessingStatus.COMPLETED, ProcessingStatus.ERROR)
        )
        # Les images en BDD non encore chargées en cache comptent comme COMPLETED
        uncached_db = len(self._db_paths) - sum(
            1 for p in self._cache
            if str(p.resolve()) in self._db_paths
        )
        return done + max(0, uncached_db)

    def get_completed_count(self) -> int:
        return sum(1 for i in self._cache.values() if i.status == ProcessingStatus.COMPLETED)

    def get_in_progress_count(self) -> int:
        return sum(1 for i in self._cache.values() if i.status == ProcessingStatus.IN_PROGRESS)

    def get_error_count(self) -> int:
        return sum(1 for i in self._cache.values() if i.status == ProcessingStatus.ERROR)

    # ─────────────────────────────────────────────────────────────────────────
    # Mise à jour statut
    # ─────────────────────────────────────────────────────────────────────────

    def update_image_status(
        self, image_path: str, status: ProcessingStatus,
        description: str = "", keywords: List[str] = None,
        embedding: List[float] = None, error_message: str = "",
    ):
        p = Path(image_path).resolve()
        for cached_path, info in self._cache.items():
            if cached_path.resolve() == p:
                info.update_status(
                    status=status,
                    description=description or None,
                    keywords=keywords,
                    embedding=embedding,
                    error_message=error_message or None,
                )
                return

    def get_image_info(self, image_path) -> Optional[ImageInfo]:
        p = Path(str(image_path)).resolve()
        for cached_path, info in self._cache.items():
            if cached_path.resolve() == p:
                return info
        return None

    def reset_all_status(self):
        for info in self._cache.values():
            info.reset_processing()

    def reset_in_progress_status(self):
        for info in self._cache.values():
            if info.status == ProcessingStatus.IN_PROGRESS:
                info.reset_processing()

    def reset_unprocessed_status(self):
        for info in self._cache.values():
            if not (
                info.status == ProcessingStatus.COMPLETED
                and info.description
                and "Déjà traitée" in info.description
            ):
                info.reset_processing()

    def is_processing_complete(self) -> bool:
        if not self._all_paths:
            return True
        return self.get_processed_count() >= len(self._all_paths)

    def get_processing_progress(self) -> float:
        total = len(self._all_paths)
        return (self.get_processed_count() / total) if total > 0 else 1.0

    # Stubs compatibilité
    def save_results(self, output_file=None) -> bool:
        return False

    def load_results(self, input_file=None) -> bool:
        return False