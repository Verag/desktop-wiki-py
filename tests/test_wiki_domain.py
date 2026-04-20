import unittest
import sqlite3
import os
from unittest.mock import patch

from desktop_wiki.core import wiki_domain
from src.desktop_wiki.core.wiki_domain import WikiDB, ValidationError, DatabaseError  

class TestWikiDB(unittest.TestCase):
    """Unit tests for WikiDB domain class"""

    def setUp(self):
        """Run before each test: create in-memory DB"""
        self.db = WikiDB(db_name=":memory:")

    # ──────────────────────────────
    # Initialization / schema tests
    # ──────────────────────────────
    def test_init_db_creates_tables(self):
        """Tables 'pages' and 'logs' should exist"""
        with sqlite3.connect(self.db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='pages'"
            )
            self.assertIsNotNone(cursor.fetchone(), "Table 'pages' not found")
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='logs'"
            )
            self.assertIsNotNone(cursor.fetchone(), "Table 'logs' not found")

    # ──────────────────────────────
    # Title validation tests
    # ──────────────────────────────
    def test_validate_title_valid(self):
        title = self.db._validate_title("My Page")
        self.assertEqual(title, "My Page")

    def test_validate_title_empty_raises(self):
        with self.assertRaises(ValidationError):
            self.db._validate_title("  ")

    def test_validate_title_too_long_raises(self):
        with self.assertRaises(ValidationError):
            self.db._validate_title("a" * 300)

    def test_validate_title_invalid_chars_raises(self):
        for t in ["Invalid/Title", "Bad*Char"]:
            with self.assertRaises(ValidationError):
                self.db._validate_title(t)

    # ──────────────────────────────
    # Content validation tests
    # ──────────────────────────────
    def test_validate_content_valid(self):
        content = "This is a valid content with more than twenty characters."
        validated = self.db._validate_content(content)
        self.assertEqual(validated, content)

    def test_validate_content_empty_raises(self):
        with self.assertRaises(ValidationError):
            self.db._validate_content("   \n\n")

    def test_validate_content_too_short_raises(self):
        with self.assertRaises(ValidationError):
            self.db._validate_content("short")

    def test_validate_content_forbidden_pattern_raises(self):
        bad_content = "This contains <script>alert('xss')</script>"
        with self.assertRaises(ValidationError):
            self.db._validate_content(bad_content)

    def test_validate_content_incomplete_raises(self):
        incomplete = "Tiny"
        with self.assertRaises(ValidationError):
            self.db._validate_content(incomplete)

    # ──────────────────────────────
    # Save / Get page tests
    # ──────────────────────────────
    def test_save_and_get_page_new(self):
        title = "Test Page"
        content = "This is valid content for a new page."
        self.db.save_page(title, content)

        page = self.db.get_page(title)
        self.assertIsNotNone(page)
        self.assertEqual(page[0], title)
        self.assertEqual(page[1], content)

    def test_save_and_get_page_update(self):
        title = "Update Page"
        content1 = "Version 1 with valid content."
        content2 = "Updated content, version 2."

        self.db.save_page(title, content1)
        self.db.save_page(title, content2)

        page = self.db.get_page(title)
        self.assertEqual(page[1], content2)

    def test_save_page_invalid_title_raises(self):
        with self.assertRaises(ValidationError):
            self.db.save_page("", "Valid content with enough length.")

    def test_save_page_invalid_content_raises(self):
        with self.assertRaises(ValidationError):
            self.db.save_page("Valid Title", "bad")

    def test_get_page_non_existent_returns_none(self):
        page = self.db.get_page("Non Existent")
        self.assertIsNone(page)

    # ──────────────────────────────
    # get_all_titles tests
    # ──────────────────────────────
    def test_get_all_titles_empty_db(self):
        self.assertEqual(self.db.get_all_titles(), [])

    def test_get_all_titles_after_save(self):
        pages = {
            "First": "Content line for First page.",
            "Second": "Content for Second page.",
            "Album": "Content for Album page."
        }
        for t, c in pages.items():
            self.db.save_page(t, c)

        titles = self.db.get_all_titles()
        self.assertEqual(sorted(titles), sorted(pages.keys()))

    # ──────────────────────────────
    # Backup tests (mocked)
    # ──────────────────────────────
    @patch("shutil.copy2")
    def test_backup_db_called_before_save(self, mock_copy):
        temp_db = WikiDB(db_name="temp_test.db")
        try:
            temp_db.save_page("Backup Test", "Valid content line for backup test.")
            mock_copy.assert_called_once()
        finally:
            # Cleanup
            for file in ["temp_test.db", "temp_test.db.bak"]:
                if os.path.exists(file):
                    os.remove(file)

    # ──────────────────────────────
    # Export tests (mocked minimal)
    # ──────────────────────────────
    def test_export_all_pages_to_html(self):
        # Save a couple of pages
        self.db.save_page("Page 1", "Valid content line for Page 1.")
        self.db.save_page("Page 2", "Valid content line for Page 2.")

        # Export HTML
        html_path = "test_export.html"
        try:
            self.db.export_all_pages_to_html(html_path)
            self.assertTrue(os.path.exists(html_path))
            with open(html_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Page 1", content)
            self.assertIn("Page 2", content)
        finally:
            if os.path.exists(html_path):
                os.remove(html_path)


if __name__ == "__main__":
    unittest.main()
