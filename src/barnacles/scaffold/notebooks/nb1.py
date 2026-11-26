# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo"]
# ///

import marimo

__generated_with = "0.26.0"
app = marimo.App(width="medium", app_title="Notebook 1")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # Notebook 1

    A notebook at the top of `notebooks/` gets a card on the catalog home page.
    It was exported with `marimo export html`: it ran **once at build time**, so it loads fast
    and needs no Python in the browser.
    """)
    return


if __name__ == "__main__":
    app.run()
