"""Safely publish verified offline mini-app examples to public Debug catalog.

Invoked only by the opt-in, branch-scoped GitHub Actions preview. Bundles
source checked out from a pinned, tested chappy-player commit. No personal
data, secrets, network captures, signing keys or APKs are published.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile

CATALOG_LIMIT = 64 * 1024
PACKAGE_LIMIT = 12 * 1024 * 1024
BASE = "https://raw.githubusercontent.com/mibesamiti-png/chappy-apps/main/debug/"

# Source folder / package basename / description. All are pure sample source.
EXAMPLES = (
    ("memo", "memo-v0.1.0.chappy",
     "オフラインメモ帳。入力と保存データを確認するDebugサンプル"),
    ("video_recorder", "chappy-recorder-v0.1.3.chappy",
     "動画録画・暗転モード・プライベート動画管理の実験版（実機検証用）"),
    ("device_lab", "chappy-device-lab-v0.2.0.chappy",
     "加速度・ジャイロ・端末振動を試せるセンサー検証アプリ"),
    ("file_lab", "chappy-file-lab-v0.2.2.chappy",
     "明示的に選んだファイルの読取・保存などを試す実験アプリ"),
    ("game_server_lab", "chappy-game-server-lab-v0.1.0.chappy",
     "手動指定のHTTPS/WSSゲームサーバー通信と入力送信を試す実験アプリ"),
    ("touch_lab", "chappy-touch-lab-v0.1.0.chappy",
     "マルチタッチ・ポインター描画・スワイプ応答の実験アプリ"),
    ("color_lab", "chappy-color-lab-v0.1.0.chappy",
     "RGBスライダー・グラデーション表示・カラーコピーの実験アプリ"),
)


def verify_file(data: bytes, app: tuple, row: dict) -> None:
    if not (100 <= len(data) <= PACKAGE_LIMIT):
        raise ValueError("Package size not allowed")
    if row["sha256"] != hashlib.sha256(data).hexdigest():
        raise ValueError("Package SHA-256 does not match")
    if row["sizeBytes"] != len(data):
        raise ValueError("Package size mismatch")
    import io
    with ZipFile(io.BytesIO(data), "r") as archive:
        names = archive.namelist()
        if (names.count("manifest.json") != 1 or
                names.count("index.html") != 1 or
                len(names) > 200 or
                len(names) != len({n.lower() for n in names})):
            raise ValueError("Invalid ZIP layout")
        if any(n.startswith("/") or ".." in n.split("/") or "\\" in n
               for n in names):
            raise ValueError("Unsafe ZIP entries")
        manifest = json.loads(archive.read("manifest.json"))
        if (manifest["id"] != row["id"] or
                manifest["name"] != row["name"] or
                manifest["version"] != row["version"] or
                manifest["permissions"] != list(app[4])):
            raise ValueError("Packaged identity or permissions changed")


def publish(root: Path, upstream: Path) -> None:
    path = root / "catalog.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    entries = catalog.get("entries")
    if catalog.get("schemaVersion") != 1 or not isinstance(entries, list):
        raise ValueError("Unexpected public catalog format")
    baseline_stable = json.dumps(
        [e for e in entries if e.get("channel") == "stable"],
        ensure_ascii=False, sort_keys=True,
    )
    media = [
        e for e in entries if e.get("channel") == "debug"
        and e.get("id") == "local.chappy.media_probe"
    ]
    if len(media) != 1:
        raise ValueError("Expected to preserve one existing Debug Media Lab")
    baseline_media = json.dumps(media[0], ensure_ascii=False, sort_keys=True)
    sys.path.insert(0, str(upstream / "tools"))
    from prepare_debug_samples import SAMPLES

    # This also runs the upstream version/permissions/ZIP schema checks.
    subprocess.run(
        [sys.executable, str(upstream / "tools/prepare_debug_samples.py")],
        cwd=upstream, check=True,
    )
    generated = upstream / "debug_sample_assets"
    by_dir = {
        item[3]: item for item in SAMPLES
    }
    listed = json.loads((generated / "index.json").read_text("utf-8"))
    source_info = {
        entry["id"]: entry for entry in listed["entries"]
    }
    target_dir = root / "debug"
    target_dir.mkdir(exist_ok=True)

    for dirname, filename, description in EXAMPLES:
        app = by_dir[dirname]
        app_id, name, version, _, perms = app
        target = target_dir / filename
        original = (generated / (dirname + ".chappy")).read_bytes()
        expected = source_info[app_id]
        if (len(original) != expected["sizeBytes"] or
                hashlib.sha256(original).hexdigest() != expected["sha256"]):
            raise ValueError("Upstream-generated sample mismatch")
        if target.exists():
            if target.is_symlink() or target.read_bytes() != original:
                raise ValueError("Refusing replacement of existing Debug package")
        else:
            shutil.copyfile(generated / (dirname + ".chappy"), target)
        row = {
            "id": app_id,
            "name": name,
            "description": description,
            "version": version,
            "channel": "debug",
            "url": BASE + filename,
            "sha256": hashlib.sha256(original).hexdigest(),
            "sizeBytes": len(original),
        }
        verify_file(original, app, row)
        existing = [
            e for e in entries
            if e.get("channel") == "debug" and e.get("id") == app_id
        ]
        if len(existing) > 1:
            raise ValueError("Duplicate existing Debug app ID")
        if existing:
            if existing[0] != row:
                raise ValueError("Refusing to silently rewrite an existing Debug version")
        else:
            entries.append(row)
        print(f"Debug: {name} {version} {len(original)} bytes")

    if json.dumps([e for e in entries if e.get("channel") == "stable"],
                  ensure_ascii=False, sort_keys=True) != baseline_stable:
        raise ValueError("Stable catalog was changed")
    if json.dumps([e for e in entries if
                   e.get("channel") == "debug" and
                   e.get("id") == "local.chappy.media_probe"],
                  ensure_ascii=False, sort_keys=True) != (
                      "[" + baseline_media + "]"):
        raise ValueError("Existing Media Lab was changed")

    keys = [(e["channel"], e["id"]) for e in entries]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate catalog key")
    debug_ids = [e["id"] for e in entries if e["channel"] == "debug"]
    if len(debug_ids) != 8:
        raise ValueError(f"Expected exactly eight Debug entries, got {len(debug_ids)}")

    # Finally validate every referenced original and added package, including
    # Stable items, against actual bytes checked into this public repository.
    for row in entries:
        url = row["url"]
        prefix = (
            "https://raw.githubusercontent.com/mibesamiti-png/chappy-apps/main/"
        )
        if not url.startswith(prefix) or not url.endswith(".chappy"):
            raise ValueError("Unexpected download host or extension")
        rel = url[len(prefix):]
        if (rel.startswith("/") or ".." in rel.split("/") or
                "\\" in rel or rel.split("/")[0] != row["channel"]):
            raise ValueError("Invalid catalog target path")
        file = root / rel
        if not file.is_file() or file.is_symlink():
            raise ValueError(f"Missing catalog package: {rel}")
        data = file.read_bytes()
        if len(data) != row["sizeBytes"] or (
            hashlib.sha256(data).hexdigest() != row["sha256"]
        ):
            raise ValueError(f"Catalog digest/size mismatch: {rel}")
        with ZipFile(file, "r") as z:
            manifest = json.loads(z.read("manifest.json"))
            if (manifest["id"] != row["id"] or
                    manifest["version"] != row["version"] or
                    manifest["name"] != row["name"]):
                raise ValueError(f"Manifest/catalog mismatch: {rel}")

    output = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    if len(output.encode("utf-8")) > CATALOG_LIMIT:
        raise ValueError("Catalog larger than supported size")
    path.write_text(output, encoding="utf-8")
    print(f"Verified {len(debug_ids)} Debug apps, all catalog package checksums "
          "and unchanged Stable entries")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: publish_debug_labs.py path/to/pinned-chappy-player")
    publish(Path(__file__).resolve().parents[1], Path(sys.argv[1]).resolve())
