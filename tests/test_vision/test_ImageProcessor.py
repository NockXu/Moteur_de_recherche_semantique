import unittest
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, MagicMock
from PIL import Image as PILImage
import io

from common.Image_Classes.Image import Image
from common.Dataset_Classes.Dataset import Dataset

from vision.ImageProcessor import ImageProcessor
from vision.ollama_wrapper import OllamaGenerateResult

from .FakeOllamaWrapper import FakeOllamaWrapper

class test_ImageProcessor(unittest.TestCase):

    def setUp(self) -> None:
        self.ollama = FakeOllamaWrapper()
        self.processor = ImageProcessor(self.ollama, "test_model")
        # Créer une image de test avec PIL (pas de dépendance à un fichier réel)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_image_path = self.temp_dir / "test_image.png"
        
        # Créer une image PIL de test
        fake_image = PILImage.new("RGB", (100, 100), color="red")
        fake_image.save(self.test_image_path)
        
        self.image_test = Image(
            path=str(self.test_image_path),
            name="test_image.png",
            dataset=Dataset(0, "test_dataset")
        )

        # Utiliser le prompt exact que ImageToData utilise
        self.prompt = """Analyse cette image et produis deux sorties distinctes optimisées pour la recherche sémantique.

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

    def test_ImageToData(self):
        # Test avec description et keywords
        self.ollama.add_response(self.prompt,
                response="""DESCRIPTION:
                test_response

                KEYWORDS:
                mot1, mot2, mot3, mot4""",
                            )
        self.processor.ImageToData(self.image_test)
        self.assertEqual(self.image_test.description, "test_response")

        # Réinitialisation des réponses
        self.ollama.responses = {}

        # Test avec seulement la description
        self.ollama.add_response(self.prompt, response="test_response")
        self.processor.ImageToData(self.image_test)
        self.assertEqual(self.image_test.description, "test_response")
        self.assertEqual(self.image_test.keywords, [])

        # Test avec déclanchement d'erreur
        self.ollama.add_response(self.prompt, OllamaGenerateResult(
                response=Exception("test_exception")
            ))
        self.assertRaises(RuntimeError, self.processor.ImageToData, self.image_test)
        


    def test_TextToEmbedding(self):
        # test avec description
        self.image_test.description = "test_response"
        self.ollama.add_embedding(
            "test_response",
            [0.1, 0.2, 0.3]
        )

        self.processor.TextToEmbedding(self.image_test)

        self.assertEqual(
            self.image_test.embedding,
            [0.1, 0.2, 0.3]
        )

        # test sans description
        self.image_test.description = ""
        self.image_test.embedding = []
        self.ollama.add_embedding(
            "",
            []
        )
        self.processor.TextToEmbedding(self.image_test)
        self.assertEqual(self.image_test.embedding, [])

        # test avec description et keywords
        self.image_test.description = "test_response"
        self.image_test.keywords = ["mot1", "mot2", "mot3", "mot4"]
        self.image_test.embedding = []
        text_for_embedding = "test_response, mot1, mot2, mot3, mot4"
        self.ollama.add_embedding(
            text_for_embedding,
            [0.1, 0.2, 0.3]
        )
        self.processor.TextToEmbedding(self.image_test)
        self.assertEqual(self.image_test.embedding, [0.1, 0.2, 0.3])

        # test qui retourne erreur
        self.image_test.description = 1
        self.image_test.embedding = None
        # Simuler une erreur dans l'embedding
        self.ollama.add_embedding(
            1,
            Exception("Erreur d'embedding simulée")
        )
        # Vérifier que RuntimeError est bien levée
        with self.assertRaises(RuntimeError) as context:
            self.processor.TextToEmbedding(self.image_test)

    def test_reduce_img(self):
        from PIL import Image as PILImage
        import tempfile
        
        # Créer un fichier temporaire dans un dossier accessible
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test_image.png"
            
            image = PILImage.new("RGB", (100, 100))
            image.save(test_file)

            image_data = Image(path=str(test_file), dataset=Dataset(0, "Dataset_test"))

            result = self.processor.reduce_img(image_data)

            self.assertIsNotNone(result)

        # Test avec mauvaise extension
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test_image.txt"
            
            test_file.write_text("test")
            
            image_data = Image(path=str(test_file), dataset=Dataset(0, "Dataset_test"))
            
            with self.assertRaises(ValueError) as context:
                self.processor.reduce_img(image_data)

    def test_clean_reduce_img(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            tmp_path = Path(tmp_dir)

            file1 = tmp_path / "a.jpg"
            file2 = tmp_path / "b.jpg"

            file1.write_text("test")
            file2.write_text("test")

            self.assertTrue(file1.exists())
            self.assertTrue(file2.exists())

            self.processor.clean_reduce_img(tmp_path)

            self.assertFalse(file1.exists())
            self.assertFalse(file2.exists())

        # Test avec un dossier qui existe pas
        result = self.processor.clean_reduce_img(Path("dossier_inexistant"))

        self.assertIsNone(result)