"""
Suite de tests pytest pour le moteur de recherche sémantique d'images.

Structure attendue du projet :
    Moteur_de_recherche_semantique/
    ├── vision/
    │   ├── ollama_wrapper.py
    │   └── ImageProcessor.py
    ├── index/
    │   ├── image.py
    │   └── vectResearch.py
    ├── embedding/
    │   └── embed.py
    ├── pytest.ini
    └── Test/
        ├── conftest.py
        └── test_semantic_engine.py  ← ce fichier

Usage :
    python -m pytest Test/test_semantic_engine.py -v
"""
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
VISION_MODEL    = "qwen2.5vl:7b"

# Chemins relatifs dynamiques depuis la racine du projet
PROJECT_ROOT = Path(__file__).parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset" / "test"
STORAGE_DIR = PROJECT_ROOT / "storage"

TEST_IMAGES = [
    DATASET_DIR / "weezer.png",
    DATASET_DIR / "weezer.jpg",
    DATASET_DIR / "weezer.jpeg",
    DATASET_DIR / "weezer.webp",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def ollama_wrapper():
    from vision.ollama_wrapper import OllamaWrapper
    return OllamaWrapper(base_url=OLLAMA_BASE_URL, timeout_s=300)


@pytest.fixture(scope="session")
def check_ollama(ollama_wrapper):
    """
    Fixture de garde pour les tests d'intégration.
    Skip le test au moment de l'exécution si Ollama est inaccessible,
    contrairement à skipif qui évalue la condition au chargement du fichier.
    """
    if not ollama_wrapper.is_server_running():
        pytest.skip("Serveur Ollama inaccessible — tests d'intégration ignorés")


@pytest.fixture(scope="session")
def image_processor(ollama_wrapper):
    from vision.ImageProcessor import ImageProcessor
    return ImageProcessor(ollama_wrapper, VISION_MODEL)


@pytest.fixture
def sample_image(tmp_path):
    """Image 1x1 pixel PNG valide pour les tests unitaires (sans Ollama)."""
    from index.image import Image
    png_bytes = bytes([
        0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A,
        0x00,0x00,0x00,0x0D,0x49,0x48,0x44,0x52,
        0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,
        0x08,0x02,0x00,0x00,0x00,0x90,0x77,0x53,
        0xDE,0x00,0x00,0x00,0x0C,0x49,0x44,0x41,
        0x54,0x08,0xD7,0x63,0xF8,0xCF,0xC0,0x00,
        0x00,0x00,0x02,0x00,0x01,0xE2,0x21,0xBC,
        0x33,0x00,0x00,0x00,0x00,0x49,0x45,0x4E,
        0x44,0xAE,0x42,0x60,0x82,
    ])
    img_path = tmp_path / "test_pixel.png"
    img_path.write_bytes(png_bytes)
    return Image(path=str(img_path), description="", keywords=[], embedding=[])


@pytest.fixture
def mock_wrapper():
    """Wrapper Ollama entièrement mocké — aucun appel réseau."""
    from vision.ollama_wrapper import OllamaGenerateResult
    wrapper = MagicMock()
    wrapper.generate_with_image.return_value = OllamaGenerateResult(
        response="Un groupe de jeunes musiciens pose devant un fond bleu uni.",
        model=VISION_MODEL,
        done=True,
    )
    wrapper.embed.return_value = [0.1] * 768
    return wrapper


# ---------------------------------------------------------------------------
# BLOC 1 — Tests unitaires (sans Ollama)
# ---------------------------------------------------------------------------

class TestOllamaWrapperUnit:
    """Tests de la logique interne du wrapper sans appel réseau."""

    def test_parse_host_port_standard(self):
        from vision.ollama_wrapper import OllamaWrapper
        w = OllamaWrapper(base_url="http://192.168.1.10:11434")
        assert w._parse_host_port() == ("192.168.1.10", 11434)

    def test_parse_host_port_no_port(self):
        from vision.ollama_wrapper import OllamaWrapper
        w = OllamaWrapper(base_url="http://localhost")
        host, port = w._parse_host_port()
        assert host == "localhost"
        assert port == 11434

    def test_base_url_trailing_slash_stripped(self):
        from vision.ollama_wrapper import OllamaWrapper
        w = OllamaWrapper(base_url="http://localhost:11434/")
        assert not w._base_url.endswith("/")

    def test_generate_result_is_frozen(self):
        from vision.ollama_wrapper import OllamaGenerateResult
        result = OllamaGenerateResult(response="test")
        with pytest.raises((AttributeError, TypeError)):
            result.response = "autre"


class TestImageProcessorUnit:
    """Tests d'ImageProcessor avec un wrapper mocké."""

    def test_description_populates_field(self, mock_wrapper, sample_image):
        from vision.ImageProcessor import ImageProcessor
        processor = ImageProcessor(mock_wrapper, VISION_MODEL)
        processor.ImageToDescription(sample_image)
        assert sample_image.description
        assert len(sample_image.description) > 10

    def test_keywords_returns_list(self, mock_wrapper, sample_image):
        from vision.ollama_wrapper import OllamaGenerateResult
        from vision.ImageProcessor import ImageProcessor
        mock_wrapper.generate_with_image.return_value = OllamaGenerateResult(
            response="rock, groupe, musique, album, bleu, années 90",
            model=VISION_MODEL, done=True,
        )
        processor = ImageProcessor(mock_wrapper, VISION_MODEL)
        processor.ImageToKeywords(sample_image)
        assert isinstance(sample_image.keywords, list)
        assert len(sample_image.keywords) >= 1

    def test_keywords_no_duplicates(self, mock_wrapper, sample_image):
        from vision.ollama_wrapper import OllamaGenerateResult
        from vision.ImageProcessor import ImageProcessor
        mock_wrapper.generate_with_image.return_value = OllamaGenerateResult(
            response="rock, rock, musique, musique, album",
            model=VISION_MODEL, done=True,
        )
        processor = ImageProcessor(mock_wrapper, VISION_MODEL)
        processor.ImageToKeywords(sample_image)
        assert len(sample_image.keywords) == len(set(sample_image.keywords))

    def test_keywords_filters_long_phrases(self, mock_wrapper, sample_image):
        from vision.ollama_wrapper import OllamaGenerateResult
        from vision.ImageProcessor import ImageProcessor
        mock_wrapper.generate_with_image.return_value = OllamaGenerateResult(
            response="rock, groupe de rock alternatif américain, musique",
            model=VISION_MODEL, done=True,
        )
        processor = ImageProcessor(mock_wrapper, VISION_MODEL)
        processor.ImageToKeywords(sample_image)
        for kw in sample_image.keywords:
            assert len(kw.split()) <= 2, f"Mot-clé trop long : '{kw}'"

    def test_description_error_raises_runtime(self, sample_image):
        from vision.ImageProcessor import ImageProcessor
        bad_wrapper = MagicMock()
        bad_wrapper.generate_with_image.side_effect = ConnectionError("timeout")
        processor = ImageProcessor(bad_wrapper, VISION_MODEL)
        with pytest.raises(RuntimeError, match="Erreur lors du traitement"):
            processor.ImageToDescription(sample_image)


class TestImageModel:
    """Tests sur le modèle Image."""

    def test_image_has_name(self, sample_image):
        assert sample_image.name

    def test_image_path_exists(self, sample_image):
        assert Path(sample_image.path).exists()

    def test_image_description_initially_empty(self, sample_image):
        assert sample_image.description == ""

    def test_image_keywords_initially_empty(self, sample_image):
        assert sample_image.keywords == []

    def test_image_embedding_initially_empty(self, sample_image):
        assert sample_image.embedding == []

    def test_image_rejects_missing_file(self, tmp_path):
        from index.image import Image
        with pytest.raises(FileNotFoundError):
            Image(path=str(tmp_path / "inexistant.png"))


class TestCosineSimilarity:
    """Tests unitaires du calcul de similarité cosinus."""

    def test_identical_vectors(self):
        from embedding.embed import cosine_similarity
        v = [1.0, 0.0, 0.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        from embedding.embed import cosine_similarity
        assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        from embedding.embed import cosine_similarity
        assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self):
        from embedding.embed import cosine_similarity
        assert cosine_similarity([0, 0, 0], [1, 2, 3]) == pytest.approx(0.0)

    def test_symmetry(self):
        from embedding.embed import cosine_similarity
        a, b = [1, 2, 3], [4, 5, 6]
        assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(b, a))


