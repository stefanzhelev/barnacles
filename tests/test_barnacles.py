import json
import re
from pathlib import Path

import pytest

from barnacles import config
from barnacles.build import build
from barnacles.cli import main
from barnacles.discovery import discover, walk

NOTEBOOK = '''import marimo

app = marimo.App(app_title="{title}")


@app.cell
def _():
    import marimo as mo
    mo.md("# hello")
    return


if __name__ == "__main__":
    app.run()
'''


def project(tmp_path: Path, yaml: str = "", notebooks: dict[str, str] | None = None) -> Path:
    (tmp_path / "barnacle.yaml").write_text(yaml)
    for rel, title in (notebooks or {"notebooks/a_one.py": "One", "notebooks/sub/two.py": "Two"}).items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(NOTEBOOK.format(title=title))
    return tmp_path


def test_discovery_defaults_and_overrides(tmp_path):
    root = project(tmp_path, """
defaults:
  notebook: {description: shared}
items:
  notebooks: {title: Home}
  notebooks/sub: {title: Subfolder, description: nested}
  notebooks/a_one.py: {slug: first, mode: html}
""")
    tree = discover(config.load(root))
    assert tree["title"] == "Home"
    sub, one = tree["children"]  # folders first
    assert (sub["title"], sub["description"], sub["notebooks"]) == ("Subfolder", "nested", 1)
    assert (one["path"], one["title"], one["mode"], one["description"]) == ("first", "One", "html", "shared")
    assert [nb["path"] for nb in walk(tree)] == ["sub/two", "first"]


@pytest.mark.parametrize("yaml, message", [
    ("items: {notebooks/nope.py: {title: x}}", "match no notebook"),
    ("items: {notebooks/a_one.py: {colour: red}}", "unknown key"),
    ("items: {notebooks/a_one.py: {mode: pdf}}", "mode must be"),
    ("paths: {dist: .}", "would wipe"),
    ("site: {logo: missing.svg}", "not found"),
    ("bogus: 1", "unknown section"),
])
def test_config_errors(tmp_path, yaml, message):
    root = project(tmp_path, yaml)
    with pytest.raises(config.ConfigError, match=message):
        discover(config.load(root))


def test_missing_config(tmp_path):
    with pytest.raises(config.ConfigError, match="barnacles init"):
        config.load(tmp_path)


def test_build_static(tmp_path):
    root = project(tmp_path, """
site: {title: "Tab & co", header_title: Top}
defaults:
  notebook: {mode: html}
paths: {dist: out/site}
""")
    build(config.load(root), screenshots=False, log=lambda _: None)
    dist = root / "out" / "site"
    page = (dist / "index.html").read_text()
    assert "<title>Tab &amp; co</title>" in page and "<span>Top</span>" in page
    assert not re.search(r"__[A-Z]+__", page)
    tree = json.loads(re.search(r'type="application/json">(.*?)</script>', page, re.S)[1].replace("<\\/", "</"))
    assert tree["notebooks"] == 2 and "source" not in json.dumps(tree)
    for f in ("app.js", "styles.css", "logo.svg", "favicon.svg",
              "notebooks/a-one/index.html", "notebooks/sub/two/index.html"):
        assert (dist / f).is_file(), f


def test_cli_init_then_build(tmp_path, capsys):
    assert main(["init", str(tmp_path)]) == 0
    assert (tmp_path / ".gitignore").is_file() and (tmp_path / "notebooks/example.py").is_file()
    assert main(["init", str(tmp_path)]) == 1  # refuses to overwrite
    assert "not overwriting" in capsys.readouterr().err
    discover(config.load(tmp_path))  # the scaffold is a valid project
