import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from program.bot import RucoyBot
from program.config import BotConfig, load_user_settings, save_user_settings
from program.gui import LauncherDialog, LaunchResult
from program.profiles import ProfileSettings, ZoneProfile
from program.state import BotState


class _MockDevice:
    def __init__(self):
        self.clicks = []
        self.use_adb = True

    def click(self, x, y):
        self.clicks.append((x, y))
        return True


class _MockVision:
    def __init__(self, red_square_result=(True, (700, 450)), mp_below=False, exhausted=False):
        self._red = red_square_result
        self._mp_below = mp_below
        self._exhausted = exhausted

    def red_square(self, frame, center=None, radius=None):
        return self._red

    def mp_below_threshold(self, frame, threshold):
        return self._mp_below

    def exhausted_caption(self, frame, template):
        return self._exhausted


class TrainingBotTests(unittest.TestCase):
    def setUp(self):
        self.profile = ZoneProfile(
            key="skeleton-lv75",
            target_name="Skeleton Lv.75",
            target_template_key="skeleton_lv75",
            minimap_template_key="minimap-skeleton-layout",
            combat_class="melee",
        )
        self.settings = ProfileSettings(
            active_profile="skeleton-lv75",
            profiles={"skeleton-lv75": self.profile},
        )

    def test_launch_result_unpacks_as_two_elements_with_config(self):
        cfg = BotConfig(power_training_enabled=True, special_skill_cooldown=1.5)
        res = LaunchResult(self.profile, "ranged", config=cfg)
        prof, c_class = res
        self.assertEqual(prof.key, "skeleton-lv75")
        self.assertEqual(c_class, "ranged")
        self.assertTrue(res.config.power_training_enabled)
        self.assertEqual(res.config.special_skill_cooldown, 1.5)

    def test_power_training_special_ability_tap_when_locked(self):
        cfg = BotConfig(
            power_training_enabled=True,
            special_skill_cooldown=1.0,
            special_skill_min_mp=0.20,
            special_skill_tap=(1545, 632),
        )
        bot = RucoyBot.__new__(RucoyBot)
        bot.config = cfg
        bot.combat_class = "melee"
        bot.state = BotState()
        bot.vision = _MockVision(red_square_result=(True, (700, 450)), mp_below=False)
        bot.device = _MockDevice()

        target = {"click_x": 700, "click_y": 450, "red_observations": 2}
        bot.state.current_target = target
        bot.state.confirmed_locked = True
        bot.state.mob_training_started_at = 10.0
        bot.state.last_special_skill_at = 5.0

        dummy_frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        bot._update_target(dummy_frame, 800, 450, now=10.0)

        # Should have clicked the special ability button
        self.assertIn((1545, 632), bot.device.clicks)
        self.assertEqual(bot.state.last_special_skill_at, 10.0)

    def test_power_training_does_not_tap_when_mana_is_too_low(self):
        cfg = BotConfig(
            power_training_enabled=True,
            special_skill_cooldown=1.0,
            special_skill_min_mp=0.25,
            special_skill_tap=(1545, 632),
        )
        bot = RucoyBot.__new__(RucoyBot)
        bot.config = cfg
        bot.combat_class = "melee"
        bot.state = BotState()
        # MP below threshold
        bot.vision = _MockVision(red_square_result=(True, (700, 450)), mp_below=True)
        bot.device = _MockDevice()

        target = {"click_x": 700, "click_y": 450, "red_observations": 2}
        bot.state.current_target = target
        bot.state.confirmed_locked = True
        bot.state.mob_training_started_at = 10.0
        bot.state.last_special_skill_at = 5.0

        dummy_frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        bot._update_target(dummy_frame, 800, 450, now=10.0)

        # Should NOT have clicked the special ability button due to low mana
        self.assertEqual(len(bot.device.clicks), 0)

    def test_max_mob_train_seconds_rotates_target_to_prevent_exhaustion(self):
        cfg = BotConfig(max_mob_train_seconds=30.0)
        bot = RucoyBot.__new__(RucoyBot)
        bot.config = cfg
        bot.combat_class = "melee"
        bot.state = BotState()
        bot.vision = _MockVision(red_square_result=(True, (700, 450)))
        bot.device = _MockDevice()

        target = {"click_x": 700, "click_y": 450, "red_observations": 2}
        bot.state.current_target = target
        bot.state.confirmed_locked = True
        bot.state.mob_training_started_at = 10.0

        dummy_frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        # 31 seconds elapsed
        bot._update_target(dummy_frame, 800, 450, now=41.5)

        # Target should be released to rotate to another mob
        self.assertIsNone(bot.state.current_target)
        self.assertFalse(bot.state.confirmed_locked)
        self.assertEqual(bot.state.mob_training_started_at, 0.0)

    def test_immediate_exhausted_switch_releases_target_without_delay(self):
        cfg = BotConfig(immediate_exhausted_switch=True)
        bot = RucoyBot.__new__(RucoyBot)
        bot.config = cfg
        bot.state = BotState()
        bot.vision = _MockVision(exhausted=True)
        bot.templates = MagicMock()
        bot.templates.get.return_value = None

        target = {"click_x": 700, "click_y": 450}
        bot.state.current_target = target
        bot.state.confirmed_locked = True
        bot.state.exhausted_caption_target = target
        bot.state.exhausted_caption_next_poll = 0.0

        dummy_frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        bot._check_exhausted_caption(dummy_frame, now=10.0)

        # Target should be released immediately
        self.assertIsNone(bot.state.current_target)
        self.assertFalse(bot.state.confirmed_locked)
        self.assertEqual(bot.state.ignored_stale_marker, (700, 450))

    def test_gui_settings_persistence(self):
        test_payload = {
            "active_profile": "skeleton-lv75",
            "combat_class": "magic",
            "training_mode": "power",
            "power_training_enabled": True,
            "special_skill_cooldown": 1.5,
            "special_skill_min_mp": 0.3,
            "max_mob_train_seconds": 45.0,
            "auto_potion_enabled": True,
            "hp_potion_threshold": 0.65,
            "mp_potion_threshold": 0.45,
            "potion_cooldown": 0.9,
            "pvp_mode": True,
            "immediate_exhausted_switch": True,
            "exhausted_caption_confirm_seconds": 8.0,
            "exhausted_travel_trigger_count": 3,
            "enable_minimap_walk": False,
            "auto_pickup_enabled": False,
            "show_preview": True,
            "prefer_adb": True,
        }
        with patch("pathlib.Path.write_text") as mock_write, patch("pathlib.Path.read_text") as mock_read, patch("pathlib.Path.is_file") as mock_is_file:
            import json
            mock_is_file.return_value = True
            mock_read.return_value = json.dumps(test_payload)
            loaded = load_user_settings()
            self.assertEqual(loaded["combat_class"], "magic")
            self.assertEqual(loaded["special_skill_cooldown"], 1.5)

            saved = save_user_settings(test_payload)
            self.assertTrue(saved)
            mock_write.assert_called_once()


if __name__ == "__main__":
    unittest.main()
