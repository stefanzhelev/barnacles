# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo"]
# ///

import marimo

__generated_with = "0.26.0"
app = marimo.App(width="medium", app_title="Notebook 3")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # Notebook 3

    Folders inside `notebooks/` become sections of the catalog. This notebook lives in
    `notebooks/folder1/`, so its card is on the Folder 1 page.
    """)
    return


if __name__ == "__main__":
    app.run()
