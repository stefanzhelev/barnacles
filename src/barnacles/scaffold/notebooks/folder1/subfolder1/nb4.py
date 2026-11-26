# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo"]
# ///

import marimo

__generated_with = "0.26.0"
app = marimo.App(width="medium", app_title="Notebook 4")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # Notebook 4

    Folders can be nested. This notebook lives in `notebooks/folder1/subfolder1/`,
    so its card is on the Subfolder 1 page, inside Folder 1.

    Like the others it is static HTML. To make a notebook interactive, set
    `mode: html-wasm` for it in `barnacles.yaml`: Python then runs in the browser.
    """)
    return


if __name__ == "__main__":
    app.run()
