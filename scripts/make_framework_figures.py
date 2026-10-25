"""Figures for FRAMEWORK.md and the talk (offline, no API calls).

    python scripts/g4_simulation_only.py        # first: writes reports/g4_simulation_only.json
    python scripts/make_framework_figures.py    # writes reports/figures/framework/ and reports/figures/circuits/

Circuit drawings need qiskit's matplotlib drawer (`pip install pylatexenc`); they are skipped if it is missing.
Samples are drawn from their public QASM; graded circuits are hidden, so their drawings are reconstructions of
the gate pattern (published size/geometry + the layering read off sample S3), not the real circuits.
"""
import json, textwrap
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch

REPO = Path(__file__).resolve().parents[1]
FW = REPO / "reports/figures/framework"; CI = REPO / "reports/figures/circuits"
BLUE, ORANGE, AQUA, INK, MUTE, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#1f2933", "#52606d", "#9aa5b1"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#cbd2d9", "xtick.color": MUTE, "ytick.color": MUTE})
STYLE = {"io": ("#eef4fc", BLUE), "step": ("#ffffff", GREY), "loop": ("#f5f7fa", GREY), "new": ("#eaf7f1", AQUA),
         "fail": ("#fdecec", "#c0392b"), "warn": ("#fff4ec", ORANGE)}

# ------------------------------------------------------------------ flowchart versions v0-v2 (vertical pipelines)
def pipeline(name, title, subtitle, items, loop=None, legend=True):
    items = [(k, [w for l in ls for w in (textwrap.wrap(l, 96, subsequent_indent="  ") or [""])]) for k, ls in items]
    heights = [3.6 + 2.6 * (len(l) - 1) for _, l in items]; total = sum(heights) + 2.6 * (len(items) - 1) + 17
    fig, ax = plt.subplots(figsize=(7.4, 0.105 * total + 0.6), dpi=200); ax.set_xlim(0, 100); ax.set_ylim(0, total); ax.axis("off")
    ax.text(2, total - 2.5, title, fontsize=10.5, fontweight="bold", color=INK, va="top")
    ax.text(2, total - 6.3, subtitle, fontsize=7.2, color=MUTE, va="top")
    y = total - 11; spans = []
    for (kind, lines), h in zip(items, heights):
        fc, ec = STYLE[kind]
        ax.add_patch(FancyBboxPatch((6, y - h), 82, h, boxstyle="round,pad=0.4,rounding_size=1.4", fc=fc, ec=ec, lw=0.9))
        ax.text(47, y - h / 2, "\n".join(lines), ha="center", va="center", fontsize=6.7, color=INK, linespacing=1.35)
        spans.append((y, y - h)); y -= h + 2.6
    for i in range(len(spans) - 1):
        ax.annotate("", xy=(47, spans[i + 1][0] + 0.4), xytext=(47, spans[i][1] - 0.4), arrowprops=dict(arrowstyle="-|>", color=MUTE, lw=0.8))
    if loop:
        a, b, lab = loop; ya = sum(spans[a]) / 2; yb = sum(spans[b]) / 2
        ax.plot([88.6, 93, 93], [yb, yb, ya], color=MUTE, lw=0.8)
        ax.annotate("", xy=(88.6, ya), xytext=(93, ya), arrowprops=dict(arrowstyle="-|>", color=MUTE, lw=0.8))
        ax.text(94, (ya + yb) / 2, lab, fontsize=6.2, color=MUTE, rotation=90, va="center")
    if legend:
        lx = 2
        for kind, lab in [("new", "new in this version"), ("fail", "tested and dropped"), ("warn", "where it broke")]:
            fc, ec = STYLE[kind]; ax.add_patch(FancyBboxPatch((lx, 0.8), 3, 2, boxstyle="round,pad=0.2", fc=fc, ec=ec, lw=0.8))
            ax.text(lx + 4, 1.8, lab, fontsize=6.2, color=MUTE, va="center"); lx += 24
    fig.savefig(FW / name, bbox_inches="tight"); plt.close(fig)

