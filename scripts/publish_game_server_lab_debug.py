"""Publish reviewed Chappy Game Server Lab v0.1.1 to Debug catalog only.

Run in a dedicated catalog PR branch with a pinned, Android-CI-tested
chappy-player source checkout. No new signed APK or Stable catalog entry.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "local.chappy.game_server_lab"
VERSION = "0.1.1"
PACKAGE_NAME = f"chappy-game-server-lab-v{VERSION}.chappy"
URL = ("https://raw.githubusercontent.com/mibesamiti-png/chappy-apps/"
       f"main/debug/{PACKAGE_NAME}")
DESCRIPTION = ("HTTPSのJSON送信欄を独立、WSS接続失敗と30秒待機上限を表示する"
               "Game Server LabのDebug検証版（実機通信確認待ち）")


def publish(upstream: Path) -> None:
    upstream = upstream.resolve()
    catalog_path = ROOT / "catalog.json"
    original = json.loads(catalog_path.read_text(encoding="utf-8"))
    if original.get("schemaVersion") != 1 or not isinstance(
        original.get("entries"), list
    ):
        raise ValueError("Invalid catalog schema")
    before = json.loads(json.dumps(original, ensure_ascii=False))
    selected = [
        row for row in original["entries"]
        if row.get("channel") == "debug" and row.get("id") == SOURCE_ID
    ]
    if len(selected) != 1:
        raise ValueError("Exactly one Game Server Lab Debug entry required")
    target = selected[0]
    if target["version"] not in ("0.1.0", VERSION):
        raise ValueError("Refusing to rewrite an unrelated Game Server Lab version")

    tested_source = upstream / "sample_apps/game_server_lab"
    if not tested_source.is_dir():
        raise ValueError("Missing reviewed HTML source")
    output = ROOT / "debug" / PACKAGE_NAME
    if output.exists():
        raise ValueError("Refusing to overwrite an existing published package")
    subprocess.run([
        sys.executable, str(upstream / "tools/pack_html_chappy.py"),
        "--source", str(tested_source),
        "--id", SOURCE_ID,
        "--name", "Chappy Game Server Lab",
        "--version", VERSION,
        "--permission", "network", "--permission", "motion",
        "--permission", "haptics",
        "--output", str(output),
    ], check=True)
    blob = output.read_bytes()
    if not 100 <= len(blob) <= 12 * 1024 * 1024:
        raise ValueError("Invalid package size")
    with ZipFile(output) as archive:
        files = archive.namelist()
        if (files.count("manifest.json") != 1 or
                files.count("index.html") != 1 or
                len(files) > 200):
            raise ValueError("Invalid package ZIP")
        manifest = json.loads(archive.read("manifest.json"))
        if (
            manifest.get("formatVersion") != 1 or
            manifest.get("id") != SOURCE_ID or
            manifest.get("name") != "Chappy Game Server Lab" or
            manifest.get("version") != VERSION or
            manifest.get("permissions") != ["network", "motion", "haptics"]
        ):
            raise ValueError("Generated package manifest mismatch")
        html = archive.read("index.html").decode("utf-8")
        for required in ("id=\"httpsBody\"", "timed(pending,30000",
                         "id=\"fillPostExample\"", "id=\"fillWssExample\""):
            if required not in html:
                raise ValueError(f"New Game Server Lab UI missing {required}")

    target.update({
        "name": "Chappy Game Server Lab",
        "description": DESCRIPTION,
        "version": VERSION,
        "channel": "debug",
        "url": URL,
        "sha256": hashlib.sha256(blob).hexdigest(),
        "sizeBytes": len(blob),
    })
    if [row for row in original["entries"] if row.get("channel") == "stable"] != [
        row for row in before["entries"] if row.get("channel") == "stable"
    ]:
        raise ValueError("Stable catalog changed unexpectedly")
    for old, new in zip(before["entries"], original["entries"]):
        if old.get("id") != SOURCE_ID or old.get("channel") != "debug":
            if old != new:
                raise ValueError("Unrelated app was changed")
    output_catalog = json.dumps(original, ensure_ascii=False, indent=2) + "\n"
    if len(output_catalog.encode("utf-8")) > 64 * 1024:
        raise ValueError("Catalog too large")
    catalog_path.write_text(output_catalog, encoding="utf-8")

    sys.path.insert(0, str(ROOT / "scripts"))
    from validate_catalog import check
    check()
    print(f"Verified Game Server Lab {VERSION}: {len(blob)} bytes, "
          f"sha256={hashlib.sha256(blob).hexdigest()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: publish_game_server_lab_debug.py upstream/")
    publish(Path(sys.argv[1]))
