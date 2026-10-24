"""Status effects, including the spec's poison stacking rules."""

from __future__ import annotations

from dataclasses import dataclass, field

CONTROL_EFFECTS = ("knockback", "knock_up", "freeze", "stun")
IMMUNE_EFFECTS = CONTROL_EFFECTS + ("slow",)
ALL_EFFECTS = (
    "knockback", "burn", "poison", "slow", "knock_up",
    "freeze", "stun", "super_armor", "damage_reduction",
)
TICK = 0.2
POISON_TICK = 0.5


@dataclass
class Effect:
    remaining: float
    source: str | None = None
    value: float = 0.0
    dps: float = 0.0
    tick_accum: float = 0.0
    total: float = 0.0


@dataclass
class PoisonInstance:
    source: str
    remaining: float
    dps: float
    tick_accum: float = 0.0


@dataclass
class StatusSet:
    effects: dict[str, Effect] = field(default_factory=dict)
    poisons: list[PoisonInstance] = field(default_factory=list)

    def add(
        self,
        kind: str,
        duration: float,
        source: str | None = None,
        value: float = 0.0,
        dps: float = 0.0,
    ) -> None:
        if kind == "poison":
            self.add_poison(source or "unknown", duration, dps)
            return
        if kind in IMMUNE_EFFECTS and self.has("super_armor"):
            return
        # Burn and other timed effects refresh; damage reduction keeps its value.
        self.effects[kind] = Effect(duration, source, value, dps, total=duration)

    def add_poison(self, source: str, duration: float, dps: float) -> None:
        for poison in self.poisons:
            if poison.source == source:
                poison.remaining += duration
                poison.dps = dps
                return
        self.poisons.append(PoisonInstance(source, duration, dps))

    def has(self, kind: str) -> bool:
        if kind == "poison":
            return bool(self.poisons)
        return kind in self.effects

    def get(self, kind: str) -> Effect | None:
        return self.effects.get(kind)

    def remove(self, kind: str) -> None:
        self.effects.pop(kind, None)
        if kind == "poison":
            self.poisons.clear()

    def clear(self) -> None:
        self.effects.clear()
        self.poisons.clear()

    def update(self, dt: float, target) -> None:
        for kind in list(self.effects):
            effect = self.effects[kind]
            effect.remaining -= dt
            if effect.remaining <= 0.0:
                del self.effects[kind]

        burn = self.effects.get("burn")
        if burn is not None:
            burn.tick_accum += dt
            while burn.tick_accum >= TICK:
                burn.tick_accum -= TICK
                target.apply_dot(burn.dps * TICK)

        # Poison settles in 0.5s chunks. Damage is applied before the
        # remaining-time decrement so a 3.0s poison still gets its sixth
        # full tick on the expiry frame.
        for poison in self.poisons:
            poison.tick_accum += dt
            while poison.tick_accum + 1e-9 >= POISON_TICK:
                poison.tick_accum -= POISON_TICK
                target.apply_dot(poison.dps * POISON_TICK)
            poison.remaining -= dt
        self.poisons = [
            poison for poison in self.poisons if poison.remaining > 0.0
        ]

    def control_locked(self) -> bool:
        if self.has("super_armor"):
            return False
        return any(self.has(kind) for kind in CONTROL_EFFECTS)

    def damage_reduction(self) -> float:
        effect = self.effects.get("damage_reduction")
        return effect.value if effect is not None else 0.0

    def slow_factor(self) -> float:
        if self.has("super_armor"):
            return 1.0
        effect = self.effects.get("slow")
        return effect.value if effect is not None else 1.0

    def describe(self) -> list[str]:
        lines: list[str] = []
        for kind, effect in sorted(self.effects.items()):
            suffix = f" ({effect.value:.0%})" if kind == "damage_reduction" else ""
            lines.append(f"{kind}: {effect.remaining:.2f}s{suffix}")
        for poison in self.poisons:
            lines.append(f"poison[{poison.source}]: {poison.remaining:.2f}s")
        return lines
