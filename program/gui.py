"""Graphical launcher dashboard for configuring the Rucoy Online AFK Training Bot."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple

from .config import (
    CONFIG,
    BotConfig,
    load_user_settings,
    resolve_user_settings_path,
    save_user_settings,
)
from .profiles import ProfileSettings, ZoneProfile


class LaunchResult(tuple):
    """Tuple subclass returning (profile, combat_class) with .config attribute."""

    profile: ZoneProfile
    combat_class: str
    config: BotConfig

    def __new__(cls, profile: ZoneProfile, combat_class: str, config: Optional[BotConfig] = None):
        inst = super().__new__(cls, (profile, combat_class))
        inst.profile = profile
        inst.combat_class = combat_class
        inst.config = config or CONFIG
        return inst


class LauncherDialog:
    """A polished, modern dark-themed dashboard to configure AFK training, Power Training (PT), auto-potions, and stamina management."""

    def __init__(self, settings: ProfileSettings):
        self.settings = settings
        self.result: Optional[LaunchResult] = None
        self.saved_cfg = load_user_settings()

        self.root = tk.Tk()
        self.root.title("Rucoy Online — AFK Training Bot")
        self.root.geometry("640x700")
        self.root.resizable(False, False)

        # Center dialog on screen
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x = max(0, (screen_w - 640) // 2)
        pos_y = max(0, (screen_h - 700) // 2)
        self.root.geometry(f"640x700+{pos_x}+{pos_y}")

        # Dark theme palette
        self.bg_color = "#10121d"        # Deep midnight slate
        self.header_bg = "#161928"       # Header surface
        self.card_bg = "#181a29"         # Card background
        self.card_inner = "#202338"      # Elevated / inner surface
        self.border_color = "#2d324d"     # Border divider
        self.fg_color = "#f8fafc"        # Crisp text
        self.fg_dim = "#94a3b8"          # Slate muted text
        self.accent_blue = "#38bdf8"     # Electric cyan / primary
        self.accent_green = "#22c55e"    # Emerald green / start
        self.accent_amber = "#f59e0b"    # Amber / PT
        self.accent_rose = "#f43f5e"     # Rose / HP
        self.accent_mana = "#3b82f6"     # Mana blue

        self.root.configure(bg=self.bg_color)
        self._init_variables()
        self._setup_styles()
        self._build_ui()
        if self.saved_cfg:
            self._apply_settings_dict(self.saved_cfg)
        else:
            self._refresh_info_card()

    def _init_variables(self) -> None:
        cfg = self.saved_cfg
        self.profile_keys = list(self.settings.profiles.keys())
        self.profile_display_names = [
            f"{k} — {self.settings.profiles[k].target_name}"
            for k in self.profile_keys
        ]

        active_idx = 0
        saved_prof = cfg.get("active_profile")
        if saved_prof and saved_prof in self.profile_keys:
            active_idx = self.profile_keys.index(saved_prof)
        elif self.settings.active_profile in self.profile_keys:
            active_idx = self.profile_keys.index(self.settings.active_profile)

        self.selected_profile_idx = tk.IntVar(value=active_idx)

        # Training Class & Mode
        saved_class = cfg.get("combat_class")
        initial_profile = self.settings.profiles[self.profile_keys[active_idx]]
        initial_class = (saved_class or initial_profile.combat_class or "melee").lower()
        self.class_var = tk.StringVar(value=initial_class)

        self.training_mode_var = tk.StringVar(value=cfg.get("training_mode", "normal"))
        self.max_time_var = tk.StringVar(value=str(int(cfg.get("max_mob_train_seconds", 0))))

        # Power Training (PT)
        self.pt_enabled_var = tk.BooleanVar(value=bool(cfg.get("power_training_enabled", False)))
        self.pt_interval_var = tk.DoubleVar(value=float(cfg.get("special_skill_cooldown", 2.0)))
        self.pt_min_mp_var = tk.DoubleVar(value=float(cfg.get("special_skill_min_mp", 0.25)))

        # Auto Potions
        self.auto_potion_var = tk.BooleanVar(value=bool(cfg.get("auto_potion_enabled", True)))
        self.hp_threshold_var = tk.DoubleVar(value=float(cfg.get("hp_potion_threshold", 0.70)))
        self.mp_threshold_var = tk.DoubleVar(value=float(cfg.get("mp_potion_threshold", 0.50)))
        self.potion_cd_var = tk.DoubleVar(value=float(cfg.get("potion_cooldown", 0.8)))
        self.pvp_mode_var = tk.BooleanVar(value=bool(cfg.get("pvp_mode", False)))

        # Exhaustion & Stamina
        self.exhaust_immediate_var = tk.BooleanVar(value=bool(cfg.get("immediate_exhausted_switch", False)))
        self.exhaust_confirm_var = tk.DoubleVar(value=float(cfg.get("exhausted_caption_confirm_seconds", 10.0)))
        self.exhaust_streak_var = tk.StringVar(value=str(int(cfg.get("exhausted_travel_trigger_count", 2))))

        # Navigation & System
        self.minimap_walk_var = tk.BooleanVar(value=bool(cfg.get("enable_minimap_walk", True)))
        self.auto_pickup_var = tk.BooleanVar(value=bool(cfg.get("auto_pickup_enabled", True)))
        self.show_preview_var = tk.BooleanVar(value=bool(cfg.get("show_preview", False)))
        self.prefer_adb_var = tk.BooleanVar(value=bool(cfg.get("prefer_adb", True)))

    def _setup_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")

        # Combobox dark styling
        style.configure(
            "TCombobox",
            fieldbackground=self.card_inner,
            background=self.card_bg,
            foreground=self.fg_color,
            arrowcolor=self.accent_blue,
            relief="flat",
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.card_inner)],
            selectbackground=[("readonly", self.card_inner)],
            selectforeground=[("readonly", self.fg_color)],
        )

        # Scale slider styling
        style.configure(
            "Horizontal.TScale",
            background=self.card_bg,
            troughcolor=self.card_inner,
            sliderthickness=14,
        )

    def _build_ui(self) -> None:
        # Header banner
        header = tk.Frame(self.root, bg=self.header_bg, padx=22, pady=14)
        header.pack(fill="x")

        title_row = tk.Frame(header, bg=self.header_bg)
        title_row.pack(fill="x")

        title_lbl = tk.Label(
            title_row,
            text="🥋 RUCOY TRAINING BOT",
            font=("Segoe UI", 15, "bold"),
            bg=self.header_bg,
            fg=self.accent_blue,
        )
        title_lbl.pack(side="left")

        badge_lbl = tk.Label(
            title_row,
            text=" AFK Optimizer v2.1 ",
            font=("Segoe UI", 8, "bold"),
            bg=self.card_inner,
            fg=self.accent_green,
            padx=8,
            pady=2,
        )
        badge_lbl.pack(side="right")

        sub_lbl = tk.Label(
            header,
            text="Autonomous Stat Training & Power Training (PT) for Melee, Distance & Magic",
            font=("Segoe UI", 9),
            bg=self.header_bg,
            fg=self.fg_dim,
        )
        sub_lbl.pack(anchor="w", pady=(3, 0))

        # Tab Navigation Bar
        tab_bar = tk.Frame(self.root, bg=self.card_inner, padx=12, pady=6)
        tab_bar.pack(fill="x")

        self.tabs = [
            ("profile", "🎯 Training"),
            ("pt", "⚡ Power Train"),
            ("potions", "🧪 Potions"),
            ("stamina", "🛡️ Stamina"),
            ("system", "⚙️ System"),
        ]

        self.tab_buttons: dict[str, tk.Button] = {}
        for tab_id, tab_label in self.tabs:
            btn = tk.Button(
                tab_bar,
                text=tab_label,
                font=("Segoe UI", 9, "bold"),
                bg=self.card_inner,
                fg=self.fg_dim,
                activebackground=self.card_bg,
                activeforeground=self.fg_color,
                relief="flat",
                bd=0,
                padx=12,
                pady=6,
                cursor="hand2",
                command=lambda t=tab_id: self._switch_tab(t),
            )
            btn.pack(side="left", padx=3)
            self.tab_buttons[tab_id] = btn

        # Container for Tab Pages
        self.tab_container = tk.Frame(self.root, bg=self.bg_color, padx=20, pady=12)
        self.tab_container.pack(fill="both", expand=True)

        self.tab_frames: dict[str, tk.Frame] = {}
        self._build_tab_profile()
        self._build_tab_pt()
        self._build_tab_potions()
        self._build_tab_stamina()
        self._build_tab_system()

        # Bottom Action Bar
        footer = tk.Frame(self.root, bg=self.card_bg, padx=20, pady=12, highlightbackground=self.border_color, highlightthickness=1)
        footer.pack(fill="x", side="bottom")

        # Left status indicator
        self.status_lbl = tk.Label(
            footer,
            text="● Ready (Background ADB Mode)",
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.accent_green,
        )
        self.status_lbl.pack(side="left")

        # Right buttons
        self.start_btn = tk.Button(
            footer,
            text="🚀 Start Training Bot",
            font=("Segoe UI", 11, "bold"),
            bg=self.accent_green,
            fg="#0b0f19",
            activebackground="#16a34a",
            activeforeground="#ffffff",
            relief="flat",
            padx=18,
            pady=7,
            cursor="hand2",
            command=self._on_start,
        )
        self.start_btn.pack(side="right")

        self.save_btn = tk.Button(
            footer,
            text="💾 Save Config",
            font=("Segoe UI", 9),
            bg=self.card_inner,
            fg=self.fg_color,
            activebackground=self.border_color,
            activeforeground=self.fg_color,
            relief="flat",
            padx=12,
            pady=7,
            cursor="hand2",
            command=self._on_save_explicit,
        )
        self.save_btn.pack(side="right", padx=6)

        self.load_btn = tk.Button(
            footer,
            text="📂 Load Config",
            font=("Segoe UI", 9),
            bg=self.card_inner,
            fg=self.fg_color,
            activebackground=self.border_color,
            activeforeground=self.fg_color,
            relief="flat",
            padx=12,
            pady=7,
            cursor="hand2",
            command=self._on_load_explicit,
        )
        self.load_btn.pack(side="right", padx=6)

        self.cancel_btn = tk.Button(
            footer,
            text="Exit",
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_dim,
            activebackground=self.border_color,
            activeforeground=self.fg_color,
            relief="flat",
            padx=12,
            pady=7,
            cursor="hand2",
            command=self._on_cancel,
        )
        self.cancel_btn.pack(side="right", padx=(0, 4))

        # Default to first tab
        self._switch_tab("profile")

    def _switch_tab(self, tab_id: str) -> None:
        for t_id, frame in self.tab_frames.items():
            if t_id == tab_id:
                frame.pack(fill="both", expand=True)
                self.tab_buttons[t_id].configure(bg=self.card_bg, fg=self.accent_blue)
            else:
                frame.pack_forget()
                self.tab_buttons[t_id].configure(bg=self.card_inner, fg=self.fg_dim)

    # ---------------- TAB 1: PROFILE & SKILL ----------------
    def _build_tab_profile(self) -> None:
        f = tk.Frame(self.tab_container, bg=self.bg_color)
        self.tab_frames["profile"] = f

        # Target Mob Profile
        card1 = self._create_card(f, "🎯 Target Mob & Training Zone")
        card1.pack(fill="x", pady=(0, 10))

        prof_label = tk.Label(card1, text="Mob Profile:", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.fg_color)
        prof_label.pack(anchor="w", padx=14, pady=(8, 4))

        self.combobox = ttk.Combobox(
            card1,
            values=self.profile_display_names,
            state="readonly",
            font=("Segoe UI", 10),
        )
        active_idx = self.selected_profile_idx.get()
        if 0 <= active_idx < len(self.profile_display_names):
            self.combobox.current(active_idx)
        self.combobox.pack(fill="x", padx=14, pady=(0, 12))
        self.combobox.bind("<<ComboboxSelected>>", self._on_profile_changed)

        # Training Class / Skill
        card2 = self._create_card(f, "⚔️ Training Skill & Weapon Class")
        card2.pack(fill="x", pady=(0, 10))

        radio_row = tk.Frame(card2, bg=self.card_bg)
        radio_row.pack(fill="x", padx=14, pady=10)

        classes = [
            ("melee", "⚔️ Melee (Knight)\nAuto-walks in-game"),
            ("ranged", "🏹 Distance (Archer)\nAuto-steps into range"),
            ("magic", "🔮 Magic (Mage)\nAuto-steps into range"),
        ]

        for val, label in classes:
            rb = tk.Radiobutton(
                radio_row,
                text=label,
                value=val,
                variable=self.class_var,
                font=("Segoe UI", 9),
                bg=self.card_bg,
                fg=self.fg_color,
                selectcolor=self.card_inner,
                activebackground=self.card_bg,
                activeforeground=self.accent_blue,
                justify="left",
                indicatoron=True,
                command=self._on_class_changed,
            )
            rb.pack(side="left", expand=True, fill="x", padx=4)

        # Training Mode & Mob Rotation
        card3 = self._create_card(f, "⏱️ Training Mode & Mob Rotation")
        card3.pack(fill="x", pady=(0, 10))

        mode_row = tk.Frame(card3, bg=self.card_bg)
        mode_row.pack(fill="x", padx=14, pady=(8, 4))

        tk.Radiobutton(
            mode_row,
            text="⏱️ Normal AFK (Tick training with training weapon)",
            value="normal",
            variable=self.training_mode_var,
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_color,
            selectcolor=self.card_inner,
            command=self._on_mode_changed,
        ).pack(anchor="w")

        tk.Radiobutton(
            mode_row,
            text="⚡ Power Training / PT (Special skill spam with mana)",
            value="power",
            variable=self.training_mode_var,
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_color,
            selectcolor=self.card_inner,
            command=self._on_mode_changed,
        ).pack(anchor="w", pady=(4, 8))

        rot_row = tk.Frame(card3, bg=self.card_bg)
        rot_row.pack(fill="x", padx=14, pady=(0, 10))

        tk.Label(rot_row, text="Max time per mob (anti-exhaust rotation):", font=("Segoe UI", 9), bg=self.card_bg, fg=self.fg_dim).pack(side="left")
        self.rot_combo = ttk.Combobox(
            rot_row,
            values=["0 — Unlimited (until dead/exhausted)", "30 — Switch every 30s", "45 — Switch every 45s", "60 — Switch every 60s", "90 — Switch every 90s", "120 — Switch every 120s"],
            state="readonly",
            width=32,
            font=("Segoe UI", 9),
        )
        cur_rot = self.max_time_var.get()
        rot_idx = 0
        for i, val_str in enumerate(["0", "30", "45", "60", "90", "120"]):
            if cur_rot == val_str:
                rot_idx = i
                break
        self.rot_combo.current(rot_idx)
        self.rot_combo.pack(side="right")
        self.rot_combo.bind("<<ComboboxSelected>>", self._on_rotation_changed)

        # Info card
        self.info_card = tk.Frame(f, bg=self.card_inner, highlightbackground=self.border_color, highlightthickness=1, padx=12, pady=8)
        self.info_card.pack(fill="x")

        self.info_target_lbl = tk.Label(self.info_card, text="", font=("Segoe UI", 9, "bold"), bg=self.card_inner, fg=self.accent_blue)
        self.info_target_lbl.pack(anchor="w")

        self.info_mechanic_lbl = tk.Label(self.info_card, text="", font=("Segoe UI", 9), bg=self.card_inner, fg=self.fg_dim, wraplength=560, justify="left")
        self.info_mechanic_lbl.pack(anchor="w", pady=(2, 0))

    # ---------------- TAB 2: POWER TRAINING (PT) ----------------
    def _build_tab_pt(self) -> None:
        f = tk.Frame(self.tab_container, bg=self.bg_color)
        self.tab_frames["pt"] = f

        card = self._create_card(f, "⚡ Power Training (PT) Configuration")
        card.pack(fill="x", pady=(0, 10))

        desc = tk.Label(
            card,
            text="Power Training accelerates skill ticks 2x-3x by repeatedly casting your class's special ability while locked onto a training mob. Ensure auto-mana potion is enabled to sustain PT.",
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_dim,
            wraplength=560,
            justify="left",
        )
        desc.pack(anchor="w", padx=14, pady=(8, 12))

        pt_check = tk.Checkbutton(
            card,
            text="Enable Power Training (Auto-Cast Special Skill)",
            variable=self.pt_enabled_var,
            font=("Segoe UI", 10, "bold"),
            bg=self.card_bg,
            fg=self.accent_amber,
            selectcolor=self.card_inner,
            activebackground=self.card_bg,
            activeforeground=self.accent_amber,
            command=self._on_pt_toggle,
        )
        pt_check.pack(anchor="w", padx=14, pady=(0, 14))

        # Slider for Special Skill Cooldown
        cd_row = tk.Frame(card, bg=self.card_bg)
        cd_row.pack(fill="x", padx=14, pady=(0, 12))

        self.pt_cd_lbl = tk.Label(
            cd_row,
            text=f"Special Skill Interval: {self.pt_interval_var.get():.1f}s",
            font=("Segoe UI", 9, "bold"),
            bg=self.card_bg,
            fg=self.fg_color,
        )
        self.pt_cd_lbl.pack(anchor="w")

        cd_scale = ttk.Scale(
            cd_row,
            from_=0.5,
            to=5.0,
            variable=self.pt_interval_var,
            command=lambda v: self.pt_cd_lbl.config(text=f"Special Skill Interval: {float(v):.1f}s"),
        )
        cd_scale.pack(fill="x", pady=(4, 0))

        # Slider for Minimum MP %
        mp_row = tk.Frame(card, bg=self.card_bg)
        mp_row.pack(fill="x", padx=14, pady=(0, 16))

        self.pt_mp_lbl = tk.Label(
            mp_row,
            text=f"Minimum Mana (MP) Required: {int(self.pt_min_mp_var.get() * 100)}%",
            font=("Segoe UI", 9, "bold"),
            bg=self.card_bg,
            fg=self.fg_color,
        )
        self.pt_mp_lbl.pack(anchor="w")

        mp_scale = ttk.Scale(
            mp_row,
            from_=0.10,
            to=0.80,
            variable=self.pt_min_mp_var,
            command=lambda v: self.pt_mp_lbl.config(text=f"Minimum Mana (MP) Required: {int(float(v) * 100)}%"),
        )
        mp_scale.pack(fill="x", pady=(4, 0))

        # Note Card
        note = tk.Frame(f, bg=self.card_inner, highlightbackground=self.border_color, highlightthickness=1, padx=14, pady=10)
        note.pack(fill="x")
        tk.Label(note, text="💡 PT Class Mechanics:", font=("Segoe UI", 9, "bold"), bg=self.card_inner, fg=self.accent_blue).pack(anchor="w")
        tk.Label(
            note,
            text="• Knight: Whirlwind / Spinning Slash taps top button (1545, 632)\n• Archer: Multi-Arrow Spread taps middle button (1545, 736)\n• Mage: Area Burst Spell taps bottom button (1545, 840)\nThe bot automatically targets the correct button for your active class.",
            font=("Segoe UI", 9),
            bg=self.card_inner,
            fg=self.fg_dim,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

    # ---------------- TAB 3: POTIONS & VITALS ----------------
    def _build_tab_potions(self) -> None:
        f = tk.Frame(self.tab_container, bg=self.bg_color)
        self.tab_frames["potions"] = f

        card = self._create_card(f, "🧪 Vitals & Auto-Potion Sustain")
        card.pack(fill="x", pady=(0, 10))

        # Master toggle
        tk.Checkbutton(
            card,
            text="Enable Auto Potions (Monitors HP & MP bars via pixel detection)",
            variable=self.auto_potion_var,
            font=("Segoe UI", 10, "bold"),
            bg=self.card_bg,
            fg=self.accent_green,
            selectcolor=self.card_inner,
        ).pack(anchor="w", padx=14, pady=(10, 12))

        # HP Slider
        hp_row = tk.Frame(card, bg=self.card_bg)
        hp_row.pack(fill="x", padx=14, pady=(0, 12))

        self.hp_lbl = tk.Label(
            hp_row,
            text=f"Health (HP) Threshold: {int(self.hp_threshold_var.get() * 100)}% (Tap HP Potion below this)",
            font=("Segoe UI", 9, "bold"),
            bg=self.card_bg,
            fg=self.accent_rose,
        )
        self.hp_lbl.pack(anchor="w")

        hp_scale = ttk.Scale(
            hp_row,
            from_=0.20,
            to=0.90,
            variable=self.hp_threshold_var,
            command=lambda v: self.hp_lbl.config(text=f"Health (HP) Threshold: {int(float(v) * 100)}% (Tap HP Potion below this)"),
        )
        hp_scale.pack(fill="x", pady=(4, 0))

        # MP Slider
        mp_row = tk.Frame(card, bg=self.card_bg)
        mp_row.pack(fill="x", padx=14, pady=(0, 12))

        self.mp_lbl = tk.Label(
            mp_row,
            text=f"Mana (MP) Threshold: {int(self.mp_threshold_var.get() * 100)}% (Tap Mana Potion below this)",
            font=("Segoe UI", 9, "bold"),
            bg=self.card_bg,
            fg=self.accent_mana,
        )
        self.mp_lbl.pack(anchor="w")

        mp_scale = ttk.Scale(
            mp_row,
            from_=0.10,
            to=0.90,
            variable=self.mp_threshold_var,
            command=lambda v: self.mp_lbl.config(text=f"Mana (MP) Threshold: {int(float(v) * 100)}% (Tap Mana Potion below this)"),
        )
        mp_scale.pack(fill="x", pady=(4, 0))

        # Potion Cooldown Slider
        cd_row = tk.Frame(card, bg=self.card_bg)
        cd_row.pack(fill="x", padx=14, pady=(0, 12))

        self.p_cd_lbl = tk.Label(
            cd_row,
            text=f"Potion Tap Cooldown: {self.potion_cd_var.get():.1f}s",
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_color,
        )
        self.p_cd_lbl.pack(anchor="w")

        p_cd_scale = ttk.Scale(
            cd_row,
            from_=0.3,
            to=2.0,
            variable=self.potion_cd_var,
            command=lambda v: self.p_cd_lbl.config(text=f"Potion Tap Cooldown: {float(v):.1f}s"),
        )
        p_cd_scale.pack(fill="x", pady=(4, 0))

        # PvP Mode
        tk.Checkbutton(
            card,
            text="High Danger / Emergency Mode (Ultra-fast 0.1s vital polling)",
            variable=self.pvp_mode_var,
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_color,
            selectcolor=self.card_inner,
        ).pack(anchor="w", padx=14, pady=(0, 14))

    # ---------------- TAB 4: STAMINA & SAFETY ----------------
    def _build_tab_stamina(self) -> None:
        f = tk.Frame(self.tab_container, bg=self.bg_color)
        self.tab_frames["stamina"] = f

        card = self._create_card(f, "🛡️ Stamina & Exhaustion Management")
        card.pack(fill="x", pady=(0, 10))

        tk.Label(
            card,
            text="In Rucoy Online, attacking a mob for too long or without dealing damage triggers 'You are exhausted', halting skill progression. Configure how the bot responds:",
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_dim,
            wraplength=560,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(8, 10))

        tk.Checkbutton(
            card,
            text="Immediate Target Swap (Release mob immediately when exhausted caption appears)",
            variable=self.exhaust_immediate_var,
            font=("Segoe UI", 9, "bold"),
            bg=self.card_bg,
            fg=self.accent_blue,
            selectcolor=self.card_inner,
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # Confirm slider
        ex_row = tk.Frame(card, bg=self.card_bg)
        ex_row.pack(fill="x", padx=14, pady=(0, 12))

        self.ex_lbl = tk.Label(
            ex_row,
            text=f"Standard Caption Confirmation Delay: {self.exhaust_confirm_var.get():.0f}s",
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_color,
        )
        self.ex_lbl.pack(anchor="w")

        ex_scale = ttk.Scale(
            ex_row,
            from_=3.0,
            to=20.0,
            variable=self.exhaust_confirm_var,
            command=lambda v: self.ex_lbl.config(text=f"Standard Caption Confirmation Delay: {float(v):.0f}s"),
        )
        ex_scale.pack(fill="x", pady=(4, 0))

        # Relocation streak
        streak_row = tk.Frame(card, bg=self.card_bg)
        streak_row.pack(fill="x", padx=14, pady=(0, 14))
        tk.Label(streak_row, text="Minimap Relocation Failsafe:", font=("Segoe UI", 9), bg=self.card_bg, fg=self.fg_dim).pack(side="left")

        self.streak_combo = ttk.Combobox(
            streak_row,
            values=["1 — Move after 1 exhausted mob", "2 — Move after 2 consecutive exhausted mobs", "3 — Move after 3 consecutive exhausted mobs"],
            state="readonly",
            width=36,
            font=("Segoe UI", 9),
        )
        s_val = self.exhaust_streak_var.get()
        s_idx = 1 if s_val == "2" else (0 if s_val == "1" else 2)
        self.streak_combo.current(s_idx)
        self.streak_combo.pack(side="right")
        self.streak_combo.bind("<<ComboboxSelected>>", self._on_streak_changed)

        # Roaming Card
        card_roam = self._create_card(f, "🗺️ Navigation & Loot")
        card_roam.pack(fill="x")

        tk.Checkbutton(
            card_roam,
            text="Enable Minimap Roaming (Auto-walk safe waypoints when training zone is empty)",
            variable=self.minimap_walk_var,
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_color,
            selectcolor=self.card_inner,
        ).pack(anchor="w", padx=14, pady=(10, 6))

        tk.Checkbutton(
            card_roam,
            text="Auto Loot Pickup (Tap drops after mob is defeated)",
            variable=self.auto_pickup_var,
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_color,
            selectcolor=self.card_inner,
        ).pack(anchor="w", padx=14, pady=(0, 12))

    # ---------------- TAB 5: SYSTEM & PRESETS ----------------
    def _build_tab_system(self) -> None:
        f = tk.Frame(self.tab_container, bg=self.bg_color)
        self.tab_frames["system"] = f

        card = self._create_card(f, "⚙️ Engine & Display Settings")
        card.pack(fill="x", pady=(0, 10))

        tk.Checkbutton(
            card,
            text="Show Live AFK Vision Preview Window (OpenCV with target lock & overlays)",
            variable=self.show_preview_var,
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_color,
            selectcolor=self.card_inner,
        ).pack(anchor="w", padx=14, pady=(10, 8))

        tk.Checkbutton(
            card,
            text="Prefer ADB Background Mode (Zero mouse takeover, emulator can stay minimized)",
            variable=self.prefer_adb_var,
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_color,
            selectcolor=self.card_inner,
        ).pack(anchor="w", padx=14, pady=(0, 14))

        # Preset management
        card_p = self._create_card(f, "💾 Settings Persistence")
        card_p.pack(fill="x")

        tk.Label(
            card_p,
            text="Your custom thresholds and configuration are automatically saved to training_settings.json when you launch or save. You can also reset to default recommended values anytime.",
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.fg_dim,
            wraplength=560,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(8, 12))

        btn_row = tk.Frame(card_p, bg=self.card_bg)
        btn_row.pack(fill="x", padx=14, pady=(0, 14))

        save_p_btn = tk.Button(
            btn_row,
            text="💾 Save Current Settings as Default",
            font=("Segoe UI", 9, "bold"),
            bg=self.card_inner,
            fg=self.accent_blue,
            activebackground=self.border_color,
            activeforeground=self.fg_color,
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._on_save_explicit,
        )
        save_p_btn.pack(side="left")

        load_p_btn = tk.Button(
            btn_row,
            text="📂 Load Saved Config",
            font=("Segoe UI", 9),
            bg=self.card_inner,
            fg=self.fg_color,
            activebackground=self.border_color,
            activeforeground=self.fg_color,
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._on_load_explicit,
        )
        load_p_btn.pack(side="left", padx=(10, 0))

        reset_btn = tk.Button(
            btn_row,
            text="🔄 Reset to Defaults",
            font=("Segoe UI", 9),
            bg=self.card_inner,
            fg=self.fg_dim,
            activebackground=self.border_color,
            activeforeground=self.fg_color,
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._on_reset_defaults,
        )
        reset_btn.pack(side="left", padx=10)

    def _create_card(self, parent: tk.Widget, title: str) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=self.card_bg,
            highlightbackground=self.border_color,
            highlightthickness=1,
        )
        hdr = tk.Label(
            card,
            text=title,
            font=("Segoe UI", 10, "bold"),
            bg=self.card_bg,
            fg=self.fg_color,
            padx=14,
            pady=6,
        )
        hdr.pack(anchor="w")
        return card

    # ---------------- EVENT HANDLERS ----------------
    def _on_profile_changed(self, event=None) -> None:
        idx = self.combobox.current()
        if 0 <= idx < len(self.profile_keys):
            prof = self.settings.profiles[self.profile_keys[idx]]
            if prof.combat_class:
                self.class_var.set(prof.combat_class.lower())
        self._refresh_info_card()

    def _on_class_changed(self) -> None:
        self._refresh_info_card()

    def _on_mode_changed(self) -> None:
        is_power = (self.training_mode_var.get() == "power")
        self.pt_enabled_var.set(is_power)
        self._refresh_info_card()

    def _on_pt_toggle(self) -> None:
        if self.pt_enabled_var.get():
            self.training_mode_var.set("power")
        else:
            self.training_mode_var.set("normal")
        self._refresh_info_card()

    def _on_rotation_changed(self, event=None) -> None:
        val_map = ["0", "30", "45", "60", "90", "120"]
        idx = self.rot_combo.current()
        if 0 <= idx < len(val_map):
            self.max_time_var.set(val_map[idx])

    def _on_streak_changed(self, event=None) -> None:
        idx = self.streak_combo.current()
        self.exhaust_streak_var.set(str(idx + 1))

    def _refresh_info_card(self) -> None:
        idx = self.combobox.current()
        if idx < 0 or idx >= len(self.profile_keys):
            return
        prof_key = self.profile_keys[idx]
        profile = self.settings.profiles[prof_key]
        c_class = self.class_var.get()
        is_pt = self.pt_enabled_var.get()

        self.info_target_lbl.config(
            text=f"Selected: {profile.target_name} ({prof_key})"
        )

        class_desc = ""
        if c_class == "melee":
            class_desc = "• Melee: Character walks directly adjacent via in-game pathfinding."
        elif c_class == "ranged":
            class_desc = "• Distance (Archer): Bot auto-approaches target until in range (<100px) then fires."
        elif c_class == "magic":
            class_desc = "• Magic (Mage): Bot auto-approaches target until in range (<100px) then casts."

        mode_desc = "• Mode: ⚡ Power Training (PT) active — special ability cast every cooldown." if is_pt else "• Mode: ⏱️ Normal AFK tick training with training weapon."
        self.info_mechanic_lbl.config(text=f"{class_desc}\n{mode_desc}")

    def _build_config(self) -> BotConfig:
        return BotConfig(
            prefer_adb=self.prefer_adb_var.get(),
            show_preview=self.show_preview_var.get(),
            enable_minimap_walk=self.minimap_walk_var.get(),
            auto_pickup_enabled=self.auto_pickup_var.get(),
            combat_class=self.class_var.get(),
            # Power Training
            power_training_enabled=self.pt_enabled_var.get(),
            special_skill_cooldown=round(self.pt_interval_var.get(), 2),
            special_skill_min_mp=round(self.pt_min_mp_var.get(), 2),
            max_mob_train_seconds=float(self.max_time_var.get()),
            # Auto Potions
            auto_potion_enabled=self.auto_potion_var.get(),
            hp_potion_threshold=round(self.hp_threshold_var.get(), 2),
            mp_potion_threshold=round(self.mp_threshold_var.get(), 2),
            potion_cooldown=round(self.potion_cd_var.get(), 2),
            pvp_mode=self.pvp_mode_var.get(),
            # Exhaustion
            immediate_exhausted_switch=self.exhaust_immediate_var.get(),
            exhausted_caption_confirm_seconds=round(self.exhaust_confirm_var.get(), 1),
            exhausted_travel_trigger_count=int(self.exhaust_streak_var.get()),
        )

    def _apply_settings_dict(self, cfg: dict) -> None:
        if not cfg:
            return

        # 1. Profile selection
        saved_prof = cfg.get("active_profile")
        if saved_prof and saved_prof in self.profile_keys:
            idx = self.profile_keys.index(saved_prof)
            self.selected_profile_idx.set(idx)
            if hasattr(self, "combobox"):
                self.combobox.current(idx)

        # 2. Combat class
        saved_class = cfg.get("combat_class")
        if saved_class and saved_class.lower() in {"melee", "ranged", "magic", "mage"}:
            c_val = "magic" if saved_class.lower() == "mage" else saved_class.lower()
            self.class_var.set(c_val)

        # 3. Training mode & PT
        if "training_mode" in cfg:
            self.training_mode_var.set(str(cfg["training_mode"]))
        if "power_training_enabled" in cfg:
            self.pt_enabled_var.set(bool(cfg["power_training_enabled"]))
        if "special_skill_cooldown" in cfg:
            self.pt_interval_var.set(float(cfg["special_skill_cooldown"]))
        if "special_skill_min_mp" in cfg:
            self.pt_min_mp_var.set(float(cfg["special_skill_min_mp"]))

        # 4. Mob rotation
        if "max_mob_train_seconds" in cfg:
            rot_val = str(int(float(cfg["max_mob_train_seconds"])))
            self.max_time_var.set(rot_val)
            val_map = ["0", "30", "45", "60", "90", "120"]
            rot_idx = val_map.index(rot_val) if rot_val in val_map else 0
            if hasattr(self, "rot_combo"):
                self.rot_combo.current(rot_idx)

        # 5. Potions
        if "auto_potion_enabled" in cfg:
            self.auto_potion_var.set(bool(cfg["auto_potion_enabled"]))
        if "hp_potion_threshold" in cfg:
            self.hp_threshold_var.set(float(cfg["hp_potion_threshold"]))
        if "mp_potion_threshold" in cfg:
            self.mp_threshold_var.set(float(cfg["mp_potion_threshold"]))
        if "potion_cooldown" in cfg:
            self.potion_cd_var.set(float(cfg["potion_cooldown"]))
        if "pvp_mode" in cfg:
            self.pvp_mode_var.set(bool(cfg["pvp_mode"]))

        # 6. Exhaustion
        if "immediate_exhausted_switch" in cfg:
            self.exhaust_immediate_var.set(bool(cfg["immediate_exhausted_switch"]))
        if "exhausted_caption_confirm_seconds" in cfg:
            self.exhaust_confirm_var.set(float(cfg["exhausted_caption_confirm_seconds"]))
        if "exhausted_travel_trigger_count" in cfg:
            streak_val = str(int(cfg["exhausted_travel_trigger_count"]))
            self.exhaust_streak_var.set(streak_val)
            s_idx = 1 if streak_val == "2" else (0 if streak_val == "1" else 2)
            if hasattr(self, "streak_combo"):
                self.streak_combo.current(s_idx)

        # 7. System toggles
        if "enable_minimap_walk" in cfg:
            self.minimap_walk_var.set(bool(cfg["enable_minimap_walk"]))
        if "auto_pickup_enabled" in cfg:
            self.auto_pickup_var.set(bool(cfg["auto_pickup_enabled"]))
        if "show_preview" in cfg:
            self.show_preview_var.set(bool(cfg["show_preview"]))
        if "prefer_adb" in cfg:
            self.prefer_adb_var.set(bool(cfg["prefer_adb"]))

        # Update dynamic labels if widgets are already created
        if hasattr(self, "hp_lbl"):
            self.hp_lbl.config(text=f"Health (HP) Threshold: {int(self.hp_threshold_var.get() * 100)}% (Tap HP Potion below this)")
        if hasattr(self, "mp_lbl"):
            self.mp_lbl.config(text=f"Mana (MP) Threshold: {int(self.mp_threshold_var.get() * 100)}% (Tap Mana Potion below this)")
        if hasattr(self, "p_cd_lbl"):
            self.p_cd_lbl.config(text=f"Potion Tap Cooldown: {self.potion_cd_var.get():.1f}s")
        if hasattr(self, "pt_cd_lbl"):
            self.pt_cd_lbl.config(text=f"Special Skill Interval: {self.pt_interval_var.get():.1f}s")
        if hasattr(self, "pt_mp_lbl"):
            self.pt_mp_lbl.config(text=f"Minimum Mana (MP) Required: {int(self.pt_min_mp_var.get() * 100)}%")
        if hasattr(self, "ex_lbl"):
            self.ex_lbl.config(text=f"Standard Caption Confirmation Delay: {self.exhaust_confirm_var.get():.0f}s")

        self._refresh_info_card()

    def _save_current_settings(self) -> bool:
        idx = self.combobox.current()
        active_prof = self.profile_keys[idx] if 0 <= idx < len(self.profile_keys) else "skeleton-lv75"
        payload = {
            "active_profile": active_prof,
            "combat_class": self.class_var.get(),
            "training_mode": self.training_mode_var.get(),
            "power_training_enabled": self.pt_enabled_var.get(),
            "special_skill_cooldown": round(self.pt_interval_var.get(), 2),
            "special_skill_min_mp": round(self.pt_min_mp_var.get(), 2),
            "max_mob_train_seconds": float(self.max_time_var.get()),
            "auto_potion_enabled": self.auto_potion_var.get(),
            "hp_potion_threshold": round(self.hp_threshold_var.get(), 2),
            "mp_potion_threshold": round(self.mp_threshold_var.get(), 2),
            "potion_cooldown": round(self.potion_cd_var.get(), 2),
            "pvp_mode": self.pvp_mode_var.get(),
            "immediate_exhausted_switch": self.exhaust_immediate_var.get(),
            "exhausted_caption_confirm_seconds": round(self.exhaust_confirm_var.get(), 1),
            "exhausted_travel_trigger_count": int(self.exhaust_streak_var.get()),
            "enable_minimap_walk": self.minimap_walk_var.get(),
            "auto_pickup_enabled": self.auto_pickup_var.get(),
            "show_preview": self.show_preview_var.get(),
            "prefer_adb": self.prefer_adb_var.get(),
        }
        return save_user_settings(payload)

    def _on_save_explicit(self) -> None:
        ok = self._save_current_settings()
        path_name = resolve_user_settings_path().name
        if ok:
            self.status_lbl.config(text=f"✓ Settings saved to {path_name}", fg=self.accent_blue)
        else:
            self.status_lbl.config(text=f"! Could not save settings to {path_name}", fg=self.accent_rose)

    def _on_load_explicit(self) -> None:
        cfg = load_user_settings()
        path_name = resolve_user_settings_path().name
        if cfg:
            self.saved_cfg = cfg
            self._apply_settings_dict(cfg)
            self.status_lbl.config(text=f"✓ Settings loaded from {path_name}", fg=self.accent_blue)
        else:
            self.status_lbl.config(text=f"! No saved settings found in {path_name}", fg=self.accent_amber)

    def _on_reset_defaults(self) -> None:
        defaults = {
            "training_mode": "normal",
            "max_mob_train_seconds": 0.0,
            "power_training_enabled": False,
            "special_skill_cooldown": 2.0,
            "special_skill_min_mp": 0.25,
            "auto_potion_enabled": True,
            "hp_potion_threshold": 0.70,
            "mp_potion_threshold": 0.50,
            "potion_cooldown": 0.8,
            "pvp_mode": False,
            "immediate_exhausted_switch": False,
            "exhausted_caption_confirm_seconds": 10.0,
            "exhausted_travel_trigger_count": 2,
            "enable_minimap_walk": True,
            "auto_pickup_enabled": True,
            "show_preview": False,
            "prefer_adb": True,
        }
        self._apply_settings_dict(defaults)
        self.status_lbl.config(text="✓ Reset to recommended training defaults", fg=self.accent_green)

    def _on_start(self) -> None:
        idx = self.combobox.current()
        if 0 <= idx < len(self.profile_keys):
            prof_key = self.profile_keys[idx]
            profile = self.settings.profiles[prof_key]
            chosen_class = self.class_var.get()
            config = self._build_config()
            self._save_current_settings()
            self.result = LaunchResult(profile, chosen_class, config)
        self.root.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.root.destroy()

    def show(self) -> Optional[LaunchResult]:
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.root.mainloop()
        return self.result


def launch_gui(settings: ProfileSettings) -> Optional[LaunchResult]:
    """Open the GUI launcher dashboard. Returns LaunchResult(profile, combat_class, config=...) or None."""
    dialog = LauncherDialog(settings)
    return dialog.show()
