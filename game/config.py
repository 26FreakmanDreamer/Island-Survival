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
BACKGROUND_PATH = ASSETS_DIR / "backgrounds" / "island-arena-16x9.png"

SCREEN_W = 1280
SCREEN_H = 720
FIXED_DT = 1.0 / 60.0

REQUIRED_STATS = ("lina", "warrior", "dummy", "nyra", "veno", "combat")
REQUIRED_ATTACKS = (
    "punch_l", "punch_r", "kick_l", "kick_r", "q", "axe_slash", "dash", "axe_throw",
    "nyra_slash", "nyra_thrust", "nyra_wave", "nyra_dash",
    "veno_bite", "veno_poison", "veno_web",
)
REQUIRED_CLIPS = (
    "idle", "walk", "jump", "crouch", "punch_l", "punch_r",
    "kick_l", "kick_r", "q", "transform", "hurt", "ko",
)
REQUIRED_FLAME_CLIPS = (
    "idle", "walk", "jump", "crouch", "punch_l", "punch_r", "kick_l", "kick_r", "q",
)
REQUIRED_WARRIOR_CLIPS = ("idle", "walk", "jump", "dash", "axe_throw", "axe_slash", "hurt", "ko")
REQUIRED_NYRA_CLIPS = (
    "idle", "walk", "jump", "crouch", "hurt", "ko",
    "nyra_slash", "nyra_thrust", "nyra_wave", "nyra_dash",
)
REQUIRED_VENO_CLIPS = (
    "idle", "walk", "hover", "jump", "hurt", "ko",
    "veno_bite", "veno_poison", "veno_web",
)
REQUIRED_STAGE = (
    "ground_y", "walls", "lane_heights", "blocks",
    "player_spawn", "dummy_spawn", "warrior_spawn", "veno_spawn",
)
ROSTER_CLASSES = ("lina", "warrior", "dummy", "nyra", "veno")
PLAYABLE_CLASSES = ("lina", "nyra")
ANIMATED_CLASSES = ("lina", "warrior", "nyra", "veno")
PROJECTILE_KINDS = ("q_wave", "axe", "sword_wave", "venom_glob", "web_bolt")


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
        veno_clips = animations.get("veno_clips", {})
        for key in REQUIRED_VENO_CLIPS:
            if key not in veno_clips:
                raise ValueError(f"animations.json missing veno clip '{key}'")
        for key, clip in veno_clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(f"animations.json veno clip '{key}' frame/duration count mismatch")
        for key in ("nyra_frame_size", "nyra_pivot", "veno_frame_size", "veno_pivot"):
            value = animations.get(key)
            if not (isinstance(value, list) and len(value) == 2):
                raise ValueError(f"animations.json missing or invalid '{key}'")
        stage = debug.get("stage", {})
        for key in REQUIRED_STAGE:
            if key not in stage:
                raise ValueError(f"debug.json stage missing '{key}'")
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
                if not spawn_key.endswith("_spawn") or spawn_key not in stage:
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
