# G4 research sandbox: overnight multi-agent setup

Every teammate's agents share findings through the git branch `sandbox` with `python sandbox/sb.py`. It talks to `origin/sandbox` directly through git plumbing: it never touches your working tree, branch or uncommitted work, and many agents can share one checkout. A manager agent (run by prmtvnassar) reads everything every ~25 min and rewrites `board.md` with assignments and an upload queue.

**Limits.** Each account may spend at most $20 in total; `guard` and the job runner (`account_cap_usd`) enforce this against your real BlueQubit account. Paid launches stop at 13:00Z on 25 Oct; submissions close at 15:30Z.

## 1. One-time setup (about 5 min, any OS)
```bash
# inside your existing clone of duquantum-bluequbit-2026
git fetch origin
git worktree add --track -b sandbox ../bq-sandbox origin/sandbox   # clean separate folder
cd ../bq-sandbox
cp ../<your-clone>/.env .          # must contain BLUEQUBIT_API_TOKEN=... (your own token, never committed)
py -3.12 -m venv .venv312          # macOS/Linux: python3.12 -m venv .venv312
.venv312/Scripts/python -m pip install -r requirements.txt     # macOS/Linux: .venv312/bin/python
.venv312/Scripts/python sandbox/sb.py init <handle>            # kevin | miao | prmtvnassar | <4th>
.venv312/Scripts/python sandbox/sb.py status                   # should print the board
```
If you already have a local branch named `sandbox`, use `git worktree add ../bq-sandbox sandbox` and then `git -C ../bq-sandbox pull`.

## 2. Launch agents for the night
Run one terminal per agent, all in `bq-sandbox`. Give each agent a unique label (`a1`, `a2`, ...). Leave the laptop plugged in with sleep disabled.

**Claude Code** (PowerShell):
```powershell
cd ..\bq-sandbox; .venv312\Scripts\Activate.ps1; $env:SB_AGENT="a1"; $env:PYTHONPATH="src"
claude --permission-mode bypassPermissions
```
(bash: `cd ../bq-sandbox && source .venv312/bin/activate && export SB_AGENT=a1 PYTHONPATH=src && claude --permission-mode bypassPermissions`)
Then paste this as the first message:
```
/loop You are agent <handle>/a1 on our G4 team. Read sandbox/PROTOCOL.md once and follow it exactly. Each wake-up, run ONE research cycle: `python sandbox/sb.py status`, follow the board's assignment for <handle>, claim, run, report with sb.py. Never ask me anything (nobody is awake); if blocked, post a question and switch to $0 work. Pace wake-ups to your running jobs (about 10-20 min). After 13:00Z start no paid jobs: publish your best vector and a final finding, then stop the loop at 15:00Z.
```
**Codex or other agents:** paste the same text without `/loop`, and add: "Keep working in cycles until 15:00Z; do not end your turn while time remains." Run it in full-auto mode.

`bypassPermissions` lets the agent run commands unattended. The $20 cap is enforced in code, and the token stays in `.env`. If you prefer not to bypass, use `--permission-mode acceptEdits` and expect it to stall on the first unapproved command.

## 3. Morning
- `python sandbox/sb.py status`: the board's **Upload queue** says which vector to upload. Use `sb.py getvec <vector-id> -o g4.csv` and `sb.py show <vector post>` for the method text to paste.
- After uploading, log it: `python sandbox/sb.py score --vector <vector-id> --points <n> --attempt <k> --note "<explanation used>"`.

## Command reference (`python sandbox/sb.py <cmd> -h`)
`status [--matrix] [--since TS]` · `show <name>` · `claim --target --cost` · `guard --cost` · `spend --job --device --cost` · `post --kind finding|run|proposal|question --title --body [--closes CLAIM]` · `vector <csv> --id --method` · `getvec <id> -o` · `score --vector --points` · `board <file>` (manager only).
Layout on the branch: `sandbox/posts/` (immutable updates) · `vectors/` (immutable 38-row CSVs) · `spend/<handle>/` (one file per job) · `board.md` · `config.json` (cap, cutoff, deadline).
