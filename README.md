# Rucoy Online AFK Training Bot

A high-performance, computer vision-driven automation system for Rucoy Online. Designed for BlueStacks 5 and MSI App Player, the bot provides background input execution via Android Debug Bridge (ADB), multi-class skill training, dynamic target lock confirmation, cellular minimap navigation, automated resource recovery, and anti-exhaustion failsafes.

---

## Overview

The bot interfaces with an emulator running Rucoy Online using either direct ADB transport or native Win32 window APIs. By analyzing game frames in real time using OpenCV and NumPy, it identifies target mobs, confirms active combat engagements via game marker graphics, manages health and mana potions, executes class-specific special skills for Power Training (PT), and navigates complex dungeon layouts using a cellular minimap pathing engine.

### Core Capabilities

- **True Background Operation**: Communicates directly through local ADB socket commands (`input tap`), eliminating mouse cursor hijacking and allowing the emulator window to remain completely in the background or behind other applications.
- **Computer Vision Targeting**: Identifies mob nametags using multi-scale template matching with color tolerance filtering and distance prioritization relative to the character.
- **Selectable Mob Capture**: Mob nametags can be matched from the ADB framebuffer or a Win32 emulator-window capture. This setting applies only to mob nameplates; other screen checks and all taps keep their configured input backend.
- **Combat Lock State Machine**: Monitors the exact in-game red target diamond/square (`marked.png`) to verify engagement before holding combat actions, preventing missed clicks or accidental map traversal.
- **Multi-Class Combat Support**: Full support for Melee, Ranged, and Magic classes, including automated approach logic for ranged combatants until target lock is verified.
- **Power Training (PT)**: Automatic execution of class-specific special abilities based on configurable cooldown timers and minimum mana reserve thresholds.
- **Anti-Exhaustion Management**: Detects in-game mob exhaustion captions, with support for immediate mob switching, timed confirmation periods, maximum engagement timers per mob, and escape-path minimap roaming.
- **Cellular Minimap Navigation**: An alignment and routing engine based on a 21x21 pixel logical grid that aligns the live in-game minimap against zone master templates to navigate between waypoints.
- **Automated Potion Management**: Scans pixel-level fill levels of the character HP and MP bars with numeric text overlay tolerance, supporting standard PvE and low-latency PvP response intervals.
- **Auto-Looting**: Detects ground loot availability upon target defeat and collects dropped items prior to seeking the next target.
- **Fault Recovery**: Detects disconnection screens and automatically triggers reconnection, recovers from unintended UI dialogs, and features a watchdog for repeated warning patterns.
- **Graphical Dashboard & CLI**: Includes both an interactive dark-themed Tkinter desktop configuration GUI and a scriptable command-line interface.

---

## Architecture

The project is structured as a modular Python package located in the `program/` directory:

| Module | Responsibility |
|---|---|
| `program.bot` | Core combat state machine, target tracking, action coordination, and main loop. |
| `program.vision` | Stateless image recognition, template matching, HP/MP bar fill analysis, and UI detection. |
| `program.navigation` | 21px cellular grid segmentation, master map template registration, and waypoint travel. |
| `program.device` | ADB connection management, auto-discovery of emulator ports, frame capture, and input dispatch. |
| `program.gui` | Polished Tkinter desktop dashboard for real-time parameter tuning and launch orchestration. |
| `program.cli` | Command-line argument parsing, profile resolution, and non-interactive runner invocation. |
| `program.config` | Immutable runtime configuration dataclasses (`BotConfig`) and template directory resolution. |
| `program.profiles` | Zone profile loading, validation of target and minimap template associations. |
| `program.state` | Mutable combat and tracking state representation (`BotState`). |
| `program.models` | Typed data models (`TargetMatch`) for target coordinates, scores, and tracking metrics. |
| `program.diagnostics` | Timestamped stream redirection and recurring error detection guard (`RepeatedOutputGuard`). |
| `program.runner` | Process-level supervision, graceful shutdown, and single-stage restart handling. |
| `program.exceptions` | Internal flow control exceptions (`BotQuit`, `RepeatedOutputReset`). |

---

## Prerequisites

### 1. Emulator Requirements
- **Recommended Emulator**: BlueStacks 5 or MSI App Player.
- **Display Resolution**: Exactly `1600 x 900` (Landscape mode).
- **Display DPI**: Default (240 DPI recommended).
- **ADB Access**: Must be enabled in emulator settings:
  - Open Emulator Settings -> Preferences / Advanced.
  - Enable **Android Debug Bridge (ADB)**.
  - The bot automatically inspects `bluestacks.conf` to extract `status.adb_port` (defaults to port `5555`).

