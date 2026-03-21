""" 1. WikiService receives the request
2. It creates a MkDocsExporter
3. It passes the database (DB) to it
4. The exporter:
 - reads pages
 - transforms the content
 - generates MkDocs files
5. The result is returned """


from exporters.mkdocs import MkDocsExporter


class WikiService:

    def __init__(self, db):
        self.db = db

    def export_to_mkdocs(self):
        exporter = MkDocsExporter(self.db)
        return exporter.export_to_mkdocs_site()