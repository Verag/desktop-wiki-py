from wiki_domain import WikiDB
from wiki_ui import WikiUI
from services.wiki_service import WikiService


# Entry point for the application
if __name__ == "__main__":
    db = WikiDB("wiki.db")          # Create database
    service = WikiService(db)       # Create service layer

    app = WikiUI(service)           # Inject service (NOT db)
    app.run()