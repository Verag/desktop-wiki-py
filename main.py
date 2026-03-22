from wiki_domain import WikiDB
from wiki_ui import WikiUI
from services.wiki_service import WikiService
import tkinter as tk
from tkinter import messagebox


try:
    db = WikiDB()                     
    service = WikiService(db)         # ← cria o service aqui!
    
    app = WikiUI(service)             # agora service existe
    app.run()

except NameError as e:
    # Mostra pop-up se 'service' ou outra variável não estiver definida
    root = tk.Tk()
    root.withdraw()                   # esconde a janela principal vazia
    messagebox.showerror(
        title="Erro ao iniciar a aplicação",
        message=f"Erro de configuração: {str(e)}\n\n"
                "Provável causa: a variável 'service' ou 'db' não foi criada antes de iniciar a UI.\n"
                "Verifica o main.py e certifica-te que tens:\n"
                "db = WikiDB()\n"
                "service = WikiService(db)\n"
                "app = WikiUI(service)"
    )
    root.destroy()

except Exception as e:
    # Captura outros erros inesperados
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Erro inesperado", f"Ocorreu um erro:\n{str(e)}")
    root.destroy()