def flowcharts():
    pipeline("flow_v0.png", "v0  Pre-event plan (23 Oct, before kickoff; v1 on 24 Oct adapted it to the released rules)",
             "docs/history/estimation_workflow_v0.md and workflow_v1.md. Assumption: approximate simulators converge as precision rises.",
             [("io", ["Read the challenge kit; validate circuit IDs and the Z-observable / qubit ordering"]),
              ("step", ["Calibrate on samples with exact answers: accuracy, score and cost of each method"]),
              ("step", ["Low-fidelity pass over every target (small MPS chi, large PPS threshold): a complete baseline first"]),
              ("loop", ["Diagnostics: pointwise change, change of vector shape, MPS-vs-PPS disagreement, transpilation sensitivity"]),
              ("loop", ["Choose the next action with the best expected benefit per cost"]),
              ("loop", ["Run it: MPS higher chi  /  PPS lower threshold  /  other transpilation"]),
              ("step", ["Choose the estimator: direct, extrapolated in precision, or fused across methods",
                        "(extrapolation and fusion only if they help on the samples)"]),
              ("io", ["Validate the per-problem CSV and method note; submit; archive provenance"])],
             loop=(3, 5, "repeat while budget and time remain"), legend=False)
    pipeline("flow_v1.png", "v1  Graded workflow (24 Oct, after samples and the first graded runs)",
             "docs/history/workflow_final_graded.md. Results: samples 100/100/100, G1 300, G2 342 -> 581, G3 534 -> 773; G4 stuck at 0 / 133.",
             [("io", ["Per problem: read the IDs; one vector = one device + identical options for every row (coherent cohort)"]),
              ("new", ["Pick the method from the circuit family, calibrated on the samples:",
                       "<= 34 qubits -> exact (G1)   |   1-D chain -> MPS (G2)   |   mostly-Clifford grid -> PPS (G3)"]),
              ("new", ["Fix the representation before precision: test PPS transpilation levels on known or pilot rows",
                       "(S3_1 at threshold 0.01: levels 2/3 returned 0; G3 pilots: level 2 returned zeros, level 1 kept the signal)"]),
              ("new", ["Every cloud job audited: fresh quote -> budget gate -> receipt -> ledger; one active job; no blind retries"]),
              ("loop", ["Raise precision; refine only rows that keep moving between precisions (G2: chi512 on 23 rows, chi2048 on q30)"]),
              ("fail", ["Extrapolation in precision and cross-method fusion: failed held-out sample tests -> switched off"]),
              ("warn", ["G4 (38-qubit Haar grid): MPS chi32 vector scored 0; PPS at threshold >= 0.001 returned zeros.",
                        "Raising precision did not change this."]),
              ("io", ["Export the complete direct vector with its method note and per-row job manifest"])])
    pipeline("flow_v2.png", "v2  G4 investigation (24-25 Oct night): find out what each simulator can see",
             "research_notes/g4_alternative_techniques.md, proxy_lab, sample_lab, debate. No new physics assumed; every step measured.",
             [("new", ["Check the circuit structure on the samples: blocks U, X_b, U†, Z_q, U, X_b, U† are exact inverses -> an echo"]),
              ("new", ["Test transpilation as a simplifier: level 3 cancels U·U† pairs outside the light cone",
                       "(locally on samples; natively it was the only level with signal on G4)"]),
              ("new", ["Build exact proxies of the same generator (16-32 qubits) and score every method against them"]),
              ("new", ["Learn what each method sees: early-contact rows ~ 0 (noise floor), signal on late-contact rows;",
                       "MPS = arrival-geometry map at every chi; PPS = front detector, about half the signs"]),
              ("new", ["Measure the geometry on the circuit itself: all-Z MPS jobs give a contact map for the price of one row"]),
              ("fail", ["Priors from proxies (class means by arrival time): 400-700 on held-out proxies, 2 on G4;",
                        "averaging / extrapolating in chi or threshold: never beat the best single input"]),
              ("new", ["Validated post-processing: subtract PPS's projection on the MPS vector",
                       "(known-answer proxy 301 -> 424; G4 133 -> ~190 with no score feedback)"]),
              ("warn", ["Ceiling of simulation + understanding with the tools we had: about 190-200.",
                        "Finer PPS on late-contact rows is the only simulator lever left (refused below 2e-5 at 38 qubits)."])])
    flow_v3()

