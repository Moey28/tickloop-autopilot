import time, random, subprocess, sys
import yaml

def argval(flag, default=None):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        return sys.argv[i+1]
    return default

cfg_path = argval('--config', '.tickloop/config/autopilot.yaml')
CFG = yaml.safe_load(open(cfg_path, 'r'))

def jittered_backoff(i):
    base = CFG['retries'].get('base_seconds', 5)
    mx   = CFG['retries'].get('max_seconds', 60)
    sleep = min(mx, base * (2 ** i))
    if CFG['retries'].get('jitter', True):
        sleep *= random.uniform(0.7, 1.3)
    return max(1, int(sleep))

cycle = 0
while True:
    cycle += 1
    print(f"[autopilot] cycle={cycle} starting collectors…", flush=True)
    rc = subprocess.call([sys.executable, '.tickloop/scripts/run_collectors.py'])
    if rc == 0:
        print("[autopilot] collectors OK → validating…", flush=True)
        rc = subprocess.call([sys.executable, '.tickloop/scripts/validate.py'])
        if rc == 0:
            print("[autopilot] ✅ success. Done.", flush=True)
            sys.exit(0)

    print(f"[autopilot] ❌ failure in cycle {cycle}. invoking supervisor…", flush=True)
    rc = subprocess.call([sys.executable, '.tickloop/scripts/supervisor.py', '--cycle', str(cycle)])
    if rc == 0:
        print("[autopilot] supervisor ok. Retrying…", flush=True)
    else:
        print("[autopilot] supervisor had no fix this round. Backoff + retry.", flush=True)

    backoff = jittered_backoff(cycle)
    print(f"[autopilot] sleeping {backoff}s …", flush=True)
    time.sleep(backoff)
