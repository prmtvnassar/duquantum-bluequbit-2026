#!/usr/bin/env python3
"""Sandbox CLI: async agent coordination over the `sandbox` git branch. Stdlib only.

Reads and writes go straight to origin/sandbox through git plumbing (temporary index,
commit-tree, push). The working tree, HEAD and index are never touched, so any number
of agents can share one checkout, on any branch, with uncommitted work. Every write
adds new files only, so concurrent pushes just retry, never conflict.
"""
import argparse, csv, io, json, math, os, re, secrets, subprocess, sys, tarfile, tempfile, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "sandbox" / "config.json").read_text(encoding="utf-8"))
REMOTE = os.environ.get("SB_REMOTE", "origin")
BR = CFG["branch"]
TRACK = f"refs/remotes/{REMOTE}/{BR}"
KINDS = ["finding", "run", "proposal", "claim", "vector", "score", "question", "directive", "join"]


def now():
    return datetime.now(timezone.utc)


def stamp():
    return now().strftime("%Y%m%dT%H%M%SZ")


def git(*a, check=True, env=None, data=None):
    r = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, input=data, env=env)
    if check and r.returncode:
        sys.exit(f"git {' '.join(a)} failed:\n{(r.stderr or r.stdout).decode(errors='replace')}")
    return r


def out(*a, **k):
    return git(*a, **k).stdout.decode().strip()


def handle():
    f = ROOT / ".sandbox_handle"
    h = os.environ.get("SB_HANDLE") or (f.read_text().strip() if f.exists() else "")
    if not h:
        sys.exit("No handle. Run: python sandbox/sb.py init <your-teammate-handle>")
    return h.lower()


def agent():
    return re.sub(r"[^a-z0-9_-]", "", (os.environ.get("SB_AGENT") or "main").lower()) or "main"


# ---- remote I/O ----------------------------------------------------------
def fetch():
    for i in range(6):
        if git("fetch", "-q", REMOTE, f"+refs/heads/{BR}:{TRACK}", check=False).returncode == 0:
            return True
        time.sleep(2 + 3 * i)
    print("WARN fetch failed; showing last fetched state", file=sys.stderr)
    return False


def snapshot():
    """{path: bytes} of sandbox/ at origin/sandbox, read from git objects in memory."""
    r = git("archive", "--format=tar", TRACK, "sandbox", check=False)
    if r.returncode:
        sys.exit(f"cannot read {TRACK}; is the branch pushed? {r.stderr.decode(errors='replace')}")
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as t:
        return {m.name: t.extractfile(m).read() for m in t.getmembers() if m.isfile()}


def ident_env(env):
    if not out("config", "user.email", check=False):
        h = handle()
        env.update(GIT_AUTHOR_NAME=f"sb-{h}", GIT_AUTHOR_EMAIL=f"{h}@sandbox.local",
                   GIT_COMMITTER_NAME=f"sb-{h}", GIT_COMMITTER_EMAIL=f"{h}@sandbox.local")
    return env


def publish(files, msg, overwrite=False):
    """Commit {repo-relative path: bytes|str} on top of origin/sandbox and push; retry on races."""
    for i in range(8):
        fetch()
        parent = out("rev-parse", TRACK)
        fd, idx = tempfile.mkstemp(prefix="sbidx-")
        os.close(fd)
        os.unlink(idx)
        env = ident_env(dict(os.environ, GIT_INDEX_FILE=idx))
        try:
            git("read-tree", parent, env=env)
            for path, data in files.items():
                if not overwrite and git("cat-file", "-e", f"{parent}:{path}", check=False).returncode == 0:
                    sys.exit(f"{path} already exists on {BR}; files are immutable, choose a new name")
                blob = out("hash-object", "-w", "--stdin", data=data.encode() if isinstance(data, str) else data)
                git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
            tree = out("write-tree", env=env)
            commit = out("commit-tree", tree, "-p", parent, "-m", f"sandbox: {msg}", env=env)
        finally:
            if os.path.exists(idx):
                os.unlink(idx)
        if git("push", "-q", REMOTE, f"{commit}:refs/heads/{BR}", check=False).returncode == 0:
            git("update-ref", TRACK, commit, check=False)
            return
        time.sleep(1 + 2 * i + secrets.randbelow(3))
    sys.exit("push failed after 8 retries (network/auth?). Nothing was published; rerun the command.")


