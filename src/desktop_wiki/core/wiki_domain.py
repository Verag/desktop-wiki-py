import sqlite3
import time
import platform
import os
import logging
from pathlib import Path
import shutil
import subprocess
import tempfile
import re
from typing import Dict, Optional, List, Tuple
from collections import defaultdict


# Module-level logger setup (can be overridden by the application)
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-7s | %(name)s | %(message)s'
    )


class WikiError(Exception):
    """Base exception for all wiki-specific errors"""
    pass


class ValidationError(WikiError):
    """Raised when input validation fails (title or content)"""
    pass


class DatabaseError(WikiError):
    """Raised when a database operation fails (IO, schema, etc.)"""
    pass


class WikiDB:
    """
    Persistence layer for a personal desktop Wiki application.

    Key improvements in this refactored version:
    - Single long-lived SQLite connection (better performance)
    - WAL mode enabled (recommended for desktop single-user scenarios)
    - Backup only on demand (not on every save – avoids unnecessary I/O)
    - Realistic validation rules for personal use
    - More informative logging (INFO for normal operations)
    - Context manager support (with WikiDB(...) as db: ...)
    - Explicit close() method
    """

    # Adjustable constants
    MAX_TITLE_LENGTH = 255
    MAX_CONTENT_LENGTH = 1_000_000      # 1 MB – plenty for personal use
    MIN_CONTENT_LENGTH = 3              # Very low minimum – user convenience
    DB_FILENAME_DEFAULT = "wiki.db"

    def __init__(
        self,
        db_path: str | Path | None = None,
        read_only: bool = False,
        create_if_not_exists: bool = True
    ):
        """
        Initialize SQLite connection.

        Args:
            db_path: Path to the .db file (or ":memory:" for tests)
                     None → uses current directory + default filename
            read_only: Open database in read-only mode
            create_if_not_exists: Create file and schema if missing
        """
        if db_path is None:
            db_path = Path.cwd() / self.DB_FILENAME_DEFAULT
        elif isinstance(db_path, str):
            db_path = Path(db_path)

        self.db_path = db_path.resolve()
        self._conn: Optional[sqlite3.Connection] = None
        self._read_only = read_only

        try:
            uri_flag = "?mode=ro" if read_only else ""
            self._conn = sqlite3.connect(
                f"{self.db_path}{uri_flag}",
                check_same_thread=False,           # Usually single-threaded in desktop apps
                timeout=10
            )
            self._conn.row_factory = sqlite3.Row   # Returns dict-like rows

            # Recommended PRAGMA settings for desktop use
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA synchronous = NORMAL")   # Good speed/safety balance
            self._conn.execute("PRAGMA cache_size = -64000")     # ~64 MB page cache

            logger.info("SQLite connection opened: %s (WAL mode)", self.db_path)

            if create_if_not_exists and not read_only:
                self._init_schema()

        except sqlite3.Error as e:
            logger.error("Failed to open database: %s", e, exc_info=True)
            raise DatabaseError(f"Could not open database: {e}") from e

    def _init_schema(self) -> None:
        """Create tables if they do not exist"""
        try:
            with self._conn:
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS pages (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        title       TEXT UNIQUE NOT NULL COLLATE NOCASE,
                        content     TEXT NOT NULL,
                        created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                        updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
                    )
                """)

                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS logs (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        action      TEXT NOT NULL,
                        page_title  TEXT NOT NULL,
                        timestamp   TEXT NOT NULL DEFAULT (datetime('now')),
                        machine     TEXT NOT NULL
                    )
                """)

                # Optional index – helps when browsing history by page
                self._conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_logs_title
                    ON logs (page_title, timestamp DESC)
                """)

            logger.info("Database schema checked/created successfully")

        except sqlite3.Error as e:
            raise DatabaseError("Failed to initialize schema") from e

    def close(self) -> None:
        """Explicitly close the database connection (good practice)"""
        if self._conn is not None:
            try:
                self._conn.close()
                logger.info("SQLite connection closed")
            except sqlite3.Error:
                logger.warning("Error while closing connection", exc_info=True)
            finally:
                self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ───────────────────────────────────────────────
    #                Validation
    # ───────────────────────────────────────────────

    def _validate_title(self, title: str) -> str:
        title = (title or "").strip()
        if not title:
            raise ValidationError("Title cannot be empty")
        if len(title) > self.MAX_TITLE_LENGTH:
            raise ValidationError(f"Title too long (max {self.MAX_TITLE_LENGTH} characters)")

        invalid = r'\/:*?"<>|'
        if any(c in invalid for c in title):
            raise ValidationError(f"Title contains invalid characters: {invalid}")

        return title

    def _validate_content(self, content: str) -> str:
        content = (content or "").strip()
        if len(content) < self.MIN_CONTENT_LENGTH:
            raise ValidationError(f"Content too short (min {self.MIN_CONTENT_LENGTH} characters)")
        if len(content) > self.MAX_CONTENT_LENGTH:
            raise ValidationError(f"Content exceeds limit ({self.MAX_CONTENT_LENGTH//1000} kB)")
        return content

    # ───────────────────────────────────────────────
    #                Core operations
    # ───────────────────────────────────────────────

    def get_page(self, title: str) -> Optional[Tuple[str, str]]:
        """Return (title, content) tuple or None if page does not exist"""
        title = self._validate_title(title)

        try:
            cursor = self._conn.execute(
                "SELECT title, content FROM pages WHERE title = ? COLLATE NOCASE",
                (title,)
            )
            row = cursor.fetchone()
            return (row["title"], row["content"]) if row else None

        except sqlite3.Error as e:
            logger.error("Failed to read page '%s': %s", title, e)
            raise DatabaseError("Error fetching page") from e

    def get_all_titles(self) -> List[str]:
        """Return sorted list of all page titles"""
        try:
            cursor = self._conn.execute(
                "SELECT title FROM pages ORDER BY title COLLATE NOCASE"
            )
            return [row["title"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseError("Error listing titles") from e

    def save_page(self, title: str, content: str, *, backup_before: bool = False) -> bool:
        """
        Create or update a page.

        Args:
            backup_before: If True, creates a backup before saving (default: False)
                           Use sparingly – slow on large files
        """
        title_clean = self._validate_title(title)
        content_clean = self._validate_content(content)

        if backup_before:
            self.create_backup()

        try:
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            machine = platform.node() or "unknown"

            with self._conn:  # Atomic transaction
                self._conn.execute(
                    """
                    INSERT INTO pages (title, content, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(title) DO UPDATE SET
                        content=excluded.content,
                        updated_at=excluded.updated_at
                    """,
                    (title_clean, content_clean, now)
                )

                self._conn.execute(
                    """
                    INSERT INTO logs (action, page_title, timestamp, machine)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("Save/Update", title_clean, now, machine)
                )

            logger.info("Page saved/updated: %s (%d characters)", title_clean, len(content_clean))
            return True

        except sqlite3.Error as e:
            logger.error("Failed to save page '%s': %s", title, e)
            raise DatabaseError(f"Error saving '{title}'") from e

    def create_backup(self, suffix: str = ".bak") -> Path:
        """Create a copy of the database file"""
        if ":memory:" in str(self.db_path):
            logger.warning("Backup skipped: in-memory database")
            return None

        backup_path = self.db_path.with_suffix(self.db_path.suffix + suffix)
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info("Backup created: %s", backup_path)
            return backup_path
        except OSError as e:
            logger.error("Backup creation failed: %s", e)
            raise DatabaseError("Failed to create backup") from e

    def vacuum(self) -> None:
        """Run VACUUM to reclaim space and optimize the database"""
        try:
            self._conn.execute("VACUUM")
            logger.info("VACUUM executed successfully")
        except sqlite3.Error as e:
            logger.warning("VACUUM failed (may be normal if in use): %s", e)
