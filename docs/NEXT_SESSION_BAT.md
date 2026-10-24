# Next Session — Bat（蝙蝠）设计与实现

> 日期：2026-10-24
> 分支：`nyra-veno-sandbox`（工作区有大量未提交改动）
> 用途：下个 session 的 Bat handoff。先读本文件 + `AGENTS.md`；若下个 session 由 Codex 执行，再读 `CODEX-README.md`；要生成图片时再读 `docs/IMAGE_GENERATION_RULES.md`。
> 当前基线：`.venv/Scripts/python.exe main.py --smoke-test` → **exit 0**（2026-10-24 已核对）。
> 默认范围：**先确认 §4，再实现**。未经确认不要改其他角色/敌人的数值、默认阵容或 `Image/`。

---

## 0. 可直接复制的开场 prompt

```text
先阅读 docs/NEXT_SESSION_BAT.md 和 AGENTS.md；如果本轮要生成图片，再读 docs/IMAGE_GENERATION_RULES.md。
本轮目标：<只做 Bat 设计 / 实现 Bat 敌人 / 实现 + 接入新美术>（默认：先确认 §4，再按 §3 分阶段实现）。

先运行 .venv/Scripts/python.exe main.py --smoke-test，确认基线 exit 0。
先不要改代码或素材：按 §4 的 Q1–Q10 逐项 grill 我，每项给出当前值/目标值、影响范围和推荐默认。
确认后再实现；每完成一个阶段跑一次 smoke。新素材必须先出 contact sheet，经我批准后才能复制进 assets/frames/。

不要 commit；不要 git reset / git checkout -- . / git stash；
不要动 Image/、instruction.docx、UI Resources/；不要覆盖 Image/Enemy/bat-128.png。
```

如果用户只说“做 Bat”而没有给具体项，**先问 §4 的清单，不要猜**。

---

## 1. 权威设定（`instruction.docx` 原文，2026-10-24）

> Bat
> 形象：Image\Enemy\bat-128.png
> Hp =50 atk =20 ,n=5 (测试时生成一只)
> 技能1：飞向character，进行一次攻击，造成伤害atk
> 技能2：空中，口中发出超声波，超声波初始方向为bat指向character方向，超声波沿着初始方向飞行。
> 如果碰到character，则对character造成一次伤害1.2atk和1s眩晕效果，然后反弹，沿着character指向bat方向回到发出超声波的bat后消失。
> 如果没有碰到character,当碰到墙壁时反弹，指向bat方向返回，如果返回的过程中碰到character，则对character造成一次伤害和1s眩晕效果，穿过character，回到发出超声波的bat后消失。
> bat在释放这个技能期间不会移动，只会在原地挥动翅膀。
> 被动：蝙蝠可以自由地在空中飞行

### 1.1 数值拆解

| 项 | 值 | 说明 |
|---|---:|---|
| HP | 50 | 与 Veno 相同 |
| ATK | 20 | `basic_atk: 20`、`extra_atk: 0` |
| 数量 | n=5（测试 1 只） | 正式游戏 5 只，沙盒先按 1 只验证 |
| 技能 1 | `1.0 × atk = 20` | 飞向玩家并攻击一次 |
| 技能 2 | `1.2 × atk = 24` | 超声波；命中附加 **1s stun** |
| 被动 | 自由飞行 | 不吃重力，可停留/上下移动 |

### 1.2 技能 2 的状态机（按原文）

```text
出膛：方向 = bat 嘴部 -> 玩家（发射瞬间的 2D 方向），沿该方向直线飞行
  ├─ 命中玩家（去程）
  │    → 24 伤害 + 1s stun
  │    → 立刻转向，朝“发射者”返回
  │    → 回到 bat 后消失
  └─ 未命中玩家，撞到墙壁
       → 转向，朝“发射者”返回
       → 返回途中若命中玩家：24 伤害 + 1s stun，穿过玩家继续返回
       → 回到 bat 后消失
```

补充约定（待 §4 确认）：

- “墙壁”至少包括左右墙 `stage.walls = (90, 1190)`；顶部/地面是否需要反弹，建议一并纳入边界处理。
- 返回目标是**发射者当前位置**，不是发射点；用 `owner` 追踪，回到约 16px 内消失。
- 去程命中后不要再造成第二次伤害；返回命中只结算一次，并且**穿过**玩家。
- 超声波不追踪玩家，只追踪“返回 bat”这一目标。
- 施法期间 bat 原地挥翅；建议理解为**施法动作期间**（约 0.65s）锁定，而不是整个弹体飞行期间，具体见 Q5。

---

## 2. 当前工作区事实（已核对，不要重复踩坑）

### 2.1 已有素材

