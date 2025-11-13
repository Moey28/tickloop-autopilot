# .tickloop/supervisor.py
# AI Supervisor: audits run, does web search (Serper), applies safe patches, pushes.
import os, re, sys, time, json, pathlib, subprocess
from datetime import datetime

ROOT = pathlib.Path(".").resolve()

def sh(cmd: str) -> int:
    print(f"$ {cmd}")
    return subprocess.call(cmd, shell=True, cwd=ROOT)

def out(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True, cwd=ROOT).decode()

def ensure_git_identity():
    sh('git config user.name "tickloop-autopilot"')
    sh('git config user.email "tickloop-autopilot@users.noreply.github.com"')

def commit_and_push_if_changes(msg: str) -> bool:
    changed = out("git status --porcelain").strip()
    if not changed:
        print("[git] no changes to commit")
        return False
    ensure_git_identity()
    sh("git add -A")
    sh(f'git commit -m "{msg}"')
    token = os.environ.get("GITHUB_TOKEN")
    repo  = os.environ.get("GITHUB_REPOSITORY")
    if token and repo:
        return sh(f'git push https://x-access-token:{token}@github.com/{repo}.git HEAD:main') == 0
    print("[git] missing GITHUB_TOKEN or GITHUB_REPOSITORY; cannot push")
    return False

# --------------------------
# Web search (Serper.dev)
# --------------------------
import requests
def serper_search(query: str, max_results=5):
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        print("[web] no SERPER_API_KEY; skipping search")
        return []
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": max_results}
    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=25)
        r.raise_for_status()
        results = r.json().get("organic", []) or []
        print(f"[web] Serper returned {len(results)} result(s)")
        for i, res in enumerate(results[:max_results], 1):
            print(f"  [{i}] {res.get('title')}: {res.get('link')}")
        return results
    except Exception as e:
        print(f"[web] Serper error: {e}")
        return []

def probe_polymarket_docs():
    queries = [
        "Polymarket CLOB markets API endpoint",
        "Polymarket markets API docs clob.polymarket.com",
        "Polymarket API rate limits markets endpoint"
    ]
    hits = []
    for q in queries:
        print(f"[web] searching: {q}")
        hits.extend(serper_search(q, max_results=3))
        time.sleep(1.0)
    return hits

# --------------------------
# Health checks & patches
# --------------------------
def patch_polymarket_env_fallback() -> bool:
    """
    If POLYMARKET_MARKETS_URL is present but EMPTY, ensure collector uses a safe fallback:
      os.getenv("POLYMARKET_MARKETS_URL") or "https://clob.polymarket.com/markets?limit=200&offset=0"
    """
    env_val = os.environ.get("POLYMARKET_MARKETS_URL", None)
    if env_val is None:
        print("[audit] POLYMARKET_MARKETS_URL not set -> code default will be used")
        return False
    if env_val.strip() != "":
        print("[audit] POLYMARKET_MARKETS_URL is non-empty -> no patch needed")
        return False

    path = ROOT / ".tickloop" / "collectors" / "polymarket_markets.py"
    if not path.exists():
        print(f"[audit] {path} not found; skipping")
        return False

    src = path.read_text(encoding="utf-8")
    pat = r'os\.getenv\(\s*"POLYMARKET_MARKETS_URL"\s*,\s*"([^"]+)"\s*\)'
    new_src = re.sub(pat, r'os.getenv("POLYMARKET_MARKETS_URL") or "\1"', src, count=1)
    if new_src != src:
        path.write_text(new_src, encoding="utf-8")
        print("[patch] applied safe fallback in polymarket_markets.py")
        return True

    if 'os.getenv("POLYMARKET_MARKETS_URL") or ' in src:
        print("[audit] safe fallback already present")
        return False

    print("[audit] pattern not found; no changes made")
    return False

def write_heartbeat():
    hb = ROOT / ".tickloop" / "heartbeat.log"
    hb.parent.mkdir(parents=True, exist_ok=True)
    with hb.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.utcnow().isoformat()}] supervisor cycle completed ✅\n")
    print("[hb] wrote .tickloop/heartbeat.log")

def main():
    print("=== TickLoop Supervisor: audit start ===")
    changed = False

    # 1) known fix for empty secret overriding default
    changed |= patch_polymarket_env_fallback()

    # 2) web recon (document changes / endpoints)
    hits = probe_polymarket_docs()
    print(f"[web] total references collected: {len(hits)}")

    # 3) commit & push any code changes
    if changed:
        pushed = commit_and_push_if_changes("supervisor: auto-fix polymarket URL fallback + web recon")
        print("✅ supervisor pushed a fix" if pushed else "⚠️ supervisor had changes but could not push")
    else:
        print("✅ supervisor audit completed; no fix required")

    # 4) heartbeat
    write_heartbeat()
    print("=== TickLoop Supervisor: done ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
