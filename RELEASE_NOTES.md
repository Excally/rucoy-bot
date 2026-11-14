# Release Notes

## Unreleased

### Changes

- Ranged and Magic briefly switch to Melee after the first target click only when the target is beyond 300px. The bot waits for the marked target, then clicks it once if it remains out of range; targets within 300px stay in the training class.
- Removed repeated walk-mark approach clicks while waiting for target confirmation.

---

## v2.3.2 - Close-Range Approach and Purple Nameplate Filter

Release date: 2026-11-14

### Changes

- Ranged and Magic skip walk-mark checks and repeated approach clicks when the target is within a 400px radius of the detected player position.
- Added the **Ignore purple named mob** launcher checkbox, persisted in `training_settings.json` and included in the Windows executable.
- Added purple nameplate matching, using a matching asset when available and deriving the purple mask from the target template otherwise.
- Rebuilt the release package with the current zombie minimap grid (1911x1638; exact 21x21 cells). The older `RucoyBot-Release.zip` had a 979x1021 zombie minimap that the grid validator correctly rejected.

### Windows release artifacts

| File | Size (bytes) | SHA-256 |
|---|---:|---|
| `RucoyBot-v2.3.2.exe` | 52,209,664 | `E65F707E6CF7567D0066E2C264053A699B9C68F10F8A7C935EBDA95C23FA43E0` |
| `RucoyBot-v2.3.2-Windows.zip` | 52,377,452 | `6B640ECE5EF623DC945083C3CA1A657C8BE9A9901FAA9257F1E1FF6FA3FEA28D` |

The one-file EXE was built with Python 3.14, Nuitka 4.2.2, and Zig 0.17.1. Nuitka warned that Windows Runtime DLLs are not bundled and must be available on the target Windows installation.

---

## v2.3.1 - Auto-Approach Quick Switch & Traversal Fixes

Release date: 2026-11-14

### Changes

- Added auto-approach quick-switch trick for Ranged and Magic classes: upon confirming a target lock (`marked.png`), the bot briefly taps Melee (`0.1s` delay) to trigger game auto-pathing / walk-mark toward the target, then immediately taps back to the training class.
- Added configurable `melee_approach_switch_delay` setting in `BotConfig` (default: `0.1s`).
- Updated GUI header badge to v2.3.1.
- Updated automated test suite covering Magic, Ranged, and Melee target-lock transition behaviors.

### Windows release artifacts

| File | Size (bytes) | SHA-256 |
|---|---:|---|
| `RucoyBot-v2.3.1.exe` | 52,200,448 | `104A364CB9FC5497791E967206457E3E7F204D484BB342AFBC709BC1CA4ACC52` |
| `RucoyBot-v2.3.1-Windows.zip` | 52,134,071 | `663C79CCC2A0C79DF8A40C6B4DFCA9B418DA311A846224FF3A024573EC9A4899` |

The EXE is a one-file Windows build made with Python 3.14, Nuitka 4.2.2, and Zig 0.17.1. It embeds the default templates and zone profiles. The ZIP adds the README, license, editable zone profiles, templates, and a clean empty settings file.

---

## v2.3.0 - Targeting and Minimap Reliability

Release date: 2026-11-13

### Changes

- Added selectable mob nameplate capture with ADB or Win32 (`--mob-capture`).
- Improved target lock detection and reacquisition behavior, including the nearest-nameplate retry when the marker is partly obscured.
- Fixed mob reacquisition argument handling and improved travel spot-change detection.
- Tightened minimap alignment checks and recovery behavior so uncertain or clipped map geometry is rejected before movement taps.

### Windows release artifacts

| File | Size (bytes) | SHA-256 |
|---|---:|---|
| `RucoyBot-v2.3.0.exe` | 51,472,896 | `D2115D608DF040815F83474E2E2480E9E2395EA42EEAB0B2B62E19C943C599AE` |
| `RucoyBot-v2.3.0-Windows.zip` | 51,429,105 | `D2E1AEB11C4743DDDC4EB91049A61F6233500D542E34C15D825D256B2FFDB1C2` |

The EXE is a one-file Windows build made with Python 3.14, Nuitka 4.2.2, and Zig 0.17.1. It embeds the default templates and zone profiles. The ZIP adds the README, license, editable zone profiles, templates, and a clean empty settings file. Nuitka reported that Windows Runtime DLLs are not bundled and must be available on the target Windows installation.

---
## v2.2.0 - Ranged/Magic Walk-Mark Approach System

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