### 2. Python Environment
- Python 3.10 or higher.
- Windows operating system (required for Win32 fallback APIs and BlueStacks auto-discovery).

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Excally/rc-bot.git
   cd rc-bot
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   The required packages include:
   - `opencv-python>=4.8.0` (Image processing and template matching)
   - `numpy>=1.24.0` (Matrix transformations and color analysis)
   - `mss>=9.0.0` (High-speed screen capture fallback)
   - `pywin32>=306` (Windows window management and input dispatch fallback)

---

## Usage

### Graphical Launcher

To launch the dark-themed desktop dashboard:

```bash
python bot.py
```
*(Launching with no arguments automatically opens the GUI. Alternatively, pass `--gui` explicitly).*

The graphical launcher provides controls for:
- Zone Profile selection (e.g., Zombie Lv.65, Skeleton Lv.75, Skeleton Warrior Lv.90).
- Combat Class selection (`melee`, `ranged`, `magic`).
- Mob nameplate capture source (`ADB` or `Win32`). Win32 capture requires the emulator window to remain visible and unobscured.
- Training Mode: Normal AFK vs. Power Training (PT).
- Power Training cooldown and minimum MP percentage requirement.
- Target rotation timeout (maximum seconds per mob).
- Auto-potion toggle, thresholds (HP% and MP%), cooldown, and PvP polling mode.
- Exhaustion handling: Immediate target drop vs. confirmation delay and consecutive exhaustion travel limit.
- Minimap roaming toggle, auto-pickup toggle, live visual preview toggle, and ADB preference.

All settings modified in the GUI are automatically persisted to `training_settings.json`.

### Command-Line Interface (CLI)

The bot can be operated entirely through the terminal:

```bash
# Launch with default active profile and melee class in console mode
python bot.py --no-gui

# Specify a target zone profile and combat class
python bot.py --profile zombie-lv65 ranged --no-gui
python bot.py --profile skeleton-warrior-lv90 magic --no-gui

# Use Win32 capture only for mob nameplate detection; leave other checks and taps on their configured backend
python bot.py --profile skeleton-warrior-lv90 melee --mob-capture win32 --no-gui

# List all configured zone profiles
python bot.py --list-profiles

# Display configuration details for the active profile
python bot.py --show-config
```

#### CLI Options Reference

| Option | Argument | Description |
|---|---|---|
| `--profile` | `NAME` | Selects the zone profile defined in `zone_profiles.json`. |
| `combat_class` | `melee\|ranged\|magic` | Positional combat class selector. |
| `--class` | `melee\|ranged\|magic` | Flag-based combat class selector. |
| `--mob-capture` | `adb\|win32` | Capture source for mob nameplate matching only (default: `adb`). |
| `--gui` | None | Explicitly opens the Tkinter GUI dashboard. |
| `--no-gui` | None | Runs directly in console mode without launching the GUI. |
| `--list-profiles` | None | Displays all configured profiles and exits. |
| `--show-config` | None | Prints the resolved configuration and templates for the selected profile and exits. |

---

## Configuration

### 1. Training Settings (`training_settings.json`)

Controls behavioral runtime parameters across sessions:

```json
{
  "active_profile": "zombie-lv65",
  "combat_class": "ranged",
  "training_mode": "normal",
  "power_training_enabled": false,
  "special_skill_cooldown": 2.0,
  "special_skill_min_mp": 0.25,
  "max_mob_train_seconds": 0.0,
  "auto_potion_enabled": true,
  "hp_potion_threshold": 0.7,
  "mp_potion_threshold": 0.5,
  "potion_cooldown": 0.8,
  "pvp_mode": false,
  "immediate_exhausted_switch": false,
  "exhausted_caption_confirm_seconds": 10.0,
  "exhausted_travel_trigger_count": 2,
  "enable_minimap_walk": true,
  "auto_pickup_enabled": true,
  "show_preview": false,
  "prefer_adb": true,
  "mob_detection_capture": "adb"
}
```

#### Key Parameter Descriptions

- `power_training_enabled`: When `true`, automatically taps the class special skill button while engaged.
- `special_skill_cooldown`: Interval in seconds between special skill activations.
- `special_skill_min_mp`: Minimum MP fill ratio (0.0 to 1.0) required to trigger special skill.
- `max_mob_train_seconds`: Maximum time in seconds to attack a single mob before switching to a new target (`0.0` disables timer).
- `immediate_exhausted_switch`: If `true`, drops target immediately upon caption recognition without waiting for confirmation.
- `exhausted_caption_confirm_seconds`: Grace period before an exhausted mob is officially abandoned when immediate switch is off.
- `exhausted_travel_trigger_count`: Number of consecutive exhausted mobs that will trigger the long-distance minimap repositioning failsafe.
- `pvp_mode`: Reduces potion checking intervals from 500ms down to 100ms for high-damage encounters.
- `enable_minimap_walk`: Enables cellular waypoint pathing when no target mobs are visible.

