import tkinter as tk
from tkinter import messagebox, scrolledtext
import sqlite3
import time
import platform
import os
import logging
import shutil

# Configurar logging
logging.basicConfig(
    filename='wiki_app.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Optional: Markdown to HTML conversion
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    print("Optional dependency missing. Install with: pip install markdown")

DB_NAME = "wiki.db"
DB_BACKUP_NAME = "wiki.db.bak"


# ====================== Database Layer ======================
class WikiDB:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT UNIQUE NOT NULL,
                        content TEXT NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action TEXT NOT NULL,
                        page_title TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        machine_name TEXT NOT NULL
                    )
                """)
        except sqlite3.Error as e:
            messagebox.showerror(
                "DB Initialization Error",
                f"Failed to initialize database: {e}"
            )
            logging.error(f"DB init error: {e}")
            raise

    def get_page(self, title: str):
        if not title.strip():
            return None
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT title, content FROM pages WHERE title = ?",
                    (title.strip(),)
                )
                return cursor.fetchone()
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", f"Failed to fetch page: {e}")
            logging.error(f"Get page error: {e}")
            return None

    def get_all_titles(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT title FROM pages ORDER BY title")
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", f"Failed to fetch titles: {e}")
            logging.error(f"Get all titles error: {e}")
            return []

    def validate_title(self, title: str) -> bool:
        title = title.strip()
        if not title:
            messagebox.showwarning("Error", "Page title cannot be empty.")
            return False
        if len(title) > 255:
            messagebox.showwarning("Error", "Page title is too long (max 255 chars).")
            return False
        invalid_chars = r'\/:*?"<>|'
        if any(char in invalid_chars for char in title):
            messagebox.showwarning("Error", "Title contains invalid characters.")
            return False
        return True

    def validate_content(self, content: str) -> tuple[bool, str]:
        content = content.strip()

        # Conteúdo vazio ou muito curto
        if not content or len(content) < 5:
            return False, "O conteúdo da página está vazio ou demasiado curto."

        # Limite máximo
        MAX_CONTENT_LENGTH = 100_000
        if len(content) > MAX_CONTENT_LENGTH:
            return False, (
                f"Conteúdo excede o limite máximo ({MAX_CONTENT_LENGTH} caracteres). "
                f"Atual: {len(content)}"
            )

        # Conteúdo muito superficial
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if len(lines) <= 1 and (not lines or len(lines[0]) < 20):
            return False, "O conteúdo parece incompleto. Adicione mais informação."

        # Padrões proibidos (exemplo básico)
        forbidden = ["<script>", "</script>", "http://", "https://"]
        for pattern in forbidden:
            if pattern.lower() in content.lower():
                return False, f"Conteúdo contém padrão proibido: '{pattern}'"

        return True, ""

    def backup_db(self):
        try:
            if os.path.exists(self.db_name):
                shutil.copy2(self.db_name, DB_BACKUP_NAME)
                logging.info("Backup do DB criado com sucesso.")
        except IOError as e:
            messagebox.showerror("Backup Error", f"Não foi possível criar backup: {e}")
            logging.error(f"Backup error: {e}")

    def save_page(self, title: str, content: str):
        title = title.strip()
        content = content.strip()

        if not self.validate_title(title):
            return False

        is_valid, error_msg = self.validate_content(content)
        if not is_valid:
            messagebox.showwarning("Conteúdo Inválido", error_msg)
            return False

        try:
            self.backup_db()

            page_exists = self.get_page(title) is not None
            action = "Update" if page_exists else "Create"

            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO pages (title, content) VALUES (?, ?)",
                    (title, content),
                )

            self.log_action(action, title)
            return True

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                messagebox.showerror(
                    "Base de dados bloqueada",
                    "O ficheiro da base de dados está bloqueado. "
                    "Tente novamente daqui a alguns segundos."
                )
            else:
                messagebox.showerror("Erro na BD", f"Não foi possível guardar: {e}")
            logging.error(f"Save operational error: {e}")
            return False

        except sqlite3.Error as e:
            messagebox.showerror("Erro na BD", f"Não foi possível guardar: {e}")
            logging.error(f"Save page error: {e}")
            return False

    def log_action(self, action: str, page_title: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        machine_name = platform.node() or "Unknown"

        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO logs (action, page_title, timestamp, machine_name)
                    VALUES (?, ?, ?, ?)
                    """,
                    (action, page_title, timestamp, machine_name),
                )
        except sqlite3.Error as e:
            print(f"Aviso: Falha ao registar log: {e}")
            logging.error(f"Log action error: {e}")


