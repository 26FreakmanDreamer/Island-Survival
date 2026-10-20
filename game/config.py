"""Paths and hot-reloadable JSON configuration."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME_DIR = ROOT / "game"
DATA_DIR = GAME_DIR / "data"
ASSETS_DIR = ROOT / "assets"
FRAMES_DIR = ASSETS_DIR / "frames" / "lina"
GENERATED_DIR = ASSETS_DIR / "generated"
CANONICAL_LINA_V1 = ROOT / "Image" / "Character" / "lina-seabright-v1-256.png"
CANONICAL_LINA_V2 = ROOT / "Image" / "Character" / "lina-seabright-v2-256.png"
BACKGROUND_PATH = ASSETS_DIR / "backgrounds" / "island-arena-16x9.png"

SCREEN_W = 1280
SCREEN_H = 720
FIXED_DT = 1.0 / 60.0

REQUIRED_STATS = ("lina", "dummy", "combat")
REQUIRED_ATTACKS = ("punch_l", "punch_r", "kick_l", "kick_r", "q")
REQUIRED_CLIPS = (
    "idle", "walk", "jump", "crouch", "punch_l", "punch_r",
    "kick_l", "kick_r", "q", "transform", "hurt", "ko",
)
REQUIRED_FLAME_CLIPS = (
    "idle", "walk", "jump", "crouch", "punch_l", "punch_r", "kick_l", "kick_r", "q",
)
REQUIRED_STAGE = ("ground_y", "walls", "lane_heights", "blocks", "player_spawn", "dummy_spawn")


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
        stage = debug.get("stage", {})
        for key in REQUIRED_STAGE:
            if key not in stage:
                raise ValueError(f"debug.json stage missing '{key}'")
        for key, clip in clips.items():
            if len(clip.get("frames", [])) != len(clip.get("durations", [])):
                raise ValueError(f"animations.json clip '{key}' frame/duration count mismatch")
