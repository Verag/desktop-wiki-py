from wiki_domain import WikiDB
from wiki_ui import WikiUI

## entry point for the application
if __name__ == "__main__":
    db = WikiDB("wiki.db")  ## create database 
    app = WikiUI(db)## create graphical interface with dependency injection
    app.run()