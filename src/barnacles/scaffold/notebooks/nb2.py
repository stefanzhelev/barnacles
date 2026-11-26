# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo"]
# ///

import marimo

__generated_with = "0.26.0"
app = marimo.App(width="medium", app_title="Notebook 2")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # Notebook 2

    Outputs are computed at build time and saved into the page. Rebuild the catalog
    (for example in a CI/CD job) to refresh them.
    """)
    return


@app.cell
def _(mo):
    _rows = [{"month": m, "orders": 40 + 7 * i} for i, m in enumerate(["Jan", "Feb", "Mar", "Apr"])]
    mo.ui.table(_rows, selection=None)
    return


if __name__ == "__main__":
    app.run()
