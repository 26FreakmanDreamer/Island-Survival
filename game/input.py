"""Keyboard/mouse state and a short action buffer.

Actions are press-only; held keys drive movement and crouch. The buffer is
aged in simulation seconds so hitstop and slow motion behave correctly.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import pygame


@dataclass
class BufferedAction:
    action: str
    age: float = 0.0


class InputBuffer:
    def __init__(self, max_age: float = 0.12) -> None:
        self.max_age = max_age
        self.entries: list[BufferedAction] = []
        self.history: deque[str] = deque(maxlen=12)

    def press(self, action: str) -> None:
        self.entries.append(BufferedAction(action))
        self.history.append(action)

    def update(self, dt: float) -> None:
        for entry in self.entries:
            entry.age += dt
        self.entries = [entry for entry in self.entries if entry.age <= self.max_age]

    def has(self, action: str) -> bool:
        return any(entry.action == action for entry in self.entries)

    def consume(self, action: str | None = None) -> str | None:
        for index in range(len(self.entries) - 1, -1, -1):
            entry = self.entries[index]
            if action is None or entry.action == action:
                self.entries.pop(index)
                return entry.action
        return None

    def consume_newest(self, actions: tuple[str, ...]) -> str | None:
        """Remove every matching entry and return the most recent action."""
        newest: str | None = None
        for index in range(len(self.entries) - 1, -1, -1):
            entry = self.entries[index]
            if entry.action in actions:
                if newest is None:
                    newest = entry.action
                self.entries.pop(index)
        return newest

    def clear(self) -> None:
        self.entries.clear()


class InputState:
    KEY_ACTIONS = {
        pygame.K_a: "left",
        pygame.K_d: "right",
        pygame.K_w: "jump",
        pygame.K_SPACE: "jump",
        pygame.K_s: "crouch",
        pygame.K_LSHIFT: "crouch",
        pygame.K_RSHIFT: "crouch",
        pygame.K_q: "q",
        pygame.K_e: "e",
        pygame.K_1: "special_1",
        pygame.K_2: "special_2",
        pygame.K_3: "special_3",
        pygame.K_4: "special_4",
    }
    # W/S keep their normal jump/crouch actions and additionally drive the
    # climb state while a ladder trigger overlaps the player. Shift stays
    # crouch-only, so it never climbs down.
    CLIMB_ACTIONS = {
        pygame.K_w: "climb_up",
        pygame.K_s: "climb_down",
        # Space leaves the ladder; W keeps climbing even when re-pressed.
        pygame.K_SPACE: "climb_jump",
    }
    BUFFERED_KEYS = {"jump", "q", "e", "special_1", "special_2", "special_3", "special_4"}

    def __init__(self, buffer_seconds: float = 0.12) -> None:
        self.buffer = InputBuffer(buffer_seconds)
        self.held: set[str] = set()
        self.history = self.buffer.history

    # --- event entry points -------------------------------------------------
    def key_down(self, key: int) -> None:
        action = self.KEY_ACTIONS.get(key)
        if action is None:
            return
        self.held.add(action)
        if action in self.BUFFERED_KEYS:
            self.buffer.press(action)
        climb_action = self.CLIMB_ACTIONS.get(key)
        if climb_action is not None:
            self.held.add(climb_action)

    def key_up(self, key: int) -> None:
        action = self.KEY_ACTIONS.get(key)
        if action is not None:
            self.held.discard(action)
        climb_action = self.CLIMB_ACTIONS.get(key)
        if climb_action is not None:
            self.held.discard(climb_action)

    def mouse_down(self, button: int) -> None:
        if button == 1:
            self.held.add("punch")
            self.buffer.press("punch")
        elif button == 3:
            self.held.add("kick")
            self.buffer.press("kick")

    def mouse_up(self, button: int) -> None:
        if button == 1:
            self.held.discard("punch")
        elif button == 3:
            self.held.discard("kick")

    # --- simulation ---------------------------------------------------------
    def update(self, dt: float) -> None:
        self.buffer.update(dt)

    def is_held(self, action: str) -> bool:
        return action in self.held

    def sync_held(self, pressed) -> None:
        """Rebuild held movement/crouch from the OS keyboard state.

        Called after focus regain, pause resume or a scene rebuild so a key
        that is still physically held keeps responding without a re-press.
        """
        self.held = {
            action
            for key, action in self.KEY_ACTIONS.items()
            if action in ("left", "right", "crouch") and pressed[key]
        }
        for key, action in self.CLIMB_ACTIONS.items():
            if action in ("climb_up", "climb_down") and pressed[key]:
                self.held.add(action)

    def clear(self) -> None:
        self.held.clear()
        self.buffer.clear()

    def describe_entries(self) -> list[str]:
        return [f"{entry.action} {entry.age:.2f}s" for entry in self.buffer.entries[-6:]]