# ---------------------------------------------------------------------------
# BLOC 2 — Tests d'intégration (nécessitent Ollama)
# ---------------------------------------------------------------------------

class TestOllamaConnection:

    @pytest.mark.integration
    def test_server_is_running(self, check_ollama, ollama_wrapper):
        assert ollama_wrapper.is_server_running()

    @pytest.mark.integration
    def test_get_version_returns_string(self, check_ollama, ollama_wrapper):
        version = ollama_wrapper.get_version()
        assert isinstance(version, str) and len(version) > 0

    @pytest.mark.integration
    def test_list_models_returns_list(self, check_ollama, ollama_wrapper):
        assert isinstance(ollama_wrapper.list_models(), list)

    @pytest.mark.integration
    def test_vision_model_available(self, check_ollama, ollama_wrapper):
        names = [m.name for m in ollama_wrapper.list_models()]
        assert any(VISION_MODEL in n for n in names), (
            f"Modèle {VISION_MODEL} introuvable. Disponibles : {names}"
        )


class TestImageProcessingIntegration:

    @pytest.fixture(scope="class")
    def real_image(self):
        from index.image import Image
        for path in TEST_IMAGES:
            if path.exists():
                return Image(path=str(path), description="", keywords=[], embedding=[])
        pytest.skip("Aucune image de test disponible dans le dataset")

    @pytest.mark.integration
    def test_description_not_empty(self, check_ollama, image_processor, real_image):
        image_processor.ImageToDescription(real_image)
        assert real_image.description and len(real_image.description) > 50

    @pytest.mark.integration
    def test_description_word_count(self, check_ollama, image_processor, real_image):
        if not real_image.description:
            image_processor.ImageToDescription(real_image)
        word_count = len(real_image.description.split())
        assert 50 <= word_count <= 300, f"{word_count} mots (attendu 50-300)"

    @pytest.mark.integration
    def test_keywords_are_list(self, check_ollama, image_processor, real_image):
        image_processor.ImageToKeywords(real_image)
        assert isinstance(real_image.keywords, list)

    @pytest.mark.integration
    def test_keywords_count_in_range(self, check_ollama, image_processor, real_image):
        if not real_image.keywords:
            image_processor.ImageToKeywords(real_image)
        count = len(real_image.keywords)
        assert 5 <= count <= 30, f"{count} mots-clés (attendu 5-30)"

    @pytest.mark.integration
    def test_keywords_no_long_phrases(self, check_ollama, image_processor, real_image):
        if not real_image.keywords:
            image_processor.ImageToKeywords(real_image)
        long_kw = [kw for kw in real_image.keywords if len(kw.split()) > 2]
        assert not long_kw, f"Mots-clés trop longs : {long_kw}"

    @pytest.mark.integration
    def test_keywords_no_duplicates(self, check_ollama, image_processor, real_image):
        if not real_image.keywords:
            image_processor.ImageToKeywords(real_image)
        assert len(real_image.keywords) == len(set(real_image.keywords))

    @pytest.mark.integration
    def test_embedding_is_float_vector(self, check_ollama, ollama_wrapper, real_image):
        from embedding.embed import TextToEmbedding
        if not real_image.description:
            pytest.skip("Description manquante")
        TextToEmbedding(ollama_wrapper, real_image)
        assert isinstance(real_image.embedding, list)
        assert len(real_image.embedding) > 0
        assert all(isinstance(x, float) for x in real_image.embedding)


