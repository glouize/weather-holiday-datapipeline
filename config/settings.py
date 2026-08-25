"""
config/settings.py
Central config loader. All scripts import from here.

Usage:
    from config.settings import cfg, ROOT, DB_FILE, CITIES
"""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent  # project root
_CONFIG_PATH = ROOT / "config.yaml"

with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
    cfg = yaml.safe_load(_f)

# Convenience resolved absolute paths
DB_FILE   = str(ROOT / cfg["database"]["path"])
CERT_FILE = str(ROOT / cfg["certs"]["cert_file"])
KEY_FILE  = str(ROOT / cfg["certs"]["key_file"])
CITIES    = cfg["cities"]
