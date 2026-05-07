from pickletools import optimize
import sys
import os
from typing import Any
from PIL import Image as PILImage
from pathlib import Path

from vision.ollama_wrapper import OllamaWrapper
from common.Image_Classes.Image import Image
from common.Dataset_Classes.Dataset import Dataset

class ImageProcessor:
    def __init__(self, wrapper: OllamaWrapper, model: str):
        self.wrapper = wrapper
        self.model = model

    def ImageToData(self, image: Image) -> None:
        """
        Génère description + keywords en un seul appel (plus stable et rapide)
        """
        try:
            prompt = """Analyse cette image et produis deux sorties distinctes optimisées pour la recherche sémantique.

Objectif :
- Une description riche et précise
- Une liste de mots-clés simples et exploitables

---

1. DESCRIPTION :

Génère une description complète, structurée et optimisée pour un embedding.

Instructions :
- Décris les objets principaux (type, forme, taille relative, position, texte visible)
- Explique les actions ou interactions visibles ou le texte
- Précise les attributs visuels (couleurs, textures, matériaux, état)
- Décris l’environnement (intérieur/extérieur, contexte, type de lieu)
- Ajoute les détails secondaires utiles (arrière-plan, éclairage, ambiance, angle de vue)
- Ajoute des concepts implicites pertinents (ex : travail, loisir, transport, vacances)

Contraintes :
- Phrases complètes uniquement
- Texte fluide (pas de liste)
- Factuel, sans supposition incertaine
- Entre 100 et 200 mots

---

2. KEYWORDS :

Génère une liste de mots-clés simples et variés.

Règles STRICTES :
- Chaque mot-clé est UNIQUE
- Un seul mot par mot-clé (pas d’expressions)
- Mots simples uniquement (ex : "rock", pas "groupe de rock")
- Entre 10 et 20 mots-clés
- Séparés par des virgules

---

FORMAT DE SORTIE OBLIGATOIRE :

DESCRIPTION:
[paragraphe]

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

                # nettoyage
                keywords = list(dict.fromkeys(
                    kw for kw in keywords if len(kw.split()) <= 2
                ))

            else:
                # fallback (le modèle a foiré le format)
                description = response
                keywords = []

            image.description = description
            image.keywords = keywords

        except Exception as e:
            raise RuntimeError(f"Erreur lors du traitement de l'image {image.path}: {str(e)}")

    def TextToEmbedding(self, image: Image) -> None:
        """
        Génère un embedding à partir de la description
        """
        try:
            if not image.description:
                image.embedding = []
                return

            result = self.wrapper.embed(
                model="nomic-embed-text:v1.5",
                text=image.description
            )
            image.embedding = result

        except Exception as e:
            raise RuntimeError(f"Erreur embedding pour {image.path}: {str(e)}")

    def reduce_img(self, image : Image) -> str:
        max_width = 1024
        max_height = 1024

        extension = [".jpg", ".jpeg", ".png", ".webp"]

        base_dir = Path(__file__).resolve().parent

        storage_dir = base_dir.parent / "storage"
        output_dir = storage_dir / "images_reduced"

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        img_extension = Path(image.path).suffix.lower()

        if img_extension not in extension:
            raise ValueError(f"Extension non supportée : {img_extension}")

        with PILImage.open(image.path) as img:
            # Conserve les proportions
            img.thumbnail((max_width, max_height))

            # Sauvegarde dans le dossier
            img_path = os.path.join(output_dir, image.name)
            img.save(
                img_path,
                optimize=True,
                quality=85
            )

            return img_path

    def clean_reduce_img(self) -> None:
        base_dir = Path(__file__).resolve().parent

        storage_dir = base_dir.parent / "storage"
        output_dir = storage_dir / "images_reduced"

        # Vérifie que le dossier existe
        if not os.path.exists(output_dir):
            return

        # Supprime tous les fichiers
        for file in os.listdir(output_dir):
            file_path = os.path.join(output_dir, file)

            if os.path.isfile(file_path):
                os.remove(file_path)
            

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
            print(f"✗ Error processing {image.name}: {str(e)}")

    for image in images:
        print(image)