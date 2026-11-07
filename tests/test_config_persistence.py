import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from program.config import (
    _is_temp_directory,
    get_app_dir,
    load_user_settings,
    resolve_user_settings_path,
    save_user_settings,
)
from program.profiles import _resolve_profile_file


class ConfigPersistenceTests(unittest.TestCase):
    def test_is_temp_directory(self):
        sys_temp = Path(tempfile.gettempdir()).resolve()
        sub_temp = sys_temp / "onefile_12345_6789"
        self.assertTrue(_is_temp_directory(sys_temp))
        self.assertTrue(_is_temp_directory(sub_temp))
        self.assertFalse(_is_temp_directory(Path(r"C:\Games\RucoyBot")))

    def test_get_app_dir_uses_nuitka_compiled_containing_dir(self):
        fake_dir_path = (Path.cwd() / "build_fake_app").resolve()
        fake_dir_path.mkdir(parents=True, exist_ok=True)
        try:
            fake_compiled = SimpleNamespace(
                containing_dir=str(fake_dir_path),
                original_argv0=str(fake_dir_path / "bot.exe"),
            )
            with patch.object(get_app_dir, "__compiled__", fake_compiled, create=True):
                resolved = get_app_dir()
                self.assertEqual(resolved, fake_dir_path)
        finally:
            try:
                fake_dir_path.rmdir()
            except OSError:
                pass

    def test_get_app_dir_ignores_temp_in_compiled_containing_dir(self):
        sys_temp = Path(tempfile.gettempdir()).resolve() / "onefile_temp_mock"
        sys_temp.mkdir(parents=True, exist_ok=True)
        try:
            fake_compiled = SimpleNamespace(
                containing_dir=str(sys_temp),
                original_argv0=None,
            )
            with patch.object(get_app_dir, "__compiled__", fake_compiled, create=True):
                # When containing_dir is in temp, it should not use it and fall back
                resolved = get_app_dir()
                self.assertNotEqual(resolved, sys_temp)
        finally:
            try:
                sys_temp.rmdir()
            except OSError:
                pass

    def test_save_and_load_user_settings_roundtrip(self):
        with tempfile.TemporaryDirectory() as fake_dir:
            fake_path = Path(fake_dir)
            with patch("program.config.get_app_dir", return_value=fake_path):
                settings_file = resolve_user_settings_path()
                self.assertEqual(settings_file, fake_path / "training_settings.json")
                self.assertFalse(settings_file.exists())

                data = {
                    "active_profile": "zombie-lv65",
                    "combat_class": "ranged",
                    "training_mode": "power",
                    "power_training_enabled": True,
                    "special_skill_cooldown": 2.5,
                    "hp_potion_threshold": 0.80,
                }
                ok = save_user_settings(data)
                self.assertTrue(ok)
                self.assertTrue(settings_file.is_file())

                loaded = load_user_settings()
                self.assertEqual(loaded["active_profile"], "zombie-lv65")
                self.assertEqual(loaded["combat_class"], "ranged")
                self.assertEqual(loaded["special_skill_cooldown"], 2.5)
                self.assertEqual(loaded["hp_potion_threshold"], 0.80)

    def test_resolve_profile_file_prefers_app_dir(self):
        with tempfile.TemporaryDirectory() as fake_dir:
            fake_path = Path(fake_dir)
            custom_profile = fake_path / "zone_profiles.json"
            custom_profile.write_text(json.dumps({"test": "data"}), encoding="utf-8")
            with patch("program.profiles.get_app_dir", return_value=fake_path):
                resolved = _resolve_profile_file()
                self.assertEqual(resolved, custom_profile)


if __name__ == "__main__":
    unittest.main()
