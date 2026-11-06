"""Fail-closed validation for the public Chappy Apps download catalog.

Checks the exact local committed .chappy bytes. No network requests, data
uploads or Android signing material are involved.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://raw.githubusercontent.com/mibesamiti-png/chappy-apps/main/"
PERMISSIONS = {"camera", "microphone", "motion", "haptics", "files", "network"}


def check() -> None:
    file = ROOT / "catalog.json"
    if file.stat().st_size > 64 * 1024:
        raise ValueError("Catalog exceeds 64 KiB")
    doc = json.loads(file.read_text(encoding="utf-8"))
    rows = doc.get("entries")
    if doc.get("schemaVersion") != 1 or not isinstance(rows, list) or len(rows) > 100:
        raise ValueError("Unsupported catalog format")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "id", "name", "description", "version", "channel", "url",
            "sha256", "sizeBytes",
        }:
            raise ValueError("Invalid catalog fields")
        channel, app_id, version = row["channel"], row["id"], row["version"]
        if channel not in ("stable", "debug"):
            raise ValueError("Unknown catalog channel")
        if not isinstance(app_id, str) or not re.fullmatch(
            r"[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+", app_id
        ):
            raise ValueError("Invalid app ID")
        if (channel, app_id) in seen:
            raise ValueError("Duplicate catalog app")
        seen.add((channel, app_id))
        if not isinstance(version, str) or not re.fullmatch(
            r"\d+\.\d+\.\d+", version
        ):
            raise ValueError("Invalid version")
        if (not isinstance(row["name"], str) or
                not 1 <= len(row["name"]) <= 60 or
                not isinstance(row["description"], str) or
                len(row["description"]) > 500):
            raise ValueError("Invalid title/description")
        url = row["url"]
        if not isinstance(url, str) or not url.startswith(BASE + channel + "/"):
            raise ValueError("Unexpected download host or channel")
        relative = url[len(BASE):]
        if not re.fullmatch(r"(stable|debug)/[a-zA-Z0-9][a-zA-Z0-9_.-]*\.chappy", relative):
            raise ValueError("Unsafe public asset path")
        data_file = ROOT / relative
        if not data_file.is_file() or data_file.is_symlink():
            raise ValueError(f"Missing published file: {relative}")
        data = data_file.read_bytes()
        if (not isinstance(row["sizeBytes"], int) or
                not 100 <= len(data) <= 12 * 1024 * 1024 or
                row["sizeBytes"] != len(data) or
                row["sha256"] != hashlib.sha256(data).hexdigest()):
            raise ValueError(f"Checksum/size mismatch: {relative}")
        with ZipFile(io.BytesIO(data), "r") as zipped:
            names = zipped.namelist()
            if (names.count("manifest.json") != 1 or
                    names.count("index.html") != 1 or
                    len(names) > 200 or
                    len(names) != len({n.lower() for n in names}) or
                    any(n.startswith("/") or ".." in n.split("/")
                        or "\\" in n for n in names)):
                raise ValueError(f"Invalid ZIP paths: {relative}")
            pkg = json.loads(zipped.read("manifest.json"))
            permissions = pkg.get("permissions")
            if (pkg.get("formatVersion") != 1 or
                    pkg.get("id") != app_id or
                    pkg.get("version") != version or
                    pkg.get("name") != row["name"] or
                    pkg.get("entry") != "index.html" or
                    not isinstance(permissions, list) or
                    len(permissions) != len(set(permissions)) or
                    any(permission not in PERMISSIONS for permission in permissions)):
                raise ValueError(f"Mini-app manifest mismatch: {relative}")
        print(f"OK [{channel}] {row['name']} v{version}: {len(data)} bytes")
    print(f"All {len(rows)} catalog entries verified, with {sum(channel == 'debug' for channel, _ in seen)} Debug mini-apps.")


if __name__ == "__main__":
    check()
