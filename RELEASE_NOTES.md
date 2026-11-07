# Release Notes - v2.2.0

## Release Title
`v2.2.0 - Ranged/Magic Walk-Mark Approach System`

---

## Overview

Version 2.2.0 introduces an intelligent approach mechanic for Ranged and Magic combat classes.  
Previously, the bot would spam movement clicks every frame while walking toward a mob, causing erratic micro-taps and instability.  
This release replaces that with a **walk-mark detection loop** that reads the game's own green movement indicator to decide when to move and when to hold.

---

## Key Features and Improvements

### 1. Walk-Mark Approach System (Ranged / Magic)
- **Template-based detection**: Loads `templates/walk-mark.png` (the green square the game draws on the ground when walking) at startup.
- **Smart approach loop** — after tapping a mob, the bot now:
  1. Checks each frame for the green walk mark.
  2. **Walk mark visible** → player is in motion; no clicks are sent.
  3. **Walk mark gone** → player stopped; bot clicks the mob body to step closer (max once per 0.7 s).
  4. Loop continues until the red lock square (`marked.png`) appears, at which point the approach state clears and normal combat resumes.
- **Zero click spam**: Movement clicks are rate-limited to ≤ 1 per 0.7 s and suppressed entirely while the walk mark is on-screen.
- **Melee unaffected**: The new approach path only activates for `ranged` and `magic` combat classes.

### 2. State Machine Additions
- `BotState.approach_walking` — tracks whether the walk-mark was last seen (player in motion).
- `BotState.approach_click_time` — timestamp of the last approach click for rate-limiting.
- Both fields are reset whenever a new target is acquired or a red lock is confirmed.

### 3. Vision Module
- `FrameVision.walk_mark_visible(frame)` — new stateless method using HSV green-channel isolation + template match (threshold 0.55) to detect the walk marker.
- `TemplateStore` now includes `"walk-mark"` in `BUILT_IN_NAMES` so the template is always loaded.

---

### 4. Executable Configuration Persistence (Standalone / Onefile)
- **App Directory Resolution**: Implemented `get_app_dir()` to accurately resolve the persistent application folder next to `bot.exe` using Nuitka compiled metadata (`__compiled__.containing_dir`).
- **Persistent Settings**: User settings are now saved to and loaded directly from `training_settings.json` located next to `bot.exe` instead of ephemeral extraction directories.
- **Embedded Fallback**: If no user configuration exists on first launch, default settings are loaded from the bundled payload and written out on save.

---

## Verification and Checksums

| File | Size (Bytes) | SHA-256 Checksum | Description |
|---|---|---|---|
| `release/bot.exe` | 52,127,232 bytes | `0E68F13776AE7E80071D595BF3198B758F6F5F2A4683B7A207769B34BA10ABB1` | Standalone one-file Windows executable (Python 3.14 / Nuitka 4.2.2 / Console + Tkinter enabled) |
| `release/RucoyBot-Release.zip` | 52,288,940 bytes | `127CEFB3B7C73E43BA2C76812DF574271C9DE87B715C834AF61DCF764402A932` | Complete distribution bundle with bot.exe, training_settings.json, zone_profiles.json, and templates |


---

## Upgrade Instructions

### Using the Pre-Built Package:
1. Extract `release/RucoyBot-Release.zip` into a clean directory.
2. Launch `bot.exe` to open the configuration dashboard.
3. Configure your desired training zone, combat class, and potion thresholds, then click **Start Bot**.

### Running from Source:
```bash
git pull origin master
pip install -r requirements.txt
python bot.py
```
