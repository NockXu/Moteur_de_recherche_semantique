import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from database.DbService import DbService
from database.sqlite.manager import SqliteManager
from database.faiss_manager.manager import FaissManager
from common.Image_Classes.Image import Image, ProcessingStatus
from common.Dataset_Classes.Dataset import Dataset


class TestDbService(unittest.TestCase):
    """Tests pour la classe DbService"""

    def setUp(self):
        """Setup pour chaque test"""
        # Créer des fichiers temporaires pour les tests
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test.db")
        self.test_faiss_path = os.path.join(self.temp_dir, "test.faiss")

    def tearDown(self):
        """Nettoyage après chaque test"""
        # Nettoyer les fichiers temporaires
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Réinitialiser le singleton
        DbService._instance = None

    @patch('database.DbService.DATABASE_FILE')
    @patch('database.DbService.FAISS_INDEX_FILE')
    def test_singleton_pattern(self, mock_faiss_file, mock_db_file):
        """Test que DbService est bien un singleton"""
        mock_db_file.return_value = self.test_db_path
        mock_faiss_file.return_value = self.test_faiss_path
        
        # Créer deux instances
        db1 = DbService()
        db2 = DbService()
        
        # Vérifier que ce sont les mêmes objets
        self.assertIs(db1, db2)
        self.assertEqual(id(db1), id(db2))

    @patch('database.DbService.DATABASE_FILE')
    @patch('database.DbService.FAISS_INDEX_FILE')
    def test_initialization(self, mock_db_file, mock_faiss_file):
        """Test l'initialisation correcte des attributs"""
        mock_db_file.return_value = self.test_db_path
        mock_faiss_file.return_value = self.test_faiss_path
        
        db = DbService()
        
        # Vérifier que les attributs existent et sont du bon type
        self.assertIsInstance(db.sqlite, SqliteManager)
        self.assertIsInstance(db.faiss, FaissManager)
        
        # Vérifier que l'instance a été créée avec succès
        self.assertIsNotNone(db.sqlite)
        self.assertIsNotNone(db.faiss)

    @patch('database.DbService.DATABASE_FILE')
    @patch('database.DbService.FAISS_INDEX_FILE')
    def test_multiple_calls_same_instance(self, mock_faiss_file, mock_db_file):
        """Test que plusieurs appels retournent la même instance avec mêmes attributs"""
        mock_db_file.return_value = self.test_db_path
        mock_faiss_file.return_value = self.test_faiss_path
        
        # Créer plusieurs instances
        db1 = DbService()
        db2 = DbService()
        
        # Vérifier que les attributs sont les mêmes
        self.assertIs(db1.sqlite, db2.sqlite)
        self.assertIs(db1.faiss, db2.faiss)

    def test_instance_creation_only_once(self):
        """Test que l'instance n'est créée qu'une seule fois"""
        # Réinitialiser le singleton avant le test
        DbService._instance = None
        
        with patch('database.DbService.DATABASE_FILE', self.test_db_path), \
             patch('database.DbService.FAISS_INDEX_FILE', self.test_faiss_path):
            
            # Créer plusieurs instances
            db1 = DbService()
            db2 = DbService()
            db3 = DbService()
            
            # Vérifier que toutes les instances sont les mêmes
            self.assertIs(db1, db2)
            self.assertIs(db2, db3)
            self.assertIs(db1, db3)
            
            # Vérifier que les attributs sont partagés
            self.assertIs(db1.sqlite, db2.sqlite)
            self.assertIs(db2.sqlite, db3.sqlite)
            self.assertIs(db1.faiss, db2.faiss)
            self.assertIs(db2.faiss, db3.faiss)

    @patch('database.DbService.DATABASE_FILE')
    @patch('database.DbService.FAISS_INDEX_FILE')
    def test_type_vars(self, mock_faiss_file, mock_db_file):
        """Test que les TypeVars sont correctement utilisés"""
        mock_db_file.return_value = self.test_db_path
        mock_faiss_file.return_value = self.test_faiss_path
        
        db = DbService()
        
        # Vérifier que les types sont corrects (runtime checking)
        self.assertTrue(hasattr(db, 'sqlite'))
        self.assertTrue(hasattr(db, 'faiss'))
        
        # Les attributs doivent être des instances des classes attendues
        self.assertIsInstance(db.sqlite, SqliteManager)
        self.assertIsInstance(db.faiss, FaissManager)

    @patch('database.DbService.DATABASE_FILE')
    @patch('database.DbService.FAISS_INDEX_FILE')
    def test_instance_persistence_across_operations(self, mock_faiss_file, mock_db_file):
        """Test que l'instance persiste à travers différentes opérations"""
        mock_db_file.return_value = self.test_db_path
        mock_faiss_file.return_value = self.test_faiss_path
        
        # Créer une instance
        db1 = DbService()
        sqlite1 = db1.sqlite
        
        # Simuler des opérations
        db2 = DbService()
        sqlite2 = db2.sqlite
        
        # Vérifier que c'est toujours la même instance SqliteManager
        self.assertIs(sqlite1, sqlite2)
        self.assertIs(db1, db2)

    def test_reset_singleton_for_testing(self):
        """Test la réinitialisation du singleton pour les tests"""
        # Créer une première instance
        with patch('database.DbService.DATABASE_FILE', self.test_db_path), \
             patch('database.DbService.FAISS_INDEX_FILE', self.test_faiss_path):
            db1 = DbService()
            
            # Réinitialiser manuellement (comme dans tearDown)
            DbService._instance = None
            
            # Créer une nouvelle instance
            db2 = DbService()
            
            # Ce ne devrait pas être les mêmes objets
            self.assertIsNot(db1, db2)


if __name__ == '__main__':
    unittest.main()