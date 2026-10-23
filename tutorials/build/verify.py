"""Build, execute student + solved notebooks, and summarise checks.

    python tutorials/build/verify.py [nb00_linear_algebra ...]

Solved notebooks must have zero FAIL/TODO and no errors. Student notebooks must run with no errors.
"""
import json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
STUDY = ROOT / "tutorials" / "study"
OUT = ROOT / "scratch" / "exec"
names = sys.argv[1:] or sorted(p.stem for p in (ROOT / "tutorials" / "build").glob("nb[0-9][0-9]_*.py"))
subprocess.run([str(PY), str(ROOT / "tutorials" / "build" / "nbbuild.py"), *names], check=True)
ok_all = True
sys.path.insert(0, str(ROOT / "tutorials" / "build"))
for name in names:
    stem = __import__(name).NAME
    for nb, solved in ((STUDY / f"{stem}.ipynb", False), (STUDY / "solutions" / f"{stem}_solved.ipynb", True)):
        t = time.time()
        r = subprocess.run([str(PY), "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
                            "--ExecutePreprocessor.kernel_name=bluqubit", "--ExecutePreprocessor.timeout=1200",
                            "--allow-errors", str(nb), "--output-dir", str(OUT)], cwd=nb.parent, capture_output=True, text=True)
        out = OUT / nb.name
        counts = {"PASS": 0, "FAIL": 0, "TODO": 0}; errors = []
        if out.exists():
            for c in json.loads(out.read_text(encoding="utf-8"))["cells"]:
                for o in c.get("outputs", []):
                    if o.get("output_type") == "error":
                        errors.append(f"{o['ename']}: {o['evalue'][:200]}")
                    for line in "".join(o.get("text", "")).splitlines():
                        for k in counts:
                            if f" {k}  " in line:
                                counts[k] += 1
                                if solved and k != "PASS": errors.append(line.encode("ascii", "replace").decode())
        else:
            errors.append(r.stderr[-1500:])
        good = not errors and (not solved or counts["FAIL"] + counts["TODO"] == 0)
        ok_all &= good
        print(f"{'OK ' if good else 'BAD'} {nb.name:45s} {time.time()-t:6.1f}s  {counts}")
        for e in errors[:8]: print("     ", e)
sys.exit(0 if ok_all else 1)
