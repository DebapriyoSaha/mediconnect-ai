from pathlib import Path
import os

BASE_DIR = Path(os.getcwd())
FRONTEND_DIR = BASE_DIR / "static"
FAVICON_PATH = FRONTEND_DIR / "favicon.svg"

print(f"Current Working Directory: {os.getcwd()}")
print(f"BASE_DIR: {BASE_DIR}")
print(f"FRONTEND_DIR: {FRONTEND_DIR}")
print(f"FAVICON_PATH: {FAVICON_PATH}")

if FAVICON_PATH.exists():
    print("✅ Favicon file exists!")
    print(f"Size: {FAVICON_PATH.stat().st_size} bytes")
else:
    print("❌ Favicon file NOT found!")
