# Barnacles

A static gallery for [marimo](https://marimo.io) notebooks. Point it at a folder of notebooks, describe them in one `barnacle.yaml`, and get a site you can host anywhere (GitHub Pages included). Folders become gallery folders, each notebook gets a card with a light/dark thumbnail, and notebooks run either in the browser (WASM) or once at build time (static HTML).

## Install

```sh
pip install barnacles                    # or: uv tool install barnacles
pip install "barnacles[thumbnails]"      # optional: notebook screenshots for the cards
playwright install chromium              #   (needed once for thumbnails)
```

## Usage

```sh
barnacles init my-gallery     # barnacle.yaml + notebooks/example.py
cd my-gallery
barnacles serve               # build, then serve at http://127.0.0.1:8000
barnacles edit                # open the notebooks in the marimo editor
barnacles build               # build into dist/ for publishing
```

Each command takes an optional project path (a folder with `barnacle.yaml`, or the file itself). `build` and `serve` accept `--no-thumbnails` for faster builds. Run `barnacles <command> -h` for all options.

## barnacle.yaml

Every key is optional. All paths, including the keys under `items`, are relative to `barnacle.yaml`.

```yaml
site:
  title: Energy notebooks         # browser tab title
  header_title: Barnacles         # text next to the logo (defaults to title)
  logo: assets/logo.svg           # defaults to the barnacles logo
  favicon: assets/favicon.svg     # defaults to the logo

paths:
  notebooks: notebooks            # default
  dist: dist                      # default; wiped on every build

defaults:                         # applied to every notebook / folder
  notebook:
    mode: html-wasm
  folder:
    description: ""

items:                            # overrides per notebook or folder, keyed by path
  "notebooks":                    # the notebooks folder itself = the home page
    title: All notebooks
  "notebooks/prices.py":
    title: Electricity prices
    description: Daily price analysis
    thumbnail: thumbnails/prices.png
  "notebooks/forecasts":
    title: Forecasts
```

Settings are resolved in this order: `items`, then `defaults`, then the built-in fallbacks below.

| item key | applies to | meaning (fallback) |
|---|---|---|
| `title` | both | display name (notebook: `marimo.App(app_title=...)`, then the slug; folder: its name; home page: "Notebooks") |
| `description` | both | text on the card and the folder page (none) |
| `mode` | notebook | `html-wasm` runs in the browser, `html` runs once at build time (`html-wasm`) |
| `slug` | notebook | URL segment (the file name, with `_` turned into `-`) |
| `thumbnail`, `thumbnail_dark` | notebook | card images for light and dark themes (a screenshot of the notebook; the light image is used for both if no dark one is given) |

Notes:

- A notebook appears without an `items` entry. You only add one to override something.
- Folders with no notebooks, and folders whose names start with `.` or `_`, are skipped.
- The build stops on unknown keys and on `items` that match no notebook or folder.
- All links in the output are relative, so it works at a domain root or under a subpath.

## Development

```sh
uv sync                                  # installs barnacles in editable mode + dev tools
uv run playwright install chromium
uv run barnacles serve demo              # the demo gallery in demo/
uv run pytest
```

Releases: bump `__version__` in `src/barnacles/__init__.py`, then publish a GitHub release. `.github/workflows/publish.yml` builds the package and uploads it to PyPI.

## License

MIT, see [LICENSE](LICENSE).
