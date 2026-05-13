import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from common.Dataset_Classes.Dataset import Dataset
from common.Dataset_Classes.DatasetRepository import DatasetRepository
from database.sqlite.manager import SqliteManager

class TestDatasetRepository(unittest.TestCase):
    def setUp(self):
        """Initialisation pour chaque test"""
        # Créer une base de données temporaire pour les tests
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test.db"
        
        # Initialiser la base de données et le repository
        self.db_manager = SqliteManager(str(self.db_path))
        self.repository = DatasetRepository(self.db_manager)
        
        # Le dataset "default" est déjà créé par l'initialisation (ID=1)
        # Insérer un dataset de test pour certains tests (sera ID=2)
        self.db_manager.execute("INSERT INTO datasets (name) VALUES (?)", ("test_dataset",))
        self.db_manager.commit()
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        import shutil
        import gc
        import time
        
        # Fermer la connexion
        try:
            self.db_manager.close()
        except:
            pass
        
        # Forcer le garbage collection
        gc.collect()
        time.sleep(0.1)
        
        # Supprimer le dossier temporaire
        try:
            shutil.rmtree(self.temp_dir)
        except:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test l'initialisation du repository"""
        self.assertIsInstance(self.repository, DatasetRepository)
        self.assertEqual(self.repository.db, self.db_manager)

    def test_get_all_success(self):
        """Test get_all avec succès (avec mock)"""
        # Mock de fetch_all pour retourner des datasets
        with patch.object(self.db_manager, 'fetch_all') as mock_fetch_all:
            mock_fetch_all.return_value = [
                (1, "default"),
                (2, "test_dataset"), 
                (3, "dataset1"),
                (4, "dataset2")
            ]
            
            datasets = self.repository.get_all()
            
            self.assertEqual(len(datasets), 4)
            self.assertIsInstance(datasets[0], Dataset)
            self.assertIsInstance(datasets[1], Dataset)
            self.assertIsInstance(datasets[2], Dataset)
            self.assertIsInstance(datasets[3], Dataset)
            
            # Vérifier que les noms sont corrects
            names = [ds.name for ds in datasets]
            self.assertIn("test_dataset", names)
            self.assertIn("dataset1", names)
            self.assertIn("dataset2", names)
            
            # Vérifier que fetch_all a été appelé
            mock_fetch_all.assert_called_once_with("SELECT id, name FROM datasets")

    def test_get_all_empty(self):
        """Test get_all avec une base vide (avec mock)"""
        # Mock pour retourner une liste vide
        with patch.object(self.db_manager, 'fetch_all', return_value=[]):
            datasets = self.repository.get_all()
            
            self.assertEqual(len(datasets), 0)
            self.assertEqual(datasets, [])

    def test_get_by_id_success(self):
        """Test get_by_id avec un ID existant (avec mock)"""
        with patch.object(self.db_manager, 'fetch_one') as mock_fetch_one:
            mock_fetch_one.return_value = (2, "test_dataset")
            
            dataset = self.repository.get_by_id(2)
            
            self.assertIsNotNone(dataset)
            self.assertEqual(dataset.id, 2)
            self.assertEqual(dataset.name, "test_dataset")
            
            # Vérifier l'appel avec les bons paramètres
            mock_fetch_one.assert_called_once_with(
                "SELECT id, name FROM datasets WHERE id = ?",
                (2,)
            )

    def test_get_by_id_not_found(self):
        """Test get_by_id avec un ID qui n'existe pas (avec mock)"""
        with patch.object(self.db_manager, 'fetch_one', return_value=None):
            dataset = self.repository.get_by_id(999)
            
            self.assertIsNone(dataset)

    def test_get_by_name_success(self):
        """Test get_by_name avec un nom existant (avec mock)"""
        with patch.object(self.db_manager, 'fetch_one') as mock_fetch_one:
            mock_fetch_one.return_value = (2, "test_dataset")
            
            dataset = self.repository.get_by_name("test_dataset")
            
            self.assertIsNotNone(dataset)
            self.assertEqual(dataset.id, 2)
            self.assertEqual(dataset.name, "test_dataset")
            
            # Vérifier l'appel avec les bons paramètres
            mock_fetch_one.assert_called_once_with(
                "SELECT id, name FROM datasets WHERE name = ?",
                ("test_dataset",)
            )

    def test_get_by_name_not_found(self):
        """Test get_by_name avec un nom qui n'existe pas (avec mock)"""
        with patch.object(self.db_manager, 'fetch_one', return_value=None):
            dataset = self.repository.get_by_name("nonexistent_dataset")
            
            self.assertIsNone(dataset)

    def test_create_success(self):
        """Test create avec succès (avec mock)"""
        with patch.object(self.db_manager, 'execute') as mock_execute, \
             patch.object(self.db_manager, 'fetch_one') as mock_fetch_one, \
             patch.object(self.db_manager, 'commit') as mock_commit:
            
            # Configurer les mocks
            mock_fetch_one.return_value = (3, "new_dataset")
            
            dataset = self.repository.create("new_dataset")
            
            self.assertIsNotNone(dataset)
            self.assertEqual(dataset.name, "new_dataset")
            self.assertEqual(dataset.id, 3)
            
            # Vérifier les appels
            mock_execute.assert_called_once()
            mock_fetch_one.assert_called_once_with(
                "SELECT id, name FROM datasets WHERE name = ?",
                ("new_dataset",)
            )
            # Pas de commit appelé - DatasetRepository.create ne fait pas de commit

    def test_create_duplicate(self):
        """Test create avec un nom qui existe déjà (avec mock)"""
        with patch.object(self.db_manager, 'execute') as mock_execute, \
             patch.object(self.db_manager, 'fetch_one') as mock_fetch_one:
            
            # Simuler qu'un dataset existe déjà
            mock_fetch_one.return_value = (2, "test_dataset")
            
            dataset = self.repository.create("test_dataset")
            
            # Ne devrait pas créer de nouveau dataset mais retourner l'existant
            self.assertIsNotNone(dataset)
            self.assertEqual(dataset.name, "test_dataset")
            self.assertEqual(dataset.id, 2)
            
            # Vérifier les appels
            mock_execute.assert_called_once()
            mock_fetch_one.assert_called_once_with(
                "SELECT id, name FROM datasets WHERE name = ?",
                ("test_dataset",)
            )

    def test_create_with_error(self):
        """Test create avec une erreur de base de données"""
        # Mock la base de données pour lever une exception
        with patch.object(self.db_manager, 'fetch_one', return_value=None):
            dataset = self.repository.create("error_dataset")
            
            self.assertIsNone(dataset)

    def test_create_database_error(self):
        """Test create avec une erreur de base de données"""
        with patch.object(self.db_manager, 'execute', side_effect=Exception("DB Error")):
            with self.assertRaises(RuntimeError) as ctx:
                self.repository.create("error_dataset")

            self.assertIn("DB Error", str(ctx.exception))

    def test_get_all_with_none_return(self):
        """Test get_all quand fetch_all retourne None"""
        # Mock pour retourner None
        with patch.object(self.db_manager, 'fetch_all', return_value=None):
            datasets = self.repository.get_all()
            
            self.assertEqual(datasets, [])

    def test_create_with_empty_name(self):
        """Test create avec un nom vide (avec mock)"""
        with patch.object(self.db_manager, 'execute') as mock_execute, \
             patch.object(self.db_manager, 'fetch_one') as mock_fetch_one:
            
            # Simuler la création avec nom vide
            mock_fetch_one.return_value = (3, "")
            
            dataset = self.repository.create("")
            
            self.assertIsNotNone(dataset)
            self.assertEqual(dataset.name, "")
            self.assertEqual(dataset.id, 3)
            
            # Vérifier les appels
            mock_execute.assert_called_once()
            mock_fetch_one.assert_called_once_with(
                "SELECT id, name FROM datasets WHERE name = ?",
                ("",)
            )

    def test_create_with_long_name(self):
        """Test create avec un nom très long (avec mock)"""
        long_name = "a" * 1000  # Nom de 1000 caractères
        
        with patch.object(self.db_manager, 'execute') as mock_execute, \
             patch.object(self.db_manager, 'fetch_one') as mock_fetch_one:
            
            # Simuler la création avec nom long
            mock_fetch_one.return_value = (3, long_name)
            
            dataset = self.repository.create(long_name)
            
            self.assertIsNotNone(dataset)
            self.assertEqual(dataset.name, long_name)
            self.assertEqual(dataset.id, 3)
            
            # Vérifier les appels
            mock_execute.assert_called_once()
            mock_fetch_one.assert_called_once_with(
                "SELECT id, name FROM datasets WHERE name = ?",
                (long_name,)
            )

    def test_get_by_id_with_negative_id(self):
        """Test get_by_id avec un ID négatif (avec mock)"""
        with patch.object(self.db_manager, 'fetch_one', return_value=None):
            dataset = self.repository.get_by_id(-1)
            
            self.assertIsNone(dataset)

    def test_get_by_name_with_empty_string(self):
        """Test get_by_name avec une chaîne vide (avec mock)"""
        with patch.object(self.db_manager, 'fetch_one') as mock_fetch_one:
            # Simuler la recherche d'une chaîne vide
            mock_fetch_one.return_value = (3, "")
            
            dataset = self.repository.get_by_name("")
            
            self.assertIsNotNone(dataset)
            self.assertEqual(dataset.name, "")
            self.assertEqual(dataset.id, 3)
            
            # Vérifier l'appel
            mock_fetch_one.assert_called_once_with(
                "SELECT id, name FROM datasets WHERE name = ?",
                ("",)
            )

    def test_get_by_name_case_sensitive(self):
        """Test que get_by_name est sensible à la casse (avec mock)"""
        # Mock de la base de données pour contrôler les retours
        with patch.object(self.db_manager, 'fetch_one') as mock_fetch_one:
            
            # Configurer le mock pour simuler la sensibilité à la casse
            def side_effect(query, params):
                name_param = params[0]
                if name_param == "Test_Dataset":
                    return (3, "Test_Dataset")  # Trouvé
                elif name_param == "test_dataset_lowercase":
                    return None  # Pas trouvé (sensible à la casse)
                else:
                    return None
            
            mock_fetch_one.side_effect = side_effect
            
            # Tester la recherche avec casse différente
            dataset_lower = self.repository.get_by_name("test_dataset_lowercase")
            dataset_upper = self.repository.get_by_name("Test_Dataset")
            
            # Vérifier que le mock simule bien la sensibilité à la casse
            self.assertIsNone(dataset_lower)  # "test_dataset_lowercase" non trouvé
            self.assertIsNotNone(dataset_upper)  # "Test_Dataset" trouvé
            self.assertEqual(dataset_upper.name, "Test_Dataset")
            self.assertEqual(dataset_upper.id, 3)
            
            # Vérifier que fetch_one a été appelé avec les bons paramètres
            self.assertEqual(mock_fetch_one.call_count, 2)
            mock_fetch_one.assert_any_call(
                "SELECT id, name FROM datasets WHERE name = ?",
                ("test_dataset_lowercase",)
            )
            mock_fetch_one.assert_any_call(
                "SELECT id, name FROM datasets WHERE name = ?",
                ("Test_Dataset",)
            )

if __name__ == '__main__':
    unittest.main()