| 文件 | 规格 | 用途 |
|---|---|---|
| `Image/Enemy/bat-128.png` | 128×128 RGBA，可见轮廓约 126×94（展翼） | **canonical 视觉源，只读** |
| `Image/Enemy/Posters/bat-poster.png` | 1024×1536 RGB | 宣传海报/姿势与洞窟氛围参考，不是运行时帧 |
| `assets/enemies/bat.png` | 1774×887 RGBA | 旧版候选，单张展翼姿势 |
| `assets/enemies/bat-cute-v2.png` | 1774×887 RGBA | 旧版候选 |
| `assets/enemies/bat-cute-v3.png` | 1774×887 RGBA | 旧版候选；`bat-cute-v3-128*.png` 是其 128 缩图 |
| `assets/generated/backgrounds/island-bat-cave-arena-16x9.png` | 16:9 | 蝙蝠洞窟背景候选，**尚未接入游戏** |
| `assets/generated/backgrounds/bat-cave-generation-notes.md` | — | 洞窟背景生成记录 |

- 按 `AGENTS.md`：**优先使用 `Image/`**；`assets/enemies/bat*` 只是旧候选，不要当成 canonical 直接接入。
- 保留版本区分，不要覆盖/重命名已有候选。新的生成结果放到 `assets/generated/raw/bat/`，新版本用新名字。
- 海报里有挂壁、飞行、吼叫等多种姿势，可作为**姿势参考**，但不要直接把海报切进游戏。

### 2.2 尚未实现

当前没有 Bat 的运行时内容：

- `game/data/roster.json` 没有 bat entry；
- `game/data/stats.json`、`attacks.json`、`animations.json` 没有 bat 数据；
- `game/` 没有 `bat.py`；
- `game/config.py` 的 `REQUIRED_STATS` / `REQUIRED_ATTACKS` / `ROSTER_CLASSES` / `ANIMATED_CLASSES` / `PROJECTILE_KINDS` 没有 bat；
- `debug.json` 的 stage 没有 `bat_spawn`；
- smoke 没有 bat 检查。

### 2.3 可复用的架构

- **数据驱动**：`roster.json` → `game/roster.py:create_fighter` → `FIGHTER_CLASSES`；`stats.json` / `attacks.json` / `animations.json` 全部可由 F5 热重载。
- **飞行参考**：`game/veno.py` 的 `ascend/hover/descend` 已经展示如何用 `stage.move_fighter(..., apply_gravity=False)`、`_hover_step` 和 `mode` 管理空中状态；Bat 可以复用思路，但要做**真正的 2D 自由飞行**，不是挂在丝线上的悬停。
- **弹体参考**：`game/projectile.py` 的 `AimedProjectile` 已实现“发射瞬间瞄准 + 直线飞行 + 命中结算”；`AxeThrow` 已实现“去程/回程 + 命中两次”的双阶段状态机。超声波建议新建 `SonicWave`，不要硬改 Veno 弹体。
- **伤害公式**：`game/combat.py:attack_damage` 支持 `basic_mult` / `extra_mult`；`basic_atk 20` 时 `1.0` = 20、`1.2` = 24。
- **状态**：`StatusSet` 已有 `stun`，Veno web 的 1s 眩晕可参考；F11 可直接演示。
- **多敌人**：`scene.enemies` / `scene.enemy`（主目标）/ `targets_for()` / `enemy_count_override` / `decides_match` 已支持；Veno 的 3 只编组是本轮 Bat n=5 的直接参考。
- **每实例冷却**：Veno 已按实例保存 `bite_cd` / `poison_cd` / `web_cd`；Bat 的 `dive_cd` / `sonic_cd` 也应放在 Bat 实例上，不要用全局变量。
- **视觉层**：`game/fx.py` 的 `fx_effects` 层 + `spawn_projectile_cast_fx` / `spawn_projectile_impact` / `spawn_hit_fx` 可挂超声波的施法/命中环、俯冲命中特效；`game/particles.py` 可发粒子。

### 2.4 关键陷阱