# ---- parsing -------------------------------------------------------------
def parse_post(name, raw):
    txt = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
    m = re.match(r"---\n(.*?)\n---\n(.*)", txt, re.S)
    meta, body = {}, txt
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
        body = m.group(2)
    meta["_file"], meta["_body"] = Path(name).stem, body.strip()
    return meta


def posts(S):
    return sorted((parse_post(p, b) for p, b in S.items() if p.startswith("sandbox/posts/") and p.endswith(".md")),
                  key=lambda m: m["_file"])


def spend_rows(S):
    rows = []
    for p, b in S.items():
        if p.startswith("sandbox/spend/") and p.endswith(".csv"):
            h = p.split("/")[2].removesuffix(".csv")
            for r in csv.DictReader(io.StringIO(b.decode())):
                r["handle"] = h
                rows.append(r)
    return rows


def spent(S, h):
    return sum(float(r["cost_usd"]) for r in spend_rows(S) if r["handle"] == h)


def template_ids():
    with (ROOT / CFG["template"]).open(encoding="utf-8") as f:
        return [r["circuit_id"] for r in csv.DictReader(f)]


def parse_vec(text):
    return {r["circuit_id"]: float(r["value"]) for r in csv.DictReader(io.StringIO(text))}


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return float("nan") if sx == 0 or sy == 0 else sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def neg_distance_prior(ids):
    """-(Manhattan distance from butterfly q0): 6x6 grid q=row*6+col, q36/q37 below q30/q31."""
    out_ = []
    for cid in ids:
        q = int(cid.rsplit("_", 1)[1])
        r, c = (q // 6, q % 6) if q < 36 else (6, q - 36)
        out_.append(-(r + c))
    return out_


def deadline_left():
    return datetime.fromisoformat(CFG["paid_cutoff_utc"]) - now()


def account_spend():
    """Lifetime billed USD of this machine's BLUEQUBIT_API_TOKEN, or None if unavailable."""
    try:
        sys.path.insert(0, str(ROOT / "src"))
        import logging
        logging.disable(logging.CRITICAL)
        from otoc.bluequbit_adapter import BlueQubitAdapter
        return BlueQubitAdapter().account_total_usd()
    except Exception as exc:  # no venv / no token / offline
        print(f"WARN account check unavailable ({type(exc).__name__}); using self-reported spend", file=sys.stderr)
        return None


# ---- commands ------------------------------------------------------------
def new_post(kind, title, body, **meta):
    h, a = handle(), agent()
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    name = f"{stamp()}-{h}-{a}-{secrets.token_hex(2)}-{slug}"
    head = {"ts": now().isoformat(timespec="seconds"), "handle": h, "agent": a, "kind": kind, "title": title}
    head.update({k: v for k, v in meta.items() if v not in (None, "")})
    text = "---\n" + "\n".join(f"{k}: {str(v).replace(chr(10), ' ')}" for k, v in head.items()) + f"\n---\n{body.strip()}\n"
    return f"sandbox/posts/{name}.md", text, name


def body_arg(b):
    return sys.stdin.read() if b in (None, "-") else b


def cmd_init(a):
    (ROOT / ".sandbox_handle").write_text(a.handle.lower())
    path, text, name = new_post("join", f"{a.handle.lower()}/{agent()} online", "joined")
    publish({path: text}, f"{a.handle.lower()} joined")
    print("registered", a.handle.lower(), "->", name)


def cmd_post(a):
    if a.kind not in KINDS:
        sys.exit(f"kind must be one of {KINDS}")
    path, text, name = new_post(a.kind, a.title, body_arg(a.body), tags=a.tags, cost_usd=f"{a.cost:.2f}",
                                vector=a.vector, closes=a.closes)
    publish({path: text}, f"{handle()}/{a.kind} {a.title[:50]}")
    print("posted", name)


def cmd_claim(a):
    path, text, name = new_post("claim", a.target, a.body or "", cost_usd=f"{a.cost:.2f}", hours=a.hours, tags=a.tags)
    publish({path: text}, f"{handle()}/claim {a.target[:50]}")
    print("claimed", name, f"(close it with --closes {name})")


def cmd_vector(a):
    h, ids = handle(), template_ids()
    v = parse_vec(Path(a.csv).read_text(encoding="utf-8-sig"))
    if set(v) != set(ids):
        sys.exit(f"CSV must have exactly the {len(ids)} template circuit_ids, header circuit_id,value")
    if any(not math.isfinite(x) or abs(x) > 1 + 1e-6 for x in v.values()):
        sys.exit("values must be finite and within [-1,1]")
    vid = f"{h}-{re.sub(r'[^a-z0-9_-]', '', a.id.lower())}"
    csv_text = "circuit_id,value\n" + "".join(f"{i},{v[i]!r}\n" for i in ids)
    rho = pearson([v[i] for i in ids], neg_distance_prior(ids))
    path, text, name = new_post("vector", f"vector {vid}", f"{a.method}\n\nrho_vs_distance_prior={rho:.3f}",
                                vector=vid, tags=a.tags, cost_usd=f"{a.cost:.2f}")
    publish({f"sandbox/vectors/{vid}.csv": csv_text, path: text}, f"{h}/vector {vid}")
    print("published", vid, f"rho_vs_distance_prior={rho:.3f}")


def cmd_getvec(a):
    fetch()
    b = snapshot().get(f"sandbox/vectors/{a.id}.csv")
    if b is None:
        sys.exit("no such vector")
    Path(a.out).write_bytes(b)
    print("wrote", a.out)


def cmd_show(a):
    fetch()
    S = snapshot()
    hits = [p for p in S if Path(p).stem.startswith(a.name) or p == a.name]
    for p in hits[:5]:
        print(f"### {p}\n{S[p].decode(errors='replace')}")
    if not hits:
        sys.exit("not found")


def cmd_spend(a):
    h = handle()
    row = f"ts,job_id,device,cost_usd,agent,note\n{now().isoformat(timespec='seconds')},{a.job},{a.device},{a.cost:.2f},{agent()},\"{(a.note or '').replace(chr(34), '')}\"\n"
    publish({f"sandbox/spend/{h}/{stamp()}-{agent()}-{re.sub(r'[^A-Za-z0-9]', '', a.job)[:24]}.csv": row},
            f"{h}/spend {a.cost:.2f} {a.device}")
    fetch()
    print(f"{h}: self-reported ${spent(snapshot(), h):.2f} / ${CFG['cap_usd_per_teammate']:.2f}")


def cmd_guard(a):
    h, cap = handle(), CFG["cap_usd_per_teammate"]
    fetch()
    rep = spent(snapshot(), h)
    acct = account_spend()
    base = max(rep, acct if acct is not None else 0)
    print(f"{h}: self-reported ${rep:.2f}, account ${'?' if acct is None else f'{acct:.2f}'}, cap ${cap:.2f}, "
          f"requested ${a.cost:.2f}, remaining after ${cap - base - a.cost:.2f}")
    if deadline_left().total_seconds() < 0:
        print(f"DENIED: past paid-job cutoff {CFG['paid_cutoff_utc']}")
        sys.exit(1)
    if base + a.cost > cap + 1e-9:
        print("DENIED: would exceed cap")
        sys.exit(1)
    print("OK")


def cmd_score(a):
    path, text, name = new_post("score", f"score {a.vector} = {a.points:g}", a.note or "", vector=a.vector,
                                points=a.points, attempt=a.attempt, tags="score")
    publish({path: text}, f"{handle()}/score {a.vector} {a.points:g}")
    print("logged", name)


def cmd_board(a):
    text = Path(a.file).read_text(encoding="utf-8")
    publish({"sandbox/board.md": text}, f"{handle()}/board", overwrite=True)
    print("board published")


def cmd_status(a):
    fetch()
    S = snapshot()
    P = posts(S)
    if a.since:
        P_recent = [p for p in P if p["_file"] > a.since]
    else:
        P_recent = P[-a.n:]
    cap = CFG["cap_usd_per_teammate"]
    rows = spend_rows(S)
    left = deadline_left()
    print(f"== NOW {now():%Y-%m-%d %H:%MZ} | paid-job cutoff {CFG['paid_cutoff_utc']} "
          f"({max(left.total_seconds(), 0) / 3600:.1f} h left) | submission deadline {CFG['deadline_utc']}")
    hs = sorted(({r["handle"] for r in rows} | {p.get("handle", "?") for p in P}) - {"manager"})
    print(f"== BUDGET (cap ${cap:.0f}/teammate, self-reported; `guard` also checks the real account)")
    for h in hs:
        s = sum(float(r["cost_usd"]) for r in rows if r["handle"] == h)
        print(f"  {h:12s} ${s:6.2f} spent, ${cap - s:6.2f} left")
    sc = [p for p in P if p.get("kind") == "score"]
    print(f"== SCORES (/{CFG['max_score']}), best first")
    for p in sorted(sc, key=lambda p: -float(p.get("points", 0)))[:8]:
        print(f"  {float(p.get('points', 0)):6.0f}  {p.get('vector', '')}  ({p.get('handle')}, attempt {p.get('attempt', '?')}) {p['_body'][:60]}")
    closed = {p.get("closes") for p in P if p.get("closes")}
    print("== OPEN CLAIMS (do not duplicate)")
    for p in P:
        if p.get("kind") != "claim" or p["_file"] in closed:
            continue
        exp = datetime.fromisoformat(p["ts"]) + timedelta(hours=float(p.get("hours", CFG["claim_hours_default"])))
        if exp > now():
            print(f"  {p['_file']}  until {exp:%H:%MZ}  ${p.get('cost_usd', '0')}  {p['title']}")
    vecs = {Path(p).stem: b.decode() for p, b in S.items() if p.startswith("sandbox/vectors/") and p.endswith(".csv")}
    if vecs:
        ids = template_ids()
        V = {k: [parse_vec(t)[i] for i in ids] for k, t in sorted(vecs.items())}
        prior = neg_distance_prior(ids)
        best = {}
        for p in sc:
            best[p.get("vector")] = max(best.get(p.get("vector"), -1e9), float(p.get("points", 0)))
        print(f"== VECTORS ({len(V)}): rho vs distance prior | best score")
        for k, x in V.items():
            print(f"  {k:30s} prior_rho={pearson(x, prior):+.2f}  score={best.get(k, '-')}")
        if a.matrix and len(V) > 1:
            ks = list(V)
            print("  pairwise Pearson (rows/cols in the order above):")
            for ki in ks:
                print("   ", ki[:24].ljust(24), " ".join(f"{pearson(V[ki], V[kj]):+.2f}" for kj in ks))
    print(f"== POSTS ({'since ' + a.since if a.since else 'last ' + str(a.n)}; full text: sb.py show <name>)")
    for p in P_recent:
        print(f"  {p['_file']}  [{p.get('kind')}] {p.get('title', '')}" + (f"  ${p['cost_usd']}" if p.get("cost_usd", "0.00") != "0.00" else ""))
    print("== BOARD (sandbox/board.md, manager-owned)")
    print(S.get("sandbox/board.md", b"(empty)").decode(errors="replace"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_, *args):
        p = sp.add_parser(name, help=help_)
        for flags, kw in args:
            p.add_argument(*flags, **kw)
        p.set_defaults(fn=fn)

    add("init", cmd_init, "register this machine's handle", (["handle"], {}))
    add("status", cmd_status, "digest: budget, scores, claims, vectors, posts, board",
        (["--n"], {"type": int, "default": 15}), (["--since"], {"help": "post-name prefix/timestamp, e.g. 20261025T0300"}),
        (["--matrix"], {"action": "store_true"}))
    add("show", cmd_show, "print posts/files by name prefix", (["name"], {}))
    add("post", cmd_post, "publish a finding/run/proposal/question/directive",
        (["--kind"], {"required": True}), (["--title"], {"required": True}), (["--tags"], {}),
        (["--cost"], {"type": float, "default": 0.0}), (["--vector"], {}), (["--closes"], {}),
        (["--body"], {"default": "-", "help": "text, or '-' to read stdin"}))
    add("claim", cmd_claim, "announce an experiment before running it",
        (["--target"], {"required": True, "help": "device + options + rows"}),
        (["--cost"], {"type": float, "default": 0.0, "help": "quoted USD"}),
        (["--hours"], {"type": float, "default": CFG["claim_hours_default"]}), (["--tags"], {}), (["--body"], {}))
    add("vector", cmd_vector, "publish an immutable 38-row candidate CSV", (["csv"], {}), (["--id"], {"required": True}),
        (["--method"], {"required": True}), (["--tags"], {}), (["--cost"], {"type": float, "default": 0.0}))
    add("getvec", cmd_getvec, "download a vector", (["id"], {}), (["-o", "--out"], {"required": True}))
    add("spend", cmd_spend, "log billed cost of a job", (["--job"], {"required": True}), (["--device"], {"required": True}),
        (["--cost"], {"type": float, "required": True}), (["--note"], {}))
    add("guard", cmd_guard, "exit 1 if a quoted job would exceed the cap or cutoff", (["--cost"], {"type": float, "required": True}))
    add("score", cmd_score, "log a website score (humans)", (["--vector"], {"required": True}),
        (["--points"], {"type": float, "required": True}), (["--attempt"], {"type": int}), (["--note"], {}))
    add("board", cmd_board, "publish a new board.md (manager only)", (["file"], {}))
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
