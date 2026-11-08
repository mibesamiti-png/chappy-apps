# Chappy Apps — public mini-app catalog

Offline `.chappy` mini-app distribution for Chappy Player. The player loads `catalog.json` from the public `main` branch and verifies each package's SHA-256, size, manifest ID and version before install.

## Current catalog

- **Stable** — `stable/asmr-sound-lab.chappy`: ASMR Sound Lab v1.4.0
- **Debug** — `debug/media-probe-v0.1.6.chappy`: Chappy Media Lab v0.1.6, native CameraX recording, one-tap dark capture, immersive system bars, a tiny red/green status LED, session-approved volume-key restart, and private video list/play/delete. **Android physical-device QA is still required.**
- **Debug** — `debug/chappy-recorder-v0.1.3.chappy`: **Chappy Recorder v0.1.3**, a standalone recording mini-app for private video, dark mode and camera controls. A compatible Chappy Player is required; **physical-device QA is pending**.
- **Debug** — `debug/memo-v0.1.0.chappy`: メモ帳 — editable local notes and persistence.
- **Debug** — `debug/chappy-device-lab-v0.2.1.chappy`: Device Lab — motion sensors and haptic feedback.
- **Debug** — `debug/chappy-file-lab-v0.2.3.chappy`: File Lab — user-approved text/JSON documents and assets.
- **Debug** — `debug/chappy-game-server-lab-v0.1.2.chappy`: Game Server Lab — user-supplied HTTPS/WSS endpoints, opt-in motion and haptics.
- **Debug** — `debug/chappy-touch-lab-v0.1.0.chappy`: Touch Lab — multi-pointer input and drag drawing (no permissions).
- **Debug** — `debug/chappy-color-lab-v0.1.0.chappy`: Color Lab — RGB sliders, gradients and optional clipboard (no permissions).
- **Stable** — Chappy Recorder v0.1.0 remains separately available. The Debug v0.1.3 and Stable v0.1.0 entries share an app ID but are different channels/versions; installing the newer Debug entry updates the installed mini-app with the usual in-app confirmation.
- The older `debug/media-probe-v0.1.2.chappy` and `debug/media-probe.chappy` files remain for manual rollback but are **not** advertised by `catalog.json`.

Installing or updating a mini-app from **Chappy Player → Chappy Apps → Debug** needs no manual ZIP import. Installing a mini-app does not update the host player's Android code: CameraX recording APIs require a compatible Debug APK until the feature is tested and shipped in the signed release.

## Eight Debug mini-apps from the public catalog

The public catalog now lists **eight Debug entries** (Media Lab plus seven additional examples), and two existing Stable entries. These are **downloadable mini-app packages**, not preinstalled Android APK features. In the Chappy Player **Chappy Apps → Debug** tab, refresh the list and install the samples you want individually. Camera, microphone, motion, files and internet use remain user-initiated and permission-gated by the host. All Debug examples are publicly visible; never put personal test data or credentials in this repository.

The seven packages were generated from an exact reviewed Chappy Player source commit and verified alongside `catalog.json` (ZIP contents, permission manifest, file size, SHA-256) using [the one-shot branch preparation workflow](.github/workflows/prepare-debug-labs.yml) and [its publisher validator](scripts/publish_debug_labs.py). Existing **Stable** file hashes and the Media Lab Debug entry are unchanged. The legacy Recorder and Media Lab ZIPs remain available in `debug/` for manual rollback, even when not listed in the live catalog.

## Chappy Recorder Stable promotion

Chappy Recorder v0.1.0 is promoted from Debug to **Stable** only after the official permanently signed **Chappy Player v0.3.0 or newer** APK update feed is published. The [promotion workflow](.github/workflows/promote-recorder-stable.yml) checks the public production update feed, verifies the existing Debug package SHA-256, size and manifest, then copies its **identical bytes** to `stable/chappy-recorder-v0.1.0.chappy` while changing the catalog entry to `channel: stable` in the same Git commit.

This workflow checks on merge, manual dispatch and every six hours. If the official signed production player is still v0.2.4, it exits without publishing an incompatible Stable mini-app. Debug package bytes are retained as an archive. Once promoted, the [Recorder Debug publishing workflow](.github/workflows/sync-recorder-debug.yml) gracefully stops updating the Recorder catalog entry, without affecting Media Lab Debug or ASMR Stable.