# ------------------------------------------------------------------ flowchart v3 (decision tree)
def flow_v3():
    fig, ax = plt.subplots(figsize=(7.4, 10.4), dpi=200); ax.set_xlim(0, 100); ax.set_ylim(-5, 142); ax.axis("off")
    def box(x, y, w, h, lines, fc="#eef4fc", ec=BLUE, fs=6.8, bold=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.5", fc=fc, ec=ec, lw=0.9))
        ax.text(x + w / 2, y + h / 2, "\n".join(lines), ha="center", va="center", fontsize=fs, color=INK, fontweight="bold" if bold else "normal", linespacing=1.35)
    def arrow(x1, y1, x2, y2, lab=None):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color=MUTE, lw=0.9))
        if lab: ax.text((x1 + x2) / 2 - 1.5, (y1 + y2) / 2 + 1.2, lab, fontsize=6.5, color=MUTE)
    box(4, 131, 92, 9, ["INPUT: OTOC(2) echo circuits  U, X_b, U†, Z_q, U, X_b, U†  (one per target qubit q)",
                        "qubits n, depth d, geometry (chain / grid), gate family (Haar / mostly Clifford), scoring metric"], bold=True)
    box(4, 118, 92, 10, ["ALWAYS: audited jobs (quote -> budget gate -> receipt -> ledger)",
                         "calibrate on known answers first (samples; exact proxies of the same generator, up to ~32 qubits)",
                         "predict each result before using it; disclose the method"], fc="#f5f7fa", ec=GREY)
    qx, qw, mx, mw, bh = 4, 33, 43, 53, 11
    rows = [(103, ["Q1. n <= ~34?", "(exact simulation allowed)"], ["EXACT STATEVECTOR", "S1, S2, G1 -> 100, 100, 300/300"]),
            (87, ["Q2. 1-D chain, or otherwise", "low entanglement?"],
             ["MPS: sweep chi upward (the chi needed grows", "roughly exponentially with depth); refine only rows", "that move between chi values.",
              "G2: chi32 342 -> chi128 498 -> mixed chi512 579 -> 581"]),
            (71, ["Q3. Mostly Clifford gates?"],
             ["PAULI PROPAGATION: test the transpilation level on", "known or pilot rows (level 1 for G3); tighten the",
              "threshold until few rows read 0.  G3: 534 -> 773"])]
    for y, q, m in rows:
        box(qx, y, qw, bh, q, fc="#ffffff"); box(mx, y, mw, bh, m, fc="#eaf7f1", ec=AQUA, fs=6.5)
        arrow(qx + qw + 0.6, y + bh / 2, mx - 0.6, y + bh / 2, "yes")
    arrow(qx + qw / 2, 118, qx + qw / 2, 103 + bh + 0.6); arrow(qx + qw / 2, 102.4, qx + qw / 2, 87 + bh + 0.6, "no")
    arrow(qx + qw / 2, 86.4, qx + qw / 2, 71 + bh + 0.6, "no"); arrow(qx + qw / 2, 70.4, qx + qw / 2, 69.6, "no")
    box(4, 56, 92, 13, ["SCRAMBLING REGIME (G4): 2-D Haar gates, depth comparable to or larger than the grid diameter.",
                        "Expect: rows the disturbance reaches early ~ 0 (noise floor); signal only on late-contact rows,",
                        "with instance-specific signs.  MPS reads arrival geometry only; PPS finds the front, about half the signs."], fc="#fff4ec", ec=ORANGE)
    steps = [["a. Exact proxies of the same generator: measure what each method scores before trusting it"],
             ["b. Contact map on the circuit: one MPS all-Z job per row (observable list at no extra cost)", "    -> which rows the disturbance reaches late"],
             ["c. PPS at the finest admissible threshold, transpilation level 3;", "    check sign stability across a threshold ladder on the late-contact rows"],
             ["d. Validated post-processing only: subtract PPS's projection on the MPS vector", "    (known-answer proxy 301 -> 424; G4 133 -> ~190 without any website score)"],
             ["e. Only if repeated, disclosed scoring is allowed: treat scores as measurements ->", "    remove measured-null vectors -> fit within their span (leave-one-out check) ->",
              "    check unmeasured directions  (G4: 199 -> 282 -> 998)"]]
    top, prev = 52, 56
    for st in steps:
        h = 4.2 + 3.0 * (len(st) - 1); arrow(50, prev - 0.5, 50, top + 0.6)
        box(8, top - h, 84, h, st, fc="#ffffff", ec="#cbd2d9", fs=6.4); prev = top - h; top = top - h - 3.4
    ax.text(4, -4, "v3 draft. Numbers are our measurements on 7 challenge circuits and ~30 exact proxies; thresholds are starting points, not rules.", fontsize=6, color=MUTE)
    fig.savefig(FW / "flow_v3.png", bbox_inches="tight"); plt.close(fig)

