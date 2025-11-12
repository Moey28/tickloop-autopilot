import yaml, pathlib

cfg_path = pathlib.Path(".tickloop/config.yaml")
with open(cfg_path, "r") as f:
    cfg = yaml.safe_load(f)

print("✅ Loaded config:")
print(cfg)
