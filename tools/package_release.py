#!/usr/bin/env python3
"""
FractalOS Official Release Packaging Tool
Builds clean, self-contained distribution bundles in dist/ with SHA256 checksums:
1. fractalos-1.0.0-web.zip & .tar.gz (Deployable web edition for any HTTP server)
2. fractalos-1.0.0-appliance.tar.gz (Bare-metal Raspberry Pi / Kiosk appliance)
3. fractalos-1.0.0-full.tar.gz (Full release distribution including docs, tests, and tools)
"""

import os
import sys
import shutil
import tarfile
import zipfile
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
VERSION = "1.0.0"

def get_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def make_tar_gz(output_filename, source_dir, arcname_prefix=""):
    with tarfile.open(output_filename, "w:gz") as tar:
        for root, dirs, files in os.walk(source_dir):
            # Exclude cache and hidden files
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".venv", "node_modules")]
            for file in files:
                if file.endswith((".pyc", ".pyo", ".DS_Store")):
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, source_dir)
                arcname = os.path.join(arcname_prefix, rel_path) if arcname_prefix else rel_path
                tar.add(file_path, arcname=arcname)

def make_zip(output_filename, source_dir, arcname_prefix=""):
    with zipfile.ZipFile(output_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".venv", "node_modules")]
            for file in files:
                if file.endswith((".pyc", ".pyo", ".DS_Store")):
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, source_dir)
                arcname = os.path.join(arcname_prefix, rel_path) if arcname_prefix else rel_path
                zipf.write(file_path, arcname=arcname)

def main():
    print(f"=== Packaging FractalOS v{VERSION} Official Release ===")
    
    # 1. Clean dist directory
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    # 2. Package Web Edition
    print("Building Web Edition bundles...")
    web_stage = DIST / f"fractalos-{VERSION}-web"
    web_stage.mkdir(parents=True)
    
    shutil.copytree(ROOT / "resources", web_stage / "resources", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy(ROOT / "README.md", web_stage / "README.md")
    if (ROOT / "LICENSE").exists():
        shutil.copy(ROOT / "LICENSE", web_stage / "LICENSE")
    
    # Simple launcher script for web edition
    server_script = web_stage / "start.sh"
    server_script.write_text("#!/bin/bash\necho 'Starting FractalOS on http://localhost:8000 ...'\npython3 -m http.server 8000 --directory resources\n")
    server_script.chmod(0o755)

    web_tar = DIST / f"fractalos-{VERSION}-web.tar.gz"
    web_zip = DIST / f"fractalos-{VERSION}-web.zip"
    make_tar_gz(web_tar, web_stage, arcname_prefix=f"fractalos-{VERSION}-web")
    make_zip(web_zip, web_stage, arcname_prefix=f"fractalos-{VERSION}-web")
    shutil.rmtree(web_stage)
    print(f"  Created: {web_tar.name} ({web_tar.stat().st_size:,} bytes)")
    print(f"  Created: {web_zip.name} ({web_zip.stat().st_size:,} bytes)")

    # 3. Package Appliance Edition
    print("Building Appliance Edition bundle...")
    app_stage = DIST / f"fractalos-{VERSION}-appliance"
    app_stage.mkdir(parents=True)

    shutil.copytree(ROOT / "resources", app_stage / "resources", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(ROOT / "extras", app_stage / "extras", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy(ROOT / "neutralino.config.json", app_stage / "neutralino.config.json")
    shutil.copy(ROOT / "README.md", app_stage / "README.md")
    
    app_tar = DIST / f"fractalos-{VERSION}-appliance.tar.gz"
    make_tar_gz(app_tar, app_stage, arcname_prefix=f"fractalos-{VERSION}-appliance")
    shutil.rmtree(app_stage)
    print(f"  Created: {app_tar.name} ({app_tar.stat().st_size:,} bytes)")

    # 4. Package Full Source / Release Archive
    print("Building Full Release bundle...")
    full_stage = DIST / f"fractalos-{VERSION}"
    full_stage.mkdir(parents=True)

    for item in ("resources", "extras", "docs", "tests", "tools"):
        if (ROOT / item).exists():
            shutil.copytree(ROOT / item, full_stage / item, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "out"))

    for f in ("README.md", "AGENTS.md", "neutralino.config.json"):
        if (ROOT / f).exists():
            shutil.copy(ROOT / f, full_stage / f)

    full_tar = DIST / f"fractalos-{VERSION}-full.tar.gz"
    make_tar_gz(full_tar, full_stage, arcname_prefix=f"fractalos-{VERSION}")
    shutil.rmtree(full_stage)
    print(f"  Created: {full_tar.name} ({full_tar.stat().st_size:,} bytes)")

    # 5. Generate SHA256 checksums
    print("\nGenerating SHA256 checksums...")
    checksums = []
    for pkg_file in sorted(DIST.iterdir()):
        if pkg_file.is_file() and pkg_file.name != "SHA256SUMS":
            sha = get_sha256(pkg_file)
            checksums.append(f"{sha}  {pkg_file.name}")
            print(f"  {sha[:16]}...  {pkg_file.name}")

    checksum_file = DIST / "SHA256SUMS"
    checksum_file.write_text("\n".join(checksums) + "\n")
    print(f"  Wrote checksums to: {checksum_file.name}")

    print("\n✓ Official release packaging complete in 'dist/' directory!")

if __name__ == "__main__":
    main()
