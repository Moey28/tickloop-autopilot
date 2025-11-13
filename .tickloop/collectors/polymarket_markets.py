# Minimal Polymarket markets fetcher (no external deps).
# Writes a CSV under data/polymarket/markets/dt=YYYY-MM-DD/markets.csv
import os, csv, json, urllib.request, time
from datetime import datetime, timezone

API_URL = os.getenv("POLYMARKET_MARKETS_URL") or "\1"

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

def main():
    data = get_json(API_URL)
    rows = data.get("data", data) if isinstance(data, dict) else data
    rows = rows or []
    out_rows = [norm_row(m) for m in rows]

    today = datetime.utcnow().strftime("%Y-%m-%d")
    out_dir = f"data/polymarket/markets/dt={today}"
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/markets.csv"

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()) if out_rows else [
            "id","slug","question","category","closed","end_date","end_date_iso","volume","liquidity","yes_price","no_price","createdTime"
        ])
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    print(f"[polymarket] wrote {len(out_rows)} rows → {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