1. **`scene._place_enemies()` 目前强制所有敌人落地**：它会 `enemy.y = base_y`、`enemy.on_ground = True`、`mode = "ground"`。Bat 是飞行敌人，必须扩展这里（建议 roster 增加 `"flying": true` 或 `spawn_modes: ["air"]`，并在 `_place_enemies` 里分支；不要只改 `bat_spawn` 的 y）。
2. **`reset_common()` 会把 `on_ground` 置 True**：`Bat.reset()` 要在调用后重新设为 `False`，恢复出生高度/飞行模式。
3. **`dash` 事件只做水平移动**（`scene.stage.move_x`）：技能 1 的“飞向玩家”不能只靠 `dash`；需要在 `Bat._update_attack` 里做自定义 2D 位移，或扩展事件类型（优先前者，避免影响其他敌人）。
4. **`AimedProjectile` 命中即 `alive = False`，撞墙也直接消失**：超声波需要“去程命中后返回、撞墙后返回、返回命中穿过玩家、回到发射者才消失”，不能直接复用它的终止逻辑。
5. **`resolve_projectile_hit` 只负责一次伤害/状态**：超声波的“去程一次、回程一次”需要 `SonicWave` 自己维护 `hit_out` / `hit_return` 与 `phase`，并在去程命中后把 phase 切到 return，而不是把弹体标记为 dead。
6. **`stage.body_half()` 在 `on_ground` 时用 `stage_body_width`**：Bat 永远在空中，应该走窄的 hurtbox 宽度；设置 `on_ground = False` 并让移动逻辑不要把它拉回地面。
7. **默认敌人是 Veno（3 只）**：`debug.json` 的 `roster.default_enemy = "veno"`。除非用户明确要求，不要为了 Bat 改默认阵容；F7 能切到 Bat 即可。
8. **F7 顺序由 `roster.json` 的 `enemies` 顺序决定**：新增 bat 会改变循环顺序；确认放在 Veno 前/后（见 Q10）。
9. **地面近战可能打不到飞行 Bat**：Bat 在 150px 高度时，Lina 的地面 punch/kick 与 Nyra 的短判定可能全部落空（参考半体型 Veno 的同类问题）。这是“自由飞行”的预期结果，不是 bug；smoke 的近战命中测试要把 Bat 放到低空，或使用 Lina Q / 跳跃攻击，并在 README 写清楚。

---

## 3. 推荐实现方案（待 §4 确认）

### 3.1 数据骨架（推荐默认，数值可调）

#### `game/data/stats.json` → `bat`

```json
"bat": {
  "hp": 50,
  "basic_atk": 20,
  "extra_atk": 0,
  "stage_body_width": 56,
  "move": {
    "walk": 300,
    "jump_v": 0,
    "gravity": 0
  },
  "hurtbox": {
    "standing": [60, 56],
    "crouching": [60, 56]
  },
  "flight": {
    "min_height": 60,
    "max_height": 280,
    "preferred_height": 150,
    "vertical_speed": 240,
    "bob": 14,
    "bob_rate": 1.8
  },
  "ai": {
    "dive_range": 420,
    "sonic_min_range": 120,
    "sonic_range": 700,
    "standoff": 220,
    "decision_interval": 0.15
  },
  "cooldowns": {
    "dive": 2.5,
    "sonic": 5.0
  }
}
```

- `hp` / `basic_atk` 来自 docx；`hurtbox`、`flight`、`ai`、`cooldowns` 是推荐默认，docx 未规定，需在 §4 确认。
- 翼展 ≈126px，但**只让身体区域可被击中**（60×56），翅膀不进入 hurtbox；否则近战会打到“空气翅膀”，手感很差。
- 若用户希望翅膀可被击中，再改为约 110×60 的 hurtbox，并重新评估近战范围。

#### `game/data/attacks.json`

```json
"bat_dive": {
  "basic_mult": 1.0,
  "extra_mult": 1.0,
  "duration": 0.75,
  "lunge": 0,
  "lunge_time": 0.0,
  "hitstun": 0.25,
  "hitstop": 0.06,
  "events": [
    {
      "t": 0.12,
      "until": 0.34,
      "type": "hitbox",
      "box": [0, -56, 76, 56],
      "knockback": 160
    }
  ]
}
```

```json
"bat_sonic": {
  "basic_mult": 1.2,
  "extra_mult": 1.2,
  "duration": 0.65,
  "lunge": 0,
  "lunge_time": 0.0,
  "hitstun": 0.1,
  "hitstop": 0.05,
  "events": [
    {
      "t": 0.24,
      "type": "projectile",
      "projectile": "sonic_wave",
      "origin_height": 24,
      "speed": 420,
      "range": 3000,
      "status": "stun",
      "status_duration": 1.0
    }
  ]
}
```

- `bat_dive` 的 hitbox 不带 `anchor`，会跟随 Bat 当前坐标（适合俯冲）；具体 box 在 128×128 画布/身体比例确认后微调。
- `bat_sonic` 的伤害由 `basic_mult: 1.2` 得到 24；`status: "stun"` 由 `Bat.on_projectile_hit` 施加（参考 `Veno.on_projectile_hit`）。
- `range: 3000` 只是防泄漏的安全上限：竞技场宽 1100，声波“去程到墙 + 回程到 Bat”最坏约 2200px，若用 1400 会在回程中途消失；实际生命周期仍由“回到发射者”或超时决定，见 §3.2。

#### `game/data/animations.json`