### 2. Zone Profiles (`zone_profiles.json`)

Defines zone-specific mob templates and matching minimap layouts:

```json
{
  "active_profile": "skeleton-lv75",
  "profiles": {
    "skeleton-lv75": {
      "target_name": "Skeleton Lv.75",
      "name_template": "skeleton_lv75",
      "minimap_template": "minimap-skeleton-layout"
    },
    "zombie-lv65": {
      "target_name": "Zombie Lv.65",
      "name_template": "zombie_lv65",
      "minimap_template": "minimap-zombie-layout"
    },
    "skeleton-warrior-lv90": {
      "target_name": "Skeleton Warrior Lv.90",
      "name_template": "skeleton_warrior_lv90",
      "minimap_template": "minimap-skeleton-2-layout"
    }
  }
}
```

---

## Minimap Navigation Specifications

The navigation system uses an exact 21x21 pixel cell representation (`MAP_CELL_PIXELS = 21`) to construct walkable graphs directly from template images in `templates/`.

### Template Color Palette Standards

Every master minimap reference image must be formatted in solid BGR cell blocks:

| Color (BGR) | RGB Hex | Semantics | Routeable |
|---|---|---|---|
| `(0, 0, 0)` | `#000000` | Walkable Floor | Yes (Core path) |
| `(132, 132, 132)` | `#848484` | Unwalkable Terrain | No |
| `(243, 243, 243)` | `#f3f3f3` | Zone Walls | No (Used for visual registration) |
| `(0, 0, 255)` | `#ff0000` | Context Walls | No (Adjacent map visual boundaries) |
| `(0, 255, 234)` | `#eaff00` | Annotations / Blocked | No |

### Pathfinding Logic

1. When idle without targets for longer than `minimap_idle_delay`, the bot taps the minimap icon.
2. The current visible minimap viewport is captured and matched against the master template using normalized cross-correlation.
3. The player position is localized within the cellular coordinate grid.
4. A safety clearance mask (1-cell dilation of all obstacles) prevents clicks near walls.
5. The bot dispatches a movement tap to an unvisited waypoint or the farthest safe node if in exhaustion failsafe mode.
6. The minimap is closed to allow combat scanning to resume.

---

## Testing

The project includes an automated test suite verifying targeting logic, exhaustion tracking, combat class approach mechanics, GUI persistence, and cellular grid path planning.

Run the test suite with `pytest`:

```bash
pytest tests/
```

### Test Coverage Highlights

- `test_combat_class.py`: Verifies skill tap coordinate resolution and class auto-approach flags.
- `test_exhaustion_behavior.py`: Tests caption polling, immediate vs. confirmed switches, and travel triggers.
- `test_target_lock.py`: Validates red square detection, lock retry sequences, and target loss timeouts.
- `test_minimap_grid.py`: Tests 21px cell extraction, palette parsing, and safe clearance generation.
- `test_gui.py`: Tests setting serialization and bidirectional GUI parameter sync.

---

## Troubleshooting

### ADB Connection Fails
- Verify that ADB is turned on in BlueStacks / MSI App Player settings.
- If running multiple emulator instances, confirm the ADB port in `C:\ProgramData\BlueStacks_nxt\bluestacks.conf` or specify port redirection.
- Test manual connection:
  ```bash
  adb connect 127.0.0.1:5555
  adb devices
  ```

### Mobs Not Being Clicked
- Confirm your emulator resolution is set to `1600 x 900`.
- Verify that the active profile in `zone_profiles.json` matches your current training dungeon.
- Check template availability in `templates/` (e.g., `zombie_lv65.png`, `skeleton_lv75.png`).

### Clicks Register But Mouse Does Not Move
- When running in ADB mode (default), the bot sends commands directly to the Android OS via `input tap`. The Windows mouse cursor will intentionally remain untouched.

---

## License and Disclaimer

This project is licensed under the **Non-Commercial Software License** — see the [LICENSE](LICENSE) file for details.

- **Non-Commercial Use Only**: You are free to use, modify, and study this software for personal and educational purposes.
- **No Sale or Monetization**: You may **not** sell, sublicense, charge fees for, or commercially exploit this software, source code, or compiled binaries without prior written consent from the author (**Xcally**).
- **Disclaimer**: Automating gameplay may violate the Terms of Service of Rucoy Online. The software is provided "as is" for research purposes; use at your own discretion.
