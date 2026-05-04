from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QListWidget, QLineEdit, QTextEdit,
    QPushButton, QLabel, QMessageBox
)

from PySide6.QtCore import Qt
import markdown


class WikiUI(QMainWindow): # The WikiUI class inherits all attributes and methods from QMainWindow.

    def __init__(self, service):
        super().__init__() # refers to constructor of father class (QMainWindow) to ensure that the window would be correctly configured.

        self.service = service

        self.setWindowTitle("Desktop Wiki")
        self.resize(1100, 700)

        self.build_ui()
        self.refresh_index()

    def build_ui(self):

        # In Qt we need a central "central widget"
        central = QWidget()
        self.setCentralWidget(central)

        # Princiapl layout (horizontal)
        main_layout = QHBoxLayout()
        central.setLayout(main_layout)

        # =========================
        # LEFT PANEL
        # =========================

        left_layout = QVBoxLayout()

        left_layout.addWidget(QLabel("Pages"))

        self.search_entry = QLineEdit()
        self.search_entry.textChanged.connect(self.search_pages)  # Whenever the text changes in this field, execute this function.
        # replace  bind("<KeyRelease>")

        left_layout.addWidget(self.search_entry)

        self.page_list = QListWidget()
        self.page_list.itemClicked.connect(self.load_selected_page)
        # replace Listbox + bind

        left_layout.addWidget(self.page_list)

        main_layout.addLayout(left_layout, 1)  
        #  "1" = relative weight (type flexbox)

        # =========================
        # RIGHT PANEL
        # =========================

        right_layout = QVBoxLayout()

        self.title_entry = QLineEdit()
        right_layout.addWidget(self.title_entry)

        editor_layout = QHBoxLayout()

        self.editor = QTextEdit()
        self.editor.textChanged.connect(self.update_preview)
        # replace KeyRelease

        editor_layout.addWidget(self.editor)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setStyleSheet("background-color: #f4f4f4;")

        editor_layout.addWidget(self.preview)

        right_layout.addLayout(editor_layout)

        # =========================
        # BUTTONS
        # =========================

        button_layout = QHBoxLayout()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_page)

        new_btn = QPushButton("New")
        new_btn.clicked.connect(self.new_page)

        export_btn = QPushButton("Export HTML")
        export_btn.clicked.connect(self.export_html)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(new_btn)
        button_layout.addWidget(export_btn)

        right_layout.addLayout(button_layout)

        main_layout.addLayout(right_layout, 3)

    # =========================
    # LOGIC 
    # =========================

    def update_preview(self):
        content = self.editor.toPlainText()
        html = markdown.markdown(content)

        self.preview.setPlainText(html)
        # Qt split plainText vs richText

    def refresh_index(self):
        try:
            titles = self.service.get_all_titles()

            self.page_list.clear()

            for title in titles:
                self.page_list.addItem(title)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def search_pages(self):
        query = self.search_entry.text().lower()

        try:
            titles = self.service.get_all_titles()

            self.page_list.clear()

            for title in titles:
                if query in title.lower():
                    self.page_list.addItem(title)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def load_selected_page(self, item):
        try:
            title = item.text()

            page = self.service.get_page(title)

            if page:
                self.title_entry.setText(page[0])
                self.editor.setPlainText(page[1])

                self.update_preview()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_page(self):
        try:
            title = self.title_entry.text().strip()
            content = self.editor.toPlainText()

            self.service.save_page(title, content)

            QMessageBox.information(self, "Saved", "Page saved successfully")

            self.refresh_index()

        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def new_page(self):
        self.title_entry.clear()
        self.editor.clear()
        self.preview.clear()

    def export_html(self):
        try:
            self.service.export_to_mkdocs(
                output_dir="wiki_export_mkdocs",
                site_name="My personal wiki",
                build_after_export=False
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


# Run the application
if __name__ == "__main__":
    app = QApplication([])

    window = WikiUI(service=None)  # inject real service
    window.show()

    app.exec()