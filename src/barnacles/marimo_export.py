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


def marimo(*args: str, cwd: Path | None = None, quiet: bool = False) -> None:
    cmd = [sys.executable, "-m", "marimo", *args]
    result = subprocess.run(cmd, cwd=cwd, capture_output=quiet, text=True)
    if result.returncode:
        detail = f"\n{result.stderr.strip()}" if quiet and result.stderr else ""
        raise RuntimeError(f"`marimo {' '.join(args)}` failed (exit {result.returncode}){detail}")


def static(source: Path, out: Path, quiet: bool = True) -> None:
    """Run the notebook once and write its output as a single HTML page (no code, no kernel)."""
    marimo("export", "html", str(source), "-o", str(out), "--no-include-code", "-f", cwd=source.parent, quiet=quiet)
    out.write_text(out.read_text().replace("</head>", HIDE_KERNEL_TOAST + "</head>", 1))


def wasm(source: Path, dest: Path, quiet: bool = True) -> None:
    """Export the notebook as a WASM app (Python runs in the browser via Pyodide) into `dest`."""
    marimo("export", "html-wasm", str(source), "-o", str(dest), "--mode", "run", "-f", cwd=source.parent, quiet=quiet)
    (dest / "CLAUDE.md").unlink(missing_ok=True)  # AI-assistant prompt marimo bundles with WASM exports
