"""Bot settings and repository-relative asset paths."""
from __future__ import annotations

from dataclasses import dataclass
import os
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
    # Movement is accepted only for a perfect map geometry match. A wrong
    # minimap tap can send the player to an unknown location.
    minimap_geometry_min_score: float = 1.0
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
    scene_unchanged_threshold: float = 8.0

    # Training mode & Power Training (PT) settings
    power_training_enabled: bool = False
    special_skill_cooldown: float = 2.0
    special_skill_min_mp: float = 0.20
    special_skill_tap: tuple[int, int] = (1545, 632)
    auto_pickup_enabled: bool = True


def _is_temp_directory(path: Path) -> bool:
    try:
        import tempfile
        temp_dir = Path(tempfile.gettempdir()).resolve()
        resolved = path.resolve()
        return (
            resolved == temp_dir
            or resolved.is_relative_to(temp_dir)
            or "onefile_" in str(resolved).lower()
        )
    except Exception:
        path_str = str(path).lower()
        return "temp" in path_str or "onefile_" in path_str


def get_app_dir() -> Path:
    """Resolve the real directory containing the executable or source project.

    In Nuitka onefile mode, sys.executable points to an ephemeral unpacked
    executable inside the system Temp folder (%TEMP%\\onefile_...).
    This function detects the original launcher directory using Nuitka's
    compiled metadata (__compiled__.containing_dir or original_argv0),
    ensuring configuration and templates persist next to the user's .exe.
    """
    # 1. Nuitka compiled function metadata (__compiled__.containing_dir or original_argv0)
    compiled_info = getattr(get_app_dir, "__compiled__", None)
    if compiled_info is not None:
        containing_dir = getattr(compiled_info, "containing_dir", None)
        if containing_dir:
            cand = Path(containing_dir).resolve()
            if cand.is_dir() and not _is_temp_directory(cand):
                return cand
        orig_argv0 = getattr(compiled_info, "original_argv0", None)
        if orig_argv0:
            cand = Path(orig_argv0).resolve().parent
            if cand.is_dir() and not _is_temp_directory(cand):
                return cand

    # 2. Check environment variables if set
    for env_var in ("NUITKA_ONEFILE_DIRECTORY", "NUITKA_ORIGINAL_ARGV0", "APP_DIR"):
        val = os.environ.get(env_var)
        if val:
            cand = Path(val).resolve()
            if cand.is_file():
                cand = cand.parent
            if cand.is_dir() and not _is_temp_directory(cand):
                return cand

    # 3. Check sys.argv[0] if running a compiled .exe
    if sys.argv and sys.argv[0]:
        try:
            argv_cand = Path(sys.argv[0]).resolve()
            if argv_cand.is_file() and argv_cand.suffix.lower() == ".exe":
                cand_dir = argv_cand.parent
                if not _is_temp_directory(cand_dir):
                    return cand_dir
        except Exception:
            pass

    # 4. Check sys.executable if frozen outside a temp directory
    is_frozen = getattr(sys, "frozen", False) or not sys.executable.lower().endswith(("python.exe", "pythonw.exe"))
    if is_frozen:
        exe_dir = Path(sys.executable).resolve().parent
        if not _is_temp_directory(exe_dir):
            return exe_dir

    # 5. Check current working directory if user config or profile files exist there
    cwd = Path.cwd()
    if (cwd / "training_settings.json").is_file() or (cwd / "zone_profiles.json").is_file():
        return cwd

    # 6. Fallback to repository root
    return Path(__file__).resolve().parent.parent


def _resolve_template_dir() -> Path:
    app_dir = get_app_dir()
    if (app_dir / "templates").is_dir():
        return app_dir / "templates"

    cwd_candidate = Path.cwd() / "templates"
    if cwd_candidate.is_dir():
        return cwd_candidate

    return Path(__file__).resolve().parent.parent / "templates"


def resolve_user_settings_path() -> Path:
    app_dir = get_app_dir()
    return app_dir / "training_settings.json"


def load_user_settings() -> dict:
    path = resolve_user_settings_path()
    if path.is_file():
        try:
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
            print(f"[+] Loaded training settings from {path}")
            return data
        except Exception as e:
            print(f"[!] Could not read training settings from {path}: {e}")
            return {}

    # If running as standalone exe and no external settings file exists yet,
    # fall back to embedded default bundled inside the onefile payload
    embedded = Path(__file__).resolve().parent.parent / "training_settings.json"
    if embedded.is_file() and embedded != path:
        try:
            import json
            data = json.loads(embedded.read_text(encoding="utf-8"))
            print("[+] Loaded default training settings from embedded bundle")
            return data
        except Exception:
            pass

    return {}


def save_user_settings(data: dict) -> bool:
    path = resolve_user_settings_path()
    try:
        import json
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[+] Saved training settings to {path}")
        return True
    except Exception as e:
        print(f"[!] Could not save training settings to {path}: {e}")
        return False


CONFIG = BotConfig()
TEMPLATE_DIR = _resolve_template_dir()

