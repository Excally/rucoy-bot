# Release Notes - v2.1.0

## Release Title
`v2.1.0 - Anti-Exhaustion Failsafe & Persistent Configuration Engine`

---

## Overview

Version 2.1.0 introduces an automated combat failsafe for melee training exhaustion, robust bidirectional configuration persistence for both source execution and standalone compiled binaries, and fine-grained mob engagement controls designed to prevent stamina depletion and pathing lockups.

---

## Key Features and Improvements

### 1. Melee Anti-Exhaustion Recovery Routine
- **Pre- and Post-Travel Viewport Verification**: Captures full-frame state immediately prior to initiating minimap navigation and after closing the minimap interface. A localized viewport comparison algorithm (`screen_unchanged`) determines if the character stayed in the same spot due to mob body blocking or path obstruction.
- **Autonomous Ranged Skill Disengagement**: If the character remains immobile following travel and the active training class is Melee:
  1. Taps the Ranged class selector at `(1550, 730)`.
  2. Casts the auto-targeting power ability at `(75, 525)` 4 consecutive times with a 1.0-second interval, clearing surrounding and blocking mobs without requiring manual target acquisition.
  3. Taps the Melee class selector at `(1550, 630)` to resume normal stance.
  4. Retries the exhausted minimap travel sequence.
- **Class-Scoped Execution**: Non-melee combat classes automatically bypass the skill-clearing sequence to prevent undesired skill or resource expenditure.

### 2. Configuration Persistence Engine (`training_settings.json`)
- **Standalone Binary Persistence**: Resolved an issue where single-file compiled executables (`bot.exe`) routed configuration writes to temporary unpack directories (`AppData/Local/Temp/onefile_...`). The configuration resolver now explicitly anchors user settings to the executable's host folder when running frozen.
- **Bidirectional GUI Synchronization**: Added complete UI hydration (`_apply_settings_dict`) ensuring that loaded configuration files update all Tkinter control variables, combobox selections, scale sliders, and status labels.
- **Dashboard Action Controls**: Added explicit controls in the desktop GUI for **Save Config**, **Load Saved Config**, and **Reset Defaults**.

### 3. Power Training (PT) & Target Rotation Controls
- **Power Training Mode**: Added automated execution of class special skills governed by configurable cooldown intervals and minimum mana reserve thresholds.
- **Maximum Mob Training Timer**: Introduced `max_mob_train_seconds` to allow scheduled target disengagement before in-game mob exhaustion triggers.
- **Immediate Exhaustion Disengagement**: Added `immediate_exhausted_switch` toggle to immediately release an exhausted target upon the first detection of the caption.

### 4. Standalone Windows Executable
- Compiled standalone executable (`release/bot.exe`) stamped with version `2.1.0.0` (GUI badge `v2.1`).
- Packaged full distribution archive (`release/RucoyBot-Release.zip`) including all required templates, zone definitions, and default configurations for zero-dependency execution.
- Added support for `--list-profiles`, `--show-config`, and headless execution flags directly from the standalone binary.

### 5. Repository Organization & Quality Assurance
- Relocated loose root images to `screenshot-stock/` and `templates/debug/`.
- Expanded automated unit test suite with 54 test cases covering targeting mechanics, exhaustion recovery click sequences, cellular minimap pathing, and GUI persistence.

---

## Verification and Checksums

| File | Size | Description |
|---|---|---|
| `release/bot.exe` | 191,794,176 bytes | Standalone one-file Windows executable (Python 3.14 / Nuitka 4.2.2) |
| `release/RucoyBot-Release.zip` | 69,970,969 bytes | Complete distribution bundle with assets and templates |

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
