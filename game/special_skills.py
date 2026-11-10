"""Shared, once-per-match special skills bound to keys 1-4.

The controller lives on the scene, not on a character: every playable
character early-returns from its own update during HURT/ATTACK/KO, so the
special keys are consumed in ``ArenaScene.tick`` before the player update.

The V5 sprite strips live under ``assets/frames/special_skills``. The
persistent strips loop while their status is active and follow the player.
"""

from __future__ import annotations

from .config import ASSETS_DIR
from .fx import SpriteStripFx

FULL_HP_MESSAGE = "You are at full HP. You do not need to heal."
MESSAGE_SECONDS = 1.5
FX_DIR = ASSETS_DIR / "frames" / "special_skills"
FRAME_PIVOT = (160.0, 278.0)
FRAME_COUNT = 6
# skill id -> (subdirectory, filename prefix, frame duration)
FX_SPECS = {
    "sacred_shield": ("sacred_shield", "sacred_shield_v4", 0.10),
    "purity_seal": ("purity_seal", "purity_seal_v4", 0.10),
    "fury_unbound": ("fury_unbound", "fury_unbound_v5", 0.08),
    "vitality_tonic": ("vitality_tonic", "vitality_tonic_v3", 0.10),
}


class SpecialSkills:
    def __init__(self, store) -> None:
        self.store = store
        self.used: set[str] = set()
        self.level = 1
        self.message = ""
        self.message_time = 0.0
        self.by_slot: dict[int, dict] = {}
        self.auras: dict[str, SpriteStripFx] = {}
        self.reset()

    def reset(self) -> None:
        self.used.clear()
        self.message = ""
        self.message_time = 0.0
        self.by_slot = self._read_definitions()
        self.auras.clear()

    def _read_definitions(self) -> dict[int, dict]:
        skills = self.store.special_skills.get("skills", [])
        definitions: dict[int, dict] = {}
        for skill in skills:
            if not isinstance(skill, dict):
                continue
            key = skill.get("key")
            if isinstance(key, int) and not isinstance(key, bool):
                definitions[key] = skill
        return definitions

    def _frames(self, skill_id: str) -> list:
        subdir, prefix, _duration = FX_SPECS[skill_id]
        folder = FX_DIR / subdir
        return [
            folder / f"{prefix}_{index:02d}.png"
            for index in range(FRAME_COUNT)
        ]

    def _durations(self, skill_id: str) -> list[float]:
        _subdir, _prefix, duration = FX_SPECS[skill_id]
        return [duration] * FRAME_COUNT

    def _start_aura(self, scene, skill_id: str) -> None:
        player = scene.player
        effect = SpriteStripFx(
            self._frames(skill_id),
            self._durations(skill_id),
            player.x,
            player.y,
            pivot=FRAME_PIVOT,
            loop=True,
            kind=f"special_aura_{skill_id}",
        )
        scene.fx_effects.append(effect)
        self.auras[skill_id] = effect

    def _spawn_tonic_fx(self, scene, skill_id: str) -> None:
        player = scene.player
        scene.fx_effects.append(
            SpriteStripFx(
                self._frames(skill_id),
                self._durations(skill_id),
                player.x,
                player.y,
                pivot=FRAME_PIVOT,
                loop=False,
                kind="special_tonic_cast",
            )
        )

    def _update_auras(self, scene) -> None:
        player = scene.player
        for skill_id, effect in list(self.auras.items()):
            if not player.statuses.has(skill_id):
                effect.alive = False
                del self.auras[skill_id]
            else:
                effect.x = player.x
                effect.y = player.y

    def _clear_auras(self) -> None:
        for effect in self.auras.values():
            effect.alive = False
        self.auras.clear()

    def update(self, dt: float, scene) -> None:
        if self.message_time > 0.0:
            self.message_time = max(0.0, self.message_time - dt)
        player = scene.player
        if player.hp <= 0.0 or scene.match_over is not None:
            self._clear_auras()
            return
        self._update_auras(scene)
        for slot in range(1, 5):
            action = f"special_{slot}"
            if not scene.input.buffer.has(action):
                continue
            scene.input.buffer.consume(action)
            self.try_use(slot, scene)

    def try_use(self, slot: int, scene) -> bool:
        skill = self.by_slot.get(slot)
        if skill is None:
            return False
        player = scene.player
        skill_id = skill["id"]
        if skill_id in self.used:
            return False
        if skill["type"] == "heal" and player.hp >= player.max_hp - 1e-6:
            self.message = FULL_HP_MESSAGE
            self.message_time = MESSAGE_SECONDS
            return False

        skill_type = skill["type"]
        if skill_type == "damage_immunity":
            player.statuses.add("sacred_shield", float(skill["duration"]))
            player.clear_hurt_visual()
            self._start_aura(scene, skill_id)
        elif skill_type == "cleanse_immunity":
            player.statuses.cleanse_negative()
            if hasattr(player, "eira_freeze"):
                player.eira_freeze = 0.0
            player.statuses.add("purity_seal", float(skill["duration"]))
            self._start_aura(scene, skill_id)
        elif skill_type == "damage_double":
            player.statuses.add(
                "fury_unbound",
                float(skill["duration"]),
                value=float(skill["damage_multiplier"]),
            )
            self._start_aura(scene, skill_id)
        elif skill_type == "heal":
            heal = (
                self.level * float(skill["heal_flat_per_level"])
                + float(skill["heal_max_hp_pct"]) * player.max_hp
            )
            player.hp = min(player.max_hp, player.hp + heal)
            self._spawn_tonic_fx(scene, skill_id)
        else:
            return False

        self.used.add(skill_id)
        self.message_time = 0.0
        return True
