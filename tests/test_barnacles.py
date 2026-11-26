import json
import re
from pathlib import Path

import pytest

from barnacles import config, thumbnails
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
    (tmp_path / "barnacles.yaml").write_text(yaml)
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


def test_exclude(tmp_path):
    root = project(tmp_path, """
exclude:
  - "notebooks/drafts/**"
  - "notebooks/archive"
  - "**/_*.py"
""", {
        "notebooks/keep.py": "Keep",
        "notebooks/_private.py": "Private",
        "notebooks/sub/ok.py": "Ok",
        "notebooks/sub/_scratch.py": "Scratch",
        "notebooks/drafts/wip.py": "Draft",
        "notebooks/drafts/deep/wip2.py": "Draft 2",
        "notebooks/archive/old.py": "Old",
    })
    tree = discover(config.load(root))
    assert [nb["path"] for nb in walk(tree)] == ["sub/ok", "keep"]
    assert [c["name"] for c in tree["children"] if c["type"] == "folder"] == ["sub"]


@pytest.mark.parametrize("yaml, message", [
    ("exclude: notebooks/drafts", "exclude must be a list"),
    ("exclude: ['notebooks/_x.py']\nitems: {notebooks/a_one.py: {title: x}, notebooks/_x.py: {title: y}}",
     "match no notebook"),
    ("items: {notebooks/nope.py: {title: x}}", "match no notebook"),
    ("items: {notebooks/a_one.py: {colour: red}}", "unknown key"),
    ("items: {notebooks/a_one.py: {mode: pdf}}", "mode must be"),
    ("paths: {dist: .}", "would wipe"),
    ("site: {logo: missing.svg}", "not found"),
    ("bogus: 1", "unknown section"),
    ("site: {theme: blue}", "site.theme must be one of"),
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
    assert 'data-theme-default="dark"' in page
    assert not re.search(r"__[A-Z]+__", page)
    tree = json.loads(re.search(r'type="application/json">(.*?)</script>', page, re.S)[1].replace("<\\/", "</"))
    assert tree["notebooks"] == 2 and "source" not in json.dumps(tree)
    for f in ("app.js", "styles.css", "logo.svg", "favicon.svg",
              "notebooks/a-one/index.html", "notebooks/sub/two/index.html"):
        assert (dist / f).is_file(), f


def test_cli_init_then_build(tmp_path, capsys):
    assert main(["init", str(tmp_path)]) == 0
    assert (tmp_path / ".gitignore").is_file() and (tmp_path / "notebooks/folder1/subfolder1/nb4.py").is_file()
    assert main(["init", str(tmp_path)]) == 1  # refuses to overwrite
    assert "not overwriting" in capsys.readouterr().err
    tree = discover(config.load(tmp_path))  # the scaffold is a valid project
    assert [(nb["path"], nb["mode"]) for nb in walk(tree)] == [
        ("folder1/subfolder1/nb4", "html"), ("folder1/nb3", "html"), ("nb1", "html"), ("nb2", "html")]


def test_cli_init_defaults_to_a_barnacles_folder(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    assert (tmp_path / "barnacles/barnacles.yaml").is_file()
    assert "cd barnacles" in capsys.readouterr().out
    assert main(["init", "."]) == 0  # an explicit folder still works
    assert (tmp_path / "barnacles.yaml").is_file()


class FakeChromium:
    def __init__(self, installed: bool):
        self.installed = installed

    def launch(self):
        if not self.installed:
            raise RuntimeError("BrowserType.launch: Executable doesn't exist at /somewhere/chrome-headless-shell")
        return "browser"


def test_launch_installs_a_missing_browser_once(monkeypatch):
    chromium, calls = FakeChromium(installed=False), []

    def install(with_deps=False, log=print):
        calls.append(with_deps)
        chromium.installed = True

    monkeypatch.setattr(thumbnails, "install_browser", install)
    pw = type("PW", (), {"chromium": chromium})()
    assert thumbnails._launch(pw, log=lambda _: None) == "browser" and calls == [False]
    assert thumbnails._launch(pw, log=lambda _: None) == "browser" and calls == [False]  # present: no install


def test_launch_does_not_install_on_other_errors(monkeypatch):
    class Broken:
        def launch(self):
            raise RuntimeError("Host system is missing dependencies to run browsers")

    monkeypatch.setattr(thumbnails, "install_browser", lambda **_: pytest.fail("should not install"))
    with pytest.raises(RuntimeError, match="missing dependencies"):
        thumbnails._launch(type("PW", (), {"chromium": Broken()})(), log=lambda _: None)
    assert "--with-deps" in thumbnails._hint("Host system is missing dependencies to run browsers")


def test_exports_get_the_responsive_fix(monkeypatch, tmp_path):
    from barnacles import marimo_export

    def fake_marimo(*args, cwd=None, quiet=False):  # stand-in for `marimo export`: write a page
        out = Path(args[args.index("-o") + 1])
        page = out if args[1] == "html" else out / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("<html><head><title>x</title></head><body></body></html>")

    monkeypatch.setattr(marimo_export, "marimo", fake_marimo)
    marimo_export.static(tmp_path / "nb.py", tmp_path / "static.html")
    marimo_export.wasm(tmp_path / "nb.py", tmp_path / "wasm")
    for page in (tmp_path / "static.html", tmp_path / "wasm" / "index.html"):
        html = page.read_text()
        assert "increase-pointer-area-x" in html and html.index("max-width: 640px") < html.index("</head>")


def test_exports_never_prompt(monkeypatch, tmp_path):
    # a notebook with a `# /// script` header makes marimo ask about a sandbox when stdin is a
    # terminal; with the output captured that question is invisible and the build hangs
    import subprocess

    from barnacles import marimo_export

    runs = []

    def run(cmd, **kwargs):
        runs.append((cmd, kwargs))
        out = Path(cmd[cmd.index("-o") + 1])  # both exports write a page that barnacles then edits
        page = out if "html" in cmd else out / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("<head></head>")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(marimo_export.subprocess, "run", run)
    marimo_export.static(tmp_path / "nb.py", tmp_path / "out.html")
    marimo_export.wasm(tmp_path / "nb.py", tmp_path / "wasm")
    assert len(runs) == 2
    for cmd, kwargs in runs:
        assert "--no-sandbox" in cmd and kwargs["stdin"] is subprocess.DEVNULL
