"""Find the notebooks and folders under the notebooks folder and build the gallery tree.

Folders: {type, path, name, title, description, folders, notebooks, children}
Notebooks: {type, path, title, description, mode, source, thumbnails}
`path` is the URL path below the gallery root, e.g. "interactive/wasm-example".
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator

from .config import FILENAME, MODES, Config, ConfigError


def app_title(source: Path) -> str | None:
    """`marimo.App(app_title=...)` from a notebook, if set."""
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "App":
            for kw in node.keywords:
                if kw.arg == "app_title" and isinstance(kw.value, ast.Constant):
                    return kw.value.value
    return None


def notebook(cfg: Config, source: Path) -> dict:
    meta = cfg.settings(source, "notebook")
    key = source.relative_to(cfg.root).as_posix()
    mode = meta.get("mode") or MODES[0]
    if mode not in MODES:
        raise ConfigError(f"{FILENAME}: items.{key}: mode must be one of {list(MODES)}, got {mode!r}")
    thumbnails = {}
    for k in ("thumbnail", "thumbnail_dark"):
        if meta.get(k):
            thumbnails[k] = cfg.root / meta[k]
            if not thumbnails[k].is_file():
                raise ConfigError(f"{FILENAME}: items.{key}: {k} = {meta[k]!r} not found")

    slug = meta.get("slug") or source.stem.replace("_", "-")
    folder = source.parent.relative_to(cfg.notebooks).as_posix()
    return {
        "type": "notebook",
        "path": slug if folder == "." else f"{folder}/{slug}",
        "title": str(meta.get("title") or app_title(source) or slug),
        "description": str(meta.get("description") or ""),
        "mode": mode,
        "source": source,
        "thumbnails": thumbnails,
    }


def folder(cfg: Config, path: Path) -> dict | None:
    """The tree under `path`: folders first, then notebooks, each sorted by name.

    Counts are recursive. Folders without notebooks (at any depth), folders whose names start
    with "." or "_" (like marimo's __marimo__), and anything matching `exclude` are left out;
    the root folder is always kept.
    """
    children, folders, notebooks = [], 0, 0
    subs = (p for p in path.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))
    for sub in sorted(p for p in subs if not cfg.excluded(p)):
        if node := folder(cfg, sub):
            children.append(node)
            folders += 1 + node["folders"]
            notebooks += node["notebooks"]
    for source in sorted(p for p in path.glob("*.py") if not cfg.excluded(p)):
        children.append(notebook(cfg, source))
        notebooks += 1
    is_root = path == cfg.notebooks
    if not notebooks and not is_root:
        return None

    names = [c["path"].rsplit("/", 1)[-1] for c in children]
    if dupes := sorted({n for n in names if names.count(n) > 1}):
        raise ConfigError(f"{path.relative_to(cfg.root)}: folders and notebooks share a name: {dupes}")
    meta = cfg.settings(path, "folder")
    rel = path.relative_to(cfg.notebooks).as_posix()
    return {
        "type": "folder",
        "path": "" if is_root else rel,
        "name": path.name,
        "title": str(meta.get("title") or ("Notebooks" if is_root else path.name)),
        "description": str(meta.get("description") or ""),
        "folders": folders,
        "notebooks": notebooks,
        "children": children,
    }


def walk(node: dict) -> Iterator[dict]:
    """Every notebook in the tree."""
    for child in node["children"]:
        yield from walk(child) if child["type"] == "folder" else [child]


def keys(node: dict, cfg: Config) -> Iterator[str]:
    """The `items` keys that match something in the tree."""
    if node["type"] == "notebook":
        yield node["source"].relative_to(cfg.root).as_posix()
        return
    yield (cfg.notebooks / node["path"]).relative_to(cfg.root).as_posix()
    for child in node["children"]:
        yield from keys(child, cfg)


def discover(cfg: Config) -> dict:
    """The gallery tree. Fails on `items` that match no notebook or non-empty folder."""
    if not cfg.notebooks.is_relative_to(cfg.root):
        raise ConfigError(f"{FILENAME}: paths.notebooks must be inside {cfg.root}")
    tree = folder(cfg, cfg.notebooks)
    if unmatched := sorted(set(cfg.items) - set(keys(tree, cfg))):
        raise ConfigError(f"{FILENAME}: items match no notebook or non-empty folder (or only excluded ones): {unmatched}")
    return tree
