"""Bot settings and repository-relative asset paths."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

@dataclass(frozen=True)
class BotConfig:
    prefer_adb: bool = True
    mob_detection_capture: str = "adb"
    window_title: str = "MSI App Player"
    show_preview: bool = False

    enable_minimap_walk: bool = True
    minimap_idle_delay: float = 0.9
    minimap_cooldown: float = 3.0
    minimap_safe_view_fraction: float = 0.70
    minimap_min_click_distance: float = 100
    minimap_max_click_distance: float = 260
    minimap_align_min_gap: float = 0.025
    # Partial views can score below 0.40; coverage and candidate separation
    # provide additional safeguards for this lower geometry threshold.
    minimap_geometry_min_score: float = 0.25
    # The map overlay is drawn over a changing game scene, so raw grayscale
    # template scores are not reliable.  Require a meaningful amount of the
    # reference linework to be visible before accepting geometry-only matches.
    minimap_min_visible_reference_fraction: float = 0.20
    minimap_min_visible_reference_pixels: int = 30000

    margin_top: float = 0.12
    margin_bottom: float = 0.06
    margin_left: float = 0.06
    margin_right: float = 0.06
    mob_body_y_offset: int = 50
    player_deadzone_radius: int = 90
    match_threshold: float = 0.60
    min_name_template_overlap: float = 0.58
    min_segment_match_threshold: float = 0.55
    min_segment_template_overlap: float = 0.65
    target_scan_width: int = 1600
    ui_match_threshold: float = 0.80
    back_icon_match_threshold: float = 0.86
    back_icon_center: tuple[int, int] = (1546, 44)
    back_icon_scales: tuple[float, ...] = (1.0, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6)
    white_text_min_channel: int = 190
    white_text_max_channel_spread: int = 50

    idle_mark_check_interval: float = 1.0
    target_position_refresh_interval: float = 0.10
    target_reacquire_radius: float = 90
    # Do not trust a lingering red outline after the target nameplate vanishes.
    target_entity_loss_timeout: float = 1.5
    # Release quickly when the exact marker disappears; a surviving nameplate
    # alone is not enough to keep a target locked.
    target_red_loss_timeout: float = 1.0
    ui_check_interval: float = 0.35
    # Exhaustion & Target Management for Training
    exhausted_caption_confirm_seconds: float = 10.0
    exhausted_caption_poll_seconds: float = 0.25
    exhausted_travel_trigger_count: int = 1
    exhausted_travel_window_seconds: float = 30.0
    exhausted_travel_hold_seconds: float = 10.0
    repeated_output_limit: int = 200
    immediate_exhausted_switch: bool = False
    max_mob_train_seconds: float = 0.0  # 0.0 = unlimited (train until exhausted/defeated)

    # Auto potion
    auto_potion_enabled: bool = True
    hp_potion_threshold: float = 0.70
    mp_potion_threshold: float = 0.50
    potion_check_interval: float = 0.5
    pvp_potion_check_interval: float = 0.1
    pvp_mode: bool = False
    potion_cooldown: float = 1.0
    hp_potion_tap: tuple[int, int] = (75, 825)
    mana_potion_tap: tuple[int, int] = (75, 675)

    # Training class
    combat_class: str = "melee"

    # Class selector buttons
    class_melee_tap: tuple[int, int] = (1550, 630)
    class_ranged_tap: tuple[int, int] = (1550, 730)
    class_magic_tap: tuple[int, int] = (1550, 830)

    # Exhaustion recovery settings (melee unstuck routine)
    exhaustion_recovery_skill_tap: tuple[int, int] = (75, 525)
    exhaustion_recovery_skill_count: int = 4
    exhaustion_recovery_skill_interval: float = 1.0
    scene_unchanged_threshold: float = 25.0

    # Training mode & Power Training (PT) settings
    power_training_enabled: bool = False
    special_skill_cooldown: float = 2.0
    special_skill_min_mp: float = 0.20
    special_skill_tap: tuple[int, int] = (1545, 632)
    auto_pickup_enabled: bool = True


def _resolve_template_dir() -> Path:
    exe_dir = Path(sys.executable).resolve().parent
    if (exe_dir / "templates").is_dir():
        return exe_dir / "templates"
    return Path(__file__).resolve().parent.parent / "templates"


def resolve_user_settings_path() -> Path:
    # When packaged as a standalone executable (e.g. Nuitka or PyInstaller):
    # sys.executable points to the .exe file itself (e.g. C:\path\to\bot.exe).
    is_frozen = getattr(sys, "frozen", False) or not sys.executable.lower().endswith(("python.exe", "pythonw.exe"))
    if is_frozen:
        exe_dir = Path(sys.executable).resolve().parent
        return exe_dir / "training_settings.json"

    # When running from source via python:
    # Check repository root or current working directory
    repo_root = Path(__file__).resolve().parent.parent
    candidate = repo_root / "training_settings.json"
    if candidate.is_file():
        return candidate

    cwd_candidate = Path.cwd() / "training_settings.json"
    if cwd_candidate.is_file():
        return cwd_candidate

    return candidate


def load_user_settings() -> dict:
    path = resolve_user_settings_path()
    if path.is_file():
        try:
            import json
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[!] Could not read training settings from {path}: {e}")
            return {}

    # If running as standalone exe and no external settings file exists yet,
    # fall back to embedded default bundled inside the onefile payload
    embedded = Path(__file__).resolve().parent.parent / "training_settings.json"
    if embedded.is_file() and embedded != path:
        try:
            import json
            return json.loads(embedded.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {}


def save_user_settings(data: dict) -> bool:
    path = resolve_user_settings_path()
    try:
        import json
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[!] Could not save training settings to {path}: {e}")
        return False


CONFIG = BotConfig()
TEMPLATE_DIR = _resolve_template_dir()
