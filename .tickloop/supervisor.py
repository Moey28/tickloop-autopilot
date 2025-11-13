# .tickloop/supervisor.py
# Minimal AI supervisor: audits common misconfig (empty secret overriding default)
# and auto-patches the collector to use a safe fallback.
import os, re, subprocess, sys, pathlib

ROOT = pathlib.Path(".").resolve()

def sh(cmd: str) -> int:
    print(f"$ {cmd}")
    return subprocess.call(cmd, shell=True, cwd=ROOT)

def ensure_git_identity():
    sh('git config user.name "tickloop-autopilot"')
    sh('git config user.email "tickloop-autopilot@users.noreply.github.com"')

def patch_polymarket_env_fallback() -> bool:
    """
    If POLYMARKET_MARKETS_URL is present but EMPTY, ensure the collector uses:
        os.getenv("POLYMARKET_MARKETS_URL") or "https://clob.polymarket.com/markets?limit=200&offset=0"
    """
    env_val = os.environ.get("POLYMARKET_MARKETS_URL", None)
    if env_val is None:
        print("[audit] POLYMARKET_MARKETS_URL not set -> default in code will be used.")
        return False
    if env_val.strip() != "":
        print("[audit] POLYMARKET_MARKETS_URL is non-empty. No patch needed.")
        return False

    path = ROOT / ".tickloop" / "collectors" / "polymarket_markets.py"
    if not path.exists():
        print(f"[audit] {path} not found; skipping.")
        return False

    src = path.read_text(encoding="utf-8")

    # Replace os.getenv("POLYMARKET_MARKETS_URL", "...") with the safe fallback
    pattern = r'os\.getenv\(\s*"POLYMARKET_MARKETS_URL"\s*,\s*"([^"]+)"\s*\)'
    if re.search(pattern, src):
        new_src = re.sub(pattern, r'os.getenv("POLYMARKET_MARKETS_URL") or "\1"', src, count=1)
        if new_src != src:
            path.write_text(new_src, encoding="utf-8")
            print("[patch] Applied safe fallback in polymarket_markets.py")
            return True

    if 'os.getenv("POLYMARKET_MARKETS_URL") or ' in src:
        print("[audit] Safe fallback already present. No patch needed.")
        return False

    print("[audit] Pattern not found; no changes made.")
    return False

def commit_and_push_if_changes(msg: str):
    changed = subprocess.check_output("git status --porcelain", shell=True, cwd=ROOT).decode().strip()
    if not changed:
        print("[git] No changes to commit.")
        return
    ensure_git_identity()
    sh("git add -A")
    sh(f'git commit -m "{msg}"')
    token = os.environ.get("GITHUB_TOKEN")
    repo  = os.environ.get("GITHUB_REPOSITORY")
    if token and repo:
        sh(f'git push https://x-access-token:{token}@github.com/{repo}.git HEAD:main')
    else:
        print("[git] Missing GITHUB_TOKEN or GITHUB_REPOSITORY; cannot push.")

def main():
    print("=== TickLoop Supervisor: audit start ===")
    changed = patch_polymarket_env_fallback()
    if changed:
        commit_and_push_if_changes("supervisor: auto-fix empty POLYMARKET_MARKETS_URL fallback")
        print("✅ Supervisor pushed a fix.")
    else:
        print("✅ Supervisor audit completed; no fix required.")
    print("=== TickLoop Supervisor: done ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
    # Multi-AI cross-check
    for name, key, url in [
        ("OpenAI", os.getenv("OPENAI_API_KEY"), "https://api.openai.com/v1/chat/completions"),
        ("Gemini", os.getenv("GEMINI_API_KEY"), "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"),
        ("DeepSeek", os.getenv("DEEPSEEK_API_KEY"), "https://api.deepseek.com/chat/completions"),
    ]:
        if not key:
            print(f"[{name}] No API key found, skipping.")
            continue
        print(f"[{name}] auditing latest logs...")
        # each model can receive a short summary / fix request
