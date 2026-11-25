# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo"]
# ///

import marimo

__generated_with = "0.26.0"
app = marimo.App(width="medium", app_title="Static HTML example")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # Static HTML example

    This page was exported with `marimo export html`. All Python ran **at build time**,
    so the output below is frozen and UI elements won't recompute in the browser.
    """)
    return


@app.cell
def _(mo):
    import datetime

    _rows = [{"month": m, "revenue": 100 + 17 * i} for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun"])]
    mo.vstack(
        [
            mo.md(f"Built at **{datetime.datetime.now():%Y-%m-%d %H:%M}**"),
            mo.ui.table(_rows, selection=None),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
