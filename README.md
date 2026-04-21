# Desktop Wiki

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**A lightweight, fast and completely offline personal wiki.**

Desktop Wiki is a simple, private, and user-friendly desktop application to organize your thoughts, study notes, personal documentation, and knowledge — your own "second brain" that stays 100% on your computer.

No cloud. No tracking. Just your notes, your way.

---

## Features

- Create and edit wiki-style pages
- Full Markdown support with live preview
- Local storage using SQLite (everything stays on your machine)
- Clean and intuitive Tkinter interface
- Quick page index with search functionality
- Action logging (see what was changed and when)
- Powerful export options:
  - Complete static MkDocs website with hierarchical navigation
  - Single HTML file export (coming soon)

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Verag/desktop-wiki-py.git
cd desktop-wiki-py
```

### 2. Create virtual environment and install
```bash
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

pip install -e .
```

### 3. Run the application manuallly
```bash
python -m desktop_wiki.main
```

## Create Desktop Shortcut (Linux)
### 1. Copy the example shortcut:
```bash
cp Desktop-Wiki.desktop.example ~/Desktop/Desktop-Wiki.desktop
```

### 2. Edit the file and update the path to match your project location.

### 3. Make it executable:
```bash
chmod +x ~/Desktop/Desktop-Wiki.desktop
```

Now you can launch your wiki with a simple double-click!

## For Developers
If you want to contribute or modify the code:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Format code
black src/

# Lint code
ruff check src/
```

## Requirements

 - Python 3.10 or higher
 - Best supported on Linux and macOS
(Windows should work but is not officially tested yet)

## About This Project
Desktop Wiki was built with the goal of creating a clean, simple, and maintainable desktop application for personal knowledge management.
It focuses on:

 - Clean layered architecture (UI → Service → Export → Database)
 - Total privacy (local-first design)
 - Code quality and extensibility

It serves both as a practical daily tool and as a learning example of building well-structured Python desktop applications.

## License
This project is licensed under the MIT License.