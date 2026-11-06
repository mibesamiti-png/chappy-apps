# Chappy Apps — public mini-app catalog

Offline `.chappy` mini-app distribution for Chappy Player. The player loads `catalog.json` from the public `main` branch and verifies each package's SHA-256, size, manifest ID and version before install.

## Current catalog

- **Stable** — `stable/asmr-sound-lab.chappy`: ASMR Sound Lab v1.4.0
- **Debug** — `debug/media-probe-v0.1.6.chappy`: Chappy Media Lab v0.1.6, native CameraX recording, one-tap dark capture, immersive system bars, a tiny red/green status LED, session-approved volume-key restart, and private video list/play/delete. **Android physical-device QA is still required.**
- **Debug** — `debug/chappy-recorder-v0.1.0.chappy`: **Chappy Recorder v0.1.0**, a standalone mini-app with rear/front camera toggle, internal free/total storage meter, 720p/1080p quality, private/gallery destination, one-tap dark recording, private video playback/deletion, and swipe brightness gestures near the status LED. **Native storage/brightness features need a matching new Debug APK; physical-device QA is pending.**
- The older `debug/media-probe-v0.1.2.chappy` and `debug/media-probe.chappy` files remain for manual rollback but are **not** advertised by `catalog.json`.

Installing or updating a mini-app from **Chappy Player → Chappy Apps → Debug** needs no manual ZIP import. Installing a mini-app does not update the host player's Android code: CameraX recording APIs require a compatible Debug APK until the feature is tested and shipped in the signed release.

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
