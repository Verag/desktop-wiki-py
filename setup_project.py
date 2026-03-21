from pathlib import Path

STRUCTURE = {
    "wikidb.py": "# TODO: Implement WikiDB (CRUD layer)\n",
    "exporters": {
        "__init__.py": "",
        "base.py": "...",
        "mkdocs.py": "# TODO: Implement MkDocsExporter\n"
    },
    "services": {
        "wiki_service.py": "..."
    }
}


def create_structure(base_path: Path, structure: dict):
    for name, content in structure.items():
        path = base_path / name

        if isinstance(content, dict):
            path.mkdir(parents=True, exist_ok=True)
            create_structure(path, content)
        else:
            if path.exists():
                print(f"⚠️  Skipped (already exists): {path}")
                continue

            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"✅ Created: {path}")


if __name__ == "__main__":
    project_root = Path(".")

    create_structure(project_root, STRUCTURE)

    print(" Structure setup complete (safe mode)")