Users should install Chappy Player **v0.3.0+** before running Stable Chappy Recorder; its Android-native camera and storage APIs are missing from older production builds. App-private video storage and camera consent rules remain unchanged. Real-device QA is still required.

## Automatic Debug publishing

The workflow [Sync Chappy Media Lab to Debug library](.github/workflows/sync-media-lab-debug.yml) runs every six hours and can also be run manually from Actions. It:

1. Checks out the public `mibesamiti-png/chappy-player` main branch and runs Media Lab Node/Python smoke tests.
2. Reads the authoritative Media Lab version from that repo's Android build workflow.
3. **Only for a higher version**, packages the source with `pack_html_chappy.py` and checks its manifest, media permissions and ZIP size.
4. Updates exactly the Media Lab **Debug** entry with a computed SHA-256 and byte size. The ASMR Stable entry is untouched.
5. Commits the new `.chappy` and matching `catalog.json` together. The same version is never rebuilt/replaced, preventing silent same-version payload changes or accidental downgrades.

The [Chappy Recorder Debug publisher](.github/workflows/sync-recorder-debug.yml) independently checks the standalone recorder source and publishes only a new Recorder version into the Debug catalog; it never overwrites the Media Lab entry or Stable app.

When changing Media Lab, bump the `--version` used in `chappy-player/.github/workflows/build-android.yml` as part of the source update; without a version bump, the Debug publisher intentionally does nothing. GitHub Actions and source checks do not replace Android physical-device QA.

**Public repository:** everything stored here can be downloaded by anyone, including Debug packages. Never commit personal user data, device diagnostics, private credentials, keystores, or access tokens. Releases are explicitly approved by Chappy Player before installation.

## Game Server Lab Debug v0.1.2 — R2 通信診断の改善

- **Chappy Apps 公開ライブラリ → Debug → 更新 → Chappy Game Server Lab (0.1.2)** から旧v0.1.0を明示的に更新できます。APKの再インストールは、このミニアプリの画面修正だけなら不要です。
- HTTPS API欄にPOST専用JSONテキストを追加し、上段のWSS送信欄と混同しないレイアウトに変更。GET/POST/WSSのテスト用URLはボタンで入力できますが、押しただけでは通信しません。
- WSSが接続中のまま続く問題は、v0.1.1側で30秒のUIタイムアウトと失敗ログを導入。ホスト（Chappy Player本体）の45秒ブリッジタイムアウトと接続中断処理の改善は**新しいAndroid Debug APK**が必要です。
- 外部接続は既存のHTTPS/WSS・公開DNS・TLS必須、個別のサーバー接続許可、プライベートIP拒否を維持。Postmanエコーサーバーは第三者サービスのため秘密情報や個人データは送らないでください。
- Debug旧v0.1.0の .chappy はロールバック用に削除しません。Stableの2つのミニアプリは変更しません。実Android上のWSSエコー接続成立はまだ再検証待ちです。

## R2/R3 Debug mini-app update (2026-11-08)

The public **Debug** catalog now advertises immutable refreshed packages generated from reviewed `chappy-player` source commit `6753d533df29b54c70d592d2f65914d85e3e0615`:

- Device Lab **v0.2.1**: sensor availability, invalid-value guards, late-sample cancellation, redacted error messages
- File Lab **v0.2.3**: 64KiB UTF-8/name preflight, safe stored drafts, transfer operation locking and progress guards
- Game Server Lab **v0.1.2**: HTTPS/WSS status and traffic counts, JSON-object preflight, overlap/timeout safeguards and safe logs

The packages and catalog SHA-256/size metadata were generated and validated together on a dedicated review branch using `scripts/refresh_debug_r3.py`. Previous Debug packages remain in `debug/` for manual rollback, while the two Stable catalog entries, Media Lab Debug v0.1.6, and Recorder Debug v0.1.3 remain unchanged. Android real-device validation is still pending. Installing the mini-apps requires a compatible Player host; `.chappy` updates do not fix a host APK crash.
