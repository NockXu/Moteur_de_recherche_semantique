from pickletools import optimize
import sys
import os
from typing import Any, Optional
from PIL import Image as PILImage
from pathlib import Path

from vision.ollama_wrapper import OllamaWrapper
from common.Image_Classes.Image import Image
from common.Dataset_Classes.Dataset import Dataset

class ImageProcessor:
    """Handles image processing and interaction with the embedding model.

    Args:
        wrapper (OllamaWrapper):
            Wrapper used to communicate with the embedding model.

        model (str):
            Name of the model used for processing images.

    """

    def __init__(self, wrapper: OllamaWrapper, model: str):
        self.wrapper = wrapper
        self.model = model

    def ImageToData(self, image: Image) -> None:
        """Generate a description and keywords in a single call.

        This function mutates the image object by setting.

            + image.description
            + image.keywords

        Args:
            image (Image):
                The image to analyze.

        Returns:
            None

        """
        try:
            prompt = """Analyse cette image et produis deux sorties distinctes optimisées pour la recherche sémantique.

Objectif :
- Une description courte et précise
- Une liste de mots-clés simples et exploitables et courte

1. DESCRIPTION :

Décris uniquement les éléments les plus importants de l'image :
1. Sujet principal.
2. Action ou texte visible.
3. Contexte.
4. Attributs visuels essentiels.

Si la limite de mots est atteinte, ignore les éléments de priorité inférieure.

Ignore les détails mineurs, l'arrière-plan non pertinent et toute supposition.

Contraintes :
- 1 à 2 phrases.
- 15 à 25 mots maximum.
- Factuel et concis.

2. KEYWORDS :

Génère une liste de mots-clés simples et variés.

Règles STRICTES :
- 5 à 8 mots-clés.
- Un seul mot par mot-clé.
- Tous différents.
- Les plus discriminants uniquement.
- Séparés par des virgules.

FORMAT DE SORTIE OBLIGATOIRE :

DESCRIPTION:
[texte]

KEYWORDS:
mot1, mot2, mot3, mot4"""

            reduced_img = self.reduce_img(image)

            result = self.wrapper.generate_with_image(
                model=self.model,
                prompt=prompt,
                image=reduced_img,
                options={"keep_alive": "10m"}
            )

            self.clean_reduce_img()

            response = result.response.strip()

            # Parsing
            if "KEYWORDS:" in response:
                desc_part, keywords_part = response.split("KEYWORDS:", 1)

                description = desc_part.replace("DESCRIPTION:", "").strip()

                keywords_raw = keywords_part.strip().replace("\n", ", ")
                keywords = [kw.strip().lower() for kw in keywords_raw.split(",") if kw.strip()]

                # cleaning
                keywords = list(dict.fromkeys(
                    kw for kw in keywords if len(kw.split()) <= 2
                ))

            else:
                # fallback (in case the model failed to follow the format)
                description = response
                keywords = []

            image.description = description
            image.keywords = keywords

        except Exception as e:
            raise RuntimeError(f"Erreur lors du traitement de l'image {image.path}: {e!s}")

    def TextToEmbedding(self, image: Image) -> None:
        """Generate an embedding from the image description and keywords.

        The embedding is built by combining the image description with its keywords
        and stored directly into the image object.

            + image.embedding

        Args:
            image (Image):
                Image instance to process.

        Returns:
            None

        Raises:
            RuntimeError:
                If embedding generation fails.

        """
        try:
            if not image.description:
                image.embedding = []
                return

            # Build text from description + keywords
            text_for_embedding = image.description

            # Add keywords if available
            if image.keywords and len(image.keywords) > 0:
                keywords_str = ", ".join(image.keywords)
                text_for_embedding += f", {keywords_str}"

            result = self.wrapper.embed(
                model="nomic-embed-text:v1.5",
                text=text_for_embedding
            )

            image.embedding = result

        except Exception as e:
            raise RuntimeError(f"Embedding error for {image.path}: {e!s}")

    def reduce_img(self, image: Image) -> str:
        """Resize and compress an image while preserving aspect ratio.

        The image is resized to fit within 1024x1024 pixels while maintaining
        its original proportions. The processed image is saved in the
        `storage/images_reduced` directory.

        Args:
            image (Image):
                Image instance containing the source file path and name.

        Returns:
            Path to the saved reduced image.

        Raises:
            ValueError:
                If the image file extension is not supported.
            OSError:
                If the image cannot be opened or saved.

        """
        max_width = 1024
        max_height = 1024

        extension = [".jpg", ".jpeg", ".png", ".webp"]

        base_dir = Path(__file__).resolve().parent

        storage_dir = base_dir.parent / "storage"
        output_dir = storage_dir / "images_reduced"

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        img_extension = Path(image.path).suffix.lower()

        if img_extension not in extension:
            raise ValueError(f"Unsupported extension: {img_extension}")

        with PILImage.open(image.path) as img:
            # Preserve aspect ratio
            img.thumbnail((max_width, max_height))

            # Save processed image
            img_path = os.path.join(output_dir, image.name)
            img.save(
                img_path,
                optimize=True,
                quality=85
            )

            return img_path

    def clean_reduce_img(self, output_dir: Path | None = None) -> None:
        """Remove all files from the reduced images directory.

        If no directory is provided, the default directory
        `storage/images_reduced` is used.

        Args:
            output_dir (Optional[Path]):
                Directory to clean. If None, the default reduced image
                storage directory is used.

        Returns:
            None

        Raises:
            OSError:
                If a file cannot be deleted.

        """
        if output_dir is None:
            base_dir = Path(__file__).resolve().parent
            storage_dir = base_dir.parent / "storage"
            output_dir = storage_dir / "images_reduced"

        if not output_dir.exists():
            return

        for file_path in output_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()

if __name__ == "__main__":
    from pathlib import Path

    processor = ImageProcessor(OllamaWrapper(timeout_s=500), "qwen2.5vl:7b")

    print("Processing images...")

    PROJECT_ROOT = Path(__file__).parent.parent
    DATASET_DIR = PROJECT_ROOT / "dataset" / "Dataset_test"

    dataset_test = Dataset(0, "Dataset_test")

    images = [
        Image(path=str(DATASET_DIR / "weezer.png"), dataset=dataset_test),
        Image(path=str(DATASET_DIR / "weezer.jpg"), dataset=dataset_test),
        Image(path=str(DATASET_DIR / "weezer.jpeg"), dataset=dataset_test),
        Image(path=str(DATASET_DIR / "weezer.webp"), dataset=dataset_test)
    ]

    processor.reduce_img(Image(path=str(DATASET_DIR / "grande.jpg"), dataset=dataset_test))

    for image in images:
        try:
            print(f"\nProcessing {image.name}...")

            processor.ImageToData(image)

            print("Description:")
            print(image.description)

            print("Keywords:")
            print(image.keywords)

            processor.TextToEmbedding(image)

            print("Embedding length:", len(image.embedding))
            print(f"✓ {image.name} processed")

        except Exception as e:
            processor.clean_reduce_img()
            print(f"✗ Error processing {image.name}: {e!s}")

    for image in images:
        print(image)