```json
"bat_frame_size": [128, 128],
"bat_pivot": [64, 96],
"bat_clips": {
  "idle": {
    "loop": true,
    "frames": ["idle/idle_00.png", "idle/idle_01.png"],
    "durations": [0.22, 0.22]
  },
  "fly": {
    "loop": true,
    "frames": ["fly/fly_00.png", "fly/fly_01.png"],
    "durations": [0.14, 0.14]
  },
  "bat_dive": {
    "loop": false,
    "frames": ["bat_dive/bat_dive_00.png", "bat_dive/bat_dive_01.png", "bat_dive/bat_dive_02.png"],
    "durations": [0.12, 0.22, 0.41]
  },
  "bat_sonic": {
    "loop": false,
    "frames": ["bat_sonic/bat_sonic_00.png", "bat_sonic/bat_sonic_01.png", "bat_sonic/bat_sonic_02.png"],
    "durations": [0.10, 0.30, 0.25]
  },
  "hurt": {
    "loop": false,
    "frames": ["hurt/hurt_00.png"],
    "durations": [0.3]
  },
  "ko": {
    "loop": false,
    "frames": ["ko/ko_00.png", "ko/ko_01.png"],
    "durations": [0.35, 0.35]
  }
}
```

- `bat_pivot = (64, 96)`：`y` 取蝙蝠身体底部（爪/尾附近），这样 `fighter.y` 仍可直观理解为“脚底”，hurtbox 从 `y-56` 到 `y`。
- 画布 128×128 与 canonical 一致；如果新姿势（俯冲/张嘴）在固定身体尺寸下放不下完整翼展，**按 `IMAGE_GENERATION_RULES` 停止并询问**，不要缩小身体或裁切翅膀。
- 初版没有素材时，可以让 `AnimationPlayer` 用 `Image/Enemy/bat-128.png` 作 fallback；但 `missing_paths()` 会列出缺失帧，smoke 的 `bat_missing_frames` 暂不作为 exit 条件，等批准帧接入后再设为 0。

#### `game/data/roster.json` → `enemies.bat`

```json
"bat": {
  "name": "Bat",
  "class": "bat",
  "stats": "bat",
  "spawn": "bat_spawn",
  "clips": "bat_clips",
  "frame_size": "bat_frame_size",
  "pivot": "bat_pivot",
  "frames_dir": "bat",
  "fallback": "Image/Enemy/bat-128.png",
  "skill_slots": ["bat_dive", "bat_sonic", null, null],
  "separates": true,
  "decides_match": true,
  "flying": true,
  "count": 1,
  "spawn_offsets": [0]
}
```

- `count: 1` 是**沙盒默认**（docx：测试时生成一只）；正式 n=5 只需把 `count` 改为 5、补 offsets/modes，等 §4 Q2 确认后再改。
- `flying: true` 是新字段，供 `_place_enemies` / `reset` 判断；也可以复用 `spawn_modes: ["air"]`，二选一，不要两套并存。
- `separates: true`：5 只蝙蝠之间也应避免完全重叠；`decides_match: true`：全部击杀才 WIN。

#### `game/data/debug.json` → stage

```json
"bat_spawn": [1000, 470]
```

- `ground_y = 620`，470 即离地约 150px；与 `flight.preferred_height` 对齐。
- 现有 stage 的 `walls = [90, 1190]`、`blocks` 在 y=560..620；Bat 飞行时应忽略 blocks（见 Q3）。

### 3.2 代码

#### 新建 `game/bat.py`

建议结构（参考 `game/veno.py` + `game/warrior.py`）：

- 构造函数：读 `stats["bat"]`，设置 `basic_atk/atk`、`stage_body_width`、hurtbox、`walk_speed`、flight/AI/cooldown 字段；`self.on_ground = False`、`self.mode = "fly"`；`self.dive_cd` / `self.sonic_cd` 每实例独立；`show_health_bar = True`（与 Veno/Warrior 一致）。
- `update(dt, scene)`：
  - `update_common(dt)`、冷却递减；
  - KO / HURT / ATTACK / control lock 分支（参考 Veno）；
  - 自由飞行：计算目标点（玩家 x + `standoff`、`preferred_height` + sine bob），按速度上限同时移动 x/y；用 `stage.walls` 夹紧 x，用 `flight.min_height/max_height` 夹紧 y；不要调用带重力的 `move_fighter` 默认路径；
  - AI：距离/技能冷却满足时选择 `bat_dive` 或 `bat_sonic`；否则保持 standoff 和高度。
- `start_attack(attack_id, scene, target)`：面向玩家、设置 `attack_runtime`、对应冷却；`bat_dive` / `bat_sonic` 分别设置。
- `_update_attack(dt)`：在 `runtime.update(dt)` 之外，对 `bat_dive` 做自定义 2D 位移（建议 t=0.05..0.30 朝玩家胸口移动，速度约 520px/s；之后减速/停住），并让 hitbox 跟随 Bat。不要在通用 `AttackRuntime` 里加蝙蝠专属逻辑。
- `take_hit` / 受击位移：Bat 的 `gravity=0`，普通 `launch`/knockback 会让它持续漂移；建议在 `Bat.update` 中对 `vy`/`kb_vx` 做衰减并夹紧飞行高度，或在 `take_hit` 后设置短时间 stagger 再回位。不要让一次击飞把它送出场景或卡在墙外。
- `force_attack(scene, target, attack_id)` / `skill_remaining(attack_id)` / `reset()`：与 Veno 一致；`reset()` 末尾恢复 `on_ground=False`、出生高度、`mode="fly"`。
- `on_projectile_hit(projectile)`：`sonic_wave` + `status == "stun"` → `target.statuses.add("stun", 1.0, source="bat_sonic")`（source 是否按 Bat 实例唯一，见 Q6）。
- `draw()`：如需 hover/飞行姿态可直接用 `super().draw()`；暂不需要特殊的丝线。

