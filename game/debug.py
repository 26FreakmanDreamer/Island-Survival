"""F1 hitbox/state overlay and F2 live simulation panel."""

from __future__ import annotations

import pygame


def _font(size: int) -> pygame.font.Font:
    try:
        return pygame.font.SysFont("consolas", size)
    except Exception:  # noqa: BLE001
        return pygame.font.Font(None, size)


class DebugOverlay:
    def __init__(self) -> None:
        self.font = _font(13)

    @staticmethod
    def _dashed_h(surface: pygame.Surface, color, x1: int, x2: int, y: int) -> None:
        dash, gap = 8, 7
        x = x1
        while x < x2:
            pygame.draw.line(surface, color, (x, y), (min(x + dash, x2), y), 1)
            x += dash + gap

    def draw(self, surface: pygame.Surface, scene) -> None:
        stage = scene.stage
        stage.draw_bounds(surface)

        lane_colors = {
            "high": (255, 210, 80),
            "fist": (255, 160, 255),
            "mid": (120, 220, 255),
            "low": (150, 255, 150),
        }
        for name, height in stage.lane_heights.items():
            color = lane_colors.get(name, (220, 220, 220))
            y = scene.player.y - height
            self._dashed_h(surface, color, int(stage.walls[0]), int(stage.walls[1]), round(y))
            label = f"{name.upper()} -{height:.0f}"
            surface.blit(self.font.render(label, True, color), (1100, round(y) - 15))

        pygame.draw.rect(surface, (70, 220, 130), scene.player.hurtbox(), 1)
        pygame.draw.rect(surface, (70, 220, 130), scene.enemy.hurtbox(), 1)
        for rect in scene.debug_hitboxes:
            pygame.draw.rect(surface, (255, 70, 70), rect, 2)

        for fighter, color in ((scene.player, (255, 220, 60)), (scene.enemy, (255, 120, 255))):
            x, y = round(fighter.x), round(fighter.y)
            pygame.draw.line(surface, color, (x - 8, y), (x + 8, y), 1)
            pygame.draw.line(surface, color, (x, y - 8), (x, y + 8), 1)
            pygame.draw.line(surface, color, (x, y), (x + 22 * fighter.facing, y), 2)
            label = f"{getattr(fighter, 'name', '?')} {fighter.state.name}"
            label_y = y - round(fighter.hurtbox_dims[1]) - 20
            surface.blit(self.font.render(label, True, color), (x - 24, label_y))


