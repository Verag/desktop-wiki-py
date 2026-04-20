import tkinter as tk
from tkinter import messagebox, scrolledtext
import os
import markdown

from desktop_wiki.core.wiki_domain import WikiDB, WikiError, ValidationError
from desktop_wiki.services.wiki_service import WikiService


class WikiUI:

    def __init__(self, service: WikiService):
        self.service  = service

        self.root = tk.Tk()
        self.root.title("Desktop Wiki")
        self.root.geometry("1100x700")

        self.build_ui()
        self.refresh_index()

    def build_ui(self):

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # LEFT PANEL (pages index)

        left_frame = tk.Frame(main_frame, width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(left_frame, text="Pages").pack()

        self.search_entry = tk.Entry(left_frame)
        self.search_entry.pack(fill=tk.X, padx=5)
        self.search_entry.bind("<KeyRelease>", self.search_pages)

        self.page_list = tk.Listbox(left_frame)
        self.page_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.page_list.bind("<<ListboxSelect>>", self.load_selected_page)

        # RIGHT PANEL (editor + preview)

        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.title_entry = tk.Entry(right_frame, font=("Arial", 14))
        self.title_entry.pack(fill=tk.X, pady=5)

        editor_frame = tk.Frame(right_frame)
        editor_frame.pack(fill=tk.BOTH, expand=True)

        self.editor = scrolledtext.ScrolledText(editor_frame)
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.editor.bind("<KeyRelease>", self.update_preview)

        self.preview = scrolledtext.ScrolledText(
            editor_frame,
            state=tk.DISABLED,
            bg="#f4f4f4"
        )
        self.preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(right_frame)
        button_frame.pack(fill=tk.X)

        tk.Button(button_frame, text="Save", command=self.save_page)\
            .pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(button_frame, text="New", command=self.new_page)\
            .pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(button_frame, text="Export HTML", command=self.export_html)\
            .pack(side=tk.LEFT, fill=tk.X, expand=True)

    def run(self):
        self.root.mainloop()

    def update_preview(self, event=None):

        content = self.editor.get("1.0", tk.END)

        html = markdown.markdown(content)

        self.preview.config(state=tk.NORMAL)
        self.preview.delete("1.0", tk.END)
        self.preview.insert(tk.END, html)
        self.preview.config(state=tk.DISABLED)

    def refresh_index(self):

        try:
            titles = self.service.get_all_titles()

            self.page_list.delete(0, tk.END)

            for title in titles:
                self.page_list.insert(tk.END, title)

        except WikiError as e:
            messagebox.showerror("Error", str(e))

    def search_pages(self, event=None):

        query = self.search_entry.get().lower()

        try:
            titles = self.service.get_all_titles()

            self.page_list.delete(0, tk.END)

            for title in titles:
                if query in title.lower():
                    self.page_list.insert(tk.END, title)

        except WikiError as e:
            messagebox.showerror("Error", str(e))

    def load_selected_page(self, event=None):

        try:
            selection = self.page_list.curselection()

            if not selection:
                return

            title = self.page_list.get(selection[0])

            page = self.service.get_page(title)

            if page:
                self.title_entry.delete(0, tk.END)
                self.title_entry.insert(0, page[0])

                self.editor.delete("1.0", tk.END)
                self.editor.insert(tk.END, page[1])

                self.update_preview()

        except WikiError as e:
            messagebox.showerror("Error", str(e))

    def save_page(self):

        try:
            title = self.title_entry.get().strip()
            content = self.editor.get("1.0", tk.END)

            self.service.save_page(title, content)

            messagebox.showinfo("Saved", "Page saved successfully")

            self.refresh_index()

        except ValidationError as e:
            messagebox.showwarning("Validation error", str(e))

        except WikiError as e:
            messagebox.showerror("Error", str(e))

    def new_page(self):

        self.title_entry.delete(0, tk.END)

        self.editor.delete("1.0", tk.END)

        self.preview.config(state=tk.NORMAL)
        self.preview.delete("1.0", tk.END)
        self.preview.config(state=tk.DISABLED)

    def export_html(self):
        try:
            export_path = self.service.export_to_mkdocs(
                output_dir="wiki_export_mkdocs",
                site_name="My personal wiki",
                build_after_export=False
            )

        except Exception as e:
            messagebox.showerror("Error in export", str(e))  