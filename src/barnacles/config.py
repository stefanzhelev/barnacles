"""barnacles.yaml: load, validate and fill in defaults.

Every path in the file (including the keys under `items`) is relative to the file itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

FILENAME = "barnacles.yaml"
WEB = Path(__file__).parent / "web"

SECTIONS = {"site", "paths", "defaults", "items"}
KEYS = {
    "site": {"title", "header_title", "logo", "favicon"},
    "paths": {"notebooks", "dist"},
    "notebook": {"title", "description", "mode", "slug", "thumbnail", "thumbnail_dark"},
    "folder": {"title", "description"},
}
MODES = ("html-wasm", "html")


class ConfigError(Exception):
    """A problem in barnacles.yaml or the project it describes."""


@dataclass
class Config:
    root: Path                      # the folder holding barnacles.yaml
    title: str
    header_title: str
    logo: Path
    favicon: Path
    notebooks: Path
    dist: Path
    defaults: dict[str, dict] = field(default_factory=dict)
    items: dict[str, dict] = field(default_factory=dict)

    def settings(self, path: Path, kind: str) -> dict:
        """defaults.<kind> overridden by the item keyed by this path."""
        key = path.relative_to(self.root).as_posix()
        item = self.items.get(key, {})
        _check_keys(f"items.{key}", item, kind)
        return {**self.defaults.get(kind, {}), **item}


def _check_keys(where: str, given: object, kind: str) -> None:
    if not isinstance(given, dict):
        raise ConfigError(f"{FILENAME}: {where} must be a mapping")
    if bad := set(given) - KEYS[kind]:
        raise ConfigError(f"{FILENAME}: {where}: unknown key(s) {sorted(bad)}; allowed: {sorted(KEYS[kind])}")


def find(project: Path) -> Path:
    """The barnacles.yaml for `project`, which is either that file or the folder holding it."""
    path = project if project.suffix in (".yaml", ".yml") else project / FILENAME
    if not path.is_file():
        raise ConfigError(f"no {FILENAME} in {project.resolve()}; create one with `barnacles init`")
    return path


def load(project: Path | str = ".") -> Config:
    path = find(Path(project)).resolve()
    root = path.parent
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"{FILENAME}: invalid YAML: {e}") from None
    if not isinstance(raw, dict):
        raise ConfigError(f"{FILENAME}: expected a mapping at the top level")
    if bad := set(raw) - SECTIONS:
        raise ConfigError(f"{FILENAME}: unknown section(s) {sorted(bad)}; allowed: {sorted(SECTIONS)}")

    site, paths, defaults = (raw.get(k) or {} for k in ("site", "paths", "defaults"))
    _check_keys("site", site, "site")
    _check_keys("paths", paths, "paths")
    if bad := set(defaults) - {"notebook", "folder"}:
        raise ConfigError(f"{FILENAME}: defaults: unknown key(s) {sorted(bad)}; allowed: ['folder', 'notebook']")
    defaults = {kind: defaults.get(kind) or {} for kind in ("notebook", "folder")}
    for kind, values in defaults.items():
        _check_keys(f"defaults.{kind}", values, kind)

    title = str(site.get("title") or "Notebooks")
    logo = root / site["logo"] if site.get("logo") else WEB / "logo.svg"
    favicon = root / site["favicon"] if site.get("favicon") else logo
    for key, file in (("logo", logo), ("favicon", favicon)):
        if not file.is_file():
            raise ConfigError(f"{FILENAME}: site.{key} = {site.get(key)!r} not found")

    cfg = Config(
        root=root,
        title=title,
        header_title=str(site.get("header_title") or title),
        logo=logo,
        favicon=favicon,
        notebooks=(root / (paths.get("notebooks") or "notebooks")).resolve(),
        dist=(root / (paths.get("dist") or "dist")).resolve(),
        defaults=defaults,
        items={Path(k).as_posix(): v or {} for k, v in (raw.get("items") or {}).items()},
    )
    if not cfg.notebooks.is_dir():
        raise ConfigError(f"{FILENAME}: paths.notebooks: {cfg.notebooks} is not a folder")
    if cfg.dist == root or cfg.dist in root.parents or cfg.notebooks.is_relative_to(cfg.dist) \
            or path.is_relative_to(cfg.dist):
        raise ConfigError(f"{FILENAME}: paths.dist = {paths.get('dist')!r} would wipe your sources; pick a separate folder")
    return cfg
