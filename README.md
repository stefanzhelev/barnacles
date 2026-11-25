# Barnacles

A static gallery for [marimo](https://marimo.io) notebooks. Point it at a folder of notebooks, describe them in one `barnacles.yaml`, and get a site you can host anywhere (GitHub Pages included). Folders become gallery folders, each notebook gets a card with a light/dark thumbnail, and notebooks run either in the browser (WASM) or once at build time (static HTML).

## Install

```sh
uv tool install barnacles      # or: pip install barnacles
```

That is all. The first build that needs card thumbnails downloads a headless Chromium (about 100 MB, see [Thumbnails](#thumbnails)).

## Usage

```sh
barnacles init my-gallery     # creates my-gallery/barnacles.yaml + my-gallery/notebooks/example.py
cd my-gallery
barnacles serve               # build, then serve at http://127.0.0.1:8000
barnacles edit                # open the notebooks in the marimo editor
barnacles build               # build into dist/ for publishing
```

Each command takes an optional project path (a folder with `barnacles.yaml`, or the file itself). `build` and `serve` accept `--no-thumbnails` for faster builds. Run `barnacles <command> -h` for all options.

## Thumbnails

Each notebook card shows a light and a dark screenshot of the notebook, taken with [Playwright](https://playwright.dev/python/)'s headless Chromium. Playwright comes with barnacles, but uv (or pip) can't download the browser itself, so barnacles does it:

- **Automatically:** when a build needs screenshots and Chromium is missing, barnacles runs `python -m playwright install --only-shell chromium` with its own Python, printing the command first. This happens once per Playwright version. The browser goes into Playwright's shared cache (`~/Library/Caches/ms-playwright` on macOS, `~/.cache/ms-playwright` on Linux, `%LOCALAPPDATA%\ms-playwright` on Windows; set `PLAYWRIGHT_BROWSERS_PATH` to change it).
- **Explicitly:** `barnacles install-browser` does the same step on its own, e.g. as a separate CI step. On a fresh Linux machine, `barnacles install-browser --with-deps` also installs Chromium's system libraries (via `apt`, so it needs sudo and Debian/Ubuntu).

If the browser can't be installed or started (offline, missing Linux libraries), the build still succeeds: it prints a warning saying how to fix it, and the cards show a letter instead. Use `--no-thumbnails` to skip screenshots, or set `thumbnail` in `barnacles.yaml` to use your own images.

### In CI

On GitHub Actions, the plain install works:

```yaml
- uses: astral-sh/setup-uv@v6
- run: uv tool install barnacles    # or: pip install barnacles
- run: barnacles build              # downloads Chromium on the first run
```

To keep the download in its own step and cache it between runs:

```yaml
- uses: astral-sh/setup-uv@v6
- run: uv tool install barnacles    # or: pip install barnacles
- uses: actions/cache@v4
  with:
    path: ~/.cache/ms-playwright
    key: ms-playwright-${{ runner.os }}-${{ hashFiles('**/requirements*.txt', '**/uv.lock') }}
- run: barnacles install-browser    # add --with-deps on minimal Linux images
- run: barnacles build
```

## barnacles.yaml

Every key is optional. All paths, including the keys under `items`, are relative to `barnacles.yaml`.

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
uv run barnacles serve demo              # the demo gallery in demo/
uv run pytest
```

Releases: bump `__version__` in `src/barnacles/__init__.py`, push, then publish a GitHub release tagged `v<version>` (e.g. `v0.2.0`). `.github/workflows/publish.yml` checks the tag matches, runs the tests, builds the package and uploads it to PyPI.

## License

MIT, see [LICENSE](LICENSE).
