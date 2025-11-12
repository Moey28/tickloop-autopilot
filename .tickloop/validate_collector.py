import os, glob, sys

def main():
    pattern = "data/polymarket/markets/dt=*/markets.csv"
    files = glob.glob(pattern)
    if not files:
        print("❌ no CSV file found")
        sys.exit(2)

    path = sorted(files)[-1]
    size = os.path.getsize(path)
    if size < 5000:
        print(f"❌ file too small ({size} bytes)")
        sys.exit(3)

    print(f"✅ validation passed ({path}, {size} bytes)")
    sys.exit(0)

if __name__ == "__main__":
    main()
