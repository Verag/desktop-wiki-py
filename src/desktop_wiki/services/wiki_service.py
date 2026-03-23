""" 1. WikiService receives the request
2. It creates a MkDocsExporter
3. It passes the database (DB) to it
4. The exporter:
 - reads pages
 - transforms the content
 - generates MkDocs files
5. The result is returned """


import desktop_wiki.exporters.mkdocs


class WikiService:

    def __init__(self, db):
        self.db = db
        
    def get_all_titles(self):
        return self.db.get_all_titles()

    def get_page(self, title):
        return self.db.get_page(title)

    def save_page(self, title, content):
        return self.db.save_page(title, content)

    def export_to_mkdocs(self, output_dir, site_name, build_after_export):
        exporter = MkDocsExporter(self.db)          # ou self.exporter se já tens instância
        export_path = exporter.export(              # ← aqui usas o nome REAL do método
            output_dir=output_dir,
            site_name=site_name,
            build_after_export=build_after_export    
        )
        return export_path