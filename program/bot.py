"""Combat, target tracking, and recovery state machine."""
from __future__ import annotations

import time
from typing import Any, Optional

import cv2
import numpy as np

from .config import BotConfig, CONFIG
from .device import InputDevice
from .exceptions import BotQuit, RepeatedOutputReset
from .models import TargetMatch
from .navigation import MinimapNavigator
from .profiles import ZoneProfile, load_profile_settings
from .state import BotState
from .vision import FrameVision, TemplateStore

class RucoyBot:
    combat_class: str = "melee"

    def __init__(
        self,
        config: BotConfig = CONFIG,
        profile: Optional[ZoneProfile] = None,
        combat_class: str = "melee",
    ):
        self.config = config
        if profile is None:
            settings = load_profile_settings()
            profile = settings.profiles[settings.active_profile]
        self.profile = profile
        self.combat_class = (
            combat_class or getattr(profile, "combat_class", "melee") or "melee"
        ).lower()
        self.templates = TemplateStore()
        self.device: Optional[InputDevice] = None
        self.vision = FrameVision(config, self.templates)
        self.navigator: Optional[MinimapNavigator] = None
        self.target_templates: list[tuple[np.ndarray, str]] = []
        self.state = BotState()
        self._mob_capture_warning_emitted = False

    def start(self) -> bool:
        images = self.templates.load(self.profile.template_keys)
        exact = images.get(self.profile.target_template_key)
        if exact is None:
            print(
                f"[-] Target template '{self.profile.target_template_key}' "
                f"for '{self.profile.target_name}' not found in {self.templates.directory}!"
            )
            return False
        if self.config.enable_minimap_walk and images.get(self.profile.minimap_template_key) is None:
            print(
                f"[-] Minimap template '{self.profile.minimap_template_key}' "
                f"for profile '{self.profile.key}' not found in {self.templates.directory}!"
            )
            return False
        self.target_templates = [(exact, "white")]
        self.device = InputDevice.connect(self.config)
        if self.device is None:
            return False
        self.navigator = MinimapNavigator(
            self.config, self.vision, self.device, self.templates,
            self.profile.minimap_template_key,
        )
        print("[+] Capturing initial frame...")
        frame = self.device.capture()
        if frame is None:
            print("[-] Failed to capture initial frame! Check if emulator is running.")
            return False
        self._verify_template(frame)
        self._print_startup()
        return True

    def _verify_template(self, frame: np.ndarray) -> None:
        fh, fw = frame.shape[:2]
        player = self.vision.player_center(frame)
        center_x, center_y = player if player is not None else (fw // 2, fh // 2)
        matches = self._find_mob_targets(frame, center_x, center_y)
        if matches:
            strongest = max(matches, key=lambda match: match["score"])
            print(f"[+] Live target matcher found a nameplate (score: {strongest['score']:.2f}).")
        else:
            print("[~] Runtime matcher found no eligible target in the startup frame; scanning will continue.")

    def _get_special_skill_coord(self) -> tuple[int, int]:
        if self.config.special_skill_tap != (1545, 632):
            return self.config.special_skill_tap
        if self.combat_class == "ranged":
            return (1545, 736)
        if self.combat_class == "magic":
            return (1545, 840)
        return (1545, 632)

    def _print_startup(self) -> None:
        assert self.device is not None
        print(f"\n[+] 🥋 Training Profile: '{self.profile.key}'")
        print(f"[+] Target Mob: '{self.profile.target_name}'")
        print(f"[+] Training Skill: {self.combat_class.upper()}")
        mode_str = "POWER TRAINING (⚡ Special Ability Spam)" if self.config.power_training_enabled else "NORMAL AFK (⏱️ Skill Tick Training)"
        print(f"[+] Training Mode: {mode_str}")
        if self.config.power_training_enabled:
            print(f"[+] Special Interval: {self.config.special_skill_cooldown:.1f}s (Min MP: {int(self.config.special_skill_min_mp * 100)}%)")
        if self.config.max_mob_train_seconds > 0:
            print(f"[+] Max Time Per Mob: {self.config.max_mob_train_seconds:.0f}s (Anti-exhaustion target rotation)")
        print(f"[+] Name template: {self.profile.target_template_key}")
        print(f"[+] Minimap template: {self.profile.minimap_template_key}")
        print(f"[+] Method: {'ADB Background Tap (Free Mouse)' if self.device.use_adb else 'Win32 Click'}")
        print(f"[+] Background: {'YES (Can stay behind other windows)' if self.device.use_adb else 'Window visible'}")
        print(f"[+] Mob nameplate capture: {self.config.mob_detection_capture.upper()}")
        print(f"[+] Roaming: Registered minimap waypoints ({'enabled' if self.config.enable_minimap_walk else 'disabled'})")
        if self.combat_class in ("ranged", "magic"):
            print(
                "[+] Class auto-approach: ON (approaching mob until red mark acquired, then hold position)"
            )
        else:
            print("[+] Class auto-approach: OFF (melee auto-walks in-game)")
        print(
            f"[+] Minimap alignment limits: map>={self.config.minimap_geometry_min_score:.2f}, "
            f"coverage>={self.config.minimap_min_visible_reference_fraction:.2f}, "
            f"gap>={self.config.minimap_align_min_gap:.3f}, "
            f"visible pixels>={self.config.minimap_min_visible_reference_pixels}"
        )
        print(f"[+] Hitbox Offset: {self.config.mob_body_y_offset}px below nametag (centered on mob body)")
        print(f"[+] Target marker check: waiting for the exact marked.png outline; nearest visible {self.profile.target_name} first")
        if self.config.immediate_exhausted_switch:
            print("[+] Exhaustion handling: IMMEDIATE switch to new mob on caption detection")
        else:
            print(
                f"[+] Exhaustion failsafe: {self.config.exhausted_travel_trigger_count} consecutive exhausted targets "
                f"within {self.config.exhausted_travel_window_seconds:.0f}s -> farthest minimap point, "
                f"hold {self.config.exhausted_travel_hold_seconds:.0f}s"
            )
        preview_status = "ON (Press q in preview window to exit)" if self.config.show_preview else "OFF (Press Ctrl+C in terminal to exit)"
        print(f"[+] Preview: {preview_status}")
        if self.config.auto_potion_enabled:
            mode = "PvP" if self.config.pvp_mode else "PvE"
            print(
                f"[+] Auto potion: ON ({mode}) "
                f"HP<{int(self.config.hp_potion_threshold * 100)}% "
                f"MP<{int(self.config.mp_potion_threshold * 100)}%"
            )
        else:
            print("[+] Auto potion: OFF")
        print("\n[+] Training loop started! AFK skill training in progress.\n")

    def run(self) -> None:
        if not self.start() or self.device is None:
            return
        try:
            while True:
                frame = self.device.capture()
                if frame is None:
                    self._capture_failed()
                    time.sleep(0.3)
                    continue
                if self.state.last_capture_warning:
                    print("[+] Screen capture recovered.")
                    self.state.last_capture_warning = 0.0
                self._process_frame(frame)
        except BotQuit:
            pass
        if self.config.show_preview:
            cv2.destroyAllWindows()
        print("[+] Bot stopped.")

    def _capture_failed(self) -> None:
        now = time.monotonic()
        if now - self.state.last_capture_warning >= 5.0:
            print("[!] Screen capture unavailable; retrying (ADB capture times out after 3s).")
            self.state.last_capture_warning = now

    def _process_frame(self, frame: np.ndarray) -> None:
        assert self.device is not None and self.navigator is not None
        state = self.state
        cfg = self.config
        fh, fw = frame.shape[:2]
        detected_player = self.vision.player_center(frame)
        cx, cy = detected_player if detected_player is not None else (fw // 2, fh // 2)
        now = time.monotonic()
        state.frame_count += 1
        # Fixed UI icon matching is considerably more expensive than the
        # target scan.  Recheck it often enough to recover from a panel, while
        # allowing intervening frames to go straight to combat detection.
        if state.frame_count == 1 or now >= state.next_ui_check_at:
            state.last_ui_state, _ = self.vision.ui_state(frame)
            state.next_ui_check_at = now + cfg.ui_check_interval
        ui_state = state.last_ui_state
        if ui_state == "combat":
            state.failed_recovery_state = None
            state.failed_recovery_count = 0
        else:
            self._recover_ui(frame, ui_state, now)
            time.sleep(0.08)
            return
        # Potion check runs every frame in combat regardless of target state.
        self._check_potions(frame, now)
        # Finish a pending loot tap before selecting the next mob. Sending it
        # after target acquisition can immediately steal the game's focus.
        if state.current_target is None and state.pickup_pending:
            if cfg.auto_pickup_enabled:
                pickup = self.vision.pickup_position(frame)
                if pickup is not None:
                    print(f"[+] Pickup available after kill; tapping ({pickup[0]}, {pickup[1]}).")
                    if self.device.click(*pickup):
                        state.pickup_pending = False
            else:
                state.pickup_pending = False
        if state.current_target is None:
            self._acquire_target(frame, cx, cy, now)
        self._check_exhausted_caption(frame, now)
        if state.exhausted_travel_pending:
            self._run_exhausted_travel_failsafe(now)
            self._preview(frame, cx, cy)
            return
        if state.current_target is not None:
            self._update_target(frame, cx, cy, now)
        if state.current_target is None:
            idle_duration = now - state.no_target_since
            if cfg.enable_minimap_walk and idle_duration >= cfg.minimap_idle_delay and now - state.last_minimap_time >= cfg.minimap_cooldown:
                print(f"[~] No '{self.profile.target_name}' in vision for {idle_duration:.1f}s -> registering minimap waypoint...")
                self._travel_with_melee_stuck_recovery()
                state.last_minimap_time = time.monotonic()
                state.no_target_since = state.last_minimap_time
        self._preview(frame, cx, cy)

    def _recover_ui(self, frame: np.ndarray, ui_state: str, now: float) -> None:
        state = self.state
        interval = 4.0 if ui_state == "disconnected" else state.ui_recovery_interval
        if now - state.last_ui_back_time < interval:
            return
        print(f"[!] UI state is {ui_state}; recovering and resuming automatically...")
        recovery = self._recover_unexpected_ui(frame)
        state.ui_recovery_interval = 5.0 if recovery == "failed" else 1.5
        if recovery == "failed":
            if state.failed_recovery_state == ui_state:
                state.failed_recovery_count += 1
            else:
                state.failed_recovery_state, state.failed_recovery_count = ui_state, 1
            if state.failed_recovery_count >= self.config.repeated_output_limit:
                raise RepeatedOutputReset(f"UI recovery for '{ui_state}' failed {state.failed_recovery_count} times")
        else:
            state.failed_recovery_state = None
            state.failed_recovery_count = 0
        state.current_target = None
        state.confirmed_locked = False
        state.idle_mark_check_needed = True
        state.no_target_since = now
        state.last_ui_back_time = now

    def _recover_unexpected_ui(self, frame: np.ndarray) -> str:
        assert self.device is not None
        if self.vision.is_disconnected(frame):
            fh, fw = frame.shape[:2]
            if not self.device.click(int(fw * 0.3125), int(fh * 0.667)):
                print("[!] Reconnect tap failed; UI recovery will retry.")
                return "failed"
            print("[~] Disconnected screen detected; selected Reconnect and will resume automatically.")
            return "reconnect"
        back = self.vision.back_icon(frame)
        if back is not None and self.navigator is not None and self.navigator._close_map(back):
            print("[+] Back action closed the unexpected UI.")
            return "back"
        self.device.back()
        time.sleep(0.35)
        after = self.device.capture()
        if after is not None and self.vision.ui_state(after)[0] == "combat":
            print("[+] System Back closed the unexpected UI.")
            return "back"
        print("[!] System Back did not return to combat; recovery is backing off.")
        return "failed"

    def _acquire_target(self, frame: np.ndarray, cx: int, cy: int, now: float) -> None:
        assert self.device is not None
        state, cfg = self.state, self.config
        has_red, position = (False, None)
        marker_checked = False
        if state.idle_mark_check_needed or now >= state.next_idle_mark_check_at:
            has_red, position = self.vision.red_square(frame)
            marker_checked = True
            state.idle_mark_check_needed = False
            state.next_idle_mark_check_at = now + cfg.idle_mark_check_interval
        if marker_checked and state.ignored_stale_marker is not None:
            if has_red and position is not None:
                if np.hypot(position[0] - state.ignored_stale_marker[0], position[1] - state.ignored_stale_marker[1]) < 140:
                    has_red = False
                else:
                    state.ignored_stale_marker = None
            else:
                state.ignored_stale_marker = None
        mobs = self._find_mob_targets(frame, cx, cy)
        if state.unconfirmed_target_position is not None:
            if now >= state.unconfirmed_target_until:
                state.unconfirmed_target_position = None
            else:
                ignored_x, ignored_y = state.unconfirmed_target_position
                mobs = [
                    mob for mob in mobs
                    if not (
                        abs(mob.get("nx", mob["click_x"]) - ignored_x) < 30
                        and abs(mob.get("ny", mob["click_y"]) - ignored_y) < 15
                    )
                ]
        if not mobs:
            if now - state.last_log_time > 5.0:
                print(f"[...] Scanning for '{self.profile.target_name}'... (frame #{state.frame_count}, res {frame.shape[1]}x{frame.shape[0]})")
                state.last_log_time = now
            return
        # find_targets sorts by player distance first; match score only breaks
        # distance ties, so a farther but sharper nameplate cannot win.
        best = mobs[0]
        bx, by = best["click_x"], best["click_y"]
        if has_red and position is not None:
            marker_gap = np.hypot(position[0] - bx, position[1] - by)
            if marker_gap <= cfg.target_reacquire_radius:
                state.ignored_stale_marker = None
                print(f"[*] Detected marked.png on the nearest Skeleton at ({position[0]}, {position[1]}); adopting target...")
                best["click_x"], best["click_y"] = position
                best["last_entity_check"], best["last_entity_seen_time"] = now, now
                state.current_target = best
                state.target_click_time = now
                state.confirmed_locked = True
                state.mob_training_started_at = now
                return
            # An exact mark on a farther/unknown mob must not override the
            # nearest-nameplate rule while starting or recovering the bot.
        if not self.device.click(bx, by):
            state.no_target_since = now
            print(f"[!] Could not tap the selected {self.profile.target_name} at ({bx}, {by}); retrying detection.")
            return
        print(f"[+] Found {len(mobs)} '{self.profile.target_name}' (selected nearest score:{best['score']:.2f} scale:{best['scale']:.1f}x)")
        print(f"    -> Clicking mob at ({bx}, {by}) [dist:{int(best['distance'])}px]")
        best["last_entity_check"], best["last_entity_seen_time"] = now, now
        best["lock_retry_count"] = 0
        state.current_target = best
        state.ignored_stale_marker = None
        state.target_click_time = now
        state.confirmed_locked = False
        state.mob_training_started_at = 0.0
        state.idle_mark_check_needed = False
        state.no_target_since = now
        # Reset approach state whenever a fresh target is selected.
        state.approach_walking = False
        state.approach_click_time = 0.0

    def _check_exhausted_caption(self, frame: np.ndarray, now: float) -> None:
        state, cfg = self.state, self.config
        if state.current_target is not state.exhausted_caption_target:
            state.exhausted_caption_target = state.current_target
            state.exhausted_caption_check_at = None
            state.exhausted_caption_next_poll = 0.0
        waiting_for_confirmation = state.exhausted_caption_check_at is not None
        due = state.current_target is not None and (
            now >= state.exhausted_caption_check_at
            if waiting_for_confirmation
            else now >= state.exhausted_caption_next_poll
        )
        caption_visible = False
        if due:
            caption_visible = self.vision.exhausted_caption(frame, self.templates.get("exhausted-caption"))
        if state.current_target is None:
            state.exhausted_caption_check_at = None
        elif waiting_for_confirmation and due:
            state.exhausted_caption_check_at = None
            state.exhausted_caption_next_poll = now + cfg.exhausted_caption_poll_seconds
            if caption_visible:
                target = state.current_target
                tx, ty = target["click_x"], target["click_y"]
                if (
                    state.exhausted_window_started_at is None
                    or now - state.exhausted_window_started_at > cfg.exhausted_travel_window_seconds
                ):
                    state.consecutive_exhausted = 0
                    state.exhausted_window_started_at = now
                state.consecutive_exhausted += 1
                print(
                    f"[~] Exhausted caption still visible after {cfg.exhausted_caption_confirm_seconds:.0f}s; "
                    f"releasing target at ({tx}, {ty}) without position blacklisting."
                )
                if state.consecutive_exhausted >= max(1, cfg.exhausted_travel_trigger_count):
                    state.exhausted_travel_pending = True
                    print(
                        f"[!] {state.consecutive_exhausted} consecutive exhausted targets within "
                        f"{cfg.exhausted_travel_window_seconds:.0f}s; "
                        f"starting farthest-waypoint minimap failsafe."
                    )
                state.current_target = None
                state.confirmed_locked = False
                state.mob_training_started_at = 0.0
                state.idle_mark_check_needed = False
                state.no_target_since = now
            else:
                self._reset_exhaustion_streak()
                if state.confirmed_locked:
                    print("[+] Exhausted caption cleared; keeping the confirmed target.")
                else:
                    tx, ty = state.current_target["click_x"], state.current_target["click_y"]
                    print(
                        "[+] Exhausted caption cleared before red-square lock; "
                        f"releasing pending target at ({tx}, {ty}) and rescanning."
                    )
                    state.current_target = None
                    state.confirmed_locked = False
                    state.mob_training_started_at = 0.0
                    state.idle_mark_check_needed = True
                    state.no_target_since = now
        elif due:
            state.exhausted_caption_next_poll = now + cfg.exhausted_caption_poll_seconds
            if caption_visible:
                if cfg.immediate_exhausted_switch:
                    target = state.current_target
                    tx, ty = target["click_x"], target["click_y"]
                    print(
                        f"[~] Exhausted caption detected; immediate switch enabled -> "
                        f"releasing target at ({tx}, {ty}) and acquiring next mob."
                    )
                    state.current_target = None
                    state.confirmed_locked = False
                    state.mob_training_started_at = 0.0
                    state.idle_mark_check_needed = True
                    state.no_target_since = now
                    state.ignored_stale_marker = (tx, ty)
                    return
                state.exhausted_caption_check_at = now + cfg.exhausted_caption_confirm_seconds
                print(f"[~] Exhausted caption detected; checking again in {cfg.exhausted_caption_confirm_seconds:.0f}s.")

    def _run_exhausted_travel_failsafe(self, now: float) -> None:
        """Move to the farthest safe visible map point after repeated exhaustion."""
        state, cfg = self.state, self.config
        state.exhausted_travel_pending = False
        state.no_target_since = now
        if not cfg.enable_minimap_walk or self.navigator is None:
            print("[!] Exhausted travel failsafe skipped because minimap walking is disabled.")
            self._reset_exhaustion_streak()
            return
        moved = self._travel_with_melee_stuck_recovery(
            farthest=True,
            keep_open_seconds=max(0.0, cfg.exhausted_travel_hold_seconds),
        )
        state.last_minimap_time = time.monotonic()
        state.no_target_since = state.last_minimap_time
        self._reset_exhaustion_streak()

        if moved:
            # The old screen coordinate belongs to the exhausted mob.  After
            # travelling, allow a fresh scan in the new camera position.
            print("[+] Exhausted travel failsafe complete; resuming normal target scanning.")
        else:
            print("[!] Exhausted travel failsafe could not move; resuming normal scanning.")

    def _travel_with_melee_stuck_recovery(
        self, *, farthest: bool = False, keep_open_seconds: float = 0.0,
    ) -> bool:
        """Retry minimap travel after ranged skill recovery if a melee trip made no progress."""
        assert self.navigator is not None
        device = getattr(self, "device", None)
        is_melee = getattr(self, "combat_class", "melee") == "melee"
        before_frame = device.capture() if device is not None and is_melee else None
        travel_options = {
            "farthest": farthest,
            "keep_open_seconds": max(0.0, keep_open_seconds),
        }
        moved = self.navigator.travel(**travel_options)

        if device is None or before_frame is None:
            return moved

        time.sleep(0.5)
        after_frame = device.capture()
        screen_unchanged_fn = getattr(self.vision, "screen_unchanged", None)
        is_unchanged = (
            screen_unchanged_fn(before_frame, after_frame)
            if after_frame is not None and screen_unchanged_fn is not None
            else False
        )
        if is_unchanged:
            print("[!] Player stayed in the same spot after minimap travel.")
            self._execute_melee_travel_recovery()
            print("[+] Retrying minimap travel after ranged power skill recovery...")
            moved = self.navigator.travel(**travel_options)

        return moved

    def _execute_melee_travel_recovery(self) -> None:
        """Switch to ranged, fire power skill 4 times (1s interval), then switch back to melee."""
        assert self.device is not None
        cfg = self.config
        print(f"[+] Melee minimap recovery: switching to Ranged class at {cfg.class_ranged_tap}...")
        self.device.click(*cfg.class_ranged_tap)
        time.sleep(0.5)

        print(
            f"[+] Using Ranged auto-target power skill at {cfg.exhaustion_recovery_skill_tap} "
            f"{cfg.exhaustion_recovery_skill_count} times ({cfg.exhaustion_recovery_skill_interval:.1f}s interval)..."
        )
        for _ in range(cfg.exhaustion_recovery_skill_count):
            self.device.click(*cfg.exhaustion_recovery_skill_tap)
            time.sleep(cfg.exhaustion_recovery_skill_interval)

        print(f"[+] Switching back to Melee class at {cfg.class_melee_tap}...")
        self.device.click(*cfg.class_melee_tap)
        time.sleep(0.5)

    def _reset_exhaustion_streak(self) -> None:
        self.state.consecutive_exhausted = 0
        self.state.exhausted_window_started_at = None

    def _update_target(self, frame: np.ndarray, cx: int, cy: int, now: float) -> None:
        assert self.device is not None
        state, cfg = self.state, self.config
        target = state.current_target
        assert target is not None
        tx, ty = target["click_x"], target["click_y"]

        # Check the active lock locally first, then globally if the mob moved
        # outside the small crop. A confirmed marker stays locked as long as
        # the marker remains visible, regardless of fight duration.
        has_red, position = self.vision.red_square(
            frame, (tx, ty), radius=int(cfg.target_reacquire_radius)
        )
        if not has_red and state.confirmed_locked:
            has_red, position = self.vision.red_square(frame)

        if has_red and position is not None:
            target["click_x"], target["click_y"] = position
            tx, ty = position
            target["red_loss_since"] = None
            state.idle_mark_check_needed = False

            if not state.confirmed_locked:
                last_red = target.get("red_last_seen", now)
                observations = target.get("red_observations", 0)
                target["red_observations"] = observations + 1 if now - last_red <= 0.5 else 1
                target["red_last_seen"] = now
                # One weak/false detection is not a lock. Require two
                # consecutive observations from the clicked target.
                if target["red_observations"] < 2:
                    return
                state.confirmed_locked = True
                state.mob_training_started_at = now
                # Clear approach state: we have a red lock now.
                state.approach_walking = False
                state.approach_click_time = 0.0
                print(f"[*] Target locked with red square! Training at ({tx}, {ty})...")

            # Max mob training duration safeguard (rotates mobs before exhaustion)
            if (
                cfg.max_mob_train_seconds > 0.0
                and state.mob_training_started_at > 0.0
                and now - state.mob_training_started_at >= cfg.max_mob_train_seconds
            ):
                print(
                    f"[~] Training duration limit ({cfg.max_mob_train_seconds:.0f}s) reached on mob at ({tx}, {ty}); "
                    f"switching target to prevent exhaustion."
                )
                state.current_target = None
                state.confirmed_locked = False
                state.mob_training_started_at = 0.0
                state.idle_mark_check_needed = True
                state.no_target_since = now
                state.ignored_stale_marker = (tx, ty)
                return

            # Power Training (PT) auto-special ability execution
            if cfg.power_training_enabled and now - state.last_special_skill_at >= cfg.special_skill_cooldown:
                can_cast = True
                if cfg.special_skill_min_mp > 0.0 and self.vision.mp_below_threshold(frame, cfg.special_skill_min_mp):
                    can_cast = False
                if can_cast and self.device is not None:
                    sp_x, sp_y = self._get_special_skill_coord()
                    self.device.click(sp_x, sp_y)
                    state.last_special_skill_at = now

            # Locked onto mob: do nothing else, never drop lock, never click ground or other mobs.
            return

        # Red mark not visible in this frame.
        if state.confirmed_locked:
            loss_since = target.get("red_loss_since")
            if loss_since is None:
                target["red_loss_since"] = now
                return
            if (
                now - loss_since < cfg.target_red_loss_timeout
                or state.exhausted_caption_check_at is not None
            ):
                return
            print(
                f"[+] Red square absent for {cfg.target_red_loss_timeout:.1f}s; "
                f"mob defeated at ({tx}, {ty}). Searching for next target."
            )
            state.current_target = None
            state.confirmed_locked = False
            state.mob_training_started_at = 0.0
            self._reset_exhaustion_streak()
            state.idle_mark_check_needed = False
            state.no_target_since = now
            state.pickup_pending = True
            state.ignored_stale_marker = (tx, ty)
            return

        # Target was clicked, but marked.png has not appeared yet (pending confirmation).
        target["red_observations"] = 0
        target.pop("red_last_seen", None)
        if state.exhausted_caption_check_at is not None:
            return

        # For ranged/magic: use walk-mark detection to throttle approach clicks
        # instead of spamming movement every frame.
        if self.combat_class in ("ranged", "magic"):
            self._approach_mob(frame, target, now)
            return

        # Refresh entity position if nameplate is still visible while walking up to mob.
        refresh_interval = max(0.05, cfg.target_position_refresh_interval)
        if now - target.get("last_entity_check", 0.0) >= refresh_interval:
            target["last_entity_check"] = now
            match = self._find_locked_entity(frame, cx, cy, target, now)
            if match is not None:
                target["last_entity_seen_time"] = now
                target["click_x"], target["click_y"] = match["click_x"], match["click_y"]
                target["nx"] = match.get("nx", target.get("nx", tx))
                target["ny"] = match.get("ny", target.get("ny", ty))
                tx, ty = target["click_x"], target["click_y"]
            elif now - target.get("last_entity_seen_time", state.target_click_time) >= cfg.target_entity_loss_timeout:
                target_name = getattr(self.profile, "target_name", "target") if hasattr(self, "profile") else "target"
                print(
                    f"[+] Nearest {target_name} nameplate disappeared for "
                    f"{cfg.target_entity_loss_timeout:.1f}s before marked.png appeared; "
                    f"rescanning at ({tx}, {ty})."
                )
                state.current_target = None
                state.confirmed_locked = False
                state.mob_training_started_at = 0.0
                self._reset_exhaustion_streak()
                state.idle_mark_check_needed = False
                state.no_target_since = now
                state.ignored_stale_marker = None
                return

        # If nameplate is still visible but red square never appeared within timeout:
        if now - state.target_click_time >= cfg.target_entity_loss_timeout:
            retries = int(target.get("lock_retry_count", 0))
            if retries < 1:
                target["lock_retry_count"] = retries + 1
                state.target_click_time = now
                if self.device.click(tx, ty):
                    print(
                        f"[~] No red mark after {cfg.target_entity_loss_timeout:.1f}s; "
                        f"retrying the target click at ({tx}, {ty})."
                    )
                else:
                    print(f"[!] Target retry click failed at ({tx}, {ty}); will keep checking for its red mark.")
                return

            ignored_position = (
                int(target.get("nx", tx)), int(target.get("ny", ty))
            )
            state.unconfirmed_target_position = ignored_position
            state.unconfirmed_target_until = now + cfg.target_entity_loss_timeout
            print(
                f"[!] No red mark after retry; skipping the unconfirmed target "
                f"at {ignored_position} briefly and searching for another mob."
            )
            state.current_target = None
            state.confirmed_locked = False
            state.mob_training_started_at = 0.0
            state.idle_mark_check_needed = True
            state.no_target_since = now
            self._reset_exhaustion_streak()

    def _find_locked_entity(
        self, frame: np.ndarray, cx: int, cy: int, target: TargetMatch, now: float,
    ) -> Optional[TargetMatch]:
        """Find this target's nameplate close to its current screen position."""
        assert self.vision is not None
        match_radius = max(60, int(self.config.target_reacquire_radius))
        search_radius = max(150, match_radius)
        tx, ty = target["click_x"], target["click_y"]
        search_pt = (
            (int(target["nx"]) + int(target.get("nw", 166)) // 2, int(target["ny"]) + int(target.get("nh", 20)) // 2)
            if "nx" in target and "ny" in target
            else (tx, ty)
        )
        matches = self._find_mob_targets(
            frame, self.target_templates, cx, cy,
            search_center=search_pt, search_radius=search_radius, include_deadzone=True,
        )
        if not matches:
            return None
        nearest = min(
            matches,
            key=lambda match: np.hypot(match["click_x"] - tx, match["click_y"] - ty),
        )
        distance = np.hypot(nearest["click_x"] - tx, nearest["click_y"] - ty)
        return nearest if distance <= match_radius else None

    def _find_mob_targets(
        self,
        frame: np.ndarray,
        center_x: int,
        center_y: int,
        *,
        search_center: Optional[tuple[int, int]] = None,
        search_radius: Optional[int] = None,
        include_deadzone: bool = True,
    ) -> list[TargetMatch]:
        """Run nameplate matching on the configured source and return tap-frame coordinates."""
        assert self.device is not None
        source = self.config.mob_detection_capture
        same_as_primary = (
            (source == "adb" and self.device.use_adb)
            or (source == "win32" and not self.device.use_adb)
        )
        detection_frame = frame if same_as_primary else self.device.capture_mob_detection()
        if detection_frame is None:
            if not self._mob_capture_warning_emitted:
                print(
                    f"[!] {source.upper()} mob capture is unavailable; "
                    "falling back to the current input frame."
                )
                self._mob_capture_warning_emitted = True
            detection_frame = frame

        input_h, input_w = frame.shape[:2]
        detect_h, detect_w = detection_frame.shape[:2]
        input_aspect = input_w / max(1, input_h)
        detect_aspect = detect_w / max(1, detect_h)
        if abs(detect_aspect - input_aspect) / input_aspect > 0.01:
            if not self._mob_capture_warning_emitted:
                print(
                    f"[!] {source.upper()} mob frame has a different aspect ratio "
                    f"({detect_w}x{detect_h}); using the current input frame instead."
                )
                self._mob_capture_warning_emitted = True
            detection_frame = frame
            detect_h, detect_w = input_h, input_w

        scale_x = detect_w / max(1, input_w)
        scale_y = detect_h / max(1, input_h)
        detect_center = (int(round(center_x * scale_x)), int(round(center_y * scale_y)))
        detect_search_center = None
        detect_search_radius = search_radius
        if search_center is not None:
            detect_search_center = (
                int(round(search_center[0] * scale_x)),
                int(round(search_center[1] * scale_y)),
            )
        if search_radius is not None:
            detect_search_radius = int(round(search_radius * (scale_x + scale_y) / 2))

        preferred_scale = None
        if source == "win32":
            # Nameplate templates are authored from the 1600px ADB framebuffer.
            # Match at the window frame's actual scale instead of approximating
            # it with one of the generic fallback scales.
            preferred_scale = detect_w / 1600.0

        matches = self.vision.find_targets(
            detection_frame,
            self.target_templates,
            *detect_center,
            search_center=detect_search_center,
            search_radius=detect_search_radius,
            include_deadzone=include_deadzone,
            preferred_scale=preferred_scale,
        )
        if detection_frame is frame:
            return matches

        # The selected capture may have a different pixel size from the input
        # backend. Convert all nameplate geometry back to input/tap coordinates.
        map_x, map_y = input_w / max(1, detect_w), input_h / max(1, detect_h)
        converted: list[TargetMatch] = []
        for match in matches:
            mapped = dict(match)
            for key, factor in (("nx", map_x), ("nw", map_x), ("click_x", map_x)):
                if key in mapped:
                    mapped[key] = int(round(mapped[key] * factor))
            for key, factor in (("ny", map_y), ("nh", map_y), ("click_y", map_y)):
                if key in mapped:
                    mapped[key] = int(round(mapped[key] * factor))
            mapped["distance"] = float(np.hypot(mapped["click_x"] - center_x, mapped["click_y"] - center_y))
            converted.append(mapped)
        return converted

    def _approach_mob(
        self, frame: np.ndarray, target: TargetMatch, now: float,
    ) -> None:
        """Ranged/magic approach: walk toward the mob only when the player has stopped.

        After the initial mob tap, the game shows a green walk-mark square while
        the character is walking.  We check for that mark:
          - Walk mark visible  → player is already walking; do nothing, wait.
          - Walk mark gone     → player stopped (arrived or stuck); click near
                                 the mob body to step closer, then wait again.

        This replaces the old click-every-frame spam for ranged/magic classes.
        """
        assert self.device is not None
        state = self.state
        walk_visible = self.vision.walk_mark_visible(frame)

        if walk_visible:
            # Player is in motion — let the game handle movement; do not click.
            if not state.approach_walking:
                print("[~] Walk mark detected; approaching mob — holding position clicks.")
            state.approach_walking = True
            return

        # Walk mark gone: player stopped moving (or first frame after tap).
        # Only re-click if enough time has passed to avoid instant re-spam.
        min_interval = 0.7  # seconds between approach re-clicks
        if now - state.approach_click_time < min_interval:
            return

        if state.approach_walking:
            print("[~] Walk mark gone; player stopped — clicking closer to mob.")
        else:
            # First approach click right after initial mob tap.
            print("[~] No walk mark yet; sending initial approach click.")

        tx, ty = target["click_x"], target["click_y"]
        if self.device.click(tx, ty):
            state.approach_walking = False   # reset; will go True when mark appears
            state.approach_click_time = now
        else:
            print(f"[!] Approach click failed at ({tx}, {ty}); will retry.")


    def _check_potions(self, frame: np.ndarray, now: float) -> None:
        cfg = self.config
        if not cfg.auto_potion_enabled:
            return
        interval = cfg.pvp_potion_check_interval if cfg.pvp_mode else cfg.potion_check_interval
        if now - self.state.last_potion_check_at < interval:
            return
        self.state.last_potion_check_at = now
        if now - self.state.last_hp_potion_at >= cfg.potion_cooldown:
            if self.vision.hp_below_threshold(frame, cfg.hp_potion_threshold):
                assert self.device is not None
                self.device.click(*cfg.hp_potion_tap)
                self.state.last_hp_potion_at = now
                print(f"[+] HP below {int(cfg.hp_potion_threshold * 100)}%; using HP potion.")
        if now - self.state.last_mp_potion_at >= cfg.potion_cooldown:
            if self.vision.mp_below_threshold(frame, cfg.mp_potion_threshold):
                assert self.device is not None
                self.device.click(*cfg.mana_potion_tap)
                self.state.last_mp_potion_at = now
                print(f"[+] MP below {int(cfg.mp_potion_threshold * 100)}%; using mana potion.")

    def _preview(self, frame: np.ndarray, cx: int, cy: int) -> None:
        if not self.config.show_preview:
            if self.device is not None and not self.device.use_adb:
                time.sleep(0.01)
            return
        display = frame.copy()
        mode_tag = "PT" if self.config.power_training_enabled else "Normal"
        cv2.putText(
            display,
            f"Training: {self.combat_class.upper()} [{mode_tag}]",
            (10, 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            1,
        )
        cv2.circle(display, (cx, cy), self.config.player_deadzone_radius, (255, 255, 0), 1)
        if self.state.current_target is not None:
            tx, ty = self.state.current_target["click_x"], self.state.current_target["click_y"]
            color = (0, 0, 255) if self.state.confirmed_locked else (0, 255, 0)
            cv2.circle(display, (tx, ty), 12, color, 2)
            cv2.line(display, (cx, cy), (tx, ty), color, 1)
        fh, fw = frame.shape[:2]
        scale = min(1.0, 1600 / fw, 900 / fh)
        cv2.imshow("Rucoy Online - AFK Training Preview", cv2.resize(display, (int(fw * scale), int(fh * scale))))
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("[+] Quit key pressed.")
            raise BotQuit
