"""Command-line profile selection for the bot."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from typing import Optional, Sequence

from .config import CONFIG
from .profiles import ProfileSettings, load_profile_settings
from .runner import run_bot


def _load_settings(parser: argparse.ArgumentParser) -> ProfileSettings:
    try:
        return load_profile_settings()
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(f"could not load zone_profiles.json: {error}")


def _combat_class_arg(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned == "mage":
        cleaned = "magic"
    if cleaned not in {"melee", "ranged", "magic"}:
        raise argparse.ArgumentTypeError(
            f"Invalid combat class '{value}'. Available classes: melee, ranged, magic (or mage)"
        )
    return cleaned


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Rucoy bot with selectable zone and template profiles.")
    parser.add_argument(
        "--profile", metavar="NAME", help="zone profile to use; defaults to active_profile in zone_profiles.json"
    )
    parser.add_argument(
        "combat_class",
        nargs="?",
        type=_combat_class_arg,
        default=None,
        help="combat class: melee, ranged, or magic (defaults to profile setting or 'melee')",
    )
    parser.add_argument("--class", dest="class_option", type=_combat_class_arg, help="combat class: melee, ranged, or magic")
    parser.add_argument(
        "--mob-capture", choices=("adb", "win32"), default=None, metavar="SOURCE",
        help="capture source used only for mob nameplate detection (default: adb)",
    )
    parser.add_argument("--gui", action="store_true", help="open GUI launcher dialog to select profile and class")
    parser.add_argument("--no-gui", action="store_true", help="run directly in console without GUI prompt")
    parser.add_argument("--list-profiles", action="store_true", help="list available profiles and exit")
    settings = _load_settings(parser)
    parser.add_argument("--show-config", action="store_true", help="show the selected templates and exit")
    args = parser.parse_args(argv)

    if args.list_profiles:
        for key, profile in settings.profiles.items():
            active = " (active)" if key == settings.active_profile else ""
            print(f"{key}{active}: {profile.target_name} [{profile.combat_class}]")
        return 0

    # Open GUI launcher when running with zero CLI arguments or when --gui is explicitly passed
    is_interactive = (argv is None and len(sys.argv) <= 1 and not args.no_gui) or args.gui
    if is_interactive:
        try:
            from .gui import launch_gui
            selection = launch_gui(settings, mob_capture_default=args.mob_capture)
            if selection is None:
                return 0
            profile, combat_class = selection[0], selection[1]
            config = getattr(selection, "config", None)
            config = config or CONFIG
            if args.mob_capture is not None:
                config = replace(config, mob_detection_capture=args.mob_capture)
            run_bot(profile, combat_class=combat_class, config=config)
            return 0
        except Exception:
            pass

    selected_key = args.profile or settings.active_profile
    profile = settings.profiles.get(selected_key)
    if profile is None:
        parser.error(f"unknown profile '{selected_key}'; use --list-profiles to see available profiles")

    combat_class = args.class_option or args.combat_class or profile.combat_class or "melee"

    if args.show_config:
        print(f"Profile: {profile.key}")
        print(f"Target: {profile.target_name}")
        print(f"Combat class: {combat_class}")
        print(f"Mob capture: {args.mob_capture or CONFIG.mob_detection_capture}")
        print(f"Name template: {profile.target_template_key}.png")
        print(f"Minimap template: {profile.minimap_template_key}.png")
        return 0

    config = replace(CONFIG, mob_detection_capture=args.mob_capture or CONFIG.mob_detection_capture)
    run_bot(profile, combat_class=combat_class, config=config)
    return 0
