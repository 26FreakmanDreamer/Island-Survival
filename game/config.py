"""Paths and hot-reloadable JSON configuration."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME_DIR = ROOT / "game"
DATA_DIR = GAME_DIR / "data"
ASSETS_DIR = ROOT / "assets"
GENERATED_DIR = ASSETS_DIR / "generated"
AXE_SPRITE_PATH = ASSETS_DIR / "sprites" / "axe" / "axe_throw.png"
STAGE_SPRITE_DIR = ASSETS_DIR / "sprites" / "stage"
BACKGROUND_PATH = ASSETS_DIR / "backgrounds" / "island-arena-16x9.png"

SCREEN_W = 1280
SCREEN_H = 720
FIXED_DT = 1.0 / 60.0

REQUIRED_STATS = ("lina", "warrior", "dummy", "nyra", "rhea", "veno", "bat", "creepy_shooter", "mech_crab", "shadow_ninja", "combat")
REQUIRED_ATTACKS = (
    "punch_l", "punch_r", "kick_l", "kick_r", "q", "axe_slash", "dash", "axe_throw",
    "nyra_slash", "nyra_thrust", "nyra_wave", "nyra_dash",
    "rhea_slash", "rhea_throw", "rhea_poison_throw", "rhea_dash", "rhea_dash_return",
    "veno_bite", "veno_poison", "veno_web", "bat_dive", "bat_sonic",
    "creepy_shot", "creepy_homing_shot", "creepy_roll_shot", "creepy_jump_shot",
    "mech_laser", "mech_charge", "mech_claw_slam", "mech_leap_slam",
    "shadow_kunai_slash", "shadow_kunai_throw", "shadow_dash",
    "shadow_phantom_form", "shadow_phantom_rend", "shadow_phantom_bind",
    "shadow_phantom_flash",
)
REQUIRED_CLIPS = (
    "idle", "walk", "jump", "crouch", "punch_l", "punch_r",
    "kick_l", "kick_r", "q", "transform", "hurt", "ko", "climb",
)
REQUIRED_FLAME_CLIPS = (
    "idle", "walk", "jump", "crouch", "punch_l", "punch_r", "kick_l", "kick_r", "q",
    "climb",
)
REQUIRED_WARRIOR_CLIPS = ("idle", "walk", "jump", "dash", "axe_throw", "axe_slash", "hurt", "ko")
REQUIRED_NYRA_CLIPS = (
    "idle", "walk", "jump", "crouch", "hurt", "ko",
    "nyra_slash", "nyra_thrust", "nyra_wave", "nyra_dash", "climb",
)
REQUIRED_RHEA_CLIPS = (
    "idle", "walk", "jump", "crouch", "hurt", "ko",
    "rhea_slash_r", "rhea_slash_l", "rhea_throw", "rhea_poison_throw",
    "rhea_dash", "rhea_dash_return", "climb",
)
REQUIRED_VENO_CLIPS = (
    "idle", "walk", "hover", "jump", "hurt", "ko",
    "veno_bite", "veno_poison", "veno_web",
)
REQUIRED_BAT_CLIPS = (
    "idle", "fly", "bat_dive", "bat_sonic", "hurt", "stun", "ko",
)
REQUIRED_CREEPY_SHOOTER_CLIPS = (
    "idle", "walk", "crouch", "jump", "hurt", "ko",
    "creepy_shot", "creepy_homing_shot", "creepy_roll_shot", "creepy_jump_shot",
)
REQUIRED_MECH_CRAB_CLIPS = (
    "idle", "walk", "jump", "hurt", "ko",
    "mech_laser", "mech_charge", "mech_claw_slam", "mech_leap_slam",
)
REQUIRED_SHADOW_NINJA_CLIPS = (
    "idle", "walk", "jump", "crouch", "hurt", "ko", "stun",
    "shadow_kunai_slash", "shadow_kunai_throw", "shadow_dash", "transform",
)
REQUIRED_SHADOW_NINJA_PHANTOM_CLIPS = (
    "idle", "walk", "shadow_phantom_rend", "shadow_phantom_bind",
    "phantom_vanish", "phantom_appear", "phantom_flash_attack",
    "phantom_pause", "phantom_shark_emerge", "phantom_shark_charge",
    "phantom_shark_recover", "revert",
)
REQUIRED_STAGE = (
    "ground_y", "walls", "lane_heights", "blocks", "ladders",
    "player_spawn", "dummy_spawn", "warrior_spawn", "veno_spawn", "bat_spawn",
)
ROSTER_CLASSES = ("lina", "warrior", "dummy", "nyra", "rhea", "veno", "bat", "creepy_shooter", "mech_crab", "shadow_ninja")
PLAYABLE_CLASSES = ("lina", "nyra", "rhea")
ANIMATED_CLASSES = ("lina", "warrior", "nyra", "rhea", "veno", "bat", "creepy_shooter", "mech_crab", "shadow_ninja")
PROJECTILE_KINDS = (
    "q_wave", "axe", "sword_wave", "venom_glob", "web_bolt", "sonic_wave",
    "rhea_shuriken", "rhea_poison_shuriken",
    "creepy_bullet", "creepy_homing_bullet", "creepy_down_bullet",
    "shadow_kunai", "shadow_phantom_bind", "shadow_phantom_flash",
)


class JsonStore:
    """Loads the five data files. A failed reload keeps the last good data."""

    def __init__(self) -> None:
        self.stats: dict = {}
        self.attacks: dict = {}
        self.animations: dict = {}
        self.debug: dict = {}
        self.roster: dict = {}
        self.last_error: str | None = None
        self.last_ok = False
        self.reload()

    def reload(self) -> bool:
        try:
            stats = self._read("stats.json")
            attacks = self._read("attacks.json")
            animations = self._read("animations.json")
            debug = self._read("debug.json")
            roster = self._read("roster.json")
            self._validate(stats, attacks, animations, debug, roster)
        except Exception as exc:  # noqa: BLE001 - surfaced in the debug panel
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.last_ok = False
            return False

        self.stats = stats
        self.attacks = attacks
        self.animations = animations
        self.debug = debug
        self.roster = roster
        self.last_error = None
        self.last_ok = True
        return True

    def _read(self, name: str) -> dict:
        path = DATA_DIR / name
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _validate(
        stats: dict,
        attacks: dict,
        animations: dict,
        debug: dict,
        roster: dict,
    ) -> None:
        for key in REQUIRED_STATS:
            if key not in stats:
                raise ValueError(f"stats.json missing '{key}'")
        combat = stats.get("combat", {})
        for key in (
            "hitstun", "hitstop", "knockback_decay", "burn_dps", "burn_duration",
            "poison_dps_pct", "input_buffer", "separation_speed", "knock_up_gravity",
        ):
            if key not in combat:
                raise ValueError(f"stats.json combat missing '{key}'")
        fx = combat.get("knock_up_fx")
        if not isinstance(fx, dict):
            raise ValueError("stats.json combat.knock_up_fx missing")
        for key in (
            "radius_x", "radius_y", "arms", "thickness", "spin",
            "color", "core_color", "alpha", "min_alpha", "min_scale",
        ):
            if key not in fx:
                raise ValueError(f"stats.json combat.knock_up_fx missing '{key}'")
        for key in ("color", "core_color"):
            value = fx.get(key)
            if not (isinstance(value, list) and len(value) == 3):
                raise ValueError(f"stats.json combat.knock_up_fx invalid '{key}'")
        lina = stats.get("lina", {})
        for key in ("hp", "basic_atk", "extra_atk", "move", "energy", "cooldowns",
                    "flame", "hurtbox"):
            if key not in lina:
                raise ValueError(f"stats.json lina missing '{key}'")
        for key in ("walk", "jump_v", "gravity"):
            if key not in lina.get("move", {}):
                raise ValueError(f"stats.json lina.move missing '{key}'")
        for key in ("max", "start", "regen", "gain"):
            if key not in lina.get("energy", {}):
                raise ValueError(f"stats.json lina.energy missing '{key}'")
        for key in ("q", "e"):
            if key not in lina.get("cooldowns", {}):
                raise ValueError(f"stats.json lina.cooldowns missing '{key}'")
        for key in ("duration", "bonus_step", "bonus_cap"):
            if key not in lina.get("flame", {}):
                raise ValueError(f"stats.json lina.flame missing '{key}'")
        for key in ("standing", "crouching"):
            if key not in lina.get("hurtbox", {}):
                raise ValueError(f"stats.json lina.hurtbox missing '{key}'")
        warrior = stats.get("warrior", {})
        for key in ("hp", "basic_atk", "extra_atk", "stage_body_width", "move", "hurtbox", "ai"):
            if key not in warrior:
                raise ValueError(f"stats.json warrior missing '{key}'")
        for key in ("walk", "jump_v", "gravity"):
            if key not in warrior.get("move", {}):
                raise ValueError(f"stats.json warrior.move missing '{key}'")
        for key in ("standing", "crouching"):
            if key not in warrior.get("hurtbox", {}):
                raise ValueError(f"stats.json warrior.hurtbox missing '{key}'")
        for key in (
            "attack_range", "attack_cooldown", "skill_gap", "dash_range", "dash_cooldown",
            "throw_min_range", "throw_range", "throw_cooldown",
        ):
            if key not in warrior.get("ai", {}):
                raise ValueError(f"stats.json warrior.ai missing '{key}'")
        nyra = stats.get("nyra", {})
        for key in (
            "hp", "basic_atk", "extra_atk", "stage_body_width", "move", "cooldowns", "hurtbox",
        ):
            if key not in nyra:
                raise ValueError(f"stats.json nyra missing '{key}'")
        for key in ("walk", "jump_v", "gravity"):
            if key not in nyra.get("move", {}):
                raise ValueError(f"stats.json nyra.move missing '{key}'")
        for key in ("q", "e"):
            if key not in nyra.get("cooldowns", {}):
                raise ValueError(f"stats.json nyra.cooldowns missing '{key}'")
        for key in ("standing", "crouching"):
            if key not in nyra.get("hurtbox", {}):
                raise ValueError(f"stats.json nyra.hurtbox missing '{key}'")
        rhea = stats.get("rhea", {})
        for key in (
            "hp", "basic_atk", "extra_atk", "stage_body_width", "move", "cooldowns", "hurtbox",
        ):
            if key not in rhea:
                raise ValueError(f"stats.json rhea missing '{key}'")
        for key in ("walk", "jump_v", "gravity"):
            if key not in rhea.get("move", {}):
                raise ValueError(f"stats.json rhea.move missing '{key}'")
        for key in ("q", "e"):
            if key not in rhea.get("cooldowns", {}):
                raise ValueError(f"stats.json rhea.cooldowns missing '{key}'")
        for key in ("standing", "crouching"):
            if key not in rhea.get("hurtbox", {}):
                raise ValueError(f"stats.json rhea.hurtbox missing '{key}'")
        veno = stats.get("veno", {})
        for key in (
            "hp", "basic_atk", "extra_atk", "stage_body_width", "move",
            "cooldowns", "hurtbox", "hover", "ai",
        ):
            if key not in veno:
                raise ValueError(f"stats.json veno missing '{key}'")
        for key in ("walk", "jump_v", "gravity"):
            if key not in veno.get("move", {}):
                raise ValueError(f"stats.json veno.move missing '{key}'")
        for key in ("bite", "poison", "web"):
            if key not in veno.get("cooldowns", {}):
                raise ValueError(f"stats.json veno.cooldowns missing '{key}'")
        for key in ("standing", "crouching"):
            if key not in veno.get("hurtbox", {}):
                raise ValueError(f"stats.json veno.hurtbox missing '{key}'")
        hover = veno.get("hover", {})
        for key in (
            "base", "min", "max", "vertical_speed", "descend_speed",
            "oscillation", "oscillation_rate",
        ):
            if key not in hover:
                raise ValueError(f"stats.json veno.hover missing '{key}'")
        if not (float(hover["min"]) <= float(hover["base"]) <= float(hover["max"])):
            raise ValueError("stats.json veno.hover must satisfy min <= base <= max")
        for key in (
            "bite_range", "close_range", "ranged_range",
            "decision_interval", "hover_min_time",
        ):
            if key not in veno.get("ai", {}):
                raise ValueError(f"stats.json veno.ai missing '{key}'")
        bat = stats.get("bat", {})
        for key in (
            "hp", "basic_atk", "extra_atk", "stage_body_width", "move",
            "cooldowns", "hurtbox", "flight", "ai",
        ):
            if key not in bat:
                raise ValueError(f"stats.json bat missing '{key}'")
        for key in ("walk", "jump_v", "gravity"):
            if key not in bat.get("move", {}):
                raise ValueError(f"stats.json bat.move missing '{key}'")
        for key in ("dive", "sonic"):
            if key not in bat.get("cooldowns", {}):
                raise ValueError(f"stats.json bat.cooldowns missing '{key}'")
        for key in ("standing", "crouching"):
            if key not in bat.get("hurtbox", {}):
                raise ValueError(f"stats.json bat.hurtbox missing '{key}'")
        flight = bat.get("flight", {})
        for key in (
            "min_height", "max_height", "preferred_height",
            "vertical_speed", "bob", "bob_rate",
        ):
            if key not in flight:
                raise ValueError(f"stats.json bat.flight missing '{key}'")
        if not (
            float(flight["min_height"])
            <= float(flight["preferred_height"])
            <= float(flight["max_height"])
        ):
            raise ValueError(
                "stats.json bat.flight must satisfy min_height <= preferred_height <= max_height"
            )
        for key in (
            "dive_range", "sonic_min_range", "sonic_range",
            "standoff", "decision_interval",
        ):
            if key not in bat.get("ai", {}):
                raise ValueError(f"stats.json bat.ai missing '{key}'")
        creepy = stats.get("creepy_shooter", {})
        for key in (
            "hp", "basic_atk", "extra_atk", "stage_body_width", "move",
            "cooldowns", "hurtbox", "ai",
        ):
            if key not in creepy:
                raise ValueError(f"stats.json creepy_shooter missing '{key}'")
        for key in ("walk", "jump_v", "gravity"):
            if key not in creepy.get("move", {}):
                raise ValueError(f"stats.json creepy_shooter.move missing '{key}'")
        for key in ("shot", "homing", "roll", "jump"):
            if key not in creepy.get("cooldowns", {}):
                raise ValueError(f"stats.json creepy_shooter.cooldowns missing '{key}'")
        for key in ("standing", "crouching"):
            if key not in creepy.get("hurtbox", {}):
                raise ValueError(f"stats.json creepy_shooter.hurtbox missing '{key}'")
        for key in (
            "near_range", "far_range", "level_tolerance", "decision_interval",
            "roll_distance", "roll_time", "platform_reach", "jump_heights",
        ):
            if key not in creepy.get("ai", {}):
                raise ValueError(f"stats.json creepy_shooter.ai missing '{key}'")
        mech = stats.get("mech_crab", {})
        for key in (
            "hp", "basic_atk", "extra_atk", "stage_body_width", "move",
            "cooldowns", "hurtbox", "ai",
        ):
            if key not in mech:
                raise ValueError(f"stats.json mech_crab missing '{key}'")
        for key in ("walk", "jump_v", "gravity"):
            if key not in mech.get("move", {}):
                raise ValueError(f"stats.json mech_crab.move missing '{key}'")
        for key in ("laser", "charge", "claw", "leap"):
            if key not in mech.get("cooldowns", {}):
                raise ValueError(f"stats.json mech_crab.cooldowns missing '{key}'")
        for key in ("standing", "crouching"):
            if key not in mech.get("hurtbox", {}):
                raise ValueError(f"stats.json mech_crab.hurtbox missing '{key}'")
        for key in (
            "laser_min_range", "laser_range", "charge_min_range", "charge_range",
            "claw_range", "leap_min_range", "leap_range", "level_tolerance",
            "decision_interval", "skill_gap",
        ):
            if key not in mech.get("ai", {}):
                raise ValueError(f"stats.json mech_crab.ai missing '{key}'")
        shadow = stats.get("shadow_ninja", {})
        for key in (
            "hp", "basic_atk", "extra_atk", "stage_body_width", "move",
            "cooldowns", "hurtbox", "ai",
        ):
            if key not in shadow:
                raise ValueError(f"stats.json shadow_ninja missing '{key}'")
        for key in ("walk", "jump_v", "gravity"):
            if key not in shadow.get("move", {}):
                raise ValueError(f"stats.json shadow_ninja.move missing '{key}'")
        for key in ("slash", "throw", "dash", "phantom_form"):
            if key not in shadow.get("cooldowns", {}):
                raise ValueError(f"stats.json shadow_ninja.cooldowns missing '{key}'")
        for key in ("standing", "crouching"):
            if key not in shadow.get("hurtbox", {}):
                raise ValueError(f"stats.json shadow_ninja.hurtbox missing '{key}'")
        for key in (
            "close_range", "far_range", "level_tolerance", "decision_interval",
            "low_hp_pct", "kunai_close_distance", "skill_gap", "opening_delay",
            "jump_cooldown", "crouch_hold", "barrier_hop_range", "threat_range",
        ):
            if key not in shadow.get("ai", {}):
                raise ValueError(f"stats.json shadow_ninja.ai missing '{key}'")
        for key in (
            "damage_threshold_pct", "claw_range", "bind_range", "flash_range",
            "behind_offset", "appear_min_wall_margin", "shadow_max_range",
            "shadow_speed", "shark_charge_distance", "shark_charge_speed",
        ):
            if key not in shadow.get("phantom", {}):
                raise ValueError(f"stats.json shadow_ninja.phantom missing '{key}'")
        dummy = stats.get("dummy", {})
        for key in ("hp", "invincible", "hurtbox", "move"):
            if key not in dummy:
                raise ValueError(f"stats.json dummy missing '{key}'")
        if "gravity" not in dummy.get("move", {}):
            raise ValueError("stats.json dummy.move.gravity missing")
        for key in REQUIRED_ATTACKS:
            if key not in attacks:
                raise ValueError(f"attacks.json missing '{key}'")
        clips = animations.get("clips", {})
        for key in REQUIRED_CLIPS:
            if key not in clips:
                raise ValueError(f"animations.json missing clip '{key}'")
        flame_clips = animations.get("flame_clips", {})
        for key in REQUIRED_FLAME_CLIPS:
            if key not in flame_clips:
                raise ValueError(f"animations.json missing flame clip '{key}'")
        for key, clip in flame_clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(f"animations.json flame clip '{key}' frame/duration count mismatch")
        warrior_clips = animations.get("warrior_clips", {})
        for key in REQUIRED_WARRIOR_CLIPS:
            if key not in warrior_clips:
                raise ValueError(f"animations.json missing warrior clip '{key}'")
        for key, clip in warrior_clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(f"animations.json warrior clip '{key}' frame/duration count mismatch")
        for key in ("warrior_frame_size", "warrior_pivot"):
            value = animations.get(key)
            if not (isinstance(value, list) and len(value) == 2):
                raise ValueError(f"animations.json missing or invalid '{key}'")
        nyra_clips = animations.get("nyra_clips", {})
        for key in REQUIRED_NYRA_CLIPS:
            if key not in nyra_clips:
                raise ValueError(f"animations.json missing nyra clip '{key}'")
        for key, clip in nyra_clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(f"animations.json nyra clip '{key}' frame/duration count mismatch")
        rhea_clips = animations.get("rhea_clips", {})
        for key in REQUIRED_RHEA_CLIPS:
            if key not in rhea_clips:
                raise ValueError(f"animations.json missing rhea clip '{key}'")
        for key, clip in rhea_clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(f"animations.json rhea clip '{key}' frame/duration count mismatch")
        veno_clips = animations.get("veno_clips", {})
        for key in REQUIRED_VENO_CLIPS:
            if key not in veno_clips:
                raise ValueError(f"animations.json missing veno clip '{key}'")
        for key, clip in veno_clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(f"animations.json veno clip '{key}' frame/duration count mismatch")
        bat_clips = animations.get("bat_clips", {})
        for key in REQUIRED_BAT_CLIPS:
            if key not in bat_clips:
                raise ValueError(f"animations.json missing bat clip '{key}'")
        for key, clip in bat_clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(f"animations.json bat clip '{key}' frame/duration count mismatch")
        creepy_clips = animations.get("creepy_shooter_clips", {})
        for key in REQUIRED_CREEPY_SHOOTER_CLIPS:
            if key not in creepy_clips:
                raise ValueError(f"animations.json missing creepy_shooter clip '{key}'")
        for key, clip in creepy_clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(
                    f"animations.json creepy_shooter clip '{key}' frame/duration count mismatch"
                )
        mech_clips = animations.get("mech_crab_clips", {})
        for key in REQUIRED_MECH_CRAB_CLIPS:
            if key not in mech_clips:
                raise ValueError(f"animations.json missing mech_crab clip '{key}'")
        for key, clip in mech_clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(
                    f"animations.json mech_crab clip '{key}' frame/duration count mismatch"
                )
        for key in ("mech_laser", "mech_charge", "mech_claw_slam", "mech_leap_slam"):
            attack = attacks.get(key, {})
            total = sum(float(value) for value in mech_clips[key].get("durations", []))
            if abs(total - float(attack.get("duration", total))) > 1e-3:
                raise ValueError(
                    f"animations.json mech_crab clip '{key}' duration {total:.3f} "
                    f"does not match attacks.json duration {attack.get('duration')}"
                )
            phases = sum(
                float(attack.get(phase, 0.0)) for phase in ("warning", "active", "recovery")
            )
            if abs(phases - float(attack.get("duration", phases))) > 1e-6:
                raise ValueError(
                    f"attacks.json '{key}' warning+active+recovery must equal duration"
                )
        shadow_clips = animations.get("shadow_ninja_clips", {})
        for key in REQUIRED_SHADOW_NINJA_CLIPS:
            if key not in shadow_clips:
                raise ValueError(f"animations.json missing shadow_ninja clip '{key}'")
        for key, clip in shadow_clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(
                    f"animations.json shadow_ninja clip '{key}' frame/duration count mismatch"
                )
        for key in ("shadow_kunai_slash", "shadow_kunai_throw", "shadow_dash"):
            attack = attacks.get(key, {})
            total = sum(
                float(value) for value in shadow_clips[key].get("durations", [])
            )
            if abs(total - float(attack.get("duration", total))) > 1e-3:
                raise ValueError(
                    f"animations.json shadow_ninja clip '{key}' duration {total:.3f} "
                    f"does not match attacks.json duration {attack.get('duration')}"
                )
        transform_total = sum(
            float(value) for value in shadow_clips["transform"].get("durations", [])
        )
        transform_attack = attacks.get("shadow_phantom_form", {})
        if abs(
            transform_total - float(transform_attack.get("duration", transform_total))
        ) > 1e-3:
            raise ValueError(
                f"animations.json shadow_ninja transform duration {transform_total:.3f} "
                "does not match attacks.json shadow_phantom_form duration"
            )
        phantom_clips = animations.get("shadow_ninja_phantom_clips", {})
        for key in REQUIRED_SHADOW_NINJA_PHANTOM_CLIPS:
            if key not in phantom_clips:
                raise ValueError(
                    f"animations.json missing shadow_ninja_phantom clip '{key}'"
                )
        for key, clip in phantom_clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(
                    f"animations.json shadow_ninja_phantom clip '{key}' "
                    "frame/duration count mismatch"
                )
        for clip_key, attack_key in (
            ("shadow_phantom_rend", "shadow_phantom_rend"),
            ("shadow_phantom_bind", "shadow_phantom_bind"),
        ):
            attack = attacks.get(attack_key, {})
            total = sum(
                float(value)
                for value in phantom_clips[clip_key].get("durations", [])
            )
            if abs(total - float(attack.get("duration", total))) > 1e-3:
                raise ValueError(
                    f"animations.json shadow_ninja_phantom clip '{clip_key}' "
                    f"duration {total:.3f} does not match attacks.json duration "
                    f"{attack.get('duration')}"
                )
        flash_total = (
            sum(float(v) for v in phantom_clips["phantom_vanish"]["durations"]) * 2.0
            + sum(float(v) for v in phantom_clips["phantom_appear"]["durations"]) * 2.0
            + sum(float(v) for v in phantom_clips["phantom_flash_attack"]["durations"])
            + sum(float(v) for v in phantom_clips["phantom_pause"]["durations"])
            + sum(float(v) for v in phantom_clips["phantom_shark_emerge"]["durations"])
            + sum(float(v) for v in phantom_clips["phantom_shark_charge"]["durations"])
            + sum(float(v) for v in phantom_clips["phantom_shark_recover"]["durations"])
            + 0.01  # hidden gap while the shadow bolt travels
        )
        flash_attack = attacks.get("shadow_phantom_flash", {})
        if abs(flash_total - float(flash_attack.get("duration", flash_total))) > 1e-3:
            raise ValueError(
                f"shadow_ninja_phantom flash phases total {flash_total:.3f} "
                "does not match attacks.json shadow_phantom_flash duration"
            )
        for key in (
            "nyra_frame_size", "nyra_pivot", "rhea_frame_size", "rhea_pivot",
            "veno_frame_size", "veno_pivot",
            "bat_frame_size", "bat_pivot",
            "creepy_shooter_frame_size", "creepy_shooter_pivot",
            "mech_crab_frame_size", "mech_crab_pivot",
            "shadow_ninja_frame_size", "shadow_ninja_pivot",
        ):
            value = animations.get(key)
            if not (isinstance(value, list) and len(value) == 2):
                raise ValueError(f"animations.json missing or invalid '{key}'")
        stage = debug.get("stage", {})
        for key in REQUIRED_STAGE:
            if key not in stage:
                raise ValueError(f"debug.json stage missing '{key}'")
        JsonStore._validate_stage(stage)
        variants = debug.get("stage_variants", {})
        if not isinstance(variants, dict):
            raise ValueError("debug.json stage_variants must be an object")
        for name, variant in variants.items():
            if not isinstance(variant, dict):
                raise ValueError(f"debug.json stage_variants '{name}' must be an object")
            for key in REQUIRED_STAGE:
                if key not in variant:
                    raise ValueError(f"debug.json stage_variants '{name}' missing '{key}'")
            JsonStore._validate_stage(variant)
        for key, clip in clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(f"animations.json clip '{key}' frame/duration count mismatch")
        for key in REQUIRED_ATTACKS:
            attack = attacks[key]
            if not any(field in attack for field in ("basic_mult", "extra_mult", "damage_mult")):
                raise ValueError(f"attacks.json '{key}' missing damage multipliers")
            for event in attack.get("events", []):
                if event.get("type") == "projectile":
                    kind = event.get("projectile")
                    if kind not in PROJECTILE_KINDS:
                        raise ValueError(
                            f"attacks.json '{key}' projectile event needs projectile in "
                            f"{PROJECTILE_KINDS}"
                        )
                if (
                    float(event.get("bonus_vs_poison_max_hp_pct", 0.0)) > 0.0
                    and not event.get("bonus_vs_poison_source")
                ):
                    raise ValueError(
                        f"attacks.json '{key}' poison max-HP bonus needs "
                        "bonus_vs_poison_source"
                    )

        characters = roster.get("characters", {})
        enemies = roster.get("enemies", {})
        if not characters:
            raise ValueError("roster.json has no characters")
        if not enemies:
            raise ValueError("roster.json has no enemies")
        for section, entries in (("character", characters), ("enemy", enemies)):
            for key, entry in entries.items():
                for field in ("name", "class", "stats", "spawn"):
                    if field not in entry:
                        raise ValueError(f"roster.json {section} '{key}' missing '{field}'")
                if entry["class"] not in ROSTER_CLASSES:
                    raise ValueError(
                        f"roster.json {section} '{key}' has unknown class '{entry['class']}'"
                    )
                if section == "character" and entry["class"] not in PLAYABLE_CLASSES:
                    raise ValueError(
                        f"roster.json character '{key}' class '{entry['class']}' is not playable"
                    )
                if entry["stats"] not in stats:
                    raise ValueError(f"roster.json {section} '{key}' stats '{entry['stats']}' missing")
                spawn_key = entry["spawn"]
                entry_stage = stage
                variant_name = entry.get("stage_variant")
                if variant_name is not None:
                    if variant_name not in variants:
                        raise ValueError(
                            f"roster.json {section} '{key}' unknown stage_variant "
                            f"'{variant_name}'"
                        )
                    entry_stage = variants[variant_name]
                if not spawn_key.endswith("_spawn") or spawn_key not in entry_stage:
                    raise ValueError(
                        f"roster.json {section} '{key}' invalid spawn '{spawn_key}'"
                    )
                clips_key = entry.get("clips")
                if clips_key is None and entry["class"] in ANIMATED_CLASSES:
                    raise ValueError(
                        f"roster.json {section} '{key}' needs a clips table"
                    )
                if clips_key is not None:
                    if clips_key not in animations:
                        raise ValueError(
                            f"roster.json {section} '{key}' clips '{clips_key}' missing"
                        )
                    for field in ("frame_size", "pivot", "frames_dir", "fallback"):
                        if field not in entry:
                            raise ValueError(
                                f"roster.json {section} '{key}' missing '{field}'"
                            )
                    for field in ("frame_size", "pivot"):
                        value = animations.get(entry[field])
                        if not (isinstance(value, list) and len(value) == 2):
                            raise ValueError(
                                f"roster.json {section} '{key}' invalid animation key '{entry[field]}'"
                            )
                for field in ("flame_clips", "flame_offsets"):
                    ref = entry.get(field)
                    if ref is not None and ref not in animations:
                        raise ValueError(
                            f"roster.json {section} '{key}' {field} '{ref}' missing"
                        )
        for key, entry in enemies.items():
            slots = entry.get("skill_slots", [])
            if not isinstance(slots, list) or len(slots) != 4:
                raise ValueError(f"roster.json enemy '{key}' skill_slots must have 4 entries")
            for slot in slots:
                if slot is not None and slot not in attacks:
                    raise ValueError(f"roster.json enemy '{key}' unknown skill '{slot}'")
        defaults = debug.get("roster", {})
        if defaults.get("default_character") not in characters:
            raise ValueError("debug.json roster.default_character missing from roster.json")
        if defaults.get("default_enemy") not in enemies:
            raise ValueError("debug.json roster.default_enemy missing from roster.json")

    @staticmethod
    def _validate_stage(stage: dict) -> None:
        """Validate the block/ladder shape introduced by the scene pass."""

        def is_number(value) -> bool:
            return isinstance(value, (int, float)) and not isinstance(value, bool)

        def is_rect(value) -> bool:
            return (
                isinstance(value, (list, tuple))
                and len(value) == 4
                and all(is_number(item) for item in value)
            )

        blocks = stage.get("blocks")
        if not isinstance(blocks, list):
            raise ValueError("debug.json stage.blocks must be a list")
        for index, entry in enumerate(blocks):
            if isinstance(entry, (list, tuple)):
                kind = "barrier"
                rect = entry
            elif isinstance(entry, dict):
                kind = entry.get("kind", "barrier")
                rect = entry.get("rect")
            else:
                raise ValueError(
                    f"debug.json stage.blocks[{index}] must be an object or rect list"
                )
            if kind not in ("barrier", "platform"):
                raise ValueError(
                    f"debug.json stage.blocks[{index}] has invalid kind '{kind}'"
                )
            if not is_rect(rect):
                raise ValueError(
                    f"debug.json stage.blocks[{index}] rect must have 4 numbers"
                )
            if isinstance(entry, dict) and "sprite_rect" in entry:
                if not is_rect(entry["sprite_rect"]):
                    raise ValueError(
                        f"debug.json stage.blocks[{index}] sprite_rect must have 4 numbers"
                    )
            if kind == "platform":
                if not isinstance(entry, dict):
                    raise ValueError(
                        f"debug.json stage.blocks[{index}] platform needs an object"
                    )
                for field in ("sprite", "sprite_rect"):
                    if field not in entry:
                        raise ValueError(
                            f"debug.json stage.blocks[{index}] platform missing '{field}'"
                        )
                if not isinstance(entry["sprite"], str):
                    raise ValueError(
                        f"debug.json stage.blocks[{index}] sprite must be a string"
                    )
                if "surface_y" in entry and not is_number(entry["surface_y"]):
                    raise ValueError(
                        f"debug.json stage.blocks[{index}] surface_y must be a number"
                    )
        ladders = stage.get("ladders")
        if not isinstance(ladders, list):
            raise ValueError("debug.json stage.ladders must be a list")
        for index, entry in enumerate(ladders):
            if not isinstance(entry, dict):
                raise ValueError(
                    f"debug.json stage.ladders[{index}] must be an object"
                )
            for field in ("rect", "top_y", "bottom_y", "sprite", "sprite_rect"):
                if field not in entry:
                    raise ValueError(
                        f"debug.json stage.ladders[{index}] missing '{field}'"
                    )
            for field in ("rect", "sprite_rect"):
                if not is_rect(entry[field]):
                    raise ValueError(
                        f"debug.json stage.ladders[{index}] {field} must have 4 numbers"
                    )
            if not isinstance(entry["sprite"], str):
                raise ValueError(
                    f"debug.json stage.ladders[{index}] sprite must be a string"
                )
            if not (is_number(entry["top_y"]) and is_number(entry["bottom_y"])):
                raise ValueError(
                    f"debug.json stage.ladders[{index}] top_y/bottom_y must be numbers"
                )
            if float(entry["top_y"]) >= float(entry["bottom_y"]):
                raise ValueError(
                    f"debug.json stage.ladders[{index}] top_y must be above bottom_y"
                )