class DebugPanel:
    def __init__(self) -> None:
        self.font = _font(12)

    def draw(self, surface: pygame.Surface, scene) -> None:
        x, y, w, h = 936, 8, 336, 704
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((7, 9, 15, 218))
        surface.blit(panel, (x, y))

        for index, line in enumerate(self._lines(scene)):
            color = (235, 235, 245)
            if line.startswith("!"):
                color = (255, 120, 120)
                line = line[1:]
            elif line.endswith(":"):
                color = (120, 220, 255)
            image = self.font.render(line[:44], True, color)
            surface.blit(image, (x + 8, y + 7 + index * 15))

    def _lines(self, scene) -> list[str]:
        player = scene.player
        enemy = scene.enemy
        characters = list(scene.store.roster.get("characters", {}))
        enemies = list(scene.store.roster.get("enemies", {}))
        character_index = (
            characters.index(scene.character_id) + 1
            if scene.character_id in characters else 0
        )
        enemy_index = (
            enemies.index(scene.enemy_id) + 1 if scene.enemy_id in enemies else 0
        )
        lines = [
            f"FPS {scene.fps:5.1f}  tick {scene.tick_count}  t {scene.sim_time:7.2f}",
            f"SCALE {scene.time_scale:.2f}x  HITSTOP {scene.hitstop * 1000:4.0f}ms",
            f"CHAR {scene.character_id} {character_index}/{len(characters)}  "
            f"ENEMY {scene.enemy_id} {enemy_index}/{len(enemies)}  "
            f"RESULT {scene.match_over or '-'}",
            f"BLOCKS {'ON' if scene.stage.blocks_enabled else 'OFF'}  B toggle",
            f"LOCK {'ON' if scene.lock_on else 'OFF'}  MMB toggle",
            f"PLAYER {player.state.name}  HP {player.hp:5.1f}/{player.max_hp:.0f}",
        ]
        if all(
            hasattr(player, attr)
            for attr in ("energy", "max_energy", "q_cd", "e_cd")
        ):
            lines.append(
                f"ENERGY {player.energy:5.1f}/{player.max_energy:.0f}  "
                f"Q {player.q_cd:4.1f}s  E {player.e_cd:4.1f}s"
            )
        elif hasattr(player, "q_cd") and hasattr(player, "e_cd"):
            lines.append(f"Q {player.q_cd:4.1f}s  E {player.e_cd:4.1f}s")
        if hasattr(player, "mark_detonations") and enemy is not None:
            lines.append(
                f"MARKS {int(enemy.marks)}/3 BURST {enemy.mark_burst_time:.2f} "
                f"LAST {enemy.mark_burst_damage:.0f} BURSTS {player.mark_detonations}"
            )
        if all(
            hasattr(player, attr)
            for attr in ("flame_time", "flame_hits", "current_flame_bonus")
        ):
            lines.append(
                f"FLAME {player.flame_time:4.2f}s  HITS {player.flame_hits}  "
                f"NEXT +{player.current_flame_bonus():.0%}"
            )
        if player.anim is not None:
            lines.append(
                f"ANIM {player.anim.variant}:{player.anim.clip_name}  "
                f"frame {player.anim.frame_index + 1}/{len(player.anim.clip['frames'])}"
            )
        lines.append(
            f"HITSTUN {player.hitstun:.2f}  KB {player.kb_vx:6.0f}  GROUND {player.on_ground}"
        )
        lines.append(f"POS {player.x:6.1f},{player.y:6.1f}  FACE {player.facing:+d}")

        runtime = getattr(player, "attack_runtime", None)
        if runtime is not None:
            lines.append(
                f"ATTACK {player.attack_id}  {runtime.time:.2f}/{runtime.duration:.2f}  "
                f"queue={getattr(player, 'queued_action', None)}"
            )
        else:
            queued = getattr(player, "queued_action", None)
            lines.append(f"ATTACK -  queue={queued}" if queued else "ATTACK -")

        lines.append("PLAYER STATUS:")
        player_status = player.statuses.describe()
        lines.extend(f"  {item}" for item in player_status)
        if not player_status:
            lines.append("  -")

        lines.append(
            f"{enemy.name.upper()} {enemy.state.name}  HP {enemy.hp:.1f}/{enemy.max_hp:.0f}"
        )
        lines.append(
            f"{enemy.name.upper()} POS {enemy.x:.1f},{enemy.y:.1f}  FACE {enemy.facing:+d}"
        )
        slots = getattr(enemy, "skill_slots", [])
        slot_bits = []
        for index, attack_id in enumerate(slots):
            if attack_id:
                remaining = enemy.skill_remaining(attack_id)
                slot_bits.append(f"S{index + 1} {attack_id} {remaining:.1f}s")
            else:
                slot_bits.append(f"S{index + 1} -")
        if slot_bits:
            lines.append("  ".join(slot_bits[:2]))
            lines.append("  ".join(slot_bits[2:]))
        if enemy.anim is not None:
            frame_count = len(enemy.anim.clip["frames"])
            lines.append(
                f"ENEMY ANIM {enemy.anim.clip_name} frame {enemy.anim.frame_index + 1}/{frame_count}"
            )
            enemy_runtime = enemy.attack_runtime
            if enemy_runtime is not None:
                lines.append(
                    f"ENEMY ATK {enemy.attack_id} {enemy_runtime.time:.2f}/{enemy_runtime.duration:.2f}"
                )
                armor = float(enemy_runtime.data.get("armor_until", 0.0))
                lines.append(f"ENEMY ARMOR until {armor:.2f}s")
            else:
                lines.append("ENEMY ATK -")
        else:
            lines.append(f"ENEMY INV {enemy.invincible}")
        if hasattr(enemy, "ai_enabled"):
            lines.append(f"ENEMY AI {'ON' if enemy.ai_enabled else 'OFF'}")
        if hasattr(enemy, "skill_cd"):
            lines.append(f"SKILL GAP {enemy.skill_cd:.2f}s")
        if hasattr(enemy, "mode"):
            lines.append(f"MODE {enemy.mode}  HOVER {enemy.hover_height:.0f}")
        for projectile in scene.projectiles:
            if getattr(projectile, "kind", "") == "axe_throw":
                lines.append(
                    f"AXE {projectile.phase} out={projectile.hit_out} "
                    f"back={projectile.hit_return}"
                )

        lines.append(f"{enemy.name.upper()} STATUS:")
        enemy_status = enemy.statuses.describe()
        lines.extend(f"  {item}" for item in enemy_status)
        if not enemy_status:
            lines.append("  -")

        if scene.last_hit is not None:
            hit = scene.last_hit
            lines.append(
                f"LAST HIT {hit['damage']:.1f}  bonus +{hit['bonus']:.0%}  -> {hit['target']}"
            )
        else:
            lines.append("LAST HIT -")

        history = " ".join(scene.input.history) if scene.input.history else "-"
        lines.append(f"INPUT {history}")
        entries = " | ".join(scene.input.describe_entries()) or "-"
        lines.append(f"BUFFER {entries}")
        player_missing = (
            set(player.anim.missing) | set(player.anim.missing_paths())
            if player.anim is not None else set()
        )
        enemy_missing = (
            set(enemy.anim.missing) | set(enemy.anim.missing_paths())
            if enemy.anim is not None else set()
        )
        lines.append(f"MISSING PLAYER {len(player_missing)}  ENEMY {len(enemy_missing)}")
        for path in list(player_missing)[:2]:
            lines.append("  !" + path.replace("\\", "/").split("/")[-1])
        for path in list(enemy_missing)[:2]:
            lines.append("  !" + path.replace("\\", "/").split("/")[-1])
        lines.append(f"RELOAD {'OK' if scene.store.last_ok else 'FAIL'}")
        if scene.store.last_error:
            lines.append("!ERR " + scene.store.last_error)
        lines.append("F1 boxes F2 panel F3 pause F4 step")
        lines.append("F5 reload F6 speed F7 enemy  [ ] char")
        lines.append("F8 AI/inv F9 reset F10 flame")
        lines.append("F11 status F12 hurt  V/C/X/Z slots 1-4")
        lines.append("B blocks  MMB lock-on  Arrows move")
        lines.append("PgUp/PgDn HP  R restart")
        return lines
