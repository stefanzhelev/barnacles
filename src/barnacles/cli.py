"""The `barnacles` command line.

  barnacles init  [DIR]      start a project in DIR (default: ./barnacles)
  barnacles build [PROJECT]  export every notebook and render the catalog
  barnacles serve [PROJECT]  build, then serve the catalog locally
  barnacles edit  [PROJECT | NOTEBOOK]   open notebooks in the marimo editor
  barnacles install-browser [--with-deps]  download the Chromium used for thumbnails

PROJECT is a folder holding barnacles.yaml (default: the current folder) or the file itself.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__, config, thumbnails
from .build import build
from .marimo_export import marimo

SCAFFOLD = Path(__file__).parent / "scaffold"


def cmd_init(args: argparse.Namespace) -> None:
    target = Path(args.dir)
    files = {}  # scaffold file -> destination ("gitignore" is shipped without its dot)
    for src in sorted(p for p in SCAFFOLD.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        rel = src.relative_to(SCAFFOLD)
        files[src] = target / (rel.with_name(".gitignore") if rel.name == "gitignore" else rel)
    if clash := [str(d) for d in files.values() if d.exists()]:
        raise config.ConfigError(f"not overwriting existing file(s): {', '.join(clash)}")
    for src, dest in files.items():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)
        print(f"  created {dest}")
    cd = "" if target.resolve() == Path.cwd() else f"cd {args.dir}\n  "
    print(f"\nNext:\n  {cd}barnacles serve")


def cmd_build(args: argparse.Namespace) -> None:
    build(config.load(args.project), screenshots=not args.no_thumbnails)


def cmd_serve(args: argparse.Namespace) -> None:
    cfg = config.load(args.project)
    if not args.no_build:
        build(cfg, screenshots=not args.no_thumbnails)
    if not (cfg.dist / "index.html").is_file():
        raise config.ConfigError(f"nothing to serve in {cfg.dist}; run `barnacles build` first")

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *a) -> None:
            pass

    server = ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(cfg.dist)))
    print(f"Serving {cfg.dist} at http://{args.host}:{server.server_port}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def cmd_edit(args: argparse.Namespace) -> None:
    target = Path(args.target)
    if target.suffix != ".py":  # a project: open its notebooks folder in marimo's file browser
        target = config.load(target).notebooks
    marimo("edit", str(target))


def cmd_install_browser(args: argparse.Namespace) -> None:
    thumbnails.install_browser(with_deps=args.with_deps)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="barnacles", description="A static HTML catalog for marimo apps.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")
    project = {"nargs": "?", "default": ".", "help": "folder with barnacles.yaml, or the file (default: .)"}

    s = sub.add_parser("init", help="create barnacles.yaml and example notebooks")
    s.add_argument("dir", nargs="?", default="barnacles", help="where to create the project (default: barnacles)")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("build", help="export every notebook and render the catalog")
    s.add_argument("project", **project)
    s.add_argument("--no-thumbnails", action="store_true", help="skip notebook screenshots (faster)")
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("serve", help="build, then serve the catalog locally")
    s.add_argument("project", **project)
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--no-build", action="store_true", help="serve the existing build")
    s.add_argument("--no-thumbnails", action="store_true", help="skip notebook screenshots (faster)")
    s.set_defaults(func=cmd_serve)

    s = sub.add_parser("edit", help="open notebooks in the marimo editor")
    s.add_argument("target", nargs="?", default=".", help="a project (opens its notebooks folder) or a notebook .py")
    s.set_defaults(func=cmd_edit)

    s = sub.add_parser("install-browser", help="download the Chromium used for thumbnails (build does this when needed)")
    s.add_argument("--with-deps", action="store_true", help="also install its system libraries (Linux; uses sudo)")
    s.set_defaults(func=cmd_install_browser)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        args.func(args)
    except (config.ConfigError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