# ------------------------------------------------------------------ data figures
def data_figures(R):
    V = {k: np.array(v["values"]) for k, v in R["circuits"].items()}
    fig = plt.figure(figsize=(7.4, 8.4), dpi=200); gs = GridSpec(12, 2, figure=fig, hspace=1.6, wspace=0.28, left=0.07, right=0.92, top=0.93, bottom=0.05)
    for i, (k, t, b) in enumerate([("S1", "S1: 4-qubit chain, 4 layers, butterfly q0", 0), ("S2", "S2: 16-qubit chain, 12 layers, butterfly q0", 0),
                                   ("G1", "G1: 30-qubit chain, 32 layers, butterfly q0", 0), ("G2", "G2: 36-qubit chain, 18 layers, butterfly q18", 18)]):
        ax = fig.add_subplot(gs[3 * i:3 * i + 3, 0]); v = V[k]
        ax.axhline(0, color="#cbd2d9", lw=0.8); ax.plot(range(len(v)), v, color=BLUE, lw=1.6, marker="o", ms=2.5)
        ax.axvline(b, color=ORANGE, lw=1, ls="--"); ax.set_ylim(-0.5, 1.1); ax.set_title(t, fontsize=7.2, loc="left", color=INK)
        ax.tick_params(labelsize=6); [ax.spines[s].set_visible(False) for s in ("top", "right")]
        if len(v) <= 4: ax.set_xticks(range(len(v)))
        if i == 3: ax.set_xlabel("target qubit q (orange dashed line = butterfly)", fontsize=6.5)
    def heat(ax, a, R_, C, title, extra=None, mark=None):
        M = np.full((R_ + (1 if extra else 0), C), np.nan); M[:R_] = a[:R_ * C].reshape(R_, C)
        for q, (r, c) in (extra or {}).items(): M[r, c] = a[q]
        lim = np.nanmax(np.abs(M)); im = ax.imshow(M, cmap="RdBu_r", norm=TwoSlopeNorm(0, -lim, lim))
        if mark is not None: ax.plot(mark[1], mark[0], marker="x", color=INK, ms=5)
        ax.set_title(title, fontsize=7.2, loc="left", color=INK); ax.set_xticks([]); ax.set_yticks([])
        cb = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03); cb.ax.tick_params(labelsize=5.5)
    heat(fig.add_subplot(gs[0:4, 1]), V["S3"], 5, 6, "S3: 5x6 mostly-Clifford, 16 layers", mark=(2, 2))
    heat(fig.add_subplot(gs[4:8, 1]), V["G3"], 6, 6, "G3: 6x6 mostly-Clifford, 24 layers", mark=(2, 2))
    heat(fig.add_subplot(gs[8:12, 1]), V["G4"] - np.median(V["G4"]), 6, 6, "G4: 6x6+2 Haar, 16 layers (shape only)", extra={36: (6, 0), 37: (6, 1)}, mark=(0, 0))
    fig.suptitle("The answer vectors of all seven circuits (grids: red > 0 > blue, x = butterfly)", x=0.02, ha="left", fontsize=9.2, color=INK)
    fig.savefig(FW / "seven_circuits.png"); plt.close(fig)

    ch = R["chronology"]; fig, ax = plt.subplots(figsize=(7.4, 3.6), dpi=200); x = np.arange(len(ch))
    ax.plot(x, [c["implied_by_final"] for c in ch], color=BLUE, lw=1.8, marker="o", ms=3.5, label="score implied by the final vector")
    ax.plot([i for i, c in enumerate(ch) if c["website"] is not None], [c["website"] for c in ch if c["website"] is not None], ls="none", marker="s", mfc="none", mec=ORANGE, ms=6, label="website score")
    ax.set_xticks(x); ax.set_xticklabels([c["step"] for c in ch], rotation=60, ha="right", fontsize=6.3); ax.set_ylabel("score /1000", fontsize=8)
    ax.legend(frameon=False, fontsize=7, loc="upper left"); [ax.spines[s].set_visible(False) for s in ("top", "right")]
    ax.grid(axis="y", color="#e4e7eb", lw=0.8); ax.set_axisbelow(True)
    ax.set_title("How our estimate of the G4 answer evolved, upload by upload", fontsize=9, loc="left", color=INK)
    fig.tight_layout(); fig.savefig(FW / "g4_chronology.png"); plt.close(fig)

    steps = [("MPS chi32\n(all rows)", 0), ("PPS 1e-4", 133), ("PPS +\nMPS256 rows", 165), ("MPS chi64", 0), ("geometry\nprior", 2),
             ("PPS minus\nMPS proj.\n(no scores)", 194), ("residual\n(PPS minus\nnull dirs)", 199), ("span\nfit", 234), ("refit 2", 282),
             ("15 checks\n(model floor)", 721), ("all 28\nprobes", 998)]
    cols = [GREY, BLUE, BLUE, GREY, GREY, AQUA, BLUE, BLUE, BLUE, "#a9c7ee", ORANGE]
    fig, ax = plt.subplots(figsize=(7.4, 3.3), dpi=200); [ax.spines[s].set_visible(False) for s in ("top", "right")]
    ax.grid(axis="y", color="#e4e7eb", lw=0.8); ax.set_axisbelow(True)
    ax.bar(range(len(steps)), [s for _, s in steps], color=cols, width=0.7)
    for i, (_, s) in enumerate(steps): ax.text(i, s + 18, str(s), ha="center", fontsize=8, color=INK)
    ax.set_xticks(range(len(steps))); ax.set_xticklabels([n for n, _ in steps], fontsize=6.2); ax.set_ylabel("G4 score /1000"); ax.set_ylim(0, 1100)
    ax.set_title("G4 score ladder (grey = null, green = simulation only, not uploaded; light blue = model floor; orange = final)", loc="left", fontsize=8.4, color=INK)
    fig.tight_layout(); fig.savefig(FW / "g4_ladder.png"); plt.close(fig)