#### 新建 `game/projectile.py::SonicWave`

建议字段/状态机：

```text
fields:
  owner, x, y, ux, uy, speed, radius, damage, hitstun, hitstop
  status = "stun", status_duration = 1.0   # 供 Bat.on_projectile_hit 读取
  visual_kind = "bat_sonic", hit_color = (210, 190, 255)
  phase = "out" | "return"
  hit_out = False, hit_return = False
  age, timeout = 8.0
  alive = True

update(dt, scene):
  age += dt; if age > timeout: alive = False
  if phase == "out":
    move along (ux, uy)
    if 撞到左右墙 / 顶部 / 地面:
      phase = "return"; 指向 owner 当前位置
    elif 命中玩家（targets_for(owner)）:
      hit_out = True
      resolve_projectile_hit(scene, self)   # 24 伤害 + 1s stun
      hit_return = True                     # 去程已命中：同一次声波不再结算回程伤害
      phase = "return"; 指向 owner 当前位置
  else:
    朝 owner 当前位置移动
    若距离 <= step 或 <= 16px: alive = False
    elif not hit_return and 命中玩家:
      hit_return = True
      resolve_projectile_hit(scene, self)   # 24 伤害 + 1s stun，穿过，不消失
```

- 去程/回程都不要因为命中玩家而 `alive = False`；只有回到 owner 或超时才消失。
- **去程命中后必须置 `hit_return = True`**（或加短暂 re-hit grace），否则弹体还叠在玩家 hurtbox 里时，return 分支会立刻再结算一次，变成 48 伤害。docx 只允许每次声波命中一次。
- 墙面判断建议同时检查 `x <= walls[0]+radius`、`x >= walls[1]-radius`、`y <= 0+radius`、`y >= ground_y-radius`；是否把 blocks 当墙，见 Q。
- `direction` 用于 `resolve_projectile_hit` 的击退方向；超声波 `knockback` 建议 0（docx 只给 stun），`hitstun` 0.1。
- `visual_kind = "bat_sonic"`、`hit_color` 建议紫白 `(210, 190, 255)`/`(245, 235, 255)`；`draw()` 用程序化同心弧/声波环即可，先不生成贴图。
- 在 `scene.spawn_projectile_from_event` 增加 `sonic_wave` 分支；在 `spawn_projectile_cast_fx` / `spawn_projectile_impact` 增加对应程序化特效（可选 `game/fx.py` 的 `RingBurst` 风格）。
- 在 `game/config.py` 的 `PROJECTILE_KINDS` 加 `"sonic_wave"`。

#### 修改 `game/scene.py::_place_enemies`

- 当前无条件 `enemy.on_ground = True` / `enemy.y = base_y` / `mode="ground"`。
- 建议：
  ```python
  if getattr(enemy, "flying", False) or self.enemy_spec.get("flying"):
      enemy.y = base_y
      enemy.on_ground = False
      enemy.mode = "fly"
  else:
      ... 现有地面/hover 逻辑
  ```
- `base_y` 来自 `bat_spawn`；`count` / `spawn_offsets` 仍复用现有 group 逻辑。
- 如果 Bat 需要忽略 blocks，移动逻辑里不要调用会挡 block 的 `stage.move_x`，或在 `Bat._move` 内只做墙面夹紧。

#### 修改 `game/config.py`

至少增加：

- `REQUIRED_STATS += ("bat",)`
- `REQUIRED_ATTACKS += ("bat_dive","bat_sonic")`
- `REQUIRED_STAGE += ("bat_spawn",)`
- `ROSTER_CLASSES += ("bat",)`
- `ANIMATED_CLASSES += ("bat",)`
- `PROJECTILE_KINDS += ("sonic_wave",)`
- `REQUIRED_BAT_CLIPS`（建议 `idle`, `fly`, `bat_dive`, `bat_sonic`, `hurt`, `ko`）及对应 `animations.json` 校验；参考现有 Veno 校验写法。
- `stats.bat` 校验：hp/basic_atk/extra_atk/stage_body_width/move/hurtbox/flight/ai/cooldowns；`flight.min_height <= preferred <= max_height`。

#### `game/roster.py`

- `from .bat import Bat`
- `FIGHTER_CLASSES["bat"] = Bat`

### 3.3 素材与帧方案（§4 确认后再生成）

当前只有一张 canonical 展翼飞行图。建议最小帧集：

