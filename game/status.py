"""Status effects, including the spec's poison stacking rules."""

from __future__ import annotations

from dataclasses import dataclass, field

CONTROL_EFFECTS = ("knockback", "knock_up", "freeze", "stun")
IMMUNE_EFFECTS = CONTROL_EFFECTS + ("slow",)
NEGATIVE_EFFECTS = (
    "burn", "poison", "slow", "freeze", "stun", "knock_up", "vulnerable",
)
ALL_EFFECTS = (
    "knockback", "burn", "poison", "slow", "knock_up",
    "freeze", "stun", "super_armor", "damage_reduction", "vulnerable",
    "sacred_shield", "purity_seal", "fury_unbound",
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
        if kind in NEGATIVE_EFFECTS and self.negative_immune():
            return
        if kind == "poison":
            self.add_poison(source or "unknown", duration, dps)
            return
        if kind in IMMUNE_EFFECTS and self.has("super_armor"):
            return
        # Burn and other timed effects refresh; damage reduction keeps its value.
        self.effects[kind] = Effect(duration, source, value, dps, total=duration)

    def add_poison(self, source: str, duration: float, dps: float) -> None:
        if self.negative_immune():
            return
        for poison in self.poisons:
            if poison.source == source:
                poison.remaining += duration
                poison.dps = dps
                return
        self.poisons.append(PoisonInstance(source, duration, dps))

    def extend_poison(self, source: str, duration: float) -> bool:
        """Extend an existing poison instance; never creates a new one."""
        if self.negative_immune():
            return False
        for poison in self.poisons:
            if poison.source == source:
                poison.remaining += duration
                return True
        return False

    def refresh_poison(self, source: str, duration: float, dps: float) -> bool:
        """Reset an existing poison's timer without extending it.

        Used by the Witch's poison zone: standing inside refreshes the
        remaining duration instead of stacking a second instance.
        """
        if self.negative_immune():
            return False
        for poison in self.poisons:
            if poison.source == source:
                poison.remaining = duration
                poison.dps = dps
                return True
        return False

    def add_vulnerable(
        self,
        step: float,
        duration: float,
        max_stacks: int = 3,
        source: str | None = None,
    ) -> None:
        """Add one vulnerability stack, capped, and refresh all stacks."""
        if self.negative_immune():
            return
        if step <= 0.0 or max_stacks <= 0:
            return
        current = self.effects.get("vulnerable")
        stacks = 0
        if current is not None and step > 0.0:
            stacks = int(round(current.value / step))
        stacks = min(max_stacks, stacks + 1)
        self.effects["vulnerable"] = Effect(
            duration, source, step * stacks, total=duration
        )

    def add_slow(
        self,
        value: float,
        duration: float,
        source: str | None = None,
    ) -> None:
        """Apply a slow multiplier, keeping the strongest one and refreshing."""
        if self.negative_immune():
            return
        if value >= 1.0:
            return
        if self.has("super_armor"):
            return
        current = self.effects.get("slow")
        if current is None or value < current.value:
            self.effects["slow"] = Effect(
                duration, source, value, total=duration
            )
        else:
            current.remaining = duration
            current.total = duration
            current.source = source

    def has(self, kind: str) -> bool:
        if kind == "poison":
            return bool(self.poisons)
        return kind in self.effects

    def has_poison_source(self, source: str | None = None) -> bool:
        """True if the target has any poison, or one from a specific source."""
        if source is None:
            return bool(self.poisons)
        return any(poison.source == source for poison in self.poisons)

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

    def negative_immune(self) -> bool:
        return self.has("purity_seal")

    def cleanse_negative(self) -> None:
        """Remove negative statuses and poisons, preserving buffs."""
        for kind in NEGATIVE_EFFECTS:
            self.effects.pop(kind, None)
        self.poisons.clear()

    def damage_dealt_multiplier(self) -> float:
        effect = self.effects.get("fury_unbound")
        return effect.value if effect is not None else 1.0

    def damage_reduction(self) -> float:
        effect = self.effects.get("damage_reduction")
        return effect.value if effect is not None else 0.0

    def vulnerable_amount(self) -> float:
        effect = self.effects.get("vulnerable")
        return effect.value if effect is not None else 0.0

    def slow_factor(self) -> float:
        if self.has("super_armor"):
            return 1.0
        effect = self.effects.get("slow")
        return effect.value if effect is not None else 1.0

    def describe(self) -> list[str]:
        lines: list[str] = []
        for kind, effect in sorted(self.effects.items()):
            if kind in ("damage_reduction", "vulnerable"):
                suffix = f" ({effect.value:.0%})"
            elif kind == "slow":
                suffix = f" ({1.0 - effect.value:.0%} slow)"
            else:
                suffix = ""
            lines.append(f"{kind}: {effect.remaining:.2f}s{suffix}")
        for poison in self.poisons:
            lines.append(f"poison[{poison.source}]: {poison.remaining:.2f}s")
        return lines
