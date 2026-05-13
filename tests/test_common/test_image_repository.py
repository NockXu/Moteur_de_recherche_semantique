import unittest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
from common.Image_Classes.ImageRepository import ImageRepository, SearchResults
from common.Image_Classes.Image import Image, ProcessingStatus
from common.Dataset_Classes.Dataset import Dataset
from common.Dataset_Classes.DatasetRepository import DatasetRepository
from database.faiss_manager.manager import DIMENSION

from database.DbService import DbService

class TestImageRepository(unittest.TestCase):
    def setUp(self):
        self.dbs = DbService()
        self.dataset = Dataset(1, "test")
        self.image = Image(Path("test/test.jpg"), self.dataset)

    def _generate_test_embeddings(self, count=2000):
        """Génère des embeddings de test sous forme de bytes comme dans la base de données"""
        embeddings = []
        ids = []
        for i in range(count):
            embedding = [(i * 0.1) % 1.0] * DIMENSION  # Valeurs différentes pour chaque embedding
            # Convertir en bytes comme dans la base de données
            embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
            embeddings.append(embedding_bytes)
            ids.append(i)
        return ids, embeddings

    def test_init(self):
        """Test l'initialisation du repository"""
        repository = ImageRepository(self.dbs.sqlite, self.dbs.faiss)
        self.assertEqual(repository.db, self.dbs.sqlite)
        self.assertEqual(repository.faiss, self.dbs.faiss)
        self.assertIsInstance(repository._dataset_repo, DatasetRepository)
        self.assertEqual(repository._dataset_cache, {})

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_get_dataset_by_id(self, mock_dataset_repo_class):
        """Test la méthode _get_dataset_by_id"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo

        # Configurer le mock pour retourner le dataset attendu
        mock_repo.get_by_id.return_value = self.dataset

        repository = ImageRepository(self.dbs.sqlite, self.dbs.faiss)
        dataset = repository._get_dataset_by_id(self.dataset.id)
        self.assertEqual(dataset, self.dataset)
        
        # Vérifier que le mock a été appelé
        mock_repo.get_by_id.assert_called_once_with(self.dataset.id)

        # Tester avec le cache
        repository._dataset_cache[self.dataset.id] = self.dataset
        dataset = repository._get_dataset_by_id(self.dataset.id)
        self.assertEqual(dataset, self.dataset)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_save_image(self, mock_dataset_repo_class):
        """Test la méthode save_image"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Mock de la base de données
        mock_db = MagicMock()
        mock_db.execute = MagicMock()  # execute ne retourne rien
        mock_db.commit = MagicMock()  # commit ne retourne rien
        
        repository = ImageRepository(mock_db, self.dbs.faiss)
        
        # L'image a déjà un dataset_id, donc pas besoin de créer le dataset
        result = repository.save_image(self.image)
        
        # Vérifications
        self.assertTrue(result)
        
        # Vérifier que la base de données a été appelée
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_save_image_with_dataset_not_existing(self, mock_dataset_repo_class):
        """Test la méthode save_image avec un dataset inexistant"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Mock de la base de données
        mock_db = MagicMock()
        mock_db.execute = MagicMock()  # execute ne retourne rien
        mock_db.commit = MagicMock()  # commit ne retourne rien
        
        repository = ImageRepository(mock_db, self.dbs.faiss)
        
        # Test avec un dataset inexistant (doit créer le dataset)
        self.image.dataset_id = None
        
        # Configurer le mock pour le cas où le dataset n'existe pas
        mock_repo.get_by_name.return_value = None
        mock_repo.create.return_value = Dataset(1, self.dataset.name)

        result = repository.save_image(self.image)

        # Vérifier que le repository a été appelé pour chercher et créer le dataset
        mock_repo.get_by_name.assert_called_once_with(self.dataset.name)
        mock_repo.create.assert_called_once_with(self.dataset.name)
        
        self.assertTrue(result)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_save_image_with_dataset_existing_but_no_id_in_image(self, mock_dataset_repo_class):
        """Test la méthode save_image avec un dataset existant mais non renseigné dans l'image"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Mock de la base de données
        mock_db = MagicMock()
        mock_db.execute = MagicMock()  # execute ne retourne rien
        mock_db.commit = MagicMock()  # commit ne retourne rien
        
        repository = ImageRepository(mock_db, self.dbs.faiss)
        
        # Test avec un dataset existant mais mal renseigner à l'image
        self.image.dataset_id = None
        mock_repo.get_by_name.return_value = Dataset(1, self.dataset.name)

        result = repository.save_image(self.image)

        # Vérifier que le repository a été appelé pour chercher le dataset
        mock_repo.get_by_name.assert_called_once_with(self.dataset.name)
        
        self.assertTrue(result)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_save_image_with_dataset_not_existing_and_with_error(self, mock_dataset_repo_class):
        """Test la méthode save_image avec un dataset inexistant et une erreur lors de la création"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Mock de la base de données
        mock_db = MagicMock()
        mock_db.execute = MagicMock()  # execute ne retourne rien
        mock_db.commit = MagicMock()  # commit ne retourne rien
        
        repository = ImageRepository(mock_db, self.dbs.faiss)
        
        # Test avec un dataset inexistant (doit créer le dataset)
        self.image.dataset_id = None
        
        def mock_get_by_name(name):
            if name == "default":
                return Dataset(1, "default")
            return None
        
        mock_repo.get_by_name.side_effect = mock_get_by_name
        mock_repo.create.return_value = None
        
        repository.save_image(self.image)

        self.assertEqual(self.image.dataset_id, 1)
        
        # Vérifier que le repository a été appelé pour chercher et créer le dataset
        mock_repo.get_by_name.assert_any_call(self.dataset.name)  # appel avec 'test'
        mock_repo.get_by_name.assert_any_call("default")  # appel avec 'default'
        self.assertEqual(mock_repo.get_by_name.call_count, 2)  # appelé 2 fois
        mock_repo.create.assert_called_once_with(self.dataset.name)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_save_image_with_dataset_return_false(self, mock_dataset_repo_class):
        """Test la méthode save_image avec un dataset inexistant et une erreur lors de la création"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Mock de la base de données
        mock_db = MagicMock()
        mock_db.execute = Exception("test exeption")
        mock_db.commit = MagicMock()  # commit ne retourne rien
        
        repository = ImageRepository(mock_db, self.dbs.faiss)
        
        # Test avec un dataset inexistant (doit créer le dataset)
        self.image.dataset_id = None
        
        def mock_get_by_name(name):
            if name == "default":
                return Dataset(1, "default")
            return None
        
        mock_repo.get_by_name.side_effect = mock_get_by_name
        mock_repo.create.return_value = None
        
        result = repository.save_image(self.image)

        self.assertFalse(result)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_save_many_images(self, mock_dataset_repo_class):
        """Test la méthode save_many_images"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Mock de la base de données
        mock_db = MagicMock()
        mock_db.executemany = MagicMock()  # executemany ne retourne rien
        mock_db.execute = MagicMock()  # execute ne retourne rien
        mock_db.commit = MagicMock()  # commit ne retourne rien
        
        repository = ImageRepository(mock_db, self.dbs.faiss)
        
        # Créer plusieurs images
        image2 = Image(Path("test/test2.jpg"), self.dataset)
        images = [self.image, image2]
        
        # Les images ont déjà des dataset_id, donc pas besoin de créer les datasets
        result = repository.save_many_images(images)
        
        # Vérifications
        self.assertEqual(result, 2)  # 2 images sauvegardées
        self.assertEqual(self.image.dataset_id, self.dataset.id)
        self.assertEqual(image2.dataset_name, self.dataset.name)
        
        # Vérifier que la base de données a été appelée
        mock_db.executemany.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_save_many_images_with_dataset_not_existing(self, mock_dataset_repo_class):
        """Test save_many_images avec des datasets inexistants"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Mock de la base de données
        mock_db = MagicMock()
        mock_db.executemany = MagicMock()
        mock_db.execute = MagicMock()
        mock_db.commit = MagicMock()
        
        repository = ImageRepository(mock_db, self.dbs.faiss)
        
        # Créer des images sans dataset_id
        self.image.dataset_id = None
        image2 = Image(Path("test/test2.jpg"), Dataset(2, "test2"))
        image2.dataset_id = None
        images = [self.image, image2]
        
        # Configurer le mock pour créer les datasets
        mock_repo.get_by_name.return_value = None
        mock_repo.create.return_value = Dataset(1, "test")
        
        result = repository.save_many_images(images)
        
        # Vérifications
        self.assertEqual(result, 2)
        self.assertIsNotNone(self.image.dataset_id)
        self.assertIsNotNone(image2.dataset_id)
        
        # Vérifier que les datasets ont été créés
        self.assertEqual(mock_repo.create.call_count, 2)
        mock_db.executemany.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_save_many_images_with_dataset_not_existing_and_with_error(self, mock_dataset_repo_class):
        """Test save_many_images avec dataset non existant mais et avec une erreur lors de la création du dataset"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Mock de la base de données
        mock_db = MagicMock()
        mock_db.executemany = MagicMock()
        mock_db.execute = MagicMock()
        mock_db.commit = MagicMock()
        
        repository = ImageRepository(mock_db, self.dbs.faiss)
        
        # Créer des images
        self.image.dataset_id = None
        image2 = Image(Path("test/test2.jpg"), Dataset(None, "test"))
        image2.dataset_id = None
        images = [self.image, image2]
        
        # Configurer le mock
        def mock_get_by_name(name):
            if name == "default":
                return Dataset(1, "default")
            return None

        mock_repo.get_by_name.side_effect = mock_get_by_name
        mock_repo.create.return_value = None
        
        result = repository.save_many_images(images)
        
        # Vérifications
        self.assertEqual(result, 2)
        self.assertEqual(self.image.dataset_id, 1)
        self.assertEqual(image2.dataset_name, "default")
        
        # Vérifier que la base de données a été appelée
        mock_db.executemany.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_save_many_images_with_dataset_existing_but_no_image_id(self, mock_dataset_repo_class):
        """Test save_many_images avec dataset existant mais pas d'image_id"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Mock de la base de données
        mock_db = MagicMock()
        mock_db.executemany = MagicMock()
        mock_db.execute = MagicMock()
        mock_db.commit = MagicMock()
        
        repository = ImageRepository(mock_db, self.dbs.faiss)
        
        # Créer des images avec dataset_id existant
        self.image.dataset_id = None
        image2 = Image(Path("test/test2.jpg"), Dataset(None, "test"))
        images = [self.image, image2]
        
        # Configurer le mock pour retourner les datasets existants
        mock_repo.get_by_name.return_value = self.dataset
        mock_repo.create.return_value = Dataset(1, "test")
        
        result = repository.save_many_images(images)
        
        # Vérifications
        self.assertEqual(result, 2)
        self.assertEqual(self.image.dataset_id, 1)
        self.assertEqual(image2.dataset_name, "test")
        
        # Vérifier que la base de données a été appelée
        mock_db.executemany.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_save_many_images_with_executemany_error(self, mock_dataset_repo_class):
        """Test save_many_images avec erreur dans executemany (fallback ligne par ligne)"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Mock de la base de données avec erreur dans executemany
        mock_db = MagicMock()
        mock_db.executemany.side_effect = Exception("Erreur batch")
        mock_db.execute = MagicMock()
        mock_db.commit = MagicMock()
        
        repository = ImageRepository(mock_db, self.dbs.faiss)
        
        images = [self.image]
        
        result = repository.save_many_images(images)
        
        # Vérifications
        self.assertEqual(result, 1)
        
        # Vérifier le fallback : executemany appelé, puis execute pour chaque ligne
        mock_db.executemany.assert_called_once()
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_save_many_images_with_executemany_and_execute_error(self, mock_dataset_repo_class):
        """Test save_many_images avec erreur dans executemany et execute (fallback ligne par ligne)"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Mock de la base de données avec erreur dans executemany
        mock_db = MagicMock()
        mock_db.executemany.side_effect = Exception("Erreur batch")
        mock_db.execute.side_effect = Exception("Erreur Ligne")
        mock_db.commit = MagicMock()
        
        repository = ImageRepository(mock_db, self.dbs.faiss)
        
        images = [self.image]
        
        result = repository.save_many_images(images)
        
        # Vérifications
        self.assertEqual(result, 0)
        
        # Vérifier le fallback : executemany appelé, puis execute pour chaque ligne
        mock_db.executemany.assert_called_once()
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_train(self, mock_dataset_repo_class):
        """Test train"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Créer 2000 embeddings différents
        ids, embeddings = self._generate_test_embeddings(2000)

        # Mock de la base de données
        mock_db = MagicMock()
        # Retourner une liste de tuples (id, embedding_blob)
        mock_db.fetch_all.return_value = [(id, embedding) for id, embedding in zip(ids, embeddings)]

        # Mock l'index faiss
        mock_faiss = MagicMock()
        mock_faiss.train = MagicMock()
        mock_faiss.add = MagicMock()
        mock_faiss.save = MagicMock()
        mock_faiss._create_index = MagicMock()
        
        repository = ImageRepository(mock_db, mock_faiss)
        
        result = repository.train_index()
        
        # Vérifications
        self.assertTrue(result)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_train_image_with_no_embedding(self, mock_dataset_repo_class):
        """Test train"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Créer 2000 embeddings différents
        ids, embeddings = self._generate_test_embeddings(2000)

        # Mock de la base de données
        mock_db = MagicMock()
        # Retourner une liste de tuples (id, embedding_blob)
        mock_db.fetch_all.return_value = [(id, None) for id in ids]

        # Mock l'index faiss
        mock_faiss = MagicMock()
        mock_faiss.train = MagicMock()
        mock_faiss.add = MagicMock()
        mock_faiss.save = MagicMock()
        mock_faiss._create_index = MagicMock()
        
        repository = ImageRepository(mock_db, mock_faiss)
        
        result = repository.train_index()
        
        # Vérifications
        self.assertFalse(result)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_train_image_with_empty_embedding(self, mock_dataset_repo_class):
        """Test train"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Créer 2000 embeddings différents
        ids, embeddings = self._generate_test_embeddings(2000)

        # Mock de la base de données
        mock_db = MagicMock()
        # Retourner une liste de tuples (id, embedding_blob)
        mock_db.fetch_all.return_value = [(id, np.array([], dtype=np.float32)) for id in ids]

        # Mock l'index faiss
        mock_faiss = MagicMock()
        mock_faiss.train = MagicMock()
        mock_faiss.add = MagicMock()
        mock_faiss.save = MagicMock()
        mock_faiss._create_index = MagicMock()
        
        repository = ImageRepository(mock_db, mock_faiss)
        
        result = repository.train_index()
        
        # Vérifications
        self.assertFalse(result)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_train_with_error(self, mock_dataset_repo_class):
        """Test train"""
        # Créer un mock de DatasetRepository
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        
        # Créer 2000 embeddings différents
        ids, embeddings = self._generate_test_embeddings(2000)

        # Mock de la base de données
        mock_db = MagicMock()
        # Retourner une liste de tuples (id, embedding_blob)
        mock_db.fetch_all.return_value = [(id, embedding) for id, embedding in zip(ids, embeddings)]

        # Mock l'index faiss
        mock_faiss = MagicMock()
        mock_faiss.train.return_value = False
        mock_faiss.add = MagicMock()
        mock_faiss.save = MagicMock()
        mock_faiss._create_index = MagicMock()
        
        repository = ImageRepository(mock_db, mock_faiss)
        
        result = repository.train_index()
        
        # Vérifications
        self.assertFalse(result)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_search(self, mock_dataset_repo_class):

        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        mock_repo.get_by_id.return_value = self.dataset

        mock_db = MagicMock()

        embedding = np.array(
            [0.5] * DIMENSION,
            dtype=np.float32
        ).tobytes()

        mock_db.fetch_all.return_value = [
            (1, embedding, 'test.jpg', 'test', 'desc', '[]', 1)
        ]

        mock_faiss = MagicMock()
        mock_faiss.search.return_value = [(1, 0.95), (1, 0.95)]

        repository = ImageRepository(mock_db, mock_faiss)

        query_embedding = [0.5] * DIMENSION

        result = repository.search(query_embedding, k=10)
        
        # Vérifications
        self.assertEqual(len(result['images']), 1)
        self.assertEqual(result['images'][0].id, 1)
        self.assertEqual(result['images'][0].path, Path('test.jpg'))
        self.assertEqual(result['k'], 10)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_search_no_result(self, mock_dataset_repo_class):

        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        mock_repo.get_by_id.return_value = self.dataset

        mock_db = MagicMock()

        mock_faiss = MagicMock()
        mock_faiss.search.return_value = []

        repository = ImageRepository(mock_db, mock_faiss)

        query_embedding = [0.5] * DIMENSION

        result = repository.search(query_embedding, k=10)
        
        # Vérifications
        self.assertEqual(len(result['images']), 0)
        self.assertEqual(result['k'], 10)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_search_no_id(self, mock_dataset_repo_class):

        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        mock_repo.get_by_id.return_value = self.dataset

        mock_db = MagicMock()

        mock_faiss = MagicMock()
        mock_faiss.search.return_value = [(-1, 0.95), (-1, 0.95)]

        repository = ImageRepository(mock_db, mock_faiss)

        query_embedding = [0.5] * DIMENSION

        result = repository.search(query_embedding, k=10)
        
        # Vérifications
        self.assertEqual(len(result['images']), 0)
        self.assertEqual(result['k'], 10)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_search_no_embedding(self, mock_dataset_repo_class):

        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        mock_repo.get_by_id.return_value = self.dataset

        mock_db = MagicMock()
        mock_db.fetch_all.return_value = [
            (
                1,
                b"",
                "path",
                "name",
                "desc",
                "[]",
                1
            )
        ]

        mock_faiss = MagicMock()
        mock_faiss.search.return_value = [(1, 0.95), (2, 0.95)]

        repository = ImageRepository(mock_db, mock_faiss)

        query_embedding = [0.5] * DIMENSION

        result = repository.search(query_embedding, k=10)
        
        # Vérifications
        self.assertEqual(len(result['images']), 0)
        self.assertEqual(result['k'], 10)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_search_no_data_in_database(self, mock_dataset_repo_class):

        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        mock_repo.get_by_id.return_value = self.dataset

        mock_db = MagicMock()
        mock_db.fetch_all.return_value = []

        mock_faiss = MagicMock()
        mock_faiss.search.return_value = [(1, 0.95), (2, 0.95)]

        repository = ImageRepository(mock_db, mock_faiss)

        query_embedding = [0.5] * DIMENSION

        result = repository.search(query_embedding, k=10)
        
        # Vérifications
        self.assertEqual(len(result['images']), 0)
        self.assertEqual(result['k'], 10)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_search_row_map_error(self, mock_dataset_repo_class):
        """Test search quand row_map.get(idx) retourne None (continue exécuté)"""
        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        mock_repo.get_by_id.return_value = self.dataset

        mock_db = MagicMock()

        embedding = np.array(
            [0.5] * DIMENSION,
            dtype=np.float32
        ).tobytes()

        # La base de données retourne l'ID 1
        mock_db.fetch_all.return_value = [
            (1, embedding, 'test.jpg', 'test', 'desc', '[]', 1)
        ]

        mock_faiss = MagicMock()
        # Mais FAISS cherche l'ID 2 qui n'existe pas dans la base
        mock_faiss.search.return_value = [(2, 0.95)]

        repository = ImageRepository(mock_db, mock_faiss)

        query_embedding = [0.5] * DIMENSION

        result = repository.search(query_embedding, k=10)
        
        # Vérifications
        self.assertEqual(len(result['images']), 0)

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_get_all(self, mock_dataset_repo_class):
        """Test get_all"""

        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        mock_repo.get_by_id.return_value = Dataset(1, "test")
        
        mock_db = MagicMock()
        mock_db.fetch_all.return_value = [
            (1, 'test_path', 'test_path', 'test_desc', '["tag1", "tag2"]', 1, b'\x00\x00\x80\x3f')
        ]
        
        repository = ImageRepository(mock_db, None)
        
        result = repository.get_all()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[0].path, Path('test_path'))
        self.assertEqual(result[0].name, 'test_path')
        self.assertEqual(result[0].description, 'test_desc')
        self.assertEqual(result[0].keywords, ["tag1", "tag2"])
        self.assertEqual(result[0].dataset_id, 1)
        self.assertNotEqual(result[0].embedding, [])

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_get_all_no_keywords_no_dataset(self, mock_dataset_repo_class):
        """Test get_all"""

        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        mock_repo.get_by_id.return_value = None
        
        mock_db = MagicMock()
        mock_db.fetch_all.return_value = [
            (1, 'test_path', 'test_path', 'test_desc', 'tag1 tag2', 1, '\x00\x00\x80\x3f')
        ]
        
        repository = ImageRepository(mock_db, None)
        
        result = repository.get_all()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[0].path, Path('test_path'))
        self.assertEqual(result[0].name, 'test_path')
        self.assertEqual(result[0].description, 'test_desc')
        self.assertEqual(result[0].keywords, [])
        self.assertEqual(result[0].dataset_id, None)
        self.assertEqual(result[0].embedding, [])

    @patch('common.Image_Classes.ImageRepository.DatasetRepository')
    def test_get_all_nothing(self, mock_dataset_repo_class):
        """Test get_all"""

        mock_repo = MagicMock()
        mock_dataset_repo_class.return_value = mock_repo
        mock_repo.get_by_id.return_value = None
        
        mock_db = MagicMock()
        mock_db.fetch_all.return_value = []
        
        repository = ImageRepository(mock_db, None)
        
        result = repository.get_all()
        
        self.assertEqual(len(result), 0)

    def test_exist_true(self):
        """Test exist"""
        mock_db = MagicMock()
        mock_db.fetch_one.return_value = "Test"
        
        repository = ImageRepository(mock_db, None)
        
        result = repository.exist(1)
        
        self.assertTrue(result)

    def test_exist_false(self):
        """Test exist"""
        mock_db = MagicMock()
        mock_db.fetch_one.return_value = None
        
        repository = ImageRepository(mock_db, None)
        
        result = repository.exist(1)
        
        self.assertFalse(result)

    def test_get_all_image_path(self):
        """Test get_all_image_path"""
        mock_db = MagicMock()
        mock_db.fetch_all.return_value = [
            ("test_path1",),
            ("test_path2",)
        ]
        
        repository = ImageRepository(mock_db, None)
        
        result = repository.get_all_image_paths()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result, {"test_path1", "test_path2"})