| clip | 帧数 | 内容 |
|---|---:|---|
| `idle` | 2 | 翅膀上/下，慢速循环 |
| `fly` | 2 | 翅膀上/下，快速循环（可与 idle 共用，若想省帧） |
| `bat_dive` | 3 | 收翅蓄力 / 前冲攻击 / 恢复 |
| `bat_sonic` | 3 | 吸气 / 张嘴发声 / 收势 |
| `hurt` | 1 | 受击 |
| `ko` | 2 | 坠落/落地 |
| **合计** | **11（或 9）** | 全部 128×128 RGBA |

- 画布/锚点：128×128，pivot `(64, 96)`；身体高度、头身比、翼展、耳朵/爪子的比例锁定。
- 生成方式：Seedream `image_to_image`，以 `Image/Enemy/bat-128.png` 为唯一角色参考；`background="transparent"`（输入图必须有透明像素）、`size="1K"`、`output_format="png"`；每帧 1–2 候选。
- prompt 必须带 `docs/IMAGE_GENERATION_RULES.md` §6 的固定块，并补充：
  - 同一只紫黑色蝙蝠，粉色耳内、紫色眼睛、白色獠牙、白色翼爪；
  - 正面/微侧飞行姿态，翅膀左右对称（便于左右翻转）；
  - 近侧翅膀在身体前、远侧在后，翅膀与身体连接正确，不穿模；
  - 保持身体/头/翼展比例、相机距离、光照一致；
  - 透明背景、无影子、无文字、无边框、无场景。
- 蝙蝠没有武器，**weapon-hand/grip 检查不适用**；但 body layering、no-interpenetration、size-lock 仍然必须检查。
- 审批：所有候选放 `assets/generated/raw/bat/`，contact sheet 放 `assets/generated/contact_sheets/bat_v1/`；128px 与 256px（200%）各看一遍，重点检查翼膜/骨架连接、耳朵、爪子、头像一致性。**用户批准后**才复制到 `assets/frames/bat/<action>/`。
- 不要直接把 `assets/enemies/bat-cute-v3*.png` 当作运行时帧；它们是旧候选，仅作姿势参考。

### 3.4 可选：Bat Cave 场景（默认不做）

- 已有 `assets/generated/backgrounds/island-bat-cave-arena-16x9.png` 与生成记录。
- 当前 `Stage` 使用全局 `BACKGROUND_PATH = assets/backgrounds/island-arena-16x9.png`，没有按敌人切换背景的机制。
- 若要接入，需要新增 stage 背景选择（roster/stage 字段或场景切换），属于独立改动；先确认是否本轮做，不要擅自替换全局背景。

### 3.5 建议实施顺序

1. 跑 smoke 确认基线；确认 §4 的全部问题。
2. 加数据（stats/attacks/animations/roster/debug）+ `game/bat.py` + config/roster 注册；先用 canonical fallback。
3. 接入 `SonicWave` + scene 的 sonic 分支/特效；让单只 Bat 能完整循环（飞行→俯冲→声波→返回→hurt/KO）。
4. 加 smoke 的 Bat 单只检查（飞行、20/24 伤害、1s stun、去程/回程、撞墙返回、施法锁定），确保现有 smoke 全绿；`bat_missing_frames` 先只打印。
5. 生成/审批 11 帧，复制到 `assets/frames/bat/`；把 `bat_missing_frames == 0` 加入 exit 条件。
6. 若确认 n=5，再改 `count` + offsets，补 `bat_group_ok`，单独平衡 5 只的冷却/仇恨。
7. 更新 README / DESIGN_DECISIONS / DEBUG / ASSET_PIPELINE / 本文件 §9。

---

## 4. 下个 session 必须先 grill 的问题（带推荐）

> 按 grilling 的方式一次问完；用户答完后把结论写回本文件 §9，再开始改代码。

### ❓ Q1 — 本轮范围

只做 Bat 的**纸面设计**（数值/技能/帧表），还是**实现代码**，还是**连美术一起接入**？

➡️ 推荐：先按本文档完成数据+`game/bat.py`+`SonicWave`+smoke（用 canonical fallback），再做 11 帧美术；美术 approval 后再把 `bat_missing_frames` 加入 exit 条件。

---

### ❓ Q2 — 数量：沙盒 1 只还是直接 5 只

docx 写 `n=5 (测试时生成一只)`。`roster.json` 的 `count` 是否先设 1，还是直接 5？

➡️ 推荐：**先 `count: 1`**，把 5 只作为数据开关（`count`/`spawn_offsets`），等单只的手感、声波返回、AI 稳定后再单独测 5 只。5 只同时放声波对玩家压力很大，需要单独平衡。

---

### ❓ Q3 — 飞行规则

是否完全自由 2D 飞行（无重力、可上下、无视 blocks），高度范围 60–280px？

