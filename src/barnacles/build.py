"""Build the static site: export every notebook with marimo and render the gallery shell around them.

<dist>/
  index.html, app.js, styles.css   the gallery shell, with the tree and site settings filled in
  logo.*, favicon.*                from site.logo / site.favicon
  notebooks/<path>/                one marimo export per notebook (shown in the shell's iframe)
  thumbnails/<path>[-dark].png     card images

All links are relative, so the output works at a domain root or under any subpath.
"""

from __future__ import annotations

import html
import json
import shutil
from typing import Callable

from . import marimo_export, thumbnails
from .config import WEB, Config
from .discovery import discover, walk


def _public(node: dict) -> dict:
    """The tree as the page sees it (no local paths)."""
    hidden = {"source", "thumbnails"}
    return {k: [_public(c) for c in v] if k == "children" else v for k, v in node.items() if k not in hidden}


def build(cfg: Config, screenshots: bool = True, log: Callable[[str], None] = print) -> dict:
    """Build the site into cfg.dist and return the gallery tree."""
    tree = discover(cfg)  # validate everything before touching dist
    notebooks = list(walk(tree))

    shutil.rmtree(cfg.dist, ignore_errors=True)
    cfg.dist.mkdir(parents=True)
    for name in ("app.js", "styles.css"):
        shutil.copy(WEB / name, cfg.dist / name)
    assets = {}
    for key, src in (("logo", cfg.logo), ("favicon", cfg.favicon)):
        assets[key] = f"{key}{src.suffix}"
        shutil.copy(src, cfg.dist / assets[key])

    log(f"Exporting {len(notebooks)} notebook(s):")
    for nb in notebooks:
        dest = cfg.dist / "notebooks" / nb["path"]
        dest.mkdir(parents=True, exist_ok=True)
        log(f"  {nb['mode']:<9} {nb['source'].relative_to(cfg.root)} -> {dest.relative_to(cfg.root)}")
        if nb["mode"] == "html":
            marimo_export.static(nb["source"], dest / "index.html")
        else:
            marimo_export.wasm(nb["source"], dest)
    thumbnails.add(notebooks, cfg.dist, screenshots=screenshots, log=log)

    page = (WEB / "index.html").read_text()
    for placeholder, value in {
        "__TITLE__": html.escape(cfg.title),
        "__HEADER_TITLE__": html.escape(cfg.header_title),
        "__LOGO__": assets["logo"],
        "__FAVICON__": assets["favicon"],
        "__THEME__": cfg.theme,
        "__NOTEBOOKS__": json.dumps(_public(tree), indent=2).replace("</", "<\\/"),  # safe inside <script>
    }.items():
        page = page.replace(placeholder, value)
    (cfg.dist / "index.html").write_text(page)
    log(f"Wrote {cfg.dist.relative_to(cfg.root) if cfg.dist.is_relative_to(cfg.root) else cfg.dist}/index.html")
    return tree
