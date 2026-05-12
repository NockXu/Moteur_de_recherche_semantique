import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from common.Image_Classes.Image import Image
from common.Dataset_Classes.Dataset import Dataset
from common.Image_Classes.ImageScanService import ImageScanService

class TestImageScanService(unittest.TestCase):
    def setUp(self):
        self.scan_service = ImageScanService()
        self.dataset = Dataset(1, "test")
        
        # Créer un dossier temporaire pour les tests
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)
        
        # Créer des fichiers de test
        self.create_test_files()
    
    def tearDown(self):
        # Nettoyer le dossier temporaire
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def create_test_files(self):
        """Créer des fichiers de test pour les scans"""
        # Fichiers images valides
        (self.test_dir / "image1.jpg").touch()
        (self.test_dir / "image2.png").touch()
        (self.test_dir / "image3.webp").touch()
        (self.test_dir / "image4.JPEG").touch()  # Test majuscule
        
        # Sous-dossier avec images
        subdir = self.test_dir / "subdir"
        subdir.mkdir()
        (subdir / "sub_image1.jpg").touch()
        (subdir / "sub_image2.png").touch()
        
        # Fichiers non-images (doivent être ignorés)
        (self.test_dir / "document.txt").touch()
        (self.test_dir / "video.mp4").touch()
        (self.test_dir / "archive.zip").touch()
        
        # Fichiers avec extensions non supportées
        (self.test_dir / "image.bmp").touch()
        (self.test_dir / "image.tiff").touch()

    def test_init(self):
        """Test l'initialisation du service"""
        service = ImageScanService()
        self.assertIsInstance(service, ImageScanService)
        self.assertEqual(service.SUPPORTED_EXTENSIONS, {".jpg", ".jpeg", ".png", ".webp"})

    def test_scan_with_valid_directory(self):
        """Test scan complet avec un dossier valide"""
        results = self.scan_service.scan(str(self.test_dir), self.dataset)
        
        # Doit trouver 6 images (4 dans racine + 2 dans sous-dossier)
        self.assertEqual(len(results), 6)
        
        # Vérifier que tous les résultats sont des objets Image
        for image in results:
            self.assertIsInstance(image, Image)
            self.assertEqual(image.dataset_id, self.dataset.id)
            self.assertEqual(image.description, "")
            self.assertEqual(image.keywords, [])
            self.assertEqual(image.embedding, [])
            self.assertIsNotNone(image.id)  # L'ID est généré automatiquement
        
        # Vérifier que les chemins sont corrects
        paths = [str(img.path) for img in results]
        self.assertIn(str(self.test_dir / "image1.jpg"), paths)
        self.assertIn(str(self.test_dir / "subdir" / "sub_image1.jpg"), paths)

    def test_scan_without_dataset(self):
        """Test scan sans dataset"""
        results = self.scan_service.scan(str(self.test_dir))
        
        self.assertEqual(len(results), 6)
        
        # Vérifier que dataset est None
        for image in results:
            self.assertIsNone(image.dataset_id)

    def test_scan_with_nonexistent_directory(self):
        """Test scan avec un dossier qui n'existe pas"""
        nonexistent_dir = str(self.test_dir / "nonexistent")
        results = self.scan_service.scan(nonexistent_dir, self.dataset)
        
        self.assertEqual(len(results), 0)

    def test_scan_with_file_instead_of_directory(self):
        """Test scan avec un fichier au lieu d'un dossier"""
        file_path = str(self.test_dir / "image1.jpg")
        results = self.scan_service.scan(file_path, self.dataset)
        
        self.assertEqual(len(results), 0)

    def test_scan_lazy(self):
        """Test scan lazy (générateur)"""
        generator = self.scan_service.scan_lazy(str(self.test_dir), self.dataset)
        
        # Vérifier que c'est bien un générateur
        self.assertTrue(hasattr(generator, '__iter__'))
        
        # Convertir en liste pour vérifier les résultats
        results = list(generator)
        self.assertEqual(len(results), 6)
        
        # Vérifier que les images sont correctes
        for image in results:
            self.assertIsInstance(image, Image)
            self.assertEqual(image.dataset_id, self.dataset.id)

    def test_scan_page_first_page(self):
        """Test scan paginé - première page"""
        results = self.scan_service.scan_page(str(self.test_dir), page=0, page_size=2, dataset=self.dataset)
        
        self.assertEqual(len(results), 2)
        
        # Vérifier que ce sont bien des images
        for image in results:
            self.assertIsInstance(image, Image)
            self.assertEqual(image.dataset_id, self.dataset.id)

    def test_scan_page_middle_page(self):
        """Test scan paginé - page du milieu"""
        results = self.scan_service.scan_page(str(self.test_dir), page=1, page_size=2, dataset=self.dataset)
        
        self.assertEqual(len(results), 2)

    def test_scan_page_last_page_partial(self):
        """Test scan paginé - dernière page incomplète"""
        results = self.scan_service.scan_page(str(self.test_dir), page=2, page_size=3, dataset=self.dataset)
        
        # Page 2 : indices 6, 7, 8 mais on n'a que 6 images au total
        self.assertEqual(len(results), 0)

    def test_scan_page_beyond_end(self):
        """Test scan paginé - page au-delà de la fin"""
        results = self.scan_service.scan_page(str(self.test_dir), page=10, page_size=5, dataset=self.dataset)
        
        self.assertEqual(len(results), 0)

    def test_scan_page_zero_page_size(self):
        """Test scan paginé avec page_size = 0"""
        results = self.scan_service.scan_page(str(self.test_dir), page=0, page_size=0, dataset=self.dataset)
        
        self.assertEqual(len(results), 0)

    def test_supported_extensions_filtering(self):
        """Test que seules les extensions supportées sont incluses"""
        results = self.scan_service.scan(str(self.test_dir), self.dataset)
        
        # Extraire les extensions des fichiers trouvés
        extensions = {img.path.suffix.lower() for img in results}
        
        # Vérifier que seulement les extensions supportées sont présentes
        expected_extensions = {".jpg", ".png", ".webp", ".jpeg"}
        self.assertEqual(extensions, expected_extensions)
        
        # Vérifier l'absence des extensions non supportées
        self.assertNotIn(".txt", extensions)
        self.assertNotIn(".mp4", extensions)
        self.assertNotIn(".zip", extensions)
        self.assertNotIn(".bmp", extensions)
        self.assertNotIn(".tiff", extensions)

    def test_case_insensitive_extensions(self):
        """Test que les extensions sont traitées de manière insensible à la casse"""
        results = self.scan_service.scan(str(self.test_dir), self.dataset)
        
        # Vérifier que image4.JPEG (majuscule) est bien inclus
        paths = [str(img.path) for img in results]
        jpeg_files = [p for p in paths if p.endswith("JPEG") or p.endswith("jpeg")]
        
        self.assertEqual(len(jpeg_files), 1)

    def test_recursive_scan(self):
        """Test que le scan est bien récursif"""
        results = self.scan_service.scan(str(self.test_dir), self.dataset)
        
        # Compter les fichiers dans la racine et les sous-dossiers
        root_files = [img for img in results if img.path.parent == self.test_dir]
        sub_files = [img for img in results if img.path.parent == self.test_dir / "subdir"]
        
        self.assertEqual(len(root_files), 4)  # 4 images dans la racine
        self.assertEqual(len(sub_files), 2)   # 2 images dans le sous-dossier