class TestVectorSearchIntegration:

    @pytest.mark.integration
    def test_search_returns_results(self, check_ollama, ollama_wrapper):
        from embedding.embed import inputToEmbedding
        from index.vectResearch import vectresearch
        if not STORAGE_DIR.exists() or not list(STORAGE_DIR.glob("*.json")):
            pytest.skip("Storage vide — indexez d'abord des images")
        results = vectresearch(
            inputToEmbedding(ollama_wrapper, "groupe de musique"),
            str(STORAGE_DIR)
        )
        assert isinstance(results, list) and len(results) > 0

    @pytest.mark.integration
    def test_search_results_sorted_descending(self, check_ollama, ollama_wrapper):
        from embedding.embed import inputToEmbedding
        from index.vectResearch import vectresearch
        if not STORAGE_DIR.exists() or not list(STORAGE_DIR.glob("*.json")):
            pytest.skip("Storage vide")
        results = vectresearch(
            inputToEmbedding(ollama_wrapper, "musique rock"),
            str(STORAGE_DIR)
        )
        if len(results) < 2:
            pytest.skip("Pas assez de résultats")
        sims = [r["similarity"] for r in results]
        assert sims == sorted(sims, reverse=True)

    @pytest.mark.integration
    def test_similarity_in_valid_range(self, check_ollama, ollama_wrapper):
        from embedding.embed import inputToEmbedding
        from index.vectResearch import vectresearch
        if not STORAGE_DIR.exists() or not list(STORAGE_DIR.glob("*.json")):
            pytest.skip("Storage vide")
        results = vectresearch(
            inputToEmbedding(ollama_wrapper, "photo"),
            str(STORAGE_DIR)
        )
        for r in results:
            assert -1.0 <= r["similarity"] <= 1.0


# ---------------------------------------------------------------------------
# BLOC 3 — Tests de storage (sans Ollama)
# ---------------------------------------------------------------------------

class TestStorage:

    def test_to_dict_contains_required_fields(self, sample_image):
        sample_image.description = "Une image de test."
        sample_image.keywords   = ["test", "image"]
        sample_image.embedding  = [0.1, 0.2, 0.3]
        data = sample_image.to_dict()
        for field in ("description", "keywords", "embedding", "path", "name"):
            assert field in data, f"Champ manquant : '{field}'"

    def test_round_trip_from_dict(self, sample_image):
        from index.image import Image
        sample_image.description = "Round-trip test."
        sample_image.keywords   = ["a", "b"]
        sample_image.embedding  = [1.0, 2.0]
        restored = Image.from_dict(sample_image.to_dict())
        assert restored.description == sample_image.description
        assert restored.keywords    == sample_image.keywords
        assert restored.embedding   == sample_image.embedding

    def test_save_as_json_creates_file(self, sample_image, tmp_path):
        sample_image.description = "Test sauvegarde."
        sample_image.keywords   = ["save", "test"]
        sample_image.embedding  = [0.5]

        # Utiliser save_as_json avec un chemin dans le répertoire temporaire
        out_path = tmp_path / "test_image.json"
        sample_image.save_as_json(str(out_path))

        assert out_path.exists()
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["description"] == "Test sauvegarde."
        assert data["keywords"] == ["save", "test"]
        assert data["embedding"] == [0.5]