# ====================== Rendering ======================
class WikiRenderer:
    @staticmethod
    def render_content(widget: tk.Text, raw_content: str):
        try:
            widget.config(state=tk.NORMAL)
            widget.delete(1.0, tk.END)

            if MARKDOWN_AVAILABLE:
                rendered = markdown.markdown(raw_content)
            else:
                rendered = raw_content

            widget.tag_config("h1", font=("Arial", 18, "bold"))
            widget.tag_config("h2", font=("Arial", 16, "bold"))
            widget.tag_config("bold", font=("Arial", 12, "bold"))
            widget.tag_config("italic", font=("Arial", 12, "italic"))
            widget.tag_config("link", foreground="blue", underline=True)

            for line in rendered.splitlines():
                line = line.strip()
                if line.startswith("<h1>"):
                    widget.insert(tk.END, line[4:-5] + "\n", "h1")
                elif line.startswith("<h2>"):
                    widget.insert(tk.END, line[4:-5] + "\n", "h2")
                elif "<strong>" in line or "<b>" in line:
                    cleaned = (
                        line
                        .replace("<strong>", "")
                        .replace("</strong>", "")
                        .replace("<b>", "")
                        .replace("</b>", "")
                    )
                    widget.insert(tk.END, cleaned + "\n", "bold")
                elif "<em>" in line or "<i>" in line:
                    cleaned = (
                        line
                        .replace("<em>", "")
                        .replace("</em>", "")
                        .replace("<i>", "")
                        .replace("</i>", "")
                    )
                    widget.insert(tk.END, cleaned + "\n", "italic")
                else:
                    widget.insert(tk.END, line + "\n")

            widget.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Rendering Error", f"Falha ao renderizar: {e}")
            widget.insert(tk.END, raw_content)
            widget.config(state=tk.DISABLED)


# ====================== UI ======================
class WikiUI:
    def __init__(self, db: WikiDB):
        self.db = db
        self.root = tk.Tk()
        self.root.title("Desktop Wiki")
        self.root.geometry("900x700")
        self.root.configure(padx=10, pady=10)

        self.status_label = tk.Label(
            self.root, text="Home", font=("Arial", 18, "bold")
        )
        self.status_label.pack(pady=10)

        self.title_entry = tk.Entry(self.root, width=60)
        self.title_entry.pack()

        self.editor = scrolledtext.ScrolledText(self.root, height=15)
        self.editor.pack(fill=tk.BOTH, expand=True, pady=10)

        self.preview = scrolledtext.ScrolledText(
            self.root, height=15, bg="#f5f5f5", state=tk.DISABLED
        )
        self.preview.pack(fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        self.save_button = tk.Button(
            button_frame,
            text="Save",
            command=self.save_current_page,
            state=tk.DISABLED
        )
        self.save_button.grid(row=0, column=0, padx=5)

        tk.Button(
            button_frame,
            text="View",
            command=lambda: self.show_page(self.title_entry.get()),
        ).grid(row=0, column=1, padx=5)

        tk.Button(
            button_frame, text="Index", command=self.show_index
        ).grid(row=0, column=2, padx=5)

        tk.Button(
            button_frame, text="Export HTML", command=self.export_full_html
        ).grid(row=0, column=3, padx=5)

        self.root.mainloop()

    def show_page(self, title: str):
        if not title:
            messagebox.showwarning("Aviso", "Introduza um título de página.")
            return

        page = self.db.get_page(title)
        self.editor.delete(1.0, tk.END)

        if page:
            self.editor.insert(tk.END, page[1])
            WikiRenderer.render_content(self.preview, page[1])
            self.status_label.config(text=f"A visualizar: {title}")
        else:
            self.editor.insert(tk.END, f"# {title}\n\nComece a escrever aqui...")
            self.preview.delete(1.0, tk.END)
            self.status_label.config(text=f"Nova página: {title}")

        self.save_button.config(state=tk.NORMAL)

    def save_current_page(self):
        title = self.title_entry.get()
        content = self.editor.get(1.0, tk.END).rstrip()
        if self.db.save_page(title, content):
            messagebox.showinfo("Sucesso", "Página guardada com sucesso.")
            self.show_page(title)

    def show_index(self):
        index_window = tk.Toplevel(self.root)
        index_window.title("Índice de Páginas")
        index_window.geometry("400x500")

        listbox = tk.Listbox(index_window)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for title in self.db.get_all_titles():
            listbox.insert(tk.END, title)

        def on_select(event):
            selection = listbox.curselection()
            if selection:
                selected = listbox.get(selection[0])
                self.title_entry.delete(0, tk.END)
                self.title_entry.insert(0, selected)
                self.show_page(selected)
                index_window.destroy()

        listbox.bind("<Double-1>", on_select)

    def export_full_html(self):
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT title, content FROM pages")
                pages = cursor.fetchall()

            if not pages:
                messagebox.showinfo("Informação", "Não existem páginas para exportar.")
                return

            html = [
                "<html><head><meta charset='utf-8'><title>Wiki</title></head>",
                "<body style='font-family: Arial; padding: 20px;'>",
                "<h1>Wiki</h1><hr>",
            ]

            for title, content in pages:
                body = (
                    markdown.markdown(content)
                    if MARKDOWN_AVAILABLE
                    else content
                )
                html.append(f"<h2>{title}</h2>{body}<hr>")

            html.append("</body></html>")

            filename = "wiki_export.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(html))

            messagebox.showinfo(
                "Sucesso",
                f"HTML exportado para:\n{os.path.abspath(filename)}"
            )

        except sqlite3.Error as e:
            messagebox.showerror("Erro na BD", f"Falha ao exportar: {e}")
            logging.error(f"Export DB error: {e}")
        except IOError as e:
            messagebox.showerror("Erro de Ficheiro", f"Falha ao escrever ficheiro: {e}")
            logging.error(f"Export IO error: {e}")


# ====================== Início ======================
if __name__ == "__main__":
    db = WikiDB()
    ui = WikiUI(db)
