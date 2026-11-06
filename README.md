# Chappy Apps — public mini-app catalog

Offline `.chappy` mini-app distribution for Chappy Player. The player loads `catalog.json` from the public `main` branch and verifies each package's SHA-256, size, manifest ID and version before install.

## Current catalog

- **Stable** — `stable/asmr-sound-lab.chappy`: ASMR Sound Lab v1.4.0
- **Debug** — `debug/media-probe-v0.1.6.chappy`: Chappy Media Lab v0.1.6, native CameraX recording, one-tap dark capture, immersive system bars, a tiny red/green status LED, session-approved volume-key restart, and private video list/play/delete. **Android physical-device QA is still required.**
- The older `debug/media-probe-v0.1.2.chappy` and `debug/media-probe.chappy` files remain for manual rollback but are **not** advertised by `catalog.json`.

Installing or updating a mini-app from **Chappy Player → Chappy Apps → Debug** needs no manual ZIP import. Installing a mini-app does not update the host player's Android code: CameraX recording APIs require a compatible Debug APK until the feature is tested and shipped in the signed release.

## Automatic Debug publishing

The workflow [Sync Chappy Media Lab to Debug library](.github/workflows/sync-media-lab-debug.yml) runs every six hours and can also be run manually from Actions. It:

1. Checks out the public `mibesamiti-png/chappy-player` main branch and runs Media Lab Node/Python smoke tests.
2. Reads the authoritative Media Lab version from that repo's Android build workflow.
3. **Only for a higher version**, packages the source with `pack_html_chappy.py` and checks its manifest, media permissions and ZIP size.
4. Updates exactly the Media Lab **Debug** entry with a computed SHA-256 and byte size. The ASMR Stable entry is untouched.
5. Commits the new `.chappy` and matching `catalog.json` together. The same version is never rebuilt/replaced, preventing silent same-version payload changes or accidental downgrades.

When changing Media Lab, bump the `--version` used in `chappy-player/.github/workflows/build-android.yml` as part of the source update; without a version bump, the Debug publisher intentionally does nothing. GitHub Actions and source checks do not replace Android physical-device QA.

**Public repository:** everything stored here can be downloaded by anyone, including Debug packages. Never commit personal user data, device diagnostics, private credentials, keystores, or access tokens. Releases are explicitly approved by Chappy Player before installation.
