# Desktop Wiki

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Lint: flake8](https://img.shields.io/badge/lint-flake8-blue.svg)](https://flake8.pycqa.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A local-first personal knowledge management system (PKM) designed for speed, privacy, and structured thinking.

This project demonstrates how to build a maintainable desktop application using a clean layered architecture, combining persistence, business logic, and export capabilities.

---

## Features

- Create and edit wiki-style pages
- Store content locally using SQLite
- Write content using Markdown
- Live preview with basic Markdown rendering
- Page index for quick navigation
- Action logging (create/update events with timestamps and machine name)
- Export pages to:
  - Single HTML file
  - Static MkDocs site with hierarchical navigation
- Offline-first and local-only by design

---

## Architecture

The project follows a layered architecture:
UI (Tkinter)
↓
Service Layer (business logic)
↓
Export Layer (MkDocs, HTML)
↓
Database Layer (SQLite)

---

### Key design principles:

- Separation of concerns
- Low coupling between layers
- Extensibility (new exporters can be added easily)
- Maintainability (clear responsibility per module)

---

## Use Cases

- Personal knowledge base ("second brain")
- Technical documentation
- Study notes and structured learning
- Offline documentation system
- Lightweight alternative to tools like Notion or Obsidian (local-only)

---

## Tech Stack

- Python
- Tkinter for the desktop UI
- SQLite for local storage
- Markdown (optional dependency) for content rendering
- MkDocs for static site export

---

## Preview

<!-- Add screenshots or GIFs here -->
<!-- Example:
![App Screenshot](docs/screenshot.png)
-->

---

## Installation

Clone the repository:

```bash
git clone https://github.com/Verag/desktop-wiki-py.git
cd desktop-wiki
```

---

 ## Run
python3 main.py

---

## Requirements

 - Python 3.10+
 - Linux or macOS
(Windows may work but is not officially tested)

---

## Export

- You can export your wiki into a static site:

 - Clean Markdown structure
 - Hierarchical navigation
 - Ready for hosting (GitHub Pages, Netlify, etc.)

---

## Motivation

This project was built to explore:

 - Clean architecture in Python desktop applications
 - Local-first software design
 - Structured knowledge systems
 - Separation between persistence, services, and export layers

It is not just a note-taking app — it is an experiment in building maintainable and extensible software.

---

## License

This project is licensed under the MIT License.

---

