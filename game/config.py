"""Paths and hot-reloadable JSON configuration."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME_DIR = ROOT / "game"
DATA_DIR = GAME_DIR / "data"
ASSETS_DIR = ROOT / "assets"
FRAMES_DIR = ASSETS_DIR / "frames" / "lina"
WARRIOR_FRAMES_DIR = ASSETS_DIR / "frames" / "warrior"
GENERATED_DIR = ASSETS_DIR / "generated"
CANONICAL_LINA_V1 = ROOT / "Image" / "Character" / "lina-seabright-v1-256.png"
CANONICAL_WARRIOR = ROOT / "Image" / "Enemy" / "warrior-336.png"
AXE_SPRITE_PATH = ASSETS_DIR / "sprites" / "axe" / "axe_throw.png"
CANONICAL_LINA_V2 = ROOT / "Image" / "Character" / "lina-seabright-v2-256.png"
BACKGROUND_PATH = ASSETS_DIR / "backgrounds" / "island-arena-16x9.png"

SCREEN_W = 1280
SCREEN_H = 720
FIXED_DT = 1.0 / 60.0

REQUIRED_STATS = ("lina", "warrior", "dummy", "combat")
REQUIRED_ATTACKS = ("punch_l", "punch_r", "kick_l", "kick_r", "q", "axe_slash", "dash", "axe_throw")
REQUIRED_CLIPS = (
    "idle", "walk", "jump", "crouch", "punch_l", "punch_r",
    "kick_l", "kick_r", "q", "transform", "hurt", "ko",
)
REQUIRED_FLAME_CLIPS = (
    "idle", "walk", "jump", "crouch", "punch_l", "punch_r", "kick_l", "kick_r", "q",
)
REQUIRED_WARRIOR_CLIPS = ("idle", "walk", "jump", "dash", "axe_throw", "axe_slash", "hurt", "ko")
REQUIRED_STAGE = (
    "ground_y", "walls", "lane_heights", "blocks",
    "player_spawn", "dummy_spawn", "warrior_spawn",
)


class JsonStore:
    """Loads the four data files. A failed reload keeps the last good data."""

    def __init__(self) -> None:
        self.stats: dict = {}
        self.attacks: dict = {}
        self.animations: dict = {}
        self.debug: dict = {}
        self.last_error: str | None = None
        self.last_ok = False
        self.reload()

    def reload(self) -> bool:
        try:
            stats = self._read("stats.json")
            attacks = self._read("attacks.json")
            animations = self._read("animations.json")
            debug = self._read("debug.json")
            self._validate(stats, attacks, animations, debug)
        except Exception as exc:  # noqa: BLE001 - surfaced in the debug panel
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.last_ok = False
            return False

        self.stats = stats
        self.attacks = attacks
        self.animations = animations
        self.debug = debug
        self.last_error = None
        self.last_ok = True
        return True

    def _read(self, name: str) -> dict:
        path = DATA_DIR / name
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _validate(stats: dict, attacks: dict, animations: dict, debug: dict) -> None:
        for key in REQUIRED_STATS:
            if key not in stats:
                raise ValueError(f"stats.json missing '{key}'")
        warrior = stats.get("warrior", {})
        for key in ("hp", "basic_atk", "extra_atk", "stage_body_width", "move", "hurtbox", "ai"):
            if key not in warrior:
                raise ValueError(f"stats.json warrior missing '{key}'")
        for key in (
            "attack_range", "attack_cooldown", "skill_gap", "dash_range", "dash_cooldown",
            "throw_min_range", "throw_range", "throw_cooldown",
        ):
            if key not in warrior.get("ai", {}):
                raise ValueError(f"stats.json warrior.ai missing '{key}'")
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
        stage = debug.get("stage", {})
        for key in REQUIRED_STAGE:
            if key not in stage:
                raise ValueError(f"debug.json stage missing '{key}'")
        for key, clip in clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(f"animations.json clip '{key}' frame/duration count mismatch")
