from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Tuple, Any
import sqlite3

from storage.config import get_database_path


class SqliteManager:
    """Manages SQLite database connection and initialization.

    This class ensures the database exists, creates it if necessary,
    and provides a persistent connection and cursor.

    If no database path is provided, a default path is retrieved via
    `get_database_path()`.

    Args:
        db_path (str | None):
            Path to the SQLite database file.

    Raises:
        Exception:
            If no valid database path can be resolved.

    """

    def __init__(self, db_path: str | None = None):
        # Use default database path if none provided
        if db_path is None:
            db_path = get_database_path()

        if db_path is None:
            raise ValueError("Database path cannot be None")

        self.db_path = Path(db_path)
        self.conn = None
        self.cursor = None

        # Ensure database exists before connecting
        self._ensure_database_exists()

        self.connect()

    # =========================
    # DATABASE INITIALIZATION
    # =========================
    def _ensure_database_exists(self) -> None:
        """Ensure that the SQLite database file exists.

        If the database does not exist, it is automatically initialized.

        Returns:
            None

        """
        if not self.db_path.exists():
            self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize the SQLite database using the initialization SQL script.

        This method creates the database file if it does not exist and executes
        the required SQL schema to set up tables.

        Returns:
            None

        Raises:
            RuntimeError:
                If database initialization fails.

        """
        try:
            import sqlite3
            from database.sqlite.init import CREATE_TABLE_SQL

            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create a dedicated connection for initialization
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Execute each SQL statement separately
            statements = CREATE_TABLE_SQL.split(";")

            for i, statement in enumerate(statements):
                statement = statement.strip()
                if statement:
                    try:
                        cursor.execute(statement)
                    except sqlite3.OperationalError as e:
                        # Ignore "table already exists" errors
                        if "already exists" not in str(e):
                            raise RuntimeError(
                                f"Error in statement {i + 1}: {e}"
                            )

            conn.commit()
            conn.close()

        except Exception as e:
            raise RuntimeError(f"Database initialization failed: {e}")

    # =========================
    # CONNECTION
    # =========================
    def connect(self) -> None:
        """Establish a connection to the SQLite database.

        Creates a connection and cursor for executing SQL queries.
        Thread safety is disabled via `check_same_thread=False`.

        Returns:
            None

        Raises:
            RuntimeError:
                If the database connection fails.

        """
        try:
            self.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self.cursor = self.conn.cursor()

        except Exception as e:
            raise RuntimeError(f"SQLite connection error: {e}")

    def close(self) -> None:
        """Close the SQLite database connection if it exists.

        Returns:
            None

        """
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    # =========================
    # EXECUTION
    # =========================
    def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        """Execute an SQL query on the SQLite database.

        Args:
            query (str):
                SQL query to execute.

            params (Tuple[Any, ...]):
                Parameters to bind to the SQL query.

        Returns:
            None

        Raises:
            RuntimeError:
                If the SQL execution fails.

        """
        try:
            self.cursor.execute(query, params)

        except Exception as e:
            raise RuntimeError(f"SQL execution error: {e}")

    from typing import List, Tuple, Any

    def executemany(self, query: str, params_list: list[tuple[Any, ...]]) -> None:
        """Execute an SQL query multiple times with different parameter sets.

        This method is used for batch inserts or updates and automatically commits
        the transaction after execution.

        Args:
            query (str):
                SQL query to execute.

            params_list (List[Tuple[Any, ...]]):
                List of parameter tuples to bind to the query.

        Returns:
            None

        Raises:
            RuntimeError:
                If the SQL execution fails.

        """
        try:
            self.cursor.executemany(query, params_list)
            self.conn.commit()

        except Exception as e:
            raise RuntimeError(f"SQL executemany error: {e}")

    def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> tuple[Any, ...] | None:
        """Execute an SQL query and return a single result.

        Args:
            query (str):
                SQL query to execute.

            params (Tuple[Any, ...]):
                Parameters to bind to the query.

        Returns:
            A single row from the database, or None if no result is found.

        """
        if self.cursor is None:
            raise RuntimeError("Database connection is closed")

        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    from typing import List, Tuple, Any

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        """Execute an SQL query and return all results.

        Args:
            query (str):
                SQL query to execute.

            params (Tuple[Any, ...]):
                Parameters to bind to the query.

        Returns:
            List of rows returned by the query. Each row is a tuple.

        """
        if self.cursor is None:
            raise RuntimeError("Database connection is closed")

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    # =========================
    # TRANSACTIONS
    # =========================
    def begin(self) -> None:
        """Begin a new database transaction.

        Returns:
            None

        """
        self.conn.execute("BEGIN")


    def commit(self) -> None:
        """Commit the current transaction.

        Returns:
            None

        """
        self.conn.commit()


    def rollback(self) -> None:
        """Roll back the current transaction.

        Returns:
            None

        """
        self.conn.rollback()

    # =========================
    # CONTEXT MANAGER
    # =========================
    def __enter__(self) -> SqliteManager:
        """Enter the runtime context related to this object.

        Returns:
            The current instance for use in a `with` statement.

        """
        return self


    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the runtime context and handle transaction finalization.

        If an exception occurred, the transaction is rolled back.
        Otherwise, it is committed. The database connection is then closed.

        Args:
            exc_type (type | None):
                Exception type if raised, otherwise None.

            exc_val (BaseException | None):
                Exception value if raised, otherwise None.

            exc_tb (traceback | None):
                Traceback object if an exception occurred.

        Returns:
            None

        """
        if exc_type:
            self.rollback()
        else:
            self.commit()

        self.close()

if __name__ == "__main__":
    manager = SqliteManager(get_database_path())