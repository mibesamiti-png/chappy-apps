"""Publish only newer, reviewed R2/R3 debug mini-apps on a QA branch.

Inputs must be a pinned, CI-verified chappy-player checkout. Old packages are
immutable and Stable catalog metadata is never changed. No personal data is used.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://raw.githubusercontent.com/mibesamiti-png/chappy-apps/main/"
MAX_PACKAGE = 12 * 1024 * 1024
# id -> source folder, expected next version, immutable new filename, description
TARGETS = {
    "local.chappy.device_lab": (
        "device_lab", "0.2.1", "chappy-device-lab-v0.2.1.chappy",
        "R3検証版：5種類のモーションセンサー、振動、傾き入力、不正値・停止後応答の保護（実機確認待ち）",
    ),
    "local.chappy.file_lab": (
        "file_lab", "0.2.3", "chappy-file-lab-v0.2.3.chappy",
        "R3検証版：テキスト・JSONの安全な読込保存、大容量保管庫、ZIP圧縮、転送進捗とキャンセル（実機確認待ち）",
    ),
    "local.chappy.game_server_lab": (
        "game_server_lab", "0.1.2", "chappy-game-server-lab-v0.1.2.chappy",
        "R2検証版：HTTPS GET/POST、WSS送受信件数、JSONチェック、30秒タイムアウト、秘匿ログ（実機確認待ち）",
    ),
}


def version(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or not all(p.isdecimal() and len(p) <= 9 for p in parts):
        raise ValueError("Invalid semantic version")
    return tuple(map(int, parts))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_catalog(catalog: dict) -> None:
    if catalog.get("schemaVersion") != 1:
        raise ValueError("Wrong catalog schema")
    entries = catalog.get("entries")
    if not isinstance(entries, list) or len(entries) != 10:
        raise ValueError("Unexpected catalog entry count")
    keys = [(r.get("channel"), r.get("id")) for r in entries]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate channel/app IDs")
    if sum(k[0] == "stable" for k in keys) != 2 or sum(k[0] == "debug" for k in keys) != 8:
        raise ValueError("Stable or Debug item count changed")
    for row in entries:
        channel = row["channel"]
        url = row["url"]
        prefix = BASE + channel + "/"
        if channel not in ("stable", "debug") or not url.startswith(prefix):
            raise ValueError("Download URL not in official channel")
        rel = url[len(BASE):]
        parts = rel.split("/")
        if len(parts) != 2 or any(not p or p in (".", "..") for p in parts):
            raise ValueError("Unexpected package path")
        if any(x in rel for x in ("\\", "%", "?", "#")) or not rel.endswith(".chappy"):
            raise ValueError("Unsafe package URL")
        path = ROOT / rel
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Package missing: {rel}")
        data = path.read_bytes()
        if not 100 <= len(data) <= MAX_PACKAGE:
            raise ValueError(f"Package size invalid: {rel}")
        if row.get("sizeBytes") != len(data) or row.get("sha256") != sha(data):
            raise ValueError(f"Package checksum mismatch: {rel}")
        with ZipFile(path, "r") as archive:
            members = archive.namelist()
            if members.count("manifest.json") != 1 or members.count("index.html") != 1:
                raise ValueError("Required ZIP members missing")
            if len(members) > 200 or len(set(x.lower() for x in members)) != len(members):
                raise ValueError("Unsafe ZIP members")
            if any(x.startswith("/") or ".." in x.split("/") or "\\" in x for x in members):
                raise ValueError("Unsafe ZIP pathname")
            manifest = json.loads(archive.read("manifest.json"))
            for key in ("id", "name", "version"):
                if manifest[key] != row[key]:
                    raise ValueError(f"Manifest/{key} mismatch: {rel}")


def run(upstream: Path) -> None:
    catalog_path = ROOT / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    verify_catalog(catalog)  # Existing packages MUST already match.
    entries = catalog["entries"]
    before = {
        (row["channel"], row["id"]): json.dumps(row, sort_keys=True, ensure_ascii=False)
        for row in entries
    }
    sys.path.insert(0, str(upstream / "tools"))
    from prepare_debug_samples import SAMPLES

    available = {id: (name, ver, dirname, perms) for id, name, ver, dirname, perms in SAMPLES}
    for id, (dirname, expected, _, _) in TARGETS.items():
        name, ver, source_dir, perms = available[id]
        if ver != expected or source_dir != dirname:
            raise ValueError("Pinned upstream sample version/source mismatch")
    subprocess.run([sys.executable, str(upstream / "tools/prepare_debug_samples.py")],
                   cwd=upstream, check=True)
    generated = upstream / "debug_sample_assets"
    index = json.loads((generated / "index.json").read_text(encoding="utf-8"))
    source_info = {row["id"]: row for row in index["entries"]}

    for id, (dirname, expected, filename, description) in TARGETS.items():
        matching = [r for r in entries if r["channel"] == "debug" and r["id"] == id]
        if len(matching) != 1:
            raise ValueError("Exactly one existing Debug entry required")
        row = matching[0]
        original_version = row["version"]
        if version(expected) < version(original_version):
            raise ValueError("Refusing Debug downgrade")
        target = ROOT / "debug" / filename
        data = (generated / (dirname + ".chappy")).read_bytes()
        origin = source_info[id]
        if origin["sha256"] != sha(data) or origin["sizeBytes"] != len(data):
            raise ValueError("Upstream index checksum mismatch")
        with ZipFile(generated / (dirname + ".chappy")) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            name, ver, src, perms = available[id]
            if (manifest["id"] != id or manifest["name"] != name or
                manifest["version"] != expected or
                manifest["permissions"] != list(perms)):
                raise ValueError("Unreviewed manifest or permissions")
        if version(expected) == version(original_version):
            if row["sha256"] != sha(data) or row["sizeBytes"] != len(data):
                raise ValueError("Refusing silent same-version replacement")
            if not target.is_file() or target.read_bytes() != data:
                raise ValueError("Previously published package bytes changed")
            continue
        if target.exists() or target.is_symlink():
            raise ValueError("Refusing overwrite of an existing published .chappy")
        target.write_bytes(data)
        row.update({
            "name": name,
            "description": description,
            "version": expected,
            "channel": "debug",
            "url": BASE + "debug/" + filename,
            "sha256": sha(data),
            "sizeBytes": len(data),
        })
        print(f"Prepared {id} v{expected}: {len(data)} bytes, SHA-256 {sha(data)}")

    for row in entries:
        key = row["channel"], row["id"]
        if key[0] != "debug" or key[1] not in TARGETS:
            if json.dumps(row, sort_keys=True, ensure_ascii=False) != before[key]:
                raise ValueError(f"Non-target entry modified: {key}")
    verify_catalog(catalog)
    text = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    if len(text.encode("utf-8")) > 64 * 1024:
        raise ValueError("Catalog over 64 KiB")
    catalog_path.write_text(text, encoding="utf-8")
    print("R3 Debug packages verified; Stable and other Debug entries unchanged")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: refresh_debug_r3.py path/to/pinned-chappy-player")
    run(Path(sys.argv[1]).resolve())
