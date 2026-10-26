"""Data-driven fighter construction from roster.json."""

from __future__ import annotations

from .animation import AnimationPlayer
from .bat import Bat
from .config import ASSETS_DIR, ROOT
from .dummy import Dummy
from .lina import Lina
from .nyra import Nyra
from .veno import Veno
from .warrior import Warrior

FIGHTER_CLASSES = {
    "lina": Lina,
    "warrior": Warrior,
    "dummy": Dummy,
    "nyra": Nyra,
    "veno": Veno,
    "bat": Bat,
}


def build_animation(store, entry: dict) -> AnimationPlayer | None:
    """Build a fighter's animation player from its roster entry.

    Entries without a ``clips`` key (the training dummy) have no sprite
    animation and return ``None``.
    """
    clips_key = entry.get("clips")
    if not clips_key:
        return None

    animations = store.animations
    flame_clips_key = entry.get("flame_clips")
    flame_offsets_key = entry.get("flame_offsets")
    return AnimationPlayer(
        animations[clips_key],
        animations.get(flame_clips_key, {}) if flame_clips_key else {},
        ASSETS_DIR / "frames" / entry["frames_dir"],
        ROOT / entry["fallback"],
        tuple(animations[entry["pivot"]]),
        frame_size=tuple(animations[entry["frame_size"]]),
        frame_offsets=animations.get(flame_offsets_key, {}) if flame_offsets_key else None,
    )


def create_fighter(entry: dict, store, stage):
    """Create the fighter class named by the roster entry."""
    fighter_class = FIGHTER_CLASSES[entry["class"]]
    return fighter_class(store, stage, entry, build_animation(store, entry))
