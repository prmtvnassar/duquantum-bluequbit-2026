"""Portable Matplotlib figures using only executed, labeled records."""

from pathlib import Path

COLORS = {"exact": "#262626", "mps": "#2864A0", "pps": "#B66B22"}


def _style():
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "figure.dpi": 120, "savefig.dpi": 150})


def _save(figure, directory, name):
    if directory:
        path = Path(directory) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(path, bbox_inches="tight")
    return figure


def plot_predictions(records, directory=None):
    import matplotlib.pyplot as plt
    from .analysis import records_frame
    _style()
    frame = records_frame(records)
    frame = frame[(frame.status == "SUCCEEDED") & frame.estimate.notna()]
    if frame.empty:
        return None
    labels = sorted(frame["sample"].unique())
    figure, axes = plt.subplots(len(labels), 1, figsize=(9, 2.8 * len(labels)), squeeze=False)
    for axis, label in zip(axes[:, 0], labels):
        group = frame[frame["sample"] == label]
        for method, linestyle in [("exact", "-"), ("mps", "--"), ("pps", ":")]:
            available = group[group.method == method]
            if available.empty:
                continue
            # Show the finest requested setting, retaining missing IDs as gaps.
            if method == "mps":
                setting = max(available.parameters, key=lambda p: float("inf") if p.get("chi") is None else p["chi"])
                available = available[available.parameters.map(lambda p: p == setting)]
            elif method == "pps":
                eta = min(p["eta"] for p in available.parameters)
                available = available[available.parameters.map(lambda p: p["eta"] == eta)]
            available = available.sort_values("qubit").set_index("qubit")
            indices = range(int(group.num_qubits.max()))
            values = available.estimate.reindex(indices)
            axis.plot(list(indices), values, marker="o", markersize=3, linestyle=linestyle,
                      color=COLORS[method], label=f"{method.upper()} ({available.setting.iloc[0]})")
        axis.set(title=f"{label}: per-ID Pauli-Z estimates", xlabel="Target qubit q", ylabel="Expectation value")
        axis.axhline(0, color="0.7", linewidth=0.7)
        axis.legend(fontsize=8, loc="best")
    figure.tight_layout()
    return _save(figure, directory, "predictions.png")


def plot_convergence(summary, directory=None):
    import matplotlib.pyplot as plt
    _style()
    if summary.empty or not summary.mae.notna().any():
        return None
    figure, axes = plt.subplots(1, 2, figsize=(10, 3.5))
    for axis, method in zip(axes, ("mps", "pps")):
        for label, group in summary[(summary.method == method) & summary.mae.notna()].groupby("sample"):
            group = group[~group.setting.str.contains("unlimited")].copy()
            if group.empty:
                continue
            group["x"] = group.setting.str.split("=").str[1].astype(float)
            group = group[group.x > 0].sort_values("x")
            axis.plot(group.x, group.mae, marker="o", label=label)
        axis.set_xscale("log", base=2 if method == "mps" else 10)
        axis.set_yscale("symlog", linthresh=1e-13)
        axis.set(title=f"{method.upper()}: error against exact references",
                 xlabel="Bond dimension chi" if method == "mps" else "Total OBP L1 budget eta",
                 ylabel="MAE on paired IDs")
        if method == "pps":
            axis.invert_xaxis()
        handles, _ = axis.get_legend_handles_labels()
        if handles:
            axis.legend(fontsize=8)
        axis.grid(alpha=0.18)
    figure.tight_layout()
    return _save(figure, directory, "convergence.png")


def plot_cost_error(summary, directory=None):
    import matplotlib.pyplot as plt
    _style()
    if summary.empty:
        return None
    valid = summary[(summary.method != "exact") & summary.mae.notna() & (summary.wall_seconds > 0)]
    if valid.empty:
        return None
    figure, axis = plt.subplots(figsize=(8, 4))
    for (label, method), group in valid.groupby(["sample", "method"]):
        axis.scatter(group.wall_seconds, group.mae, label=f"{label} {method.upper()}",
                     color=COLORS[method], marker="o" if method == "mps" else "s", alpha=0.8)
        for row in group.itertuples():
            axis.annotate(row.setting, (row.wall_seconds, row.mae), xytext=(4, 4),
                          textcoords="offset points", fontsize=7)
    axis.set_xscale("log")
    axis.set_yscale("symlog", linthresh=1e-13)
    axis.set(xlabel="Sum of task wall times, including process startup (s)", ylabel="MAE on paired IDs",
             title="Accuracy and end-to-end CPU cost")
    axis.grid(alpha=0.18)
    axis.legend(fontsize=8)
    figure.tight_layout()
    return _save(figure, directory, "cost_error.png")


def plot_diagnostics(records, directory=None):
    import matplotlib.pyplot as plt
    from .analysis import records_frame
    _style()
    frame = records_frame(records)
    if frame.empty:
        return None
    figure, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for axis, method, column, xlabel in [
        (axes[0], "mps", "max_bond_actual", "Bond limit chi"),
        (axes[1], "pps", "peak_num_paulis", "Total OBP L1 budget eta"),
    ]:
        valid = frame[(frame.method == method) & frame[column].notna()]
        for label, group in valid.groupby("sample"):
            points = []
            for setting, item in group.groupby("setting"):
                raw = setting.split("=")[1]
                if raw == "unlimited" or float(raw) <= 0:
                    continue
                points.append((float(raw), item[column].max()))
            if points:
                x, y = zip(*sorted(points))
                axis.plot(x, y, marker="o", label=label)
        axis.set_xscale("log", base=2 if method == "mps" else 10)
        if method == "pps":
            axis.invert_xaxis()
        axis.set(xlabel=xlabel, ylabel="Maximum across executed IDs",
                 title="Actual MPS bond" if method == "mps" else "Peak retained Pauli terms")
        handles, _ = axis.get_legend_handles_labels()
        if handles:
            axis.legend(fontsize=8)
        axis.grid(alpha=0.18)
    figure.tight_layout()
    return _save(figure, directory, "diagnostics.png")


def plot_checks(checks, directory=None):
    import matplotlib.pyplot as plt
    import numpy as np
    _style()
    if checks.empty:
        return None
    cases = list(dict.fromkeys(checks["case"]))
    figure, axis = plt.subplots(figsize=(10, 3.7))
    for offset, method in zip((-0.22, 0, 0.22), ("exact", "mps", "pps")):
        selected = checks[checks.method == method].set_index("case").reindex(cases)
        axis.scatter(np.arange(len(cases)) + offset, selected.abs_error,
                     label=method.upper(), color=COLORS[method], marker={"exact": "o", "mps": "s", "pps": "^"}[method])
    axis.set_xticks(range(len(cases)), cases, rotation=25, ha="right")
    axis.set_yscale("symlog", linthresh=1e-13)
    axis.set(ylabel="Absolute error against analytic/Statevector check",
             title="Synthetic correctness checks only — not S1/S2/S3 results")
    axis.legend(fontsize=8)
    axis.grid(axis="y", alpha=0.18)
    figure.tight_layout()
    return _save(figure, directory, "synthetic_checks.png")
