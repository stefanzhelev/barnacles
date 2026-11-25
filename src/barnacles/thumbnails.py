"""Card thumbnails: the images set in barnacles.yaml, or light + dark screenshots of each notebook.

Screenshots need the optional `thumbnails` extra (Playwright) and a headless Chromium:
    pip install "barnacles[thumbnails]" && playwright install chromium
"""

from __future__ import annotations

import shutil
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from . import marimo_export

SIZE = {"width": 640, "height": 360}  # 16:9 like the gallery cards; small, so it shows the narrow layout
THEMES = {"light": "", "dark": "-dark"}  # color scheme -> file suffix


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass


def _screenshot(pages: dict[str, Path], out: Path) -> None:
    """Screenshot each page (notebook path -> rendered html) in light and dark mode into `out`.

    Exported notebooks use marimo's "system" theme, so emulating prefers-color-scheme switches them.
    """
    from playwright.sync_api import sync_playwright

    root = next(iter(pages.values())).parent
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
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


def add(notebooks: list[dict], dist: Path, screenshots: bool, log: Callable[[str], None] = print) -> None:
    """Set nb["thumbnail"] / nb["thumbnail_dark"] (paths relative to dist) on each notebook."""
    out = dist / "thumbnails"
    todo: dict[str, Path] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for i, nb in enumerate(notebooks):
            if nb["thumbnails"]:  # configured images; a light-only one is used in both themes
                for key, src in nb["thumbnails"].items():
                    dest = out / f"{nb['path']}{THEMES['dark'] if key == 'thumbnail_dark' else ''}{src.suffix}"
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(src, dest)
                    nb[key] = dest.relative_to(dist).as_posix()
            elif screenshots:
                todo[nb["path"]] = Path(tmp) / f"{i}.html"
                marimo_export.static(nb["source"], todo[nb["path"]])
        if not todo:
            return
        log(f"Screenshotting {len(todo)} notebook(s) in light + dark mode")
        try:
            _screenshot(todo, out)
        except Exception as e:  # no Playwright / Chromium: cards fall back to a letter placeholder
            first = (str(e).strip().splitlines() or [type(e).__name__])[0]
            log(f"  warning: no thumbnails ({first}); "
                'install with `pip install "barnacles[thumbnails]" && playwright install chromium`')
        for nb in notebooks:
            for key, suffix in (("thumbnail", ""), ("thumbnail_dark", THEMES["dark"])):
                if nb["path"] in todo and (out / f"{nb['path']}{suffix}.png").exists():
                    nb[key] = f"thumbnails/{nb['path']}{suffix}.png"