➡️ 推荐：是。Bat 是“自由地在空中飞行”的被动；blocks 是地面障碍，飞行应越过，不参与碰撞。左右墙、顶部、地面仍夹紧。

---

### ❓ Q4 — 技能 1 的“飞向并攻击”

是一次**俯冲近战**（bat 本体移动到玩家附近，命中 box 跟随本体），还是发射一个弹体/远程攻击？

➡️ 推荐：俯冲近战。t≈0.05–0.30 朝玩家胸口移动（约 520px/s），hitbox 跟随本体，命中 20 伤害；未命中则冲过头并恢复。不要做成第二个远程技能。

---

### ❓ Q5 — 技能 2 的“释放期间不会移动”范围

是**只在施法动作期间**（约 0.65s）锁定，还是**直到超声波回到 bat** 都锁定？

➡️ 推荐：只在施法动作期间锁定（约 0.65s），声波飞出后 Bat 可以恢复飞行；否则它会长时间停在原地，和“自由飞行”的被动冲突。若用户坚持按字面全程锁定，则把 `sonic` 的 `duration` 延长到声波返回，并接受更大的惩罚窗口。

---

### ❓ Q6 — 超声波返回与消失

返回目标是**发射者当前位置**还是发射点？蝙蝠死亡/移出屏幕时怎么处理？stun 的 source 是否每只独立？

➡️ 推荐：追踪发射者当前位置，距离 ≤16px 消失；发射者死亡则再飞 0.5s 或撞边界后消失；`source` 用 `bat_sonic`（1s 眩晕不叠加，重复命中刷新即可）。若用户希望多只蝙蝠的眩晕独立计时，再改为每实例唯一 source。

---

### ❓ Q7 — 冷却与 AI 参数

docx 没写 Bat 冷却。推荐 `dive 2.5s`、`sonic 5.0s`（每实例），AI `dive_range 420`、`sonic_range 700`、`standoff 220`。是否接受？

➡️ 推荐：先用这组值；5 只时再单独观察，必要时改成 `dive 3.0s` / `sonic 7.0s`。冷却必须每只独立（参考 Veno）。

---

### ❓ Q8 — 画布、pivot 与 hurtbox

128×128、pivot `(64,96)`、身体 hurtbox `60×56`（翅膀不可被击中），是否接受？

➡️ 推荐：接受。翼展约 126px，如果整对翅膀都算 hurtbox，近战会打到“空气”，所以只让身体可被击中；pivot 取身体底部，便于 `y` 与地面坐标统一。若用户希望更容易命中，可把 hurtbox 调到 `80×60`，但仍不包含翼尖。

---

### ❓ Q9 — 美术生成时机

本轮是否直接生成 11 帧并走 contact sheet，还是先用 canonical 单帧 fallback 验证代码？

➡️ 推荐：先代码+fallback 跑通 smoke 和手感，再生成帧；生成前重读 `IMAGE_GENERATION_RULES.md`，contact sheet 批准后才复制进 `assets/frames/bat/`。若时间有限，至少先做 `idle/fly/hurt/ko`，技能帧用现有帧占位。

---

### ❓ Q10 — F7 顺序 / Cave 场景

Bat 放在 F7 的哪个位置（Veno 前/后）？是否要同时接入 `island-bat-cave-arena-16x9.png`？

➡️ 推荐：F7 顺序保持现有 `Warrior → Veno → Dummy` 不变，把 Bat 插在 Veno 后、Dummy 前（或按用户指定）；Cave 背景作为独立可选项，本轮不默认接入，避免影响其他敌人。

---

## 5. 验收与 smoke（实现阶段）

### 5.1 基线

```bat
.venv/Scripts/python.exe main.py --smoke-test
```

当前基线应 **exit 0**，所有现有字段为 True，`missing_frames=0` 等。新增 Bat 后，**现有字段不得回归**。

### 5.2 建议新增检查（命名可调整）

| 检查 | 预期 |
|---|---|
| `bat_present` | name="Bat"、HP=50、atk=20、`skill_slots=["bat_dive","bat_sonic",null,null]` |
| `bat_dive_ok` | 一次俯冲命中造成 **20** 伤害 |
| `bat_sonic_ok` | 声波命中造成 **24** 伤害 + `statuses.has("stun")`，stun 约 1s |
| `bat_sonic_return_ok` | 去程命中后 phase 切到 return，最终回到发射者并 `alive=False` |
| `bat_sonic_wall_return_ok` | 去程未命中 → 撞墙 → 回程命中玩家（24 + stun）→ 穿过 → 回到 bat 消失 |
| `bat_sonic_lock_ok` | 施法期间 bat 的 x/y 不变 |
| `bat_flight_ok` | 无重力：连续 tick 后仍 `on_ground=False` 且高度在 `[min,max]`；水平移动正常 |
| `bat_slots_ok` | V/C 触发俯冲/声波；X/Z 为 no-op |
| `bat_missing_frames` | 素材接入后为 **0**（未接入前只打印、不参与 exit） |
| `bat_group_ok`（若 count=5） | 5 只全部生成；全部死亡后 `match_over == "WIN"` |

