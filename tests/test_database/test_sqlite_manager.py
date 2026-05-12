import unittest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

from database.sqlite.manager import SqliteManager


class TestSqliteManager(unittest.TestCase):
    """Tests complets pour SqliteManager"""

    def setUp(self):
        """Initialisation pour chaque test"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test.db"
        
    def tearDown(self):
        """Nettoyage après chaque test"""
        import shutil
        import gc
        import time
        
        # Forcer le garbage collection pour libérer les connexions
        gc.collect()
        
        # Attendre un peu pour que SQLite libère les verrous
        time.sleep(0.2)
        
        # Supprimer le dossier temporaire de manière plus robuste
        try:
            shutil.rmtree(self.temp_dir)
        except:
            # Si ça échoue, attendre et réessayer
            time.sleep(0.5)
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except:
                pass

    def test_init(self):
        """Test initialisation"""
        self.manager = SqliteManager(str(self.db_path))
        self.assertEqual(self.manager.db_path, self.db_path)
        self.assertIsNotNone(self.manager.conn)
        self.assertIsNotNone(self.manager.cursor)
        self.assertTrue(self.db_path.exists())

    def test_init_without_path(self):
        """Test initialisation sans paramètre (utilise get_database_path par défaut)"""
        self.manager = SqliteManager()
        
        # Vérifie que get_database_path() a été utilisé
        from storage.config import get_database_path
        expected_path = get_database_path()
        
        self.assertEqual(str(self.manager.db_path), expected_path)
        self.assertIsNotNone(self.manager.conn)
        self.assertIsNotNone(self.manager.cursor)

    @patch('database.sqlite.manager.get_database_path')
    def test_init_with_mocked_none_path(self, mock_get_path):
        """Test initialisation avec get_database_path retournant None"""
        mock_get_path.return_value = None
        
        with self.assertRaises(Exception) as context:
            SqliteManager()
        
        mock_get_path.assert_called_once()
        self.assertIn("db_path cannot be None", str(context.exception))

    @patch('sqlite3.connect')
    def test_init_connection_error(self, mock_connect):
        """Test initialisation avec erreur de connexion SQLite"""
        mock_connect.side_effect = sqlite3.OperationalError("Unable to open database file")
        
        with self.assertRaises(RuntimeError) as context:
            SqliteManager(str(self.db_path))
        
        self.assertIn("Error initializing database", str(context.exception))
        self.assertIn("Unable to open database file", str(context.exception))
    
    def test_connect_error(self):
        """Test erreur de connexion SQLite"""
        # Créer un manager valide
        manager = SqliteManager(str(self.db_path))
        
        # Fermer la connexion existante
        manager.conn = None
        manager.cursor = None
        
        # Mock sqlite3.connect pour lever une exception lors de connect()
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.OperationalError("Connection failed")
            
            with self.assertRaises(RuntimeError) as context:
                manager.connect()
            
            self.assertIn("Erreur connexion SQLite", str(context.exception))
            self.assertIn("Connection failed", str(context.exception))
        
    def test_close(self):
        """Test fermeture de la connexion"""
        self.manager = SqliteManager(str(self.db_path))
        
        # Vérifier que la connexion est ouverte
        self.assertIsNotNone(self.manager.conn)
        self.assertIsNotNone(self.manager.cursor)
        
        # Fermer la connexion
        self.manager.close()
        
        # Vérifier que la connexion est fermée (sqlite3 ne met pas conn à None)
        # On vérifie plutôt que la connexion est bien fermée
        try:
            # Tenter d'utiliser la connexion fermée devrait lever une erreur
            self.manager.cursor.execute("SELECT 1")
            self.fail("La connexion devrait être fermée")
        except sqlite3.ProgrammingError:
            # C'est normal, la connexion est fermée
            pass

    def test_execute_success(self):
        """Test exécution d'une requête"""
        manager = SqliteManager(str(self.db_path))
        
        manager.begin()

        # Créer une table
        manager.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
        
        # Insérer des données
        manager.execute("INSERT INTO test (name) VALUES (?)", ("test",))
        
        manager.commit()

        # Vérifier que la donnée a été insérée avec fetch_one
        result = manager.fetch_one("SELECT * FROM test")
        self.assertEqual(result[1], "test")
    
    def test_execute_error(self):
        """Test erreur d'exécution d'une requête"""
        manager = SqliteManager(str(self.db_path))
        
        # Tenter d'exécuter une requête SQL invalide
        with self.assertRaises(RuntimeError) as context:
            manager.execute("INVALID SQL SYNTAX")
        
        self.assertIn("SQL error", str(context.exception))

    def test_executemany_success(self):
        """Test exécution multiple de requêtes"""
        manager = SqliteManager(str(self.db_path))
        
        # Créer une table
        manager.execute("CREATE TABLE IF NOT EXISTS test_batch (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)")
        
        # Insérer plusieurs lignes
        data = [
            ("name1", 10),
            ("name2", 20),
            ("name3", 30)
        ]
        manager.executemany("INSERT INTO test_batch (name, value) VALUES (?, ?)", data)
        
        # Vérifier les insertions
        results = manager.fetch_all("SELECT name, value FROM test_batch ORDER BY id")
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], ("name1", 10))
        self.assertEqual(results[1], ("name2", 20))
        self.assertEqual(results[2], ("name3", 30))

    def test_executemany_error(self):
        """Test erreur d'exécution multiple"""
        manager = SqliteManager(str(self.db_path))
        
        # Tenter d'exécuter une requête SQL invalide
        with self.assertRaises(RuntimeError) as context:
            manager.executemany("INVALID SYNTAX", [("data",)])
        
        self.assertIn("SQL error", str(context.exception)) 

    def test_rollback(self):
        """Test rollback de transaction"""
        manager = SqliteManager(str(self.db_path))
        
        # Créer la table en dehors de la transaction
        manager.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
        
        manager.begin()
        
        # Insérer des données dans la transaction
        manager.execute("INSERT INTO test (name) VALUES (?)", ("test",))
        
        manager.rollback()

        # Vérifier que la donnée n'a pas été insérée
        result = manager.fetch_one("SELECT * FROM test")
        self.assertIsNone(result)

    def test_context_manager_success(self):
        """Test utilisation comme context manager (succès)"""
        manager = SqliteManager(str(self.db_path))
        
        # Créer une table
        manager.execute("CREATE TABLE IF NOT EXISTS test_context (id INTEGER PRIMARY KEY, value TEXT)")
        
        # Utiliser comme context manager
        with manager:
            manager.execute("INSERT INTO test_context (value) VALUES (?)", ("context_value",))
        
        # Vérifier que la connexion est fermée après le context manager
        try:
            manager.fetch_one("SELECT 1")
            self.fail("La connexion devrait être fermée")
        except sqlite3.ProgrammingError:
            pass  # Normal, la connexion est fermée
        
        # Créer un nouveau manager pour vérifier les données
        manager2 = SqliteManager(str(self.db_path))
        result = manager2.fetch_one("SELECT value FROM test_context")
        self.assertEqual(result[0], "context_value")

    def test_context_manager_failure(self):
        """Test utilisation comme context manager (échec)"""
        manager = SqliteManager(str(self.db_path))
        
        # Créer une table
        manager.execute("CREATE TABLE IF NOT EXISTS test_context_fail (id INTEGER PRIMARY KEY, value TEXT)")
        
        # Utiliser comme context manager avec une erreur
        try:
            with manager:
                manager.execute("INSERT INTO test_context_fail (value) VALUES (?)", ("value1",))
                manager.execute("INVALID SQL")  # Provoque une erreur
        except:
            pass  # Ignorer l'erreur
        
        # Vérifier que la connexion est fermée après le context manager
        try:
            manager.fetch_one("SELECT 1")
            self.fail("La connexion devrait être fermée")
        except sqlite3.ProgrammingError:
            pass  # Normal, la connexion est fermée
        
        # Créer un nouveau manager pour vérifier que les données sont annulées
        manager2 = SqliteManager(str(self.db_path))
        result = manager2.fetch_one("SELECT value FROM test_context_fail")
        self.assertIsNone(result)

    @patch('sqlite3.connect')
    def test_init_sqlite_error(self, mock_connect):
        """Test erreur dans init_sqlite avec instruction SQL invalide"""
        # Créer un mock de connexion et curseur
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Faire en sorte que execute lève une exception sur la 2ème instruction
        def side_effect(statement):
            if "images" in statement:  # La 2ème instruction CREATE TABLE images
                raise sqlite3.OperationalError("syntax error")
            # Pour les autres instructions, simuler un succès
            return None
        
        mock_cursor.execute.side_effect = side_effect
        
        # Supprimer la base de données pour forcer l'initialisation
        if self.db_path.exists():
            self.db_path.unlink()
        
        # L'initialisation devrait échouer
        with self.assertRaises(Exception) as context:
            from database.sqlite.init import init_sqlite
            init_sqlite()
        
        self.assertIn("Error in statement", str(context.exception))

if __name__ == '__main__':
    unittest.main()
