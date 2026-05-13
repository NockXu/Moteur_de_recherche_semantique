import unittest
import tempfile
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import List

from database.faiss_manager.manager import FaissManager, DIMENSION


class TestFaissManager(unittest.TestCase):
    """Tests complets pour FaissManager"""

    def setUp(self):
        """Initialisation pour chaque test"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.index_path = self.temp_dir / "test.index"
        
    def tearDown(self):
        """Nettoyage après chaque test"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_without_file(self):
        """Test de l'initialisation sans fichier existant"""
        manager = FaissManager(self.index_path)
        self.assertIsNotNone(manager.index)
        self.assertEqual(manager.dimension, DIMENSION)
        self.assertEqual(manager.index_path, self.index_path)

    def test_init_with_existing_file(self):
        """Test de l'initialisation avec fichier existant"""
        # Créer un index valide et le sauvegarder
        manager1 = FaissManager(self.index_path)
        manager1.save()
        
        # Vérifier qu'on peut le charger
        manager2 = FaissManager(self.index_path)
        self.assertIsNotNone(manager2.index)
        self.assertEqual(manager2.dimension, DIMENSION)
        self.assertEqual(manager2.index_path, self.index_path)

    def test_init_with_error(self):
        """Test de l'initialisation avec erreur de chargement"""
        # Créer un fichier pour que read_index soit appelé
        self.index_path.touch()
        
        with patch('database.faiss_manager.manager.faiss.read_index', side_effect=Exception("Erreur simulée")):
            with self.assertRaises(RuntimeError):
                FaissManager(self.index_path)
    
    def test_save_success(self):
        # Créer un index valide et le sauvegarder
        manager = FaissManager(self.index_path)
        result = manager.save()
        self.assertTrue(result)

    def test_save_error(self):
        # Créer un index valide et le sauvegarder en enlevant l'index
        manager = FaissManager(self.index_path)
        manager.index = None
        result = manager.save()
        self.assertFalse(result)

    def test_train_and_add_success(self):
        # Créer un index valide et le sauvegarder
        manager = FaissManager(self.index_path)
        manager.save()

        # Créer 2000 embeddings différents
        embeddings = []
        ids = []
        for i in range(2000):
            embedding = [(i * 0.1) % 1.0] * DIMENSION  # Valeurs différentes pour chaque embedding
            embeddings.append(embedding)
            ids.append(i)
        
        # Entraîner l'index avec suffisamment de données
        success = manager.train(embeddings)
        self.assertTrue(success)
        
        # Ajouter les embeddings
        manager.add(embeddings, ids)
        
        # Vérifier que l'index contient bien les éléments
        self.assertEqual(manager.index.ntotal, 2000)

    def test_train_error(self):
        # Créer un index valide et le sauvegarder
        manager = FaissManager(self.index_path)
        manager.save()

        # Créer 30 embeddings différents
        embeddings = []
        ids = []
        for i in range(30):
            embedding = [(i * 0.1) % 1.0] * DIMENSION  # Valeurs différentes pour chaque embedding
            embeddings.append(embedding)
            ids.append(i)

        result = manager.train(embeddings)
        self.assertFalse(result)

        # rendre l'index en None
        manager.index = None

        # Créer 2000 embeddings différents
        embeddings = []
        ids = []
        for i in range(2000):
            embedding = [(i * 0.1) % 1.0] * DIMENSION  # Valeurs différentes pour chaque embedding
            embeddings.append(embedding)
            ids.append(i)

        result = manager.train(embeddings)
        self.assertFalse(result)

    def test_reset(self):
        # Créer un index valide et le sauvegarder
        manager = FaissManager(self.index_path)
        manager.save()

        # Créer 2000 embeddings différents
        embeddings = []
        ids = []
        for i in range(2000):
            embedding = [(i * 0.1) % 1.0] * DIMENSION  # Valeurs différentes pour chaque embedding
            embeddings.append(embedding)
            ids.append(i)
        
        # Entraîner l'index avec suffisamment de données
        manager.train(embeddings)
        
        # Ajouter les embeddings
        manager.add(embeddings, ids)
        self.assertEqual(manager.index.ntotal, 2000)
        
        # Réinitialiser l'index
        manager.reset()
        self.assertEqual(manager.index.ntotal, 0)

    def test_stat(self):
        # Créer un index valide et le sauvegarder
        manager = FaissManager(self.index_path)
        manager.save()
        
        # Vérifier les statistiques
        stats = manager.stats()
        self.assertIsNotNone(stats)

        manager.index = None
        stats = manager.stats()
        self.assertDictEqual(stats, {'available': False})

    def test_search_success(self):
        # Créer un index valide et le sauvegarder
        manager = FaissManager(self.index_path)
        manager.save()

        # Créer 2000 embeddings différents
        embeddings = []
        ids = []
        for i in range(2000):
            embedding = [(i * 0.1) % 1.0] * DIMENSION  # Valeurs différentes pour chaque embedding
            embeddings.append(embedding)
            ids.append(i)
        
        # Entraîner l'index avec suffisamment de données
        manager.train(embeddings)
        
        # Ajouter les embeddings
        manager.add(embeddings, ids)
        self.assertEqual(manager.index.ntotal, 2000)
        
        # Vérifier la recherche
        results = manager.search([0.1] * DIMENSION, k=5)
        self.assertEqual(len(results), 5)

    def test_search_failure(self):
        # Créer un index valide et le sauvegarder
        manager = FaissManager(self.index_path)
        manager.save()
        
        # Vérifier la recherche
        results = manager.search([0.1] * DIMENSION, k=5)
        self.assertEqual(len(results), 0)

        # Créer 2000 embeddings différents
        embeddings = []
        ids = []
        for i in range(2000):
            embedding = [(i * 0.1) % 1.0] * DIMENSION  # Valeurs différentes pour chaque embedding
            embeddings.append(embedding)
            ids.append(i)
        
        # Entraîner l'index avec suffisamment de données
        manager.train(embeddings)
        
        # Ajouter les embeddings
        manager.add(embeddings, ids)
        self.assertEqual(manager.index.ntotal, 2000)

        # Test sans index
        manager.index = None
        results = manager.search([0.1] * DIMENSION, k=5)
        self.assertEqual(len(results), 0)

if __name__ == '__main__':
    unittest.main()
