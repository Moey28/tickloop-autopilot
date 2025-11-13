import os, re, subprocess, sys, pathlib, json

REPO = os.environ.get("GITHUB_REPOSITORY", "")
ROOT = pathlib.Path(".").resolve()

def sh(cmd):
    print(f"$ {cmd}")
    return subprocess.call(cmd, shell=True, cwd=ROOT)

def ensure_git_identity():
    sh('git config user.name "tickloop-autopilot"')
    sh('git config user.email "tickloop-autopilot@users.noreply.github.com"')

def patch_polymarket_env_fallback():
    """If POLYMARKET_MARKETS_URL is empty, ensure code falls back to default."""
    env_val = os.environ.get("POLYMARKET_MARKETS_URL", None)
    if env_val is None:
        print("[audit] POLYMARKET_MARKETS_URL not set -> fine (code default will be used).")
        return False
    if env_val.strip() != "":
        print("[audit] POLYMARKET_MARKETS_URL is set (non-empty). No patch needed.")
        return False

    path = ROOT / ".tickloop" / "collectors" / "polymarket_markets.py"
    if not path.exists():
        print(f"[audit] {path} not found; skipping patch.")
        return False

    src = path.read_text(encoding="utf-8")

    # Look for os.getenv("POLYMARKET_MARKETS_URL", "https://...") and make it:
    # os.getenv("POLYMARKET_MARKETS_URL") or "https://..."
    pattern = r'os\.getenv\(\s*"POLYMARKET_MARKETS_URL"\s*,\s*"([^"]+)"\s*\)'
    if re.search(pattern, src):
        new_src = re.sub(
            pattern,
            r'os.getenv("POLYMARKET_MARKETS_URL") or "\\1"',
            src,
            count=1,
        )
        if new_src != src:
            path.write_text(new_src, encoding="utf-8")
            print("[patch] Applied fallback fix in polymarket_markets.py "
                  "(env var may be empty; now safely falls back).")
            return True

    # If code already uses the safe form, nothing to do.
    if 'os.getenv("POLYMARKET_MARKETS_URL") or ' in src:
        print("[audit] Fallback already safe. No patch needed.")
        return False

    print("[audit] Could not find the exact pattern to patch; leaving as is.")
    return False

def commit_and_push_if_changes(msg):
    sh("git status --porcelain")
    changed = subprocess.check_output("git status --porcelain", shell=True, cwd=ROOT).decode().strip()
    if not changed:
        print("[git] No changes to commit.")
        return
    ensure_git_identity()
    sh('git add -A')
    sh(f'git commit -m "{msg}"')
    # Use the Actions token
    token = os.environ.get("GITHUB_TOKEN")
    repo  = os.environ.get("GITHUB_REPOSITORY")
    if token and repo:
        sh(f'git push https://x-access-token:{token}@github.com/{repo}.git HEAD:main')
    else:
        print("[git] Missing GITHUB_TOKEN or GITHUB_REPOSITORY; cannot push.")

def main():
    print("=== TickLoop Supervisor: AI audit start ===")
    # 1) Known health check: empty endpoint secret -> patch fallback
    changed = patch_polymarket_env_fallback()

    # 2) TODO hooks: call LLMs to suggest improvements, lint, etc.
    # (You already have OPENAI_API_KEY available; we keep this minimal for now.)

    if changed:
        commit_and_push_if_changes("supervisor: auto-fix empty POLYMARKET_MARKETS_URL fallback")
        print("✅ Supervisor applied a code fix and pushed it.")
    else:
        print("✅ Supervisor audit completed; no code changes needed.")
    print("=== TickLoop Supervisor: done ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
