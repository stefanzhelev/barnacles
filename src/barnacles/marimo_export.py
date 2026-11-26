"""Thin wrappers around `marimo export`, run with the same Python as barnacles."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Static (`html`) exports have no kernel, so marimo shows a "This notebook is not connected to a
# kernel" toast as soon as a UI element (e.g. mo.ui.table) reports its value. There is no export
# flag for it, so hide that one toast with a small script injected into <head>.
HIDE_KERNEL_TOAST = """<script>
new MutationObserver(() => {
  for (const t of document.querySelectorAll("li[data-state]")) {
    if (t.textContent.includes("not connected to a kernel")) t.style.display = "none";
  }
}).observe(document.documentElement, { childList: true, subtree: true });
</script>
"""

# Each cell output has a hover action bar (the fullscreen button) placed 2.25rem outside its right
# edge, plus an invisible hover zone (`increase-pointer-area-x`, a ::before/::after reaching 50px
# past both edges) so the pointer can travel to it. Below 640px the outputs span the whole page,
# so both stick out past the edge and, though invisible, widen the page: a horizontal scrollbar on
# phones. Moving the bar inside would put it under marimo's "..." menu button, and on a phone the
# notebook already fills the screen (and touch screens have no hover), so there hide both.
RESPONSIVE_CSS = """<style>
@media (max-width: 640px) {
  #App .\\-right-9 { display: none; }
  #App .increase-pointer-area-x::before, #App .increase-pointer-area-x::after { display: none; }
}
</style>
"""


def _inject(page: Path, html: str) -> None:
    """Add `html` at the end of the page's <head>."""
    page.write_text(page.read_text().replace("</head>", html + "</head>", 1))

# Exports always run in barnacles' own environment. Without this, marimo asks whether to use a
# sandboxed venv for notebooks with a `# /// script` dependency header (when uv is installed and
# stdin is a terminal), and the answer would change how a build behaves from one machine to another.
NO_SANDBOX = "--no-sandbox"


def marimo(*args: str, cwd: Path | None = None, quiet: bool = False) -> None:
    cmd = [sys.executable, "-m", "marimo", *args]
    # a quiet run hides marimo's output, so it must never wait on the terminal for an answer
    stdin = subprocess.DEVNULL if quiet else None
    result = subprocess.run(cmd, cwd=cwd, stdin=stdin, capture_output=quiet, text=True)
    if result.returncode:
        detail = f"\n{result.stderr.strip()}" if quiet and result.stderr else ""
        raise RuntimeError(f"`marimo {' '.join(args)}` failed (exit {result.returncode}){detail}")


def static(source: Path, out: Path, quiet: bool = True) -> None:
    """Run the notebook once and write its output as a single HTML page (no code, no kernel)."""
    marimo("export", "html", str(source), "-o", str(out), "--no-include-code", "-f", NO_SANDBOX, cwd=source.parent, quiet=quiet)
    _inject(out, HIDE_KERNEL_TOAST + RESPONSIVE_CSS)


def wasm(source: Path, dest: Path, quiet: bool = True) -> None:
    """Export the notebook as a WASM app (Python runs in the browser via Pyodide) into `dest`."""
    marimo("export", "html-wasm", str(source), "-o", str(dest), "--mode", "run", "-f", NO_SANDBOX, cwd=source.parent, quiet=quiet)
    (dest / "CLAUDE.md").unlink(missing_ok=True)  # AI-assistant prompt marimo bundles with WASM exports
    _inject(dest / "index.html", RESPONSIVE_CSS)
