# Tests OpenAI, DeepSeek, and Gemini API keys by listing models.
# Uses only stdlib so we don't need requirements.txt yet.
import os, sys, json, urllib.request

def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def test_openai():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return ("openai", False, "missing OPENAI_API_KEY")
    try:
        data = get_json("https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {key}"})
        # expect a list in data["data"]
        models = data.get("data", [])
        sample = models[0]["id"] if models else "no models returned"
        return ("openai", True, f"ok (sample model: {sample})")
    except Exception as e:
        return ("openai", False, str(e))

def test_deepseek():
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        return ("deepseek", False, "missing DEEPSEEK_API_KEY")
    try:
        data = get_json("https://api.deepseek.com/v1/models",
                        headers={"Authorization": f"Bearer {key}"})
        models = data.get("data", [])
        sample = (models[0]["id"] if models else "no models returned")
        return ("deepseek", True, f"ok (sample model: {sample})")
    except Exception as e:
        return ("deepseek", False, str(e))

def test_gemini():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return ("gemini", False, "missing GEMINI_API_KEY")
    try:
        data = get_json(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}")
        models = data.get("models", [])
        sample = (models[0]["name"] if models else "no models returned")
        return ("gemini", True, f"ok (sample model: {sample})")
    except Exception as e:
        return ("gemini", False, str(e))

def main():
    results = [test_openai(), test_deepseek(), test_gemini()]
    for name, ok, msg in results:
        status = "✅" if ok else "❌"
        print(f"{status} {name}: {msg}")
    # succeed if at least one works
    if any(ok for _, ok, _ in results):
        sys.exit(0)
    sys.exit(1)

if __name__ == "__main__":
    main()