# ------------------------------------------------------------------ circuit drawings (qiskit)
def circuits():
    try:
        import pylatexenc  # noqa: F401  (required by qiskit's matplotlib drawer)
        from qiskit import QuantumCircuit
        from qiskit.circuit import Gate
    except ImportError:
        print("skipping circuit drawings (pip install pylatexenc)"); return
    st = {"fontsize": 9, "subfontsize": 7, "displaycolor": {"U": (BLUE, "#ffffff"), "U†": (BLUE, "#ffffff"), "SU4": ("#9cc3f0", INK), "Cliff+": ("#a6e3cd", INK)}}
    def save(qc, name, scale, fold=-1):
        f = qc.draw(output="mpl", fold=fold, scale=scale, style=st); f.savefig(CI / name, dpi=170, bbox_inches="tight"); plt.close(f)
    n = 6; qc = QuantumCircuit(n, 1); U = Gate("U", n, []); Ud = Gate("U†", n, [])
    qc.append(U, range(n)); qc.x(0); qc.append(Ud, range(n)); qc.z(4); qc.append(U, range(n)); qc.x(0); qc.append(Ud, range(n)); qc.measure(4, 0)
    save(qc, "echo_skeleton.png", 0.8)
    lines = (REPO / "problems/01_sample_S1/circuits/Duke_S1_0.qasm").read_text().splitlines(); body = lines[3:]
    cut = next(i for i, l in enumerate(body) if l.startswith("x "))
    save(QuantumCircuit.from_qasm_str("\n".join(lines[:3] + body[:cut])), "S1_first_block_real.png", 0.5, fold=40)
    def chain(nq): return [[(a, a + 1) for a in range(0, nq - 1, 2)], [(a, a + 1) for a in range(1, nq - 1, 2)]]
    def gridl(R_, C, extra=None):
        pos = {r * C + c: (r, c) for r in range(R_) for c in range(C)}; pos.update(extra or {})
        inv = {v: k for k, v in pos.items()}; L = {"H0": [], "V0": [], "H1": [], "V1": []}
        for q, (r, c) in pos.items():
            if (r, c + 1) in inv: L["H0" if c % 2 == 0 else "H1"].append((q, inv[(r, c + 1)]))
            if (r + 1, c) in inv: L["V0" if r % 2 == 0 else "V1"].append((q, inv[(r + 1, c)]))
        return [L[k] for k in ("H0", "V0", "H1", "V1")], len(pos)
    def period(nq, layers, label, name):
        qc = QuantumCircuit(nq)
        for L in layers:
            for a, b in L: qc.append(Gate(label, 2, []), [a, b])
            qc.barrier()
        save(qc, name, 0.4)
    period(16, chain(16), "SU4", "S2_pattern.png"); period(30, chain(30), "SU4", "G1_pattern_reconstructed.png")
    period(36, chain(36), "SU4", "G2_pattern_reconstructed.png")
    L, nq = gridl(5, 6); period(nq, L, "Cliff+", "S3_pattern.png")
    L, nq = gridl(6, 6); period(nq, L, "Cliff+", "G3_pattern_reconstructed.png")
    L, nq = gridl(6, 6, {36: (6, 0), 37: (6, 1)}); period(nq, L, "SU4", "G4_pattern_reconstructed.png")

if __name__ == "__main__":
    FW.mkdir(parents=True, exist_ok=True); CI.mkdir(parents=True, exist_ok=True)
    R = json.load(open(REPO / "reports/g4_simulation_only.json"))
    flowcharts(); data_figures(R); circuits(); print("figures written to", FW, "and", CI)
