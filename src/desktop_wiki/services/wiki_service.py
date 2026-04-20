"""
WikiService acts as the business logic layer between the UI and the database.

1. WikiService receives the request
2. It creates a MkDocsExporter
3. It passes the database connection to the exporter
4. The exporter reads all pages, transforms the content, and generates MkDocs files
5. The result (export path) is returned to the caller
"""

from desktop_wiki.exporters.mkdocs import MkDocsExporter


class WikiService:
    """Main service class responsible for wiki operations."""

    def __init__(self, db):
        self.db = db

    def get_all_titles(self):
        """Return a list of all page titles in the wiki."""
        return self.db.get_all_titles()

    def get_page(self, title: str):
        """Retrieve a single page by its title."""
        return self.db.get_page(title)

    def save_page(self, title: str, content: str):
        """Save or update a page with the given title and content."""
        return self.db.save_page(title, content)

    def export_to_mkdocs(
        self,
        output_dir: str = "../wiki_export_mkdocs",
        site_name: str = "My Personal Wiki",
        build_after_export: bool = True
    ) -> str:
        """
        Export the entire wiki to MkDocs format.

        This method creates a complete MkDocs project structure that can be
        built into a static website.

        Args:
            output_dir (str): 
                Directory where the MkDocs project will be exported.
                Default: "../wiki_export_mkdocs" (outside src/, at project root)
            site_name (str): 
                Name of the website (appears in the header and browser tab).
                Default: "My Personal Wiki"
            build_after_export (bool): 
                If True, automatically runs `mkdocs build` after exporting.
                Default: True

        Returns:
            str: Path to the exported MkDocs project.
        """
        # Create the MkDocs exporter and pass the database
        exporter = MkDocsExporter(self.db)

        # Perform the export
        export_path = exporter.export(
            output_dir=output_dir,
            site_name=site_name,
            build_after_export=build_after_export
        )

        return export_path