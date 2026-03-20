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


    def export_to_mkdocs_site(
        self,
        output_dir: str | Path = "wiki_export_mkdocs",
        site_name: str = "My Personal Wiki",
        site_url: Optional[str] = None,
        use_temp_dir: bool = False,
        clean_before: bool = True,
        build_after_export: bool = True,
        max_nesting_level: int = 4,  # prevents overly deep folder structures
    ) -> Path:
        """
            Exports the entire wiki to a MkDocs + Material for MkDocs static site with natural,
            hierarchical navigation.

            Main improvements over basic flat export:
            - Creates folder structure based on dot namespaces (page.title.subpage → folders)
            - Generates correct **relative** Markdown links → click and stay in flow
            - Real tree navigation (expandable sections)
            - Robust handling of case-insensitive duplicates, aliases, broken links
            - Clean filenames and safe path generation
            - Friendly index page + dark/light mode toggle

            Args:
                output_dir: Where to create the MkDocs project
                site_name: Name shown in browser title and header
                site_url: Optional base URL (useful for GitHub Pages, Netlify, etc.)
                use_temp_dir: If True, export is created in a temporary folder
                clean_before: Delete existing output directory before starting
                build_after_export: Automatically run `mkdocs build` after files are written
                max_nesting_level: Maximum folder depth (to prevent insane nesting)

            Returns:
                Path to the root of the generated MkDocs project (contains mkdocs.yml)

            Raises:
                ValueError: No pages available to export
                RuntimeError: mkdocs build failed
                OSError / subprocess errors on file or command failures
            """
        
        # Prepare output directory
        if use_temp_dir:
            output_path = Path(tempfile.mkdtemp(prefix="wiki-mkdocs-"))
        else:
            output_path = Path(output_dir).resolve()

        if clean_before and output_path.exists():
            shutil.rmtree(output_path, ignore_errors=True)

        output_path.mkdir(parents=True, exist_ok=True)
        docs_dir = output_path / "docs"
        docs_dir.mkdir(exist_ok=True)

        logger.info("Exporting wiki to hierarchical MkDocs structure → %s", output_path)

        # ────────────────────────────────────────────────────────────────
        # 1. Collect all pages and build title → relative path mapping
        # ────────────────────────────────────────────────────────────────
        all_titles = self.get_all_titles()
        if not all_titles:
            raise ValueError("No pages available for export")

        # We normalize for case-insensitive lookup but keep original case
        title_normalized_to_original: Dict[str, str] = {}
        title_to_path: Dict[str, Path] = {}           # original title → relative path inside docs/
        title_to_clean: Dict[str, str] = {}

        for orig_title in all_titles:
            norm = orig_title.strip().lower()
            if norm in title_normalized_to_original:
                logger.warning("Duplicate title (case-insensitive): %r → keeping first occurrence", orig_title)
                continue
            title_normalized_to_original[norm] = orig_title

            # Generate safe filename / path
            parts = orig_title.split(".")
            clean_parts = [
                re.sub(r'[^a-z0-9_-]+', '-', p.strip().lower()).strip('-')
                for p in parts
            ]
            clean_parts = [p for p in clean_parts if p]  # remove empty parts

            # Enforce maximum nesting depth
            if len(clean_parts) > max_nesting_level + 1:
                clean_parts = clean_parts[:max_nesting_level] + ["".join(clean_parts[max_nesting_level:])]

            filename = clean_parts[-1] or "unnamed"
            if not filename.endswith(".md"):
                filename += ".md"

            rel_path = Path(*clean_parts[:-1]) / filename
            title_to_path[orig_title] = rel_path
            title_to_clean[orig_title] = ".".join(clean_parts[:-1] + [filename[:-3]])

        # ────────────────────────────────────────────────────────────────
        # 2. Export content + convert wiki-style [[links]] to Markdown
        # ────────────────────────────────────────────────────────────────
        def convert_wikilink(match) -> str:
            content = match.group(1).strip()
            if not content:
                return match.group(0)

            # [[Alias|Target]] or [[Target]]
            if '|' in content:
                alias, target = [x.strip() for x in content.split('|', 1)]
            else:
                alias = content
                target = content

            target_norm = target.lower().strip()

            if target_norm not in title_normalized_to_original:
                # Page doesn't exist → subtle visual warning
                return f'<span style="color:#e67e22">[[{alias}]]</span>'

            real_title = title_normalized_to_original[target_norm]
            target_path = title_to_path[real_title]

            # Calculate correct **relative** path from current file to target
            current_file = current_page_path.parent      # set inside the export loop below
            rel_link = Path(target_path).relative_to(current_file).as_posix()

            return f"[{alias}]({rel_link})"

        link_pattern = re.compile(r'\[\[(.+?)\]\]')

        exported_count = 0

        for orig_title in sorted(title_to_path.keys(), key=str.lower):
            page = self.get_page(orig_title)
            if not page:
                continue

            _, raw_content = page

            current_page_path = docs_dir / title_to_path[orig_title]

            # Ensure parent directories exist
            current_page_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert wiki links (needs current_page_path context)
            md_content = link_pattern.sub(convert_wikilink, raw_content)

            current_page_path.write_text(md_content, encoding="utf-8")
            exported_count += 1
            logger.debug("Exported: %s → %s", orig_title, title_to_path[orig_title])

        logger.info("Successfully exported %d pages", exported_count)

        # ────────────────────────────────────────────────────────────────
        # 3. Build hierarchical navigation tree
        # ────────────────────────────────────────────────────────────────
        def build_nav_tree():
            tree = defaultdict(dict)
            for orig_title, rel_path in title_to_path.items():
                parts = rel_path.with_suffix("").parts
                current = tree
                for part in parts[:-1]:
                    # Human-friendly section titles
                    current = current.setdefault(part.replace("-", " ").title(), {})
                # Final leaf
                leaf_name = parts[-1].replace("-", " ").title()
                current[leaf_name] = rel_path.as_posix()
            return tree

        def dict_to_yaml_nav(d: dict, indent: int = 0) -> List[str]:
            lines = []
            indent_str = "  " * indent
            # Sort: folders first, then pages; alphabetical within groups
            for k, v in sorted(d.items(), key=lambda x: (isinstance(x[1], dict), x[0].lower())):
                if isinstance(v, dict):
                    lines.append(f"{indent_str}- {k}:")
                    lines.extend(dict_to_yaml_nav(v, indent + 1))
                else:
                    lines.append(f"{indent_str}- {k}: {v}")
            return lines

        tree = build_nav_tree()
        nav_lines = dict_to_yaml_nav(tree, indent=1)

        # ────────────────────────────────────────────────────────────────
        # 4. Generate mkdocs.yml configuration
        # ────────────────────────────────────────────────────────────────
        mkdocs_content = f"""site_name: "{site_name}"
    site_author: "Your Name"
    site_description: "Personal wiki exported on {time.strftime('%Y-%m')}"
    # repo_url: ""  # optional - uncomment and fill if you want edit links

    theme:
    name: material
    palette:
        - scheme: default
        primary: indigo
        accent: indigo
        toggle:
            icon: material/weather-sunny
            name: Switch to dark mode
        - scheme: slate
        toggle:
            icon: material/weather-night
            name: Switch to light mode
    features:
        - navigation.sections
        - navigation.tracking
        - navigation.expand
        - navigation.indexes
        - navigation.top
        - search.suggest
        - search.highlight
        - content.code.copy
        - content.code.annotate
        - toc.integrate

    markdown_extensions:
    - pymdownx.highlight:
        anchor_linenums: true
    - pymdownx.inlinehilite
    - pymdownx.snippets
    - pymdownx.superfences
    - pymdownx.tasklist:
        custom_checkbox: true
    - admonition
    - footnotes
    - attr_list
    - md_in_html
    - toc:
        permalink: true
    - pymdownx.emoji:
        emoji_index: !!python/name:material.extensions.emoji.twemoji
        emoji_generator: !!python/name:material.extensions.emoji.to_svg

    plugins:
    - search
    # - glightbox  # uncomment after `pip install mkdocs-glightbox`

    nav:
    """ + "\n".join("  " + line for line in nav_lines if line.strip())

        if site_url:
            mkdocs_content += f"\nsite_url: {site_url.rstrip('/')}\n"

        (output_path / "mkdocs.yml").write_text(mkdocs_content, encoding="utf-8")

        # ────────────────────────────────────────────────────────────────
        # 5. Create a nicer home / index page
        # ────────────────────────────────────────────────────────────────
        index_content = f"""# Welcome to {site_name}

    Exported on **{time.strftime("%Y-%m-%d %H:%M")}**  
    Total pages: **{exported_count}**

    Navigation tips:
    - Use the expandable sidebar menu
    - Press `/` or click the search bar at the top (very fast)

    Happy reading!
    """

        (docs_dir / "index.md").write_text(index_content, encoding="utf-8")

        # ────────────────────────────────────────────────────────────────
        # 6. Optional: build the static site
        # ────────────────────────────────────────────────────────────────
        if build_after_export:
            try:
                subprocess.run(
                    ["mkdocs", "build", "--site-dir", str(output_path / "site")],
                    cwd=str(output_path),
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info("MkDocs build completed → static site ready at: %s/site", output_path)
                logger.info("Open in browser:   %s/site/index.html", output_path)
            except subprocess.CalledProcessError as e:
                logger.error("MkDocs build failed:\n%s", e.stderr)
                raise RuntimeError("mkdocs build command failed") from e

        return output_path