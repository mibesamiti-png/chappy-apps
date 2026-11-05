# Chappy Apps — public mini-app catalog

Offline `.chappy` mini-app distribution for Chappy Player.

- `stable/asmr-sound-lab.chappy`: ASMR Sound Lab v1.4.0
- `debug/`: optional test packages
- `catalog.json`: schema v1 with measured SHA-256 and byte size

The player fetches `catalog.json` from `main` and validates matching packages before asking the user to install them. Updating `.chappy` packages does **not** require updating the player APK.

**Public repo:** everything in this repository is publicly downloadable. Never commit personal data, private source, API keys, keystores, or tokens.

When replacing a package, regenerate the catalog from the real package bytes and ensure the ID and version match its `manifest.json`. The player only permits trusted packages created by the owner.