### 5.3 测试隔离

- 单只 Bat 测试前设置 `scene.enemy_count_override = 1`，测完恢复；参考 Phase D 的 Veno 单只检查。
- 声波测试建议临时关闭 blocks（`scene.stage.blocks_enabled = False`），避免地面 block 干扰弹道；测完恢复。
- 直接调用 `bat.force_attack(scene, player, "bat_sonic")` 让弹道可控；再用 `scene.tick(FIXED_DT)` 推进。
- 墙面反弹测试可把 Bat 放在靠近 `stage.walls` 的位置，让声波朝外发射，玩家站在返回路径上。
- `fx_cleanup_ok` / 现有 projectile 清理逻辑不能被 Bat 破坏；超时/回程必须保证弹体最终 `alive=False`。

---

## 6. 文件清单（预计）

**新增**

- `game/bat.py`
- `game/projectile.py::SonicWave`（类，位于现有文件内）
- `assets/frames/bat/`（批准后的帧）
- `docs/NEXT_SESSION_BAT.md`（本文件）

**修改**

- `game/data/stats.json`（bat）
- `game/data/attacks.json`（bat_dive / bat_sonic）
- `game/data/animations.json`（bat_clips / bat_frame_size / bat_pivot）
- `game/data/roster.json`（bat enemy）
- `game/data/debug.json`（bat_spawn；按需 F7 顺序）
- `game/config.py`（REQUIRED_* / ROSTER_CLASSES / ANIMATED_CLASSES / PROJECTILE_KINDS）
- `game/roster.py`（FIGHTER_CLASSES）
- `game/scene.py`（`_place_enemies` 飞行分支、sonic 事件/特效）
- `game/projectile.py`（SonicWave）
- `game/fx.py`（可选：声波环/命中环）
- `main.py`（Bat smoke phase）
- `README.md`、`docs/DESIGN_DECISIONS.md`、`docs/DEBUG.md`、`docs/ASSET_PIPELINE.md`

**不要动**

- `Image/`（尤其 `Image/Enemy/bat-128.png`、海报）
- `instruction.docx`
- `UI Resources/`
- 其他敌人的已有数值/帧，除非用户明确要求

---

## 7. Guardrails（本项目当前约定）

- **不要 commit**，除非用户明确要求。
- **不要** `git reset` / `git checkout -- .` / `git stash`；工作区有大量未提交改动。
- `Image/` 是 canonical 视觉源，只读；不要覆盖。
- `instruction.docx`、`UI Resources/` 不要动。
- 新素材必须：读取 `docs/IMAGE_GENERATION_RULES.md` → 生成到 `assets/generated/raw/bat/` → contact sheet → 用户批准 → 复制到 `assets/frames/bat/`。
- 不要用 pytest；验证用 `--smoke-test` + F1/F2 + 预览图。
- 不要写日志文件。
- F5 只热重载 JSON/PNG；改 `game/*.py`、`config.py`、`game/fx.py` 的常量需要重启 Python。
- 不要为了 Bat 改默认阵容；默认仍是 Lina vs 3 Venos，直到用户明确要求。
- 不要改其他敌人的伤害/判定/冷却/AI。

---

## 8. 相关文件索引

- Bat canonical：`Image/Enemy/bat-128.png`
- Bat 海报：`Image/Enemy/Posters/bat-poster.png`
- Cave 背景：`assets/generated/backgrounds/island-bat-cave-arena-16x9.png`
- Cave 记录：`assets/generated/backgrounds/bat-cave-generation-notes.md`
- 敌人类参考：`game/veno.py`（飞行/AI/每实例冷却）、`game/warrior.py`（技能槽/force_attack）
- 弹体参考：`game/projectile.py`（`AimedProjectile`、`AxeThrow`）
- 场景/生成入口：`game/scene.py`（`_place_enemies`、`spawn_projectile_from_event`、`spawn_projectile_impact`、`spawn_hit_fx`）
- 伤害公式：`game/combat.py::attack_damage`
- 数据校验：`game/config.py`
- 通用新增敌人指南：`docs/NEXT_SESSION_CHARACTERS.md`
- 素材流程：`docs/ASSET_PIPELINE.md`
- 生图规则：`docs/IMAGE_GENERATION_RULES.md`
- 当前 smoke：`main.py` Phase D 之后

---

## 9. 本次 session 结论（下个 session 填写）

```text
Q1 范围：
Q2 数量：
Q3 飞行：
Q4 技能 1：
Q5 技能 2 锁定：
Q6 返回/消失：
Q7 冷却/AI：
Q8 画布/pivot/hurtbox：
Q9 美术：
Q10 F7/Cave：
已完成：
smoke：
未完成/风险：
```
