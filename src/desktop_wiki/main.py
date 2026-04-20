from desktop_wiki.core.wiki_domain import WikiDB
from desktop_wiki.ui.wiki_ui import WikiUI
from desktop_wiki.services.wiki_service import WikiService
import tkinter as tk
from tkinter import messagebox


try:
    db = WikiDB()                     
    service = WikiService(db)         #create service here!
    
    app = WikiUI(service)             # now, service exists!
    app.run()

except NameError as e:
    # Show pop-up if 'service' or another variable is not defined
    root = tk.Tk()
    root.withdraw()                   # hide empty principal windows
    messagebox.showerror(
        title="Error starting application",
        message=f"Configuration error: {str(e)}\n\n"
                "Likely cause: the variable 'service' or 'db' was not created before starting the UI.\n"
                "Check main.py and ensure you have:\n"
                "db = WikiDB()\n"
                "service = WikiService(db)\n"
                "app = WikiUI(service)"
    )
    root.destroy()

except Exception as e:
    # capture others unexpected errors and show a pop-up
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error", f"An unexpected error occurred:\n{str(e)}")
    root.destroy()