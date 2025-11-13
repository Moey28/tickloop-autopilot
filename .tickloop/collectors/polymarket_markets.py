#!/usr/bin/env python3
# Minimal Polymarket markets fetcher (no external deps).
# Writes:
#  - data/polymarket/markets/dt=YYYY-MM-DD/markets.csv   (daily partition)
#  - data/polymarket/latest.csv                           (rolling pointer)
#  - data/polymarket/YYYY-MM-DDTHH-MM-SSZ_polymarket_markets.csv  (immutable snapshot)

import os, csv, json, urllib.request, time, string
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_URL = "https://clob.polymarket.com/markets?limit=200&offset=0"

def clean_url(raw: str) -> str:
    raw = (raw or "").strip()
    # strip non-printable chars that sometimes creep into secrets
    cleaned = "".join(ch for ch in raw if ch in string.printable)
    try:
        u = urlparse(cleaned)
        if u.scheme in ("http", "https") and u.netloc:
            return cleaned
    except Exception:
        pass
    return DEFAULT_URL

API_URL = clean_url(os.getenv("POLYMARKET_MARKETS_URL"))

def get_json(url, retries=5, backoff=1.5):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "tickloop/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            time.sleep(backoff * (i + 1))
    raise RuntimeError(f"failed after retries: {last}")

def norm_row(m):
    # Be defensive: API fields can vary
    def g(*keys, default=None):
        for k in keys:
            if k in m and m[k] is not None:
                return m[k]
        return default
    end_ts = g("end_date","endDate")
    end_iso = None
    try:
        if end_ts is not None:
            end_iso = datetime.fromtimestamp(float(end_ts), tz=timezone.utc).isoformat()
    except Exception:
        end_iso = None
    return {
        "id": g("id","_id","market_id"),
        "slug": g("slug"),
        "question": g("question","title"),
        "category": (g("category") or (g("categories") or [None]))[0] if isinstance(g("categories"), list) else g("category"),
        "closed": g("closed"),
        "end_date": end_ts,
        "end_date_iso": end_iso,
        "volume": g("volume"),
        "liquidity": g("liquidity","liquidity_in_usd"),
        "yes_price": g("yes_price","yesPrice"),
        "no_price": g("no_price","noPrice"),
        "createdTime": g("createdTime","created_at","createdAt"),
    }

def write_csv(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = list(rows[0].keys()) if rows else [
        "id","slug","question","category","closed","end_date","end_date_iso",
        "volume","liquidity","yes_price","no_price","createdTime"
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def main():
    data = get_json(API_URL)
    rows = data.get("data", data) if isinstance(data, dict) else data
    rows = rows or []
    out_rows = [norm_row(m) for m in rows]

    # A) your original daily partition
    today = datetime.utcnow().strftime("%Y-%m-%d")
    daily_path = Path(f"data/polymarket/markets/dt={today}/markets.csv")
    write_csv(out_rows, daily_path)

    # B) rolling "latest.csv"
    latest_path = Path("data/polymarket/latest.csv")
    write_csv(out_rows, latest_path)

    # C) immutable snapshot with UTC timestamp
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    snap_path = Path(f"data/polymarket/{ts}_polymarket_markets.csv")
    write_csv(out_rows, snap_path)

    print(f"[polymarket] wrote {len(out_rows)} rows →")
    print(f"  - {daily_path}")
    print(f"  - {latest_path}")
    print(f"  - {snap_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
