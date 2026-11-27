"""Card thumbnails: the images set in marimo.yaml, or light + dark screenshots of each notebook.

Screenshots use Playwright's headless Chromium. Playwright is a regular dependency, but its browser is
a separate download, so the first build that needs it installs it (into Playwright's shared cache,
see `install_browser`). Run `barnacles install-browser` to do that step explicitly, e.g. in CI.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from . import marimo_export

SIZE = {"width": 640, "height": 360}  # 16:9 like the gallery cards; small, so it shows the narrow layout
THEMES = {"light": "", "dark": "-dark"}  # color scheme -> file suffix
# headless launches only need Chromium's headless shell (smaller than the full browser)
INSTALL = [sys.executable, "-m", "playwright", "install", "--only-shell", "chromium"]


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass


def install_browser(with_deps: bool = False, log: Callable[[str], None] = print) -> None:
    """Download the Chromium that Playwright drives (a no-op when it is already there).

    with_deps also installs the system libraries Chromium needs on Linux (uses sudo + apt).
    """
    cmd = INSTALL + (["--with-deps"] if with_deps else [])
    log("Installing headless Chromium for thumbnails (about 100 MB, once per Playwright version):")
    log(f"  $ {shlex.join(cmd)}")
    sys.stdout.flush()  # keep our lines ahead of the installer's output when piped (CI logs)
    if subprocess.run(cmd).returncode:
        raise RuntimeError("installing Chromium failed; see the output above")


def _launch(pw, log: Callable[[str], None]):
    """Launch headless Chromium, installing it first if this Playwright version has none yet."""
    try:
        return pw.chromium.launch()
    except Exception as e:
        if "Executable doesn't exist" not in str(e):
            raise
    install_browser(log=log)
    return pw.chromium.launch()


def _screenshot(sources: dict[str, Path], out: Path, log: Callable[[str], None]) -> None:
    """Screenshot each notebook (path -> source .py) in light and dark mode into `out`.

    The browser is launched first, so nothing is exported when it cannot run. Notebooks are
    exported as static HTML, which uses marimo's "system" theme, so emulating
    prefers-color-scheme switches them.
    """
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        browser = _launch(pw, log)
        pages = {}
        for i, (nb_path, source) in enumerate(sources.items()):
            pages[nb_path] = Path(tmp) / f"{i}.html"
            marimo_export.static(source, pages[nb_path])
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=tmp))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            for scheme, suffix in THEMES.items():
                page = browser.new_page(viewport=SIZE, color_scheme=scheme, reduced_motion="reduce")
                for nb_path, html in pages.items():
                    page.goto(f"http://127.0.0.1:{server.server_port}/{html.name}", wait_until="load")
                    # hide marimo's chrome and watermark, like `marimo export thumbnail`
                    page.add_style_tag(content='.print\\:hidden,[data-testid="watermark"]{display:none !important;}')
                    page.wait_for_function("""() => [...document.querySelectorAll('div[id^="cell-"]')]
                        .some((c) => getComputedStyle(c).visibility !== "hidden")""", timeout=30_000)
                    page.wait_for_timeout(1500)  # let fonts, tables and charts settle
                    target = out / f"{nb_path}{suffix}.png"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=target)
                page.close()
        finally:
            server.shutdown()


def _hint(error: str) -> str:
    if "missing dependencies" in error.lower():  # Linux without Chromium's system libraries
        return "install them with `barnacles install-browser --with-deps` (Linux, uses sudo)"
    return "retry with `barnacles install-browser`, or build with --no-thumbnails"


def add(notebooks: list[dict], dist: Path, screenshots: bool, log: Callable[[str], None] = print) -> None:
    """Set nb["thumbnail"] / nb["thumbnail_dark"] (paths relative to dist) on each notebook."""
    out = dist / "thumbnails"
    todo: dict[str, Path] = {}  # notebook path -> source, for the ones to screenshot
    for nb in notebooks:
        if nb["thumbnails"]:  # configured images; a light-only one is used in both themes
            for key, src in nb["thumbnails"].items():
                dest = out / f"{nb['path']}{THEMES['dark'] if key == 'thumbnail_dark' else ''}{src.suffix}"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dest)
                nb[key] = dest.relative_to(dist).as_posix()
        elif screenshots:
            todo[nb["path"]] = nb["source"]
    if not todo:
        return
    log(f"Screenshotting {len(todo)} notebook(s) in light + dark mode")
    try:
        _screenshot(todo, out, log)
    except Exception as e:  # cards fall back to a letter placeholder
        first = (str(e).strip().splitlines() or [type(e).__name__])[0]
        log(f"  warning: no thumbnails ({first}); {_hint(str(e))}")
    for nb in notebooks:
        for key, suffix in (("thumbnail", ""), ("thumbnail_dark", THEMES["dark"])):
            if nb["path"] in todo and (out / f"{nb['path']}{suffix}.png").exists():
                nb[key] = f"thumbnails/{nb['path']}{suffix}.png"
