"""checks.py: self-checks for the study-notebook exercises.

Every check prints one line: a pass, a fail with a hint, or "not done yet". It never raises, so a
notebook always runs top to bottom even with unfinished exercises.
"""
from __future__ import annotations

import numpy as np

PASS, FAIL, TODO = "PASS", "FAIL", "TODO"


def _say(status, name, msg=""):
    icon = {"PASS": "✅", "FAIL": "❌", "TODO": "⏳"}[status]
    print(f"{icon} {status}  {name}" + (f"  - {msg}" if msg else ""))
    return status == PASS


def close(name, got, expected, tol=1e-6, hint=""):
    """Compare a number / array with the expected one."""
    if got is None or got is Ellipsis:
        return _say(TODO, name, "fill in your answer")
    try:
        g, e = np.asarray(got, dtype=complex), np.asarray(expected, dtype=complex)
        if g.shape != e.shape:
            return _say(FAIL, name, f"shape {g.shape}, expected {e.shape}. {hint}")
        err = float(np.max(np.abs(g - e))) if g.size else 0.0
    except Exception as ex:  # noqa: BLE001
        return _say(FAIL, name, f"could not compare ({ex}). {hint}")
    if err <= tol:
        return _say(PASS, name)
    return _say(FAIL, name, f"off by {err:.3g}. {hint}")


def equal(name, got, expected, hint=""):
    if got is None or got is Ellipsis:
        return _say(TODO, name, "fill in your answer")
    if got == expected:
        return _say(PASS, name)
    return _say(FAIL, name, f"got {got!r}. {hint}")


def fn(name, f, cases, tol=1e-6, hint=""):
    """cases: list of (args_tuple, expected).  Calls f(*args) on each and compares."""
    for args, expected in cases:
        try:
            got = f(*args)
        except NotImplementedError:
            return _say(TODO, name, "function not written yet")
        except Exception as ex:  # noqa: BLE001
            return _say(FAIL, name, f"raised {type(ex).__name__}: {ex}. {hint}")
        if isinstance(expected, (bool, str, set, frozenset)) or (
                isinstance(expected, (tuple, list)) and any(isinstance(v, str) for v in expected)):
            ok = bool(got == expected)
            err_txt = f"got {got!r}, expected {expected!r}"
        else:
            try:
                g, e = np.asarray(got, dtype=complex), np.asarray(expected, dtype=complex)
                ok = g.shape == e.shape and (g.size == 0 or float(np.max(np.abs(g - e))) <= tol)
                err_txt = f"wrong result for one test input (got shape {g.shape}, expected {e.shape})"
            except Exception as ex:  # noqa: BLE001
                ok, err_txt = False, f"could not compare: {ex}"
        if not ok:
            return _say(FAIL, name, f"{err_txt}. {hint}")
    return _say(PASS, name, f"{len(cases)} test cases")


def truthy(name, cond, hint="", todo=False):
    if todo:
        return _say(TODO, name, "fill in your answer")
    return _say(PASS if cond else FAIL, name, "" if cond else hint)
