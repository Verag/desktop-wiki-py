
import tkinter as tk
from tkinter import messagebox, scrolledtext
import sqlite3
import time
import platform
import os

# Optional: Markdown to HTML conversion
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    print("Optional dependency missing. Install with: pip install markdown")

DB_NAME = "wiki.db"

# ====================== Database Layer ======================

def init_db():
    """Initialize database and required tables."""
    with sqlite3.connect(DB_NAME) as conn:
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


def get_page(title: str):
    """Fetch a page by title."""
    if not title.strip():
        return None

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title, content FROM pages WHERE title = ?",
            (title.strip(),)
        )
        return cursor.fetchone()


def get_all_titles():
    """Return all page titles ordered alphabetically."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM pages ORDER BY title")
        return [row[0] for row in cursor.fetchall()]


def save_page(title: str, content: str):
    """Insert or update a page and log the action."""
    title = title.strip()
    content = content.strip()

    if not title:
        messagebox.showwarning("Error", "Page title cannot be empty.")
        return False

    page_exists = get_page(title) is not None
    action = "Update" if page_exists else "Create"

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO pages (title, content) VALUES (?, ?)",
            (title, content)
        )

    log_action(action, title)
    return True


def log_action(action: str, page_title: str):
    """Register an action in the audit log."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    machine_name = platform.node()

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO logs (action, page_title, timestamp, machine_name)
            VALUES (?, ?, ?, ?)
            """,
            (action, page_title, timestamp, machine_name)
        )

# ====================== HTML / Markdown Rendering ======================

def render_content(widget: tk.Text, raw_content: str):
    """
    Render Markdown or basic HTML into a Tkinter Text widget.
    This is a simplified renderer.
    """
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
            widget.insert(
                tk.END,
                line.replace("<strong>", "").replace("</strong>", "")
                    .replace("<b>", "").replace("</b>", "") + "\n",
                "bold"
            )
        elif "<em>" in line or "<i>" in line:
            widget.insert(
                tk.END,
                line.replace("<em>", "").replace("</em>", "")
                    .replace("<i>", "").replace("</i>", "") + "\n",
                "italic"
            )
        else:
            widget.insert(tk.END, line + "\n")

    widget.config(state=tk.DISABLED)

# ====================== UI Actions ======================

def show_page(title: str):
    """Load and display a page."""
    if not title:
        messagebox.showwarning("Warning", "Please enter a page title.")
        return

    page = get_page(title)
    editor.delete(1.0, tk.END)

    if page:
        editor.insert(tk.END, page[1])
        render_content(preview, page[1])
        status_label.config(text=f"Viewing page: {title}")
    else:
        editor.insert(tk.END, f"# {title}\n\nStart writing here...")
        preview.delete(1.0, tk.END)
        status_label.config(text=f"New page: {title}")

    save_button.config(state=tk.NORMAL)


def save_current_page():
    """Save the current page."""
    title = title_entry.get()
    content = editor.get(1.0, tk.END)

    if save_page(title, content):
        messagebox.showinfo("Success", "Page saved successfully.")
        show_page(title)


def show_index():
    """Display the page index."""
    index_window = tk.Toplevel(root)
    index_window.title("Page Index")
    index_window.geometry("400x500")

    listbox = tk.Listbox(index_window)
    listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    for title in get_all_titles():
        listbox.insert(tk.END, title)

    def on_select(event):
        selection = listbox.curselection()
        if selection:
            selected = listbox.get(selection[0])
            title_entry.delete(0, tk.END)
            title_entry.insert(0, selected)
            show_page(selected)
            index_window.destroy()

    listbox.bind("<Double-1>", on_select)


def export_full_html():
    """Export all pages into a single HTML file."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, content FROM pages")
        pages = cursor.fetchall()

    if not pages:
        messagebox.showinfo("Info", "No pages to export.")
        return

    html = [
        "<html><head><meta charset='utf-8'><title>Wiki</title></head>",
        "<body style='font-family: Arial; padding: 20px;'>",
        "<h1>Wiki</h1><hr>"
    ]

    for title, content in pages:
        body = markdown.markdown(content) if MARKDOWN_AVAILABLE else content
        html.append(f"<h2>{title}</h2>{body}<hr>")

    html.append("</body></html>")

    filename = "wiki_export.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    messagebox.showinfo("Success", f"HTML exported to:\n{os.path.abspath(filename)}")

# ====================== UI Setup ======================

root = tk.Tk()
root.title("Desktop Wiki")
root.geometry("900x700")
root.configure(padx=10, pady=10)

status_label = tk.Label(root, text="Home", font=("Arial", 18, "bold"))
status_label.pack(pady=10)

title_entry = tk.Entry(root, width=60)
title_entry.pack()

editor = scrolledtext.ScrolledText(root, height=15)
editor.pack(fill=tk.BOTH, expand=True, pady=10)

preview = scrolledtext.ScrolledText(root, height=15, bg="#f5f5f5", state=tk.DISABLED)
preview.pack(fill=tk.BOTH, expand=True)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

save_button = tk.Button(button_frame, text="Save", command=save_current_page, state=tk.DISABLED)
save_button.grid(row=0, column=0, padx=5)

tk.Button(button_frame, text="View", command=lambda: show_page(title_entry.get())).grid(row=0, column=1, padx=5)
tk.Button(button_frame, text="Index", command=show_index).grid(row=0, column=2, padx=5)
tk.Button(button_frame, text="Export HTML", command=export_full_html).grid(row=0, column=3, padx=5)

# ====================== App Start ======================

init_db()
root.mainloop()

