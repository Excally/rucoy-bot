import inspect
import unittest
from unittest.mock import patch

import numpy as np

from program.bot import RucoyBot
from program.config import BotConfig
from program.navigation import MinimapNavigator
from program.state import BotState
from program.vision import FrameVision


class _AlwaysExhaustedVision:
    def exhausted_caption(self, frame, template):
        return True

    def screen_unchanged(self, before, after, threshold=None):
        return True


class _ClearedCaptionVision:
    def exhausted_caption(self, frame, template):
        return False


class _Templates:
    def get(self, key):
        return None


class _TravelRecorder:
    def __init__(self, result=True):
        self.calls = []
        self.result = result

    def travel(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _MapTemplates:
    def __init__(self, reference):
        self.reference = reference

    def get(self, key):
        return self.reference if key == "minimap" else None


class _MapVision:
    def ui_state(self, frame):
        return "minimap", (1546, 44)


class ExhaustionBehaviorTests(unittest.TestCase):
    def _bot(self):
        bot = RucoyBot.__new__(RucoyBot)
        bot.config = BotConfig(exhausted_travel_trigger_count=2)
        bot.state = BotState()
        bot.vision = _AlwaysExhaustedVision()
        bot.templates = _Templates()
        bot.navigator = _TravelRecorder()
        return bot

    def _confirm_exhausted(self, bot, now):
        target = {"click_x": 700, "click_y": 450}
        bot.state.current_target = target
        bot.state.exhausted_caption_target = target
        bot.state.exhausted_caption_check_at = now
        bot._check_exhausted_caption(np.zeros((900, 1600, 3), dtype=np.uint8), now)

    def test_exhausted_targets_trigger_farthest_travel_with_ten_second_hold(self):
        bot = self._bot()

        self._confirm_exhausted(bot, 10.0)
        self._confirm_exhausted(bot, 35.0)

        self.assertEqual(bot.state.consecutive_exhausted, 2)
        self.assertTrue(bot.state.exhausted_travel_pending)
        self.assertFalse(hasattr(bot.state, "blacklist"))
        self.assertFalse(hasattr(bot.state, "ignored_exhausted_marker"))

        bot._run_exhausted_travel_failsafe(35.0)

        self.assertEqual(
            bot.navigator.calls,
            [{"farthest": True, "keep_open_seconds": 10.0}],
        )
        self.assertEqual(bot.state.consecutive_exhausted, 0)
        self.assertIsNone(bot.state.exhausted_window_started_at)

    def test_exhaustion_streak_resets_when_events_are_more_than_one_minute_apart(self):
        bot = self._bot()

        self._confirm_exhausted(bot, 10.0)
        self._confirm_exhausted(bot, 70.1)

        self.assertEqual(bot.state.consecutive_exhausted, 1)
        self.assertFalse(bot.state.exhausted_travel_pending)
        self.assertEqual(bot.state.exhausted_window_started_at, 70.1)

    def test_cleared_caption_releases_pending_unconfirmed_target(self):
        bot = self._bot()
        bot.vision = _ClearedCaptionVision()
        target = {"click_x": 800, "click_y": 354}
        bot.state.current_target = target
        bot.state.exhausted_caption_target = target
        bot.state.exhausted_caption_check_at = 25.0
        bot.state.consecutive_exhausted = 1
        bot.state.exhausted_window_started_at = 10.0

        bot._check_exhausted_caption(np.zeros((900, 1600, 3), dtype=np.uint8), 25.0)

        self.assertIsNone(bot.state.current_target)
        self.assertFalse(bot.state.confirmed_locked)
        self.assertTrue(bot.state.idle_mark_check_needed)
        self.assertEqual(bot.state.no_target_since, 25.0)
        self.assertEqual(bot.state.consecutive_exhausted, 0)
        self.assertIsNone(bot.state.exhausted_window_started_at)

    def test_cleared_caption_keeps_confirmed_target(self):
        bot = self._bot()
        bot.vision = _ClearedCaptionVision()
        target = {"click_x": 800, "click_y": 354}
        bot.state.current_target = target
        bot.state.exhausted_caption_target = target
        bot.state.exhausted_caption_check_at = 25.0
        bot.state.confirmed_locked = True

        bot._check_exhausted_caption(np.zeros((900, 1600, 3), dtype=np.uint8), 25.0)

        self.assertIs(bot.state.current_target, target)
        self.assertTrue(bot.state.confirmed_locked)

    def test_target_scanner_has_no_position_blacklist_parameter(self):
        self.assertNotIn("blacklist", inspect.signature(FrameVision.find_targets).parameters)
        self.assertNotIn("exhausted_mob_blacklist_seconds", BotConfig.__dataclass_fields__)

    def test_navigator_closes_map_after_ten_second_hold(self):
        reference = np.zeros((21, 21, 3), dtype=np.uint8)
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        clock = [0.0]

        class Device:
            def __init__(self):
                self.clicks = []

            def capture(self):
                return frame

            def click(self, x, y, synchronous=False):
                self.clicks.append((x, y, synchronous))
                return True

        device = Device()
        navigator = MinimapNavigator.__new__(MinimapNavigator)
        navigator.config = BotConfig()
        navigator.vision = _MapVision()
        navigator.device = device
        navigator.templates = _MapTemplates(reference)
        navigator.minimap_template_key = "minimap"
        navigator.cell_map = object()
        navigator.reference_id = id(reference)
        navigator.safe_mask = np.ones((1, 1), dtype=bool)
        navigator.waypoints = []
        navigator.route = None
        navigator.last_route_target = None
        navigator.align = lambda image, template: {
            "valid": True, "origin": (0, 0), "scale": 1.0,
            "score": 1.0, "geometry": 1.0, "coverage": 1.0, "gap": 1.0,
        }
        navigator.player_marker = lambda image: (100, 100)
        navigator.destination = lambda *args, **kwargs: (300, 300)
        closed_at = []
        navigator._close_map = lambda icon: closed_at.append(clock[0]) or True

        def sleep(seconds):
            clock[0] += seconds

        with patch("program.navigation.time.monotonic", lambda: clock[0]), \
                patch("program.navigation.time.sleep", sleep):
            moved_and_closed = navigator.travel(farthest=True, keep_open_seconds=10.0)

        self.assertTrue(moved_and_closed)
        self.assertEqual(device.clicks, [(300, 300, True)])
        self.assertEqual(len(closed_at), 1)
        self.assertGreaterEqual(closed_at[0], 10.8)

    def test_exhausted_caption_detects_real_frame_and_rejects_negative_or_blank(self):
        vision = FrameVision()
        import cv2
        from pathlib import Path
        template_path = Path("templates/exhausted-caption.png")
        if not template_path.exists():
            return
        template = cv2.imread(str(template_path))
        self.assertIsNotNone(template)

        self.assertFalse(vision.exhausted_caption(np.zeros((900, 1600, 3), dtype=np.uint8), template))
        self.assertFalse(vision.exhausted_caption(None, template))
        self.assertFalse(vision.exhausted_caption(np.zeros((900, 1600, 3), dtype=np.uint8), None))

        positive_path = Path("screenshot-stock/Screenshot_2026.10.11_15.24.04.835.png")
        if not positive_path.exists():
            positive_path = Path("Screenshot_2026.10.11_15.24.04.835.png")
        if positive_path.exists():
            pos_frame = cv2.imread(str(positive_path))
            self.assertTrue(vision.exhausted_caption(pos_frame, template))

        negative_path = Path("screenshot-stock/Screenshot_2026.10.11_09.06.57.232.png")
        if not negative_path.exists():
            negative_path = Path("Screenshot_2026.10.11_09.06.57.232.png")
        if negative_path.exists():
            neg_frame = cv2.imread(str(negative_path))
            self.assertFalse(vision.exhausted_caption(neg_frame, template))

    def test_screen_unchanged_detects_same_scene_and_rejects_different(self):
        vision = FrameVision()
        frame1 = np.full((900, 1600, 3), 100, dtype=np.uint8)
        frame2 = frame1.copy()
        self.assertTrue(vision.screen_unchanged(frame1, frame2))

        # Minor noise (e.g. idle animation) still counts as unchanged
        frame_noisy = frame1.copy()
        frame_noisy[400:450, 750:850] = 120
        self.assertTrue(vision.screen_unchanged(frame1, frame_noisy))

        # Major scene shift (e.g. moved camera/tiles) counts as changed
        frame_shifted = np.full((900, 1600, 3), 200, dtype=np.uint8)
        self.assertFalse(vision.screen_unchanged(frame1, frame_shifted))

    def test_melee_exhausted_travel_triggers_recovery_and_travel_retry_when_stuck(self):
        bot = self._bot()
        bot.combat_class = "melee"

        clicks = []
        frame = np.full((900, 1600, 3), 80, dtype=np.uint8)

        class MockDevice:
            def capture(self):
                return frame

            def click(self, x, y):
                clicks.append((x, y))
                return True

        bot.device = MockDevice()

        with patch("program.bot.time.sleep", return_value=None):
            bot._run_exhausted_travel_failsafe(100.0)

        # 1x Ranged switch (1550, 730), 4x Power skill (75, 525), 1x Melee switch (1550, 630)
        expected_clicks = [
            (1550, 730),
            (75, 525),
            (75, 525),
            (75, 525),
            (75, 525),
            (1550, 630),
        ]
        self.assertEqual(clicks, expected_clicks)
        # Navigator travel should be called twice (initial attempt + retry after clearing mobs)
        self.assertEqual(len(bot.navigator.calls), 2)

    def test_ranged_class_does_not_trigger_melee_recovery_when_stuck(self):
        bot = self._bot()
        bot.combat_class = "ranged"

        clicks = []
        frame = np.full((900, 1600, 3), 80, dtype=np.uint8)

        class MockDevice:
            def capture(self):
                return frame

            def click(self, x, y):
                clicks.append((x, y))
                return True

        bot.device = MockDevice()

        with patch("program.bot.time.sleep", return_value=None):
            bot._run_exhausted_travel_failsafe(100.0)

        self.assertEqual(clicks, [])
        self.assertEqual(len(bot.navigator.calls), 1)


if __name__ == "__main__":
    unittest.main()
