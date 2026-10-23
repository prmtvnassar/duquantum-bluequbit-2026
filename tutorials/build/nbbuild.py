"""Builds the study notebooks from the nbXX_*.py content files.

    python tutorials/build/nbbuild.py            # writes tutorials/study/*.ipynb and tutorials/study/solutions/*_solved.ipynb

Each content module defines NAME (file stem) and CELLS, a list made with md(), code() and ex().
Exercises become a stub in the student notebook and the worked solution in the solved one.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from textwrap import dedent

import nbformat as nbf

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "study"
SOL = OUT / "solutions"


def md(s):
    return [("md", dedent(s).strip("\n"))]


def code(s):
    return [("code", dedent(s).strip("\n"))]


def ex(title, prompt, stub, solution, check, hint=None):
    text = f"### ✏️ Exercise: {title}\n\n" + dedent(prompt).strip("\n")
    if hint:
        text += "\n\n<details><summary>Hint (click)</summary>\n\n" + dedent(hint).strip("\n") + "\n\n</details>"
    stub, solution, check = (dedent(s).strip("\n") for s in (stub, solution, check))
    return [("md", text), ("ex", stub, solution, check)]


KERNEL = {"name": "bluqubit", "display_name": "Python (BluQubit)", "language": "python"}


def build(module_name):
    mod = importlib.import_module(module_name)
    for solved in (False, True):
        nb = nbf.v4.new_notebook()
        nb.metadata["kernelspec"] = KERNEL
        nb.metadata["language_info"] = {"name": "python"}
        for cell in (c for group in mod.CELLS for c in group):
            if cell[0] == "md":
                nb.cells.append(nbf.v4.new_markdown_cell(cell[1]))
            elif cell[0] == "code":
                nb.cells.append(nbf.v4.new_code_cell(cell[1]))
            else:
                _, stub, solution, check = cell
                body = solution if solved else stub
                nb.cells.append(nbf.v4.new_code_cell(body + "\n\n# --- check (don't edit) ---\n" + check))
        if solved:
            # solved notebooks live one folder down: make imports still find the helpers
            nb.cells.insert(0, nbf.v4.new_code_cell(
                "import sys, os\nsys.path.insert(0, os.path.abspath('..'))\nos.chdir('..')  # run from the study folder"))
            nb.cells.insert(0, nbf.v4.new_markdown_cell(
                "> **Solved version.** Every exercise is filled in. Try the student notebook first."))
        path = (SOL / f"{mod.NAME}_solved.ipynb") if solved else (OUT / f"{mod.NAME}.ipynb")
        path.parent.mkdir(parents=True, exist_ok=True)
        nbf.write(nb, path)
        print("wrote", path.relative_to(HERE.parent.parent))


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    names = sys.argv[1:] or sorted(p.stem for p in HERE.glob("nb[0-9][0-9]_*.py"))
    for name in names:
        build(name)
