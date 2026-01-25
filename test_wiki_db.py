import unittest
import sqlite3
import os
from unittest.mock import patch

# Adjust the import based on your main file name
from construct_app_full import WikiDB  # Replace "wiki_app" with your actual main file/module name


class TestWikiDB(unittest.TestCase):
    """Unit tests for the WikiDB class"""

    def setUp(self):
        """Executed before each test: creates an in-memory database instance"""
        self.db = WikiDB(db_name=":memory:")  # Temporary in-memory DB
        # Clean any existing data (though :memory: starts fresh)
        """ with sqlite3.connect(self.db.db_name) as conn:
            conn.execute("DELETE FROM pages")
            conn.execute("DELETE FROM logs")
            conn.commit() """

    def tearDown(self):
        """Executed after each test"""
        # Not strictly needed with :memory:, but good practice
        pass

    # ──────────────────────────────────────────────
    # Initialization and table structure tests
    # ──────────────────────────────────────────────

    def test_init_db_creates_tables(self):
        """Verify that 'pages' and 'logs' tables are created"""
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

    # ──────────────────────────────────────────────
    # validate_title tests
    # ──────────────────────────────────────────────

    def test_validate_title_valid(self):
        self.assertTrue(self.db.validate_title("My Awesome Page"))

    def test_validate_title_empty(self):
        self.assertFalse(self.db.validate_title("   "))

    def test_validate_title_too_long(self):
        long_title = "a" * 300
        self.assertFalse(self.db.validate_title(long_title))

    def test_validate_title_invalid_chars(self):
        self.assertFalse(self.db.validate_title("Page with / slash"))
        self.assertFalse(self.db.validate_title("Title with * asterisk"))

    # ──────────────────────────────────────────────
    # validate_content tests
    # ──────────────────────────────────────────────

    def test_validate_content_valid(self):
        valid_content = "# Title\n\nThis is valid content with more than 20 characters."
        is_valid, msg = self.db.validate_content(valid_content)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")

    def test_validate_content_empty(self):
        is_valid, msg = self.db.validate_content("   \n\n  ")
        self.assertFalse(is_valid)
        self.assertIn("empty", msg.lower())

    def test_validate_content_too_short(self):
        is_valid, msg = self.db.validate_content("hi")
        self.assertFalse(is_valid)

    def test_validate_content_too_long(self):
        long_text = "a" * 150_000
        is_valid, msg = self.db.validate_content(long_text)
        self.assertFalse(is_valid)
        self.assertIn("exceeds", msg.lower())

    def test_validate_content_forbidden_pattern(self):
        bad_content = "This text contains <script>alert('xss')</script>"
        is_valid, msg = self.db.validate_content(bad_content)
        self.assertFalse(is_valid)
        self.assertIn("forbidden", msg.lower())

    # ──────────────────────────────────────────────
    # save_page + get_page (full cycle) tests
    # ──────────────────────────────────────────────

    def test_save_and_get_page_new(self):
        title = "Test Page"
        content = "Unit test content."

        success = self.db.save_page(title, content)
        self.assertTrue(success)

        saved = self.db.get_page(title)
        self.assertIsNotNone(saved)
        self.assertEqual(saved[0], title)
        self.assertEqual(saved[1].strip(), content.strip())

    def test_save_and_get_page_update(self):
        title = "Duplicate Page"
        content1 = "Version 1"
        content2 = "Version 2 updated"

        # First save
        self.db.save_page(title, content1)

        # Update
        success = self.db.save_page(title, content2)
        self.assertTrue(success)

        saved = self.db.get_page(title)
        self.assertEqual(saved[1].strip(), content2)

    def test_save_page_invalid_title(self):
        success = self.db.save_page("", "Some content")
        self.assertFalse(success)

    def test_save_page_invalid_content_empty(self):
        success = self.db.save_page("Valid Title", "   ")
        self.assertFalse(success)

    def test_get_page_non_existent(self):
        result = self.db.get_page("This page does not exist")
        self.assertIsNone(result)

    def test_get_all_titles_empty_db(self):
        titles = self.db.get_all_titles()
        self.assertEqual(titles, [])

    def test_get_all_titles_after_save(self):
        self.db.save_page("First", "abc")
        self.db.save_page("Second Page", "def")
        self.db.save_page("Album", "xyz")

        titles = self.db.get_all_titles()
        self.assertEqual(len(titles), 3)
        # Alphabetically sorted
        self.assertEqual(titles, ["Album", "First", "Second Page"])

    # ──────────────────────────────────────────────
    # Backup test (mocked to avoid real file creation)
    # ──────────────────────────────────────────────

    @patch("shutil.copy2")
    def test_backup_db_called_before_save(self, mock_copy):
        # Use a temp file-based DB just for this test
        temp_db = WikiDB(db_name="temp_test.db")
        try:
            temp_db.save_page("Backup Test", "Content")
            mock_copy.assert_called_once()
        finally:
            # Clean up
            for file in ["temp_test.db", "temp_test.db.bak"]:
                if os.path.exists(file):
                    os.remove(file)


if __name__ == "__main__":
    unittest.main()