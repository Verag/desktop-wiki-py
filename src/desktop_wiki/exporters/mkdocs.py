import time
import shutil
import subprocess
import tempfile
import re
import os
from pathlib import Path
from typing import Dict, Optional, List
from collections import defaultdict
import logging
from .base import Exporter # relative import of Exporter base class

logger = logging.getLogger(__name__) #Creates a logger with the name of the current module.


class MkDocsExporter(Exporter):
    """
    Export wiki content from WikiDB into a static MkDocs site.
    """

    def export(
        self,
        output_dir: str | Path = "wiki_export_mkdocs",
        site_name: str = "My Personal Wiki",
        site_url: Optional[str] = None,
        use_temp_dir: bool = False,
        clean_before: bool = True,
        build_after_export: bool = True,
        max_nesting_level: int = 4,
    ) -> Path:

        # ────────────────────────────────────────────────
        # 1. Prepare directories
        # ────────────────────────────────────────────────
        if use_temp_dir:
            output_path = Path(tempfile.mkdtemp(prefix="wiki-mkdocs-"))
        else:
            output_path = Path(output_dir).resolve()

        if clean_before and output_path.exists():
            shutil.rmtree(output_path, ignore_errors=True)

        output_path.mkdir(parents=True, exist_ok=True)
        docs_dir = output_path / "docs"
        docs_dir.mkdir(exist_ok=True)

        logger.info("Exporting wiki to MkDocs → %s", output_path)

        # ────────────────────────────────────────────────
        # 2. Collect page titles
        # ────────────────────────────────────────────────
        all_titles = self.db.get_all_titles()
        if not all_titles:
            raise ValueError("No pages available for export")

        title_normalized_to_original: Dict[str, str] = {}
        title_to_path: Dict[str, Path] = {}

        for orig_title in all_titles:
            norm = orig_title.strip().lower()

            if norm in title_normalized_to_original:
                logger.warning("Duplicate title ignored: %r", orig_title)
                continue

            title_normalized_to_original[norm] = orig_title

            parts = orig_title.split(".")
            clean_parts = [
                re.sub(r'[^a-z0-9_-]+', '-', p.strip().lower()).strip('-')
                for p in parts
            ]
            clean_parts = [p for p in clean_parts if p]

            if len(clean_parts) > max_nesting_level + 1:
                clean_parts = clean_parts[:max_nesting_level] + [
                    "".join(clean_parts[max_nesting_level:])
                ]

            filename = clean_parts[-1] or "unnamed"
            filename += ".md"

            rel_path = Path(*clean_parts[:-1]) / filename
            title_to_path[orig_title] = rel_path

        # ────────────────────────────────────────────────
        # 3. Convert wikilinks [[...]]
        # ────────────────────────────────────────────────
        link_pattern = re.compile(r'\[\[(.+?)\]\]')

        def convert_wikilink(match, current_page_path):
            content = match.group(1).strip()

            if not content:
                return match.group(0)

            if "|" in content:
                alias, target = [x.strip() for x in content.split("|", 1)]
            else:
                alias = content
                target = content

            target_norm = target.lower()

            if target_norm not in title_normalized_to_original:
                return f'<span style="color:#e67e22">[[{alias}]]</span>'

            real_title = title_normalized_to_original[target_norm]
            target_path = docs_dir / title_to_path[real_title]

            rel_link = os.path.relpath(
                target_path,
                start=current_page_path.parent
            )

            return f"[{alias}]({rel_link})"

        # ────────────────────────────────────────────────
        # 4. Export pages
        # ────────────────────────────────────────────────
        exported_count = 0

        for orig_title in sorted(title_to_path.keys(), key=str.lower):
            page = self.db.get_page(orig_title)
            if not page:
                continue

            _, raw_content = page

            current_page_path = docs_dir / title_to_path[orig_title]
            current_page_path.parent.mkdir(parents=True, exist_ok=True)

            def replace(match):
                return convert_wikilink(match, current_page_path)

            md_content = link_pattern.sub(replace, raw_content)

            current_page_path.write_text(md_content, encoding="utf-8")
            exported_count += 1

        logger.info("Exported %d pages", exported_count)

        # ────────────────────────────────────────────────
        # 5. Build navigation tree
        # ────────────────────────────────────────────────
        def build_nav_tree():
            tree = defaultdict(dict)

            for orig_title, rel_path in title_to_path.items():
                parts = rel_path.with_suffix("").parts
                current = tree

                for part in parts[:-1]:
                    current = current.setdefault(part.replace("-", " ").title(), {})

                leaf = parts[-1].replace("-", " ").title()
                current[leaf] = rel_path.as_posix()

            return tree

        def dict_to_yaml_nav(d: dict, indent: int = 0) -> List[str]:
            lines = []
            indent_str = "  " * indent

            for k, v in sorted(d.items(), key=lambda x: (isinstance(x[1], dict), x[0].lower())):
                if isinstance(v, dict):
                    lines.append(f"{indent_str}- {k}:")
                    lines.extend(dict_to_yaml_nav(v, indent + 1))
                else:
                    lines.append(f"{indent_str}- {k}: {v}")

            return lines

        tree = build_nav_tree()
        nav_lines = dict_to_yaml_nav(tree, indent=1)

        # ────────────────────────────────────────────────
        # 6. Generate mkdocs.yml
        # ────────────────────────────────────────────────
        mkdocs_content = f"""site_name: "{site_name}"

theme:
  name: material

nav:
""" + "\n".join("  " + line for line in nav_lines if line.strip())

        if site_url:
            mkdocs_content += f"\nsite_url: {site_url.rstrip('/')}\n"

        (output_path / "mkdocs.yml").write_text(mkdocs_content, encoding="utf-8")

        # ────────────────────────────────────────────────
        # 7. Create index page
        # ────────────────────────────────────────────────
        index_content = f"""# {site_name}

Exported on {time.strftime("%Y-%m-%d %H:%M")}

Total pages: {exported_count}
"""

        (docs_dir / "index.md").write_text(index_content, encoding="utf-8")

        # ────────────────────────────────────────────────
        # 8. Optional build
        # ────────────────────────────────────────────────
        if build_after_export:
            try:
                subprocess.run(
                    ["mkdocs", "build", "--site-dir", str(output_path / "site")],
                    cwd=str(output_path),
                    check=True,
                    capture_output=True,
                    text=True
                )

                logger.info("MkDocs build completed: %s/site", output_path)

            except subprocess.CalledProcessError as e:
                logger.error("MkDocs build failed:\n%s", e.stderr)
                raise RuntimeError("mkdocs build failed") from e

        return output_path