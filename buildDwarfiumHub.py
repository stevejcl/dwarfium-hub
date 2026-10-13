"""Build Dwarfium-Hub (same nicegui-pack foundation as Astro Dwarf Session
and Dwarfium Scope Archive): one-file windowed executable in dist/, then
DwarfiumHub-<RUNNER_OS>.zip of dist/.

    python buildDwarfiumHub.py
"""
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

APP_NAME = "DwarfiumHub"
SOURCE_FILE = "dwarfium_hub.py"
ICON_NAME = "DwarfiumHub.ico"
DIST_DIR = Path("dist")
BUILD_DIR = Path("build")

for folder in (DIST_DIR, BUILD_DIR):
    if folder.exists():
        shutil.rmtree(folder)

# version.py from the first [X.Y.Z] of CHANGELOG.md (hub/version.py reads it when frozen)
version = "Unknown"
m = re.search(r"\[V?([\d.]+[a-z]?)\]", Path("CHANGELOG.md").read_text(encoding="utf-8"))
if m:
    version = m.group(1)
Path("version.py").write_text(f'APP_VERSION = "{version}"\n', encoding="utf-8")
print(f"Version: {version}")

icon_args = ["--icon", ICON_NAME] if Path(ICON_NAME).exists() else []
subprocess.run([
    "nicegui-pack", "--onefile", "--windowed", *icon_args,
    "--name", APP_NAME,
    SOURCE_FILE,
], check=True)

suffix = os.environ.get("RUNNER_OS", "unknown")  # Windows, Linux, macOS
zip_path = Path(f"{APP_NAME}-{suffix}.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for path in DIST_DIR.rglob("*"):
        zipf.write(path, path.relative_to(DIST_DIR))
print(f"Built {zip_path}")
