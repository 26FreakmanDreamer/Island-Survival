# Next Session — Shadow Ninja 普通形态设计与接入

> 日期：2026-11-04（初版）；2026-11-06 更新为**已实现**。
> 状态：**普通形态已实现并验证**。`main.py --smoke-test` → **exit 0**，所有 `shadow_ninja_*` 为 true，
> `shadow_ninja_missing_frames == 0`、`shadow_ninja_fx_missing == 0`；35 帧 + 2 帧苦无 FX 已安装到
> `assets/frames/shadow_ninja/`。`instruction.docx` 未被修改。
> 基线：当前分支 `rhea-thorn-integration`，HEAD `0e749c1` + 未提交的 Rhea / Bat / Mech-Crab / 场景改动。
> 权威规格：`instruction.docx` 的 Shadow Ninja 段（P294–P311）。本文只摘录；**绝不修改 docx**。
> 本轮只做 **普通形态（normal form）**；P302–P305 的幻影形态（phantom form）只记录、不实现。
> 默认角色 **Lina**，默认敌人仍是 **Creepy Shooter**。
> 阅读顺序：本文 → `instruction.docx` 的 Shadow Ninja 段 → `AGENTS.md` → `README.md` →
> `docs/DESIGN_DECISIONS.md` → `docs/DEBUG.md` → `docs/ASSET_PIPELINE.md`；
> 如果要生成动画帧，再读 `docs/IMAGE_GENERATION_RULES.md`。

---

## 0. 给下一个 session 的开场 prompt（可直接复制）

```text
读取 docs/NEXT_SESSION_SHADOW_NINJA.md、instruction.docx 的 Shadow Ninja 段（P294–P311）、
AGENTS.md、README.md、docs/DESIGN_DECISIONS.md、docs/DEBUG.md、docs/ASSET_PIPELINE.md；
如果要生成动画帧，再读 docs/IMAGE_GENERATION_RULES.md。

先运行 .venv/Scripts/python.exe main.py --smoke-test，确认基线 exit 0，然后按本文 §5 的
Q1–Q12 一次性 grill 我。每项给出当前 docx 原文、建议值和影响范围。我确认后，先把答案写入
本文 §6“已确认决策”，再按 §7 的顺序实施；不要先改代码/JSON/素材。

本轮范围：只新增单个 enemy Shadow Ninja 的“普通形态”（普通攻击/技能 1–3/被动印记/AI），
技能 4 的幻影形态留给下一个 session；不要实现幻影形态、幻影三技能、变身无敌或变身清印记。
包含数据、类、AI、场景、smoke、F1/F2/F6 验证，以及经批准的动画/FX。

不要修改 instruction.docx、Image/、UI Resources/、sketch/、其他角色/敌人、背景/BGM；
不要用 pytest；验证用 --smoke-test、F1/F2/F6 和预览图；不要 commit，除非我明确要求。
素材按 base → 动作帧 contact sheet → 游戏内预览的顺序逐轮审批；不要直接把
Image/Enemy/shadow-ninja-256.png 当运行时帧，也不要把苦无/冲刺残影/印记烘焙进角色帧。
```

---

## 1. 本轮范围

### 1.1 做

- 新增单个 enemy **Shadow Ninja（普通形态）**，F7 可选，默认敌人不变。
- 普通形态的 4 个技能槽：技能 1 苦无近刺、技能 2 暗影苦无投掷、技能 3 冲刺、技能 4 **留空**。
- 被动：技能 1/2/3 命中叠加印记（最多 3 层），第 4 次命中引爆：额外 `atk` 伤害 + 眩晕 1s，
  印记重置为 1 层。
- 生命、攻击力、移速跟随当前玩家角色：HP/ATK 与角色相同，移速为角色的 1.5 倍。
- 普通形态的 AI、霸体/控制交互、投射物、冲刺穿身、眩晕、印记 HUD、F1/F2 调试。
- 普通形态的动画帧、苦无投射物 FX、命中 FX、印记 pips / 引爆特效。
- `main.py` smoke、F7 顺序、既有测试同步更新。

### 1.2 不做（本轮明确排除）

- **幻影形态**（技能 4）、幻影三技能、变身无敌、变身清印记/负面、幻影独立冷却。
- 全游戏战斗 UI（顶部红色双血条、蓝色被动条、Q/E 技能 logo、1–4 special skill 购买次数/
  每局一次）——当前项目是 debug sandbox，仍用 F1/F2；不要顺手重做 UI。
- 商店、食物、等级、金币、存档、BGM/背景切换、战斗入场 poster/VS 动画。
- 其他角色/敌人、`Image/`、`UI Resources/`、`sketch/`、`instruction.docx` 的修改。
- 多体编组；Shadow Ninja 单只（`count` 缺省 1）。
- pytest、commit/push（除非用户明确要求）。

---

## 2. instruction.docx 原文与事实

### 2.1 原文（P294–P311，普通形态）

> **Shadow Ninja**
> 攻击和血量都和面对的character相同
> 移速为面对character的1.5倍
> 形象：`Image\Enemy\shadow-ninja-256.png`
> 被动：使用技能1，2，3攻击到敌人会在敌人身上叠加印记，最多叠加3层。第4次攻击会引爆印记
> （印记变为0层），造成atk伤害，并将目标眩晕1s，并重新开始叠印记，即引爆后敌人又获得一层印记
> （印记变为1层）。
> 技能1：（0.5s）手持苦无攻击敌人（近），造成atk伤害
> 技能2：（5s）向前方丢出苦无（暗影）（远程，低），造成1.2atk，眩晕1s
> 技能3：（8s）向前方冲刺一段距离（约为半个屏幕距离），造成1.5atk伤害，冲刺时无视碰撞箱体积。
> 技能4：（15s）变身幻影形态，
> 形象：`Image\Enemy\shadow-ninja-phantom-no-aura-256.png`
> 幻影形态期间（包括变身帧）不会受到任何伤害，免疫一切负面效果，刷新对方在自己身上叠的印记和
> 负面状态，幻影形态不可让对方叠印记，或者任何被动，无hitbox。
> 幻影形态的每个技能拥有全新的动作模型，且技能冷却独立计算。幻影形态每个技能只能使用一次，
> 3个技能全部使用完毕自动解除形态。解除形态后此技能才进入冷却。
> AI：
> 距离较近时优先2控制+1靠近攻击；如果2冷却，直接1攻击；多叠被动。
> 距离较远，可先2，等到2的暗影离目标很近（期间可以向目标移动），则释放3逼近，之后使用1。
> 也可以直接3突进，再使用2，1.
> 在距离近时，如果血量较低，也可以3技能拉开距离，等待技能冷却，多用远程控制。
> 当血量较低，或者将会受到大量伤害时，优先使用4变身。变身期间AI如上。

### 2.2 幻影形态原文（P302–P305，本轮只记录，不实现）

> 技能4：（15s）变身幻影形态，
> 形象：`Image\Enemy\shadow-ninja-phantom-no-aura-256.png`
> 幻影形态期间（包括变身帧）不会受到任何伤害，免疫一切负面效果，刷新对方在自己身上叠的印记和
> 负面状态，幻影形态不可让对方叠印记，或者任何被动，无hitbox。
> 幻影形态的每个技能拥有全新的动作模型，且技能冷却独立计算。幻影形态每个技能只能使用一次，
> 3个技能全部使用完毕自动解除形态。解除形态后此技能才进入冷却。

幻影形态的 3 个技能名/数值/动作模型 **docx 未给出**；下一个 session 需要单独设计并 grill。
本轮的技能 4 槽位留空（`null`），F2 显示 `-`，Z 键无操作；AI 不进入变身分支。

### 2.3 已明确的事实

- Shadow Ninja 位于 `instruction.docx` 的 **Enemy** 段，是敌人，不是可玩角色；F7 可选。
- 普通形态没有“专属场景”段落；docx 只给形象、HP/ATK/移速、被动、技能 1–3、技能 4 变身和 AI。
- 普通形态的 HP/ATK 不是固定值，而是复制“面对的 character”；当前三个可玩角色都是
  HP 100 / basic_atk 20 / extra_atk 0 / walk 260（见 `game/data/stats.json`）。
- 技能 1 的 `(0.5s)` 是动作时长；docx 没有给技能 1 的冷却。技能 2 冷却 5s，技能 3 冷却 8s，
  技能 4 冷却 15s。
- 技能 2 是“远程，低”：按 docx 的子弹分类，低弹道击中腿部，跳跃可躲、俯身不可躲；
  固定低车道，不随角色/敌人身高变化。
- 技能 3 的“无视碰撞箱体积”没有明确是仅穿角色，还是连 platform/barrier 也穿；需要 §5 Q5 确认。
- 印记在“敌人”身上——Shadow Ninja 的敌人就是 player character，所以印记应显示在 **玩家** 身上，
  不是 Shadow Ninja 自己身上。这与 Nyra 的印记方向相反（Nyra 把印记叠在敌人身上）。
- 第 4 次攻击引爆后印记为 **1 层**（不是 0 层）；“造成 atk 伤害”是额外伤害还是替换第 4 次攻击
  本身的伤害，docx 没有写清；需要 §5 Q6 确认。
- AI 的“低血量优先 4 变身”本轮不实现；普通形态低血量策略用技能 3 拉开距离 + 技能 2 控制。
- 全游戏战斗 UI/BGM/商店/等级不在当前 sandbox 实现范围内；本轮沿用现有 enemy HP 条 + F1/F2。

### 2.4 docx 没有写、必须由本轮确定的内容

- 普通形态的 hitbox/ hurtbox / `stage_body_width` / 画布 / pivot / 体高。
- 技能 1 的冷却、前摇/命中窗口、击退、hitstun/hitstop。
- 技能 2 的施法时长、出手帧、苦无速度/射程/半径、是否被 block 挡住、命中眩晕与印记的先后。
- 技能 3 的冲刺速度/时长/距离、是否穿 platform/barrier、命中后击退、冲刺结束后的落点处理。
- 印记的 UI（pips/图标/颜色）、是否与 Nyra 共用字段、引爆的伤害顺序/减伤/霸体交互。
- AI 的决策间隔、技能间隔、近/远距离阈值、苦无飞行中何时接冲刺、是否使用普通跳跃/平台。
- 场景与出生点、F7 顺序、默认敌人是否保持 Creepy Shooter。
- 动画帧数/动作列表/FX 清单与审批顺序。

---

## 3. 当前实现快照（代码事实）

### 3.1 玩家角色与动态数值

- `game/data/stats.json`：
  - `lina` / `nyra` / `rhea` 均为 `hp 100`、`basic_atk 20`、`extra_atk 0`、
    `move.walk 260`、`move.jump_v 760`、`move.gravity 2200`；
    standing hurtbox `[56, 210]`，crouching `[56, 130]`。
- `Fighter` 保存 `max_hp`、`hp`、`basic_atk`、`extra_atk`、`atk`；`set_attack_stats(cfg)` 设
  `atk = basic_atk + extra_atk`。各 playable 类在构造时设置 `walk_speed`。
- `ArenaScene._rebuild_fighters()`（`game/scene.py` 约 232）**先创建 player，再创建 enemies**；
  `create_fighter(entry, store, stage)` 不把 player 传给 enemy 构造函数。
- `ArenaScene.reset()`（约 372）依次 `player.reset()`、`enemy.reset()`，`reset()` 没有 scene 参数。
- `set_character()` / `set_enemy()` 都走 `_rebuild_fighters()`。
- 结论：Shadow Ninja 需要一个 **scene 侧的同步钩子**（见 §4.2 / §7），不能在 `__init__` 里直接
  拿 player；也不要在每 tick 重拷 `max_hp`（会把战斗中的临时变化/伤害重置）。

### 3.2 敌人接入点

- `game/roster.py` 的 `FIGHTER_CLASSES` 注册 class；`create_fighter` 用 roster entry 构造。
- `game/config.py` 的校验列表：
  - `REQUIRED_STATS`、`REQUIRED_ATTACKS`；
  - `REQUIRED_*_CLIPS`、`ROSTER_CLASSES`、`ANIMATED_CLASSES`；
  - `frame_size`/`pivot` 检查；Mech-Crab 有 clip 总时长 = attack duration、
    `warning+active+recovery = duration` 的额外校验，可复用/简化。
- `game/data/roster.json` enemy entry 需要：`name`、`class`、`stats`、`spawn`、`clips`、
  `frame_size`、`pivot`、`frames_dir`、`fallback`、`skill_slots`、`separates`、`decides_match`；
  可选 `stage_variant`。
- `game/data/animations.json` 的 enemy clip 结构：
  `{"idle": {"loop": true, "frames": [...], "durations": [...]}, ...}`；
  frame 路径相对 `assets/frames/<frames_dir>/`。
- `game/data/debug.json` 的 `stage` / `stage_variants` 每个都必须有
  `REQUIRED_STAGE` 的 key；roster 的 `spawn` 必须在对应 stage 的 `*_spawn` 中存在。
- `main.py` 需要 F7 链、roster_ok、smoke flags、SMOKE 打印和最终 conjunction 同步。

### 3.3 印记系统（Nyra 的现成实现与缺口）

- `Fighter.__init__`：`self.marks = 0`、`mark_burst_time`、`mark_burst_damage`。
- Nyra 的被动在 `game/nyra.py:331` `on_hit_success`：
  - `attack.get("marks_on_hit")` 决定是否叠印记；
  - `target.marks += 1`，`< 4` 直接返回；
  - 第 4 层：`amount = 1.8 * self.atk + 0.10 * target.max_hp`，按 `damage_reduction()` 折减，
    `target.take_hit(...)`，`mark_burst_time = 0.4`，`target.marks = 1`；
  - hitstop 0.10 + 粒子。
- `Fighter.take_hit` 在 KO 分支清 `marks`；`reset_common` 也清。
- `game/scene.py:1282` `_draw_mark_fx`：
  - 仅当 `self.player` 有 `mark_detonations`（即 player 是 Nyra）才画；
  - 只遍历 `self.enemies`，在敌人头顶画 3 个蓝色菱形 pips + 引爆环。
- **缺口**：Shadow Ninja 的印记在 player 身上，不能直接复用这个绘制路径；Nyra 与 Shadow Ninja
  同场时两边都可能有印记（Nyra 在敌人身上、Shadow 在 player 身上）。建议 **新增独立的
  `shadow_marks` / `shadow_mark_burst_time` 字段**，不要复用 Nyra 的 `marks`，避免 UI/来源混淆。
- `game/status.py`：`StatusSet.add("stun", ...)` 在目标有 `super_armor` 时会直接忽略；
  Rhea/Nyra 的 `take_hit` 在霸体下只扣血、不进 HURT。引爆伤害照常结算，眩晕按霸体规则被免疫。
- `resolve_hit` 只在 hitbox 命中后调用 `attacker.on_hit_success(attack, target, bonus)`；
  projectile 命中走 `resolve_projectile_hit` → `projectile.owner.on_projectile_hit(projectile)`，
  **不会**调用 `on_hit_success`。技能 2 的印记/眩晕必须在 `on_projectile_hit` 里处理。

### 3.4 投射物 / 冲刺 / 眩晕

- `game/config.py` 的 `PROJECTILE_KINDS` 是白名单；`attacks.json` 的 projectile event 必须用
  白名单里的 kind，否则 config 校验失败。
- `game/scene.py:913` `spawn_projectile_from_event` 按 `projectile` kind 分支构造：
  `AimedProjectile`（venom/web）、`ShurikenProjectile`（Rhea）、`SonicWave`、Creepy 子弹等。
  新苦无建议新增独立 `ShadowKunaiProjectile`，避免改 Rhea 的 shuriken 贴图映射。
- `AimedProjectile` / `ShurikenProjectile` 的命中结算都会调用 `resolve_projectile_hit`，
  再由 owner 的 `on_projectile_hit` 加状态；`status`/`status_duration` 需要 projectile 对象保存。
- `AttackRuntime` 的 `dash` event 直接调 `scene.stage.move_x(attacker, facing*speed*dt)`；
  `Stage.move_x` 会撞墙、撞 block，除非 `fighter.ignore_terrain` 为真。
- `_separate_fighters` 只检查 **player** 的 `attack_runtime.data["pass_through_enemy"]`；
  enemy 的 dash 即使写了 `pass_through_enemy` 也不会跳过分离。敌人冲刺穿身要用
  `self.ignore_separation = True`（Mech-Crab 的 leap 就是这样），结束后清掉。
- 冲刺穿 terrain 需要 `ignore_terrain = True`；结束时要 `Stage.resolve_overlap` 或落点处理，
  否则可能卡进 platform。建议普通形态只穿角色、不穿 block（见 Q5）。
- 新增 hit FX 名称必须加入 `ArenaScene.spawn_hit_fx`（`game/scene.py` 约 808）；
  projectile 的施法/命中特效要在 `spawn_projectile_cast_fx` / `spawn_projectile_impact` 里加
  `shadow_kunai` 分支；projectile event 上的 `hit_fx` 不会被 `resolve_projectile_hit` 使用。

### 3.5 场景 / F7 / smoke

- 默认 stage：ground 620、walls [90,1190]、两个 barrier（400..490、700..790）、
  长 platform 170..649 surface 220、短 platform 796..1110 surface 268、两条 ladder；
  spawn：player 280,620 / dummy 600,620 / warrior 600,620 / veno 820,620 / bat 820,470。
- `stage_variants` 已有 `creepy_shooter`、`warrior`、`bat`、`veno`、`mech_crab`；
  目前 **没有** `shadow_ninja` variant，也没有 `shadow_ninja_spawn`。
- 默认敌人是 `creepy_shooter`（`default_enemy_ok`）；F7 顺序当前是
  warrior → veno → bat → creepy_shooter → mech_crab → dummy。
- `main.py` F7 断言在约 2665–2672：`f7_cycle_ok` / `f7_bat_ok` / `f7_creepy_ok` /
  `f7_mech_crab_ok` / `f7_dummy_ok`；`roster_ok` 约 2700 汇总。
- `main.py` smoke 的 Mech-Crab phase 在约 3505–3813；scene variant 检查在约 3870；
  SMOKE 打印在约 3890；最终 conjunction 在约 4168+。
- `platform_spawn_clear_ok` 会遍历 roster 检查所有 spawn 的 body 不与 platform 相交；
  新 spawn 必须在场景中是干净的。
- 当前没有 `assets/frames/shadow_ninja/`；`Image/Enemy/shadow-ninja-256.png` 是 256×256 RGBA，
  alpha bbox 几乎满画布（0,3–255,254）；另有 `shadow-ninja-phantom-no-aura-256.png`、
  `shadow-ninja-phantom-shadow-256.png` 和 `Image/Enemy/Posters/shadow-ninja-poster-v5.png`。
- `Sound Clip/BGM/shadow_ninja_battle_music.ogg` / `_v2.wav` 存在，但项目没有 BGM 播放层；
  本轮不接音频。

---

## 4. 建议设计（draft，必须经 §5 grill 确认）

### 4.1 命名与文件

| 项 | 建议值 |
|---|---|
| roster id | `shadow_ninja` |
| Python 类 | `game/shadow_ninja.py::ShadowNinja` |
| stats key | `shadow_ninja` |
| attack ids | `shadow_kunai_slash` / `shadow_kunai_throw` / `shadow_dash` |
| clips key | `shadow_ninja_clips` |
| frame size / pivot | `shadow_ninja_frame_size [384,384]` / `shadow_ninja_pivot [192,372]` |
| frames dir | `assets/frames/shadow_ninja/`；苦无 FX 在 `assets/frames/shadow_ninja/fx/` |
| fallback | `Image/Enemy/shadow-ninja-256.png` |
| spawn key | `shadow_ninja_spawn` |
| stage variant | `shadow_ninja`（建议 flat variant，见 Q9） |
| skill_slots | `["shadow_kunai_slash","shadow_kunai_throw","shadow_dash",null]` |
| 数量 | 1（`count` 缺省） |
| F7 | warrior → veno → bat → creepy_shooter → mech_crab → **shadow_ninja** → dummy |

`roster.json` 建议 entry（若 Q9 选 flat variant）：

```json
"shadow_ninja": {
  "name": "Shadow Ninja",
  "class": "shadow_ninja",
  "stats": "shadow_ninja",
  "spawn": "shadow_ninja_spawn",
  "stage_variant": "shadow_ninja",
  "clips": "shadow_ninja_clips",
  "frame_size": "shadow_ninja_frame_size",
  "pivot": "shadow_ninja_pivot",
  "frames_dir": "shadow_ninja",
  "fallback": "Image/Enemy/shadow-ninja-256.png",
  "skill_slots": ["shadow_kunai_slash", "shadow_kunai_throw", "shadow_dash", null],
  "separates": true,
  "decides_match": true
}
```

若 Q9 选默认 stage：删掉 `stage_variant`，在 `debug.json` 的默认 `stage` 加
`"shadow_ninja_spawn": [1000, 620]`。若选 flat variant：在 `debug.json` 新增
`stage_variants.shadow_ninja`，复制默认 `ground_y/walls/lane_heights` 和全部 spawn keys，
把 `blocks`/`ladders` 设为 `[]`，并加 `shadow_ninja_spawn`。

### 4.2 基础属性与动态同步

建议 `stats.json` 先放一份 fallback（当前角色数值），运行时再用 scene 钩子覆盖：

```json
"shadow_ninja": {
  "hp": 100,
  "basic_atk": 20,
  "extra_atk": 0,
  "stage_body_width": 100,
  "move": { "walk": 390, "jump_v": 760, "gravity": 2200 },
  "cooldowns": { "slash": 0.0, "throw": 5.0, "dash": 8.0 },
  "hurtbox": { "standing": [56, 210], "crouching": [56, 130] },
  "ai": {
    "close_range": 170.0,
    "far_range": 520.0,
    "level_tolerance": 60.0,
    "decision_interval": 0.12,
    "low_hp_pct": 0.4,
    "kunai_close_distance": 160.0,
    "skill_gap": 0.2
  }
}
```

同步规则（推荐）：

- 在 `ArenaScene._rebuild_fighters()` 完成 player + enemies 构造、`_place_enemies()` 之后，
  对每个 enemy 调用可选的 `sync_from_player(self.player, full_heal=True)`。
- 在 `ArenaScene.reset()` 完成 `player.reset()` + `enemy.reset()` + `_place_enemies()` 后，
  再调用一次；保证 F9 后 HP/ATK/移速仍对应当前角色。
- `ShadowNinja.sync_from_player(player, full_heal)`：
  - `max_hp = player.max_hp`；
  - `basic_atk = player.basic_atk`；`extra_atk = player.extra_atk`；`atk = player.atk`；
  - `walk_speed = player.walk_speed * 1.5`；
  - `full_heal` 时 `hp = max_hp`；
  - 不改 `jump_v/gravity/hurtbox`（这些用自身数据）。
- 不在每 tick 重拷；不在战斗中途把 player 的临时 max HP/atk 变化反向写回敌人。
- 切换角色（`set_character`）会 `_rebuild_fighters`，自动同步；F7 切换敌人也一样。

### 4.3 被动印记（建议独立字段）

建议在 `Fighter` 增加：

```python
self.shadow_marks = 0
self.shadow_mark_burst_time = 0.0
self.shadow_mark_burst_damage = 0.0
```

- `update_common` 递减 `shadow_mark_burst_time`。
- `take_hit` 的 KO 分支、`reset_common` 清空这三个字段。
- `ShadowNinja._add_shadow_mark(scene, target)`：
  - `target.hp <= 0` 或 `target.invincible` → 不加；
  - `target.shadow_marks += 1`；`< 4` 返回；
  - 引爆：`amount = self.atk * (1 - target.statuses.damage_reduction())`；
    `target.take_hit(amount, 0.0, 0.0, self.facing)`；
  - 若目标仍存活：`target.statuses.add("stun", 1.0, source="shadow_ninja_mark")`
    （霸体会在 `StatusSet.add` 里自动免疫）；
  - `target.shadow_mark_burst_time = 0.4`；`target.shadow_mark_burst_damage = amount`；
  - `target.shadow_marks = 1 if target.hp > 0 else 0`；
  - `scene.hitstop = max(scene.hitstop, 0.08)`；粒子/环特效。
- 只有技能 1/2/3 命中调用；技能 4（本轮 null）和幻影形态不调用。
- 印记不衰减、不过期；KO/reset 清空。
- 引爆的“额外 atk 伤害”与第 4 次攻击本身的伤害是 **两段**（推荐；见 Q6）。
- 若第 4 次命中本身是技能 2（已带 1s 眩晕），引爆的 1s 眩晕会用同一个 `stun` 状态刷新；
  当前 `StatusSet.add` 不叠加，所以总时长仍是 1s。如果希望变成 2s，需要额外规则（Q6）。
- UI：在 player 头顶画 3 个紫色 pips（第 4 次命中时满 3 格 → 引爆环 → 变回 1 格）；
  F2 增加 `SHADOW MARKS n/3`。不要改 Nyra 的蓝色菱形绘制路径。

### 4.4 技能 1–3（建议数据）

> 以下为 draft；`duration` 必须与 clip 总时长一致，且 hitbox 窗口落在动作帧内。

```json
"shadow_kunai_slash": {
  "basic_mult": 1.0, "extra_mult": 1.0,
  "duration": 0.5, "lunge": 0, "lunge_time": 0.0,
  "energy_gain": 0, "hitstun": 0.2, "hitstop": 0.05,
  "events": [
    {
      "t": 0.18, "until": 0.28, "type": "hitbox",
      "box": [20, -170, 130, 120],
      "knockback": 80,
      "hit_fx": "shadow_slash_hit"
    }
  ]
}
```

- 近身苦无刺/斩；`atk` = 1.0×；命中叠 1 层印记。
- 建议技能 1 无硬冷却（`cooldowns.slash = 0.0`），由 0.5s 动作和 AI 的 0.7s 攻击节奏控制；
  若用户希望更慢，可改为 0.6–0.8s。

```json
"shadow_kunai_throw": {
  "basic_mult": 1.2, "extra_mult": 1.2,
  "duration": 0.45, "lunge": 0, "lunge_time": 0.0,
  "energy_gain": 0, "hitstun": 0.15, "hitstop": 0.04,
  "events": [
    {
      "t": 0.22, "type": "projectile",
      "id": "shadow_kunai_throw",
      "projectile": "shadow_kunai",
      "lane": "low",
      "speed": 900, "range": 900,
      "origin_forward": 30,
      "hitbox_radius": 10,
      "knockback": 0,
      "status": "stun",
      "status_duration": 1.0
    }
  ]
}
```

- 低车道（`lane_heights.low = 60`px above feet），跳跃可躲、俯身不可躲。
- 默认不穿 block（`penetrates_blocks` 不设或 false）；若用户要穿透，显式加 true。
- 命中：1.2×atk + 眩晕 1s + 叠 1 层印记。眩晕/印记在 `ShadowNinja.on_projectile_hit` 里处理；
  projectile 的 `status`/`status_duration` 必须由新 projectile 类保存。
- 投射物新增 `ShadowKunaiProjectile`（直线、低车道、单次命中、撞 block/墙/射程消失、
  2 帧水平苦无贴图，不旋转、一亮一暗），不要直接复用 Rhea 的 shuriken 贴图映射。

```json
"shadow_dash": {
  "basic_mult": 1.5, "extra_mult": 1.5,
  "duration": 0.45, "lunge": 0, "lunge_time": 0.0,
  "energy_gain": 0, "hitstun": 0.3, "hitstop": 0.08,
  "events": [
    { "t": 0.06, "until": 0.45, "type": "dash", "speed": 1600 },
    {
      "t": 0.06, "until": 0.45, "type": "hitbox",
      "box": [0, -80, 90, 80],
      "knockback": 120,
      "hit_fx": "shadow_dash_hit"
    }
  ]
}
```

- 1600px/s × 0.39s（t=0.06–0.45）≈ 640px，接近“半个屏幕”。
- 冲刺期间 `ignore_separation = True`，可穿过 player 身体；是否穿 platform/barrier 见 Q5。
- 单次命中、1.5×atk、叠 1 层印记；撞墙/block 时按 `Stage.move_x` 停止。
- 冲刺结束清 `ignore_separation`；若开启 `ignore_terrain`，结束必须 resolve overlap。

### 4.5 技能 4 / 幻影形态（本轮不实现）

- `skill_slots[3] = null`；F2 显示 `-`；Z 键无操作；AI 不进入变身分支。
- 不要为了“看起来完整”而做一个半成品变身/无敌；幻影形态单独开 session，按 P302–P305 设计。
- 本轮低血量 AI 用技能 3 拉开距离 + 技能 2 控制，不进入技能 4。

### 4.6 AI（建议）

- 决策节流：`decision_interval 0.12`；`skill_gap 0.2` 内只走位。
- 面向目标（8px deadzone）；只在地面行动；本轮不做 ladder。
- 近距离（`<= 170`）：
  - 技能 2 可用 → 先投苦无（控制 + 印记）；
  - 技能 2 冷却 → 技能 1；
  - 低血量（`hp <= max_hp * 0.4`）→ 技能 3 向反方向拉开，等冷却，多用技能 2。
- 远距离（`> 170`，`<= 520`）：
  - 技能 2 可用 → 投苦无；苦无飞行期间向目标移动；
  - 当自己的苦无离目标很近（建议 `<= 160`px，或即将命中）且技能 3 可用 → 冲刺逼近；
  - 冲刺后接技能 1；若技能 2 不可用，可直接技能 3 → 技能 2 → 技能 1。
- 超出 520：走向目标，等技能 2/3 冷却；不要空放。
- 苦无追踪：遍历 `scene.projectiles`，筛选 `owner is self` 且 `kind == "shadow_kunai"`；
  若没有自己的苦无（已命中/被挡/消失），不要继续等。
- 不普攻（敌人没有普通攻击）、不爬梯、不使用技能 4。
- 若选择默认 stage（有 platform），需要 §5 Q7 决定是否加基础跳跃/平台追击；若选 flat variant，
  不需要跳跃 AI，只保留 jump 受击/击飞动画。

### 4.7 HUD / 调试

- `ShadowNinja.show_health_bar = True`；默认 hurtbox 高度 210，不需要 `health_bar_lift`。
- F1：56×210 hurtbox、技能 1/3 hitbox、技能 2 低车道线、冲刺路径。
- F2：
  - 四个 skill slot：`shadow_kunai_slash`、`shadow_kunai_throw`、`shadow_dash`、`-`；
  - 三个冷却 + `skill_gap`；
  - 当前 attack/clip/frame；
  - `SHADOW MARKS n/3`（player 身上的印记）；
  - AI 开关。
- 印记 pips：player 头顶 3 个紫色菱形/苦无形；引爆时画 0.4s 环 + 粒子。
- 不重做全游戏战斗 UI；不接 BGM/背景切换。

### 4.8 场景 / 出生点（建议）

- 建议新增 flat `stage_variants.shadow_ninja`：沿用默认背景/`ground_y`/`walls`/`lane_heights`，
  但 `blocks: []`、`ladders: []`，player `[280,620]`，ninja `[1000,620]`。
  - 理由：技能 3 只有水平冲刺，普通跳跃也够不到 400px 高的默认 platform；有 platform 时玩家
    可以站平台让战斗停摆。
  - 若用户坚持默认 stage，则改为在默认 `stage` 加 `shadow_ninja_spawn`，并接受平台限制/另加跳跃 AI。
- `debug.json` stage variant 必须包含 `REQUIRED_STAGE` 的全部 key；`blocks`/`ladders` 可为空。
- 背景不变；`Sound Clip/BGM/shadow_ninja_battle_music.ogg` 存在但本轮不接。
- spawn `[1000,620]` 需通过 `platform_spawn_clear_ok`。

### 4.9 动画 / FX（建议预算）

建议 384×384 画布、pivot (192,372)、body 214（与 Nyra/Rhea/Creepy 一致）；若头发/苦无在
384 边缘被裁，再改 512×512 / pivot (256,500)，在 base 审批时定。

| clip | 帧数 | durations | 说明 |
|---|---:|---|---|
| idle | 4 | 0.30×4 | 呼吸、头发/衣摆微动，苦无低持 |
| walk | 6 | 0.10×6 | 潜行步，左右腿交替，不滑步 |
| jump | 2 | 0.20×2 | 上升/下落，屈膝 |
| hurt | 2 | 0.10×2 | 后仰，头发/衣摆 |
| ko | 4 | 0.25/0.20/0.25/0.30 | 失衡、跪倒、倒地 |
| shadow_kunai_slash | 5 | 0.07×5 | 前摇 2 + 斩 2 + 收 1；hitbox t=0.14–0.24 |
| shadow_kunai_throw | 5 | 0.09×5 | 前摇 2 + 投掷 2 + 收 1；t=0.22 出手，02 帧为发射帧 |
| shadow_dash | 5 | 0.09×5 | 压低/突进/收势；dash t=0.06–0.45 |
| stun | 1 | 0.50 | 眩晕姿态 |

- 合计 35 帧；苦无投射物 2 帧 32×32（水平、不旋转、一亮一暗）；冲刺残影/命中特效程序化。
- 不把苦无、残影、印记、命中火花烘焙进角色帧；角色帧只做动作。
- 生成必须遵守 `docs/IMAGE_GENERATION_RULES.md`：同壳体/武器/脚比例、无穿模、武器握持正确、
  透明背景、无影子/文字/边框、尺寸锁定。
- canonical 是 3/4 动态姿势；运行时需要重新生成 **右向侧视** base（可镜像），不要直接把
  `Image/Enemy/shadow-ninja-256.png` 当运行时帧。
- 导入模板：

```text
py tools/import_frames.py --action idle --src assets/generated/raw/shadow_ninja/idle --out assets/generated/staged/shadow_ninja/idle --base assets/generated/base/shadow_ninja_side_base.png --body-height 214 --canvas 384 --pivot-x 192 --pivot-y 372 --expect 4
py tools/contact_sheet.py --action shadow_ninja_idle --frames assets/generated/staged/shadow_ninja/idle --out assets/generated/contact_sheets/shadow_ninja_idle_v1.png --durations 0.30,0.30,0.30,0.30 --cell 384 --pivot-x 192 --pivot-y 372
```

- 建议新增 `tools/preview_shadow_ninja.py`，输出到
  `assets/generated/contact_sheets/shadow_ninja_ingame_v1/`：
  01_startup、02_slash、03_throw_low、04_throw_blocked、05_dash、06_marks_1、07_marks_2、
  08_marks_3、09_mark_burst、10_stun、11_idle、12_f1_overlay、13_f2_panel、14_stage。

---

## 5. 开工前必须 grill 的问题

> 每项请用户确认；确认后写入 §6。未确认前不要改代码/JSON/素材。

### Q1 — 本轮是否只做普通形态？

docx 的 Shadow Ninja 包含技能 4 变身幻影形态；用户本轮明确说“普通形态”。

➡️ **建议**：只做普通形态；`skill_slots[3] = null`，Z 键无操作，F2 显示 `-`，AI 不进入变身。
幻影形态（含变身帧、无敌、清印记/负面、3 个一次性技能）留到下一个 session。

### Q2 — HP/ATK/移速如何复制？

docx：攻击和血量与面对 character 相同；移速为 1.5 倍。

➡️ **建议**：在 scene 重建/重置后，把 `player.max_hp`、`player.basic_atk`、`player.extra_atk`、
`player.atk`、`player.walk_speed * 1.5` 拷到 Shadow Ninja；`full_heal` 时 HP 回满；不每 tick
重拷、不在战斗中反向同步。当前三角色都是 100 HP / 20 ATK / 260 walk，所以实际是 100/20/390。

### Q3 — 技能 1 的冷却与节奏？

docx 只写 `(0.5s)`，没有冷却。

➡️ **建议**：技能 1 动作 0.5s、无硬冷却（`cooldowns.slash = 0.0`），由 AI 的攻击节奏
（约 0.7s 一次）和 0.5s 动作限制；F2 显示 0.0。

### Q4 — 技能 2 的苦无参数与 block 行为？

docx：向前方丢苦无（暗影，远程，低），1.2atk + 眩晕 1s，冷却 5s。

➡️ **建议**：施法 0.45s、t=0.22 出手；低车道（60px）；速度 900、射程 900、半径 10、
出手点前方 30px；不穿 block（撞 barrier/platform 消失）；命中 1.2atk + 眩晕 1s + 1 层印记。
若希望苦无穿 block，再加 `penetrates_blocks: true`。

### Q5 — 技能 3 的冲刺距离与“无视碰撞箱体积”范围？

docx：向前冲刺约半个屏幕，1.5atk，冲刺时无视碰撞箱体积，冷却 8s。

➡️ **建议**：1600px/s × 0.39s（t=0.06–0.45）≈ 640px；单次命中；冲刺期间 `ignore_separation = True`
穿 player 身体；仍撞墙和 barrier/platform（不穿地形）。如果用户希望连 block 也穿，需开启
`ignore_terrain` 并在冲刺结束 resolve overlap；风险更高。

### Q6 — 第 4 次命中的引爆细节？

docx：第 4 次攻击引爆印记（印记变 0），造成 atk 伤害，眩晕 1s，然后印记变 1。

➡️ **建议**：第 4 次攻击 **先结算自身技能伤害**，再额外结算 `atk` 引爆伤害（两段）；
引爆伤害受 `damage_reduction` 影响，命中霸体时伤害照扣、眩晕被 `StatusSet` 免疫；
引爆后印记 = 1（目标死亡则 0）；不衰减、不跨 reset 保留。印记用独立
`shadow_marks` 字段 + 玩家头顶紫色 pips，避免与 Nyra 的蓝色印记混淆。
若第 4 次命中是技能 2，自身 1s 眩晕与引爆 1s 眩晕当前会刷新同一个 `stun`，总时长 1s；
建议保持刷新（不叠加），若用户要 2s 再单独处理。

### Q7 — AI 是否要平台/跳跃能力？

docx AI 只写距离策略，没有平台/跳跃；默认 stage 有 400px 高 platform。

➡️ **建议**：如果 §Q9 选 flat 场景，则不需要平台 AI，只保留 jump 受击/击飞动画；如果选默认
stage，则加基础跳跃（2 帧）与简单的“目标在上方时走向平台边缘起跳”，不做 ladder。
苦无飞行中用 `scene.projectiles` 跟踪自己的 `shadow_kunai`，距离目标 ≤160px 时接技能 3。

### Q8 — 身体 / hurtbox / 画布？

docx 只给 256×256 形象和“与角色相同”的数值。

➡️ **建议**：384×384、pivot (192,372)、body 214；hurtbox 56×210、`stage_body_width` 100
（人形标准，与 Lina/Rhea/Creepy 一致）。若 base 的头发/苦无被裁，再改 512×512 / pivot (256,500)。

### Q9 — 场景与出生点？

docx 没有 Shadow Ninja 专属场景。

➡️ **建议**：新增 flat `stage_variants.shadow_ninja`（无 barrier/platform/ladder），
player `[280,620]`、ninja `[1000,620]`，背景不变；避免玩家站平台导致战斗停摆。
备选：默认 stage + `shadow_ninja_spawn`，但需要跳跃 AI 且仍有 400px 平台限制。

### Q10 — 动画预算与审批顺序？

➡️ **建议**：35 帧（idle 4 / walk 6 / jump 2 / crouch 1 / hurt 2 / KO 4 / 三技能各 5 / stun 1）；
苦无 FX 2 帧。严格按 base → 每动作 contact sheet → 游戏内预览逐轮审批；最终
`shadow_ninja_missing_frames == 0`、`shadow_ninja_fx_missing == 0`。

### Q11 — F7 顺序与默认敌人？

docx 没有规定。

➡️ **建议**：插在 `mech_crab` 之后、`dummy` 之前；
`warrior → veno → bat → creepy_shooter → mech_crab → shadow_ninja → dummy`；
默认敌人仍是 **Creepy Shooter**（`default_enemy_ok` 不变）。

### Q12 — HUD / 范围控制？

docx 的完整战斗 UI（顶部血条/蓝色被动条/QE logo/1–4 special skill 购买次数）属于完整游戏，
当前 sandbox 没有实现。

➡️ **建议**：本轮沿用 sandbox 的 enemy HP 条、F1/F2、玩家头顶印记 pips；不做完整战斗 UI、
不接 BGM/背景切换/商店/等级。

---

## 6. 已确认决策（2026-11-04 grill）

> 用户已于 2026-11-04 确认以下全部决策。此表覆盖 §4 的 draft；`instruction.docx` 仍是最高权威。

| 问题 | 决策 | 日期 |
|---|---|---|
| Q1 只做普通形态 | 是。`skill_slots[3] = null`，Z 无操作，F2 显示 `-`，AI 不进入变身；幻影形态下一个 session。 | 2026-11-04 |
| Q2 HP/ATK/移速复制 | 只在战斗开始时初始化复制一次（`_rebuild_fighters` + `reset()`，Q14 a），不每 tick 重拷。复制 `max_hp` / `basic_atk` / `extra_atk` / `atk`；`walk = player.walk * 1.5`；同步时满血。 | 2026-11-04 |
| Q3 技能 1 | 0.5s 是**冷却**，不是动作时长。动作 0.35s（5 帧 × 0.07s），冷却 0.5s 从出手开始（Q15 a）。 | 2026-11-04 |
| Q4 技能 2 苦无 | 普通形态**不穿 block**；幻影形态才穿，留给下一个 session。0.45s 施法、t=0.22 出手、low lane 60、速度 900、射程 900、半径 10、1.2atk + 眩晕 1s + 1 层印记。 | 2026-11-04 |
| Q5 技能 3 冲刺 | 普通形态**只穿 player 身体**，仍撞墙/barrier/platform；幻影形态才可穿 block。1600px/s × 0.39s（t=0.06–0.45）≈ 640px，1.5atk，单次命中。 | 2026-11-04 |
| Q6 印记引爆 | 同意 §4.3 推荐：第 4 次命中先结算技能伤害，再额外 1.0×atk；乘 `(1-DR)`；眩晕 1s（霸体只免控、伤害照扣）；引爆后 1 层（死亡则 0）；不衰减；独立 `shadow_marks`；player 头顶紫色 pips；技能 2 作为第 4 次命中时眩晕刷新为 1s（不叠到 2s）。 | 2026-11-04 |
| Q7 AI / 跳跃 | 需要跳跃能力（Q16 c）：AI 用跳跃躲来袭攻击/投射物；未来场景可跳上 barrier（Q19）。近/远/低血量策略与苦无跟踪接冲刺按 §4.6。 | 2026-11-04 |
| Q8 身体 / hurtbox | 384×384、pivot (192,372)、body 214；hurtbox 站立 56×210、蹲下 56×130；`stage_body_width 100`。只有 base 被裁时才升 512×512 / pivot (256,500)。 | 2026-11-04 |
| Q9 场景 / spawn | 新增 flat `stage_variants.shadow_ninja`：`blocks: []`、`ladders: []`，沿用 ground/walls/lanes；player `[280,620]`、ninja `[1000,620]`。 | 2026-11-04 |
| Q10 动画预算 | **35 帧**：idle 4 / walk 6 / jump 2 / **crouch 1** / hurt 2 / KO 4 / 三技能各 5 / stun 1；苦无投射物 **2 帧**（水平、不旋转、一亮一暗）。base → 每动作 contact sheet → 游戏内预览逐轮审批；不烘焙 FX。 | 2026-11-04 |
| Q11 F7 / 默认 | warrior → veno → bat → creepy_shooter → mech_crab → shadow_ninja → dummy；默认敌人仍是 Creepy Shooter。 | 2026-11-04 |
| Q12 HUD / 范围 | 沿用 sandbox：enemy HP 条、F1/F2/F6/F8/F9、player 头顶印记 pips；F2 增加 `SHADOW MARKS n/3`。不做完整战斗 UI/BGM/商店/等级。 | 2026-11-04 |
| Q13 数值 / 平衡 | 严格按 docx 数值；加约 0.6s AI 开局延迟；本轮不调伤害。 | 2026-11-04 |
| Q14 “战斗开始”范围 | (a) `_rebuild_fighters` 和 `reset()` 都同步一次，绝不每 tick 重拷。 | 2026-11-04 |
| Q15 技能 1 动作 / 冷却 | (a) 动作 0.35s（5 帧 × 0.07s），冷却 0.5s 从出手开始；AI 约每 0.5s 可用一次，`skill_gap 0.2`。 | 2026-11-04 |
| Q16 AI 跳跃用途 | (c) AI 跳跃躲来袭攻击/投射物；同时按 Q19 跳上 barrier。 | 2026-11-04 |
| Q17 蹲/跳攻防矩阵 | 双方都有防御动作：Shadow Ninja AI 会蹲/跳躲玩家攻击；玩家蹲下躲高位技能 1；玩家跳跃躲低位技能 2 和低位冲刺。 | 2026-11-04 |
| Q18 hitbox 高度 | 技能 1 高位 `[20,-195,130,55]`（底部 −140；站立 210 命中、蹲下 130 躲开）；冲刺低位 `[0,-80,90,80]`（顶部从 110 下移到 80；满跳峰值约 131px，余量约 51px；蹲下 130 仍命中）；技能 2 low lane 60 不变。 | 2026-11-04 |
| Q19 barrier 跳跃范围 | 保留 flat `shadow_ninja` variant；实现通用“前方 solid block 阻挡时跳上去”AI，供未来场景使用；smoke 用临时 barrier 验证。 | 2026-11-04 |
| Q20 蹲下动画 / AI 触发 | 加 1 帧 crouch（0.5s 保持），总 35 帧；数据驱动威胁判断：高位攻击/投射物 → 蹲下，低位/中位 → 跳跃，barrier 挡路 → 跳上；`jump_cooldown 0.8s`，`crouch_hold 0.35s`。 | 2026-11-04 |

### 最终实现记录（2026-11-06）

- 代码：`game/shadow_ninja.py`、`game/projectile.py` 的 `ShadowKunaiProjectile`、
  `game/scene.py` 的数值同步/印记绘制/投射物分支、`game/fighter.py` 的 `shadow_marks`、
  `game/debug.py` 的 `SHADOW MARKS`、`main.py` 的 Phase H/F7/最终 conjunction。
- 数据：`stats.json`、`attacks.json`、`animations.json`、`roster.json`、`debug.json`、
  `config.py`、`roster.py`。
- 最终 hitbox：技能 1 `[20,-195,130,55]`；技能 3 `[0,-80,90,80]`；技能 2 low lane 60。
  AI 高位阈值 `bottom >= 140`，低位/中位阈值 `top <= 125`。
- 动画：35 帧（idle 4 / walk 6 / jump 2 / crouch 1 / hurt 2 / KO 4 / 三技能各 5 / stun 1）。
  walk 使用 v5 固定缩放归一化；slash 使用 v6 归一化；throw 使用 v5，02 帧为发射帧且角色帧
  不含苦无；dash 使用 v3（01–03 更俯身/更低）；KO 末帧闭眼；crouch 使用深蹲 v2。
- 苦无 FX：2 帧 32×32（`shadow_kunai_00..01.png`），水平、不旋转、一亮一暗；由 base 苦无
  裁切后经 Seedream `image_to_image` 提取、smooth 降采样得到。
- 场景：flat `stage_variants.shadow_ninja`，无 block/ladder，spawn `[1000,620]`。
- 验证：`main.py --smoke-test` → **exit 0**；`shadow_ninja_present/stats/slots/slash/throw/dash/
  marks/ai/crouch/jump_dodge/barrier_hop/win/cleanup` 全 true；`missing_frames == 0`，
  `fx_missing == 0`；游戏内预览 14 张在 `assets/generated/contact_sheets/shadow_ninja_ingame_v1/`。
- 文档：README / DESIGN_DECISIONS / DEBUG / ASSET_PIPELINE / 本文 /
  `docs/SHADOW_NINJA_ANIMATION_DESIGN.md` 已更新；`instruction.docx` 未修改。

---

## 7. 建议实施顺序

1. **基线**：确认工作区未提交改动不被 revert/stash/checkout；运行
   `main.py --smoke-test` 确认 exit 0。
2. **Grill**：按 §5 Q1–Q12 一次性问完，答案写入 §6；确认前不改代码/JSON/素材。
3. **数据/注册骨架**：
   - `stats.json` / `attacks.json`（三技能，技能 4 null）/ `animations.json`（先用 fallback 帧或占位）/
     `roster.json` / `debug.json`；
   - `config.py` 的 REQUIRED_STATS/ATTACKS/CLIPS/ROSTER_CLASSES/ANIMATED_CLASSES；
   - `roster.py` 注册；`game/shadow_ninja.py` 类骨架；
   - F7 插入；先让 `shadow_ninja_present` / `shadow_ninja_stats_ok` / `shadow_ninja_slots_ok` 通过。
4. **动态数值同步**：scene 钩子 + `sync_from_player`；切换 Lina/Nyra/Rhea 检查 HP/ATK/walk。
5. **印记系统**：Fighter 的 `shadow_marks` 字段、清空、player 头顶 pips、F2 计数；
   先用 `force_attack` 单技能验证 1→2→3→引爆→1。
6. **技能 1**：动作/hitbox/伤害/印记。
7. **技能 2**：`ShadowKunaiProjectile`、低车道、block、眩晕、印记；cast/impact FX。
8. **技能 3**：冲刺、穿身、命中、印记、撞墙/block、结束清理。
9. **AI**：近/远/低血量优先级、苦无跟踪、技能 2→3 接法；F8 开关。
10. **动画**：base 审批 → idle/walk/jump/hurt/ko → 三技能 → 苦无 FX → contact sheet →
    游戏内预览；安装到 `assets/frames/shadow_ninja/`。
11. **Smoke**：新增 Phase（Mech-Crab 之后）；同步 F7/roster_ok/SMOKE 打印/最终 conjunction；
    `main.py --smoke-test` exit 0，所有 `shadow_ninja_*` true。
12. **手动验证**：F1/F2/F6/F8/F9、角色切换、KO/win、场景切换、印记/眩晕/霸体、
    技能 4 空槽；确认没有残留投射物/印记/状态。
13. **文档**：实现并验证、用户确认设计后，才按 `AGENTS.md` 问一次是否更新 README/docs/手册。

---

## 8. smoke / 手动验证清单

### 8.1 建议新增 flags（全部纳入最终 conjunction）

| flag | 检查内容 |
|---|---|
| `shadow_ninja_present` | roster 能构造；class/name/stats/slots 正确；单只 |
| `shadow_ninja_stats_ok` | `max_hp` / `atk` / `walk_speed` 与当前 player 一致（HP/ATK 相等，walk=1.5×）；切换 Lina/Nyra/Rhea 后仍正确 |
| `shadow_ninja_slash_ok` | 0.35s 动作 / 0.5s 冷却；atk 伤害；命中叠 1 层印记；HURT/击退正常 |
| `shadow_ninja_throw_ok` | 5s 冷却；低车道；1.2atk；眩晕 1s；命中叠 1 层；被 barrier/platform 挡住 |
| `shadow_ninja_dash_ok` | 8s 冷却；位移≈640px；1.5atk；穿 player 身体；撞墙/block 停止；命中叠 1 层 |
| `shadow_ninja_marks_ok` | 最多 3 层；第 4 次额外 atk 伤害 + 眩晕 1s；引爆后 1 层；KO/reset 清空；霸体只免疫眩晕；与 Nyra 印记互不干扰 |
| `shadow_ninja_ai_ok` | 近距离 2→1；2 冷却→1；远距离 2→跟踪→3→1；低血量 3 拉开；不使用技能 4 |
| `shadow_ninja_slots_ok` | V/C/X/Z 映射；slot 4 空槽安全；F2 显示 `-` |
| `shadow_ninja_win_ok` | KO 后 WIN/重开正常；印记/投射物清理 |
| `shadow_ninja_cleanup_ok` | KO/reset/set_enemy 后无残影/苦无/印记/眩晕/临时霸体 |
| `shadow_ninja_missing_frames` | 所有配置 clip 文件存在，必须 0 |
| `shadow_ninja_fx_missing` | 2 帧苦无 FX 文件存在，必须 0 |

### 8.2 必须同步更新的旧测试

- `main.py` 的 F7 链（约 2665）：在 `f7_mech_crab_ok` 后加 `f7_shadow_ninja_ok`，
  `f7_dummy_ok` 变成再下一次 F7；`roster_ok` 加 `f7_shadow_ninja_ok`。
- `main.py` 的 SMOKE 打印/final conjunction：加所有 `shadow_ninja_*`。
- `platform_spawn_clear_ok`：确认 `shadow_ninja_spawn` 的 body 不与 platform/barrier 相交。
- 若加 flat stage variant：`scene_variant_switch_ok` 增加 Shadow Ninja variant 检查
  （0 barrier / 0 platform / 0 ladder / spawn `[1000,620]`）。
- `default_enemy_ok` 保持 Creepy Shooter，不要被新敌人抢默认。
- `ROSTER_CLASSES` / `ANIMATED_CLASSES` / `REQUIRED_STATS` / `REQUIRED_ATTACKS` 更新后，
  所有旧 smoke 仍应全绿。

### 8.3 手动检查

- F7 选 Shadow Ninja；F8 开 AI；观察近/远/低血量行为；确认不会使用技能 4。
- F1：hurtbox 56×210、技能 1/3 hitbox、技能 2 低车道、冲刺路径。
- F2：四槽（第 4 槽 `-`）、三冷却、`skill_gap`、当前 clip/frame、`SHADOW MARKS n/3`。
- V：技能 1，连续 4 次看印记 1→2→3→引爆→1；引爆有额外伤害 + 眩晕 1s。
- C：技能 2，低弹道；跳跃可躲、俯身不可躲；撞 barrier/platform 消失；命中眩晕 1s；
  与 Nyra 的印记 UI 不混。若 Shadow Ninja 使用 flat variant（无 block），smoke 可临时在
  `scene.stage.blocks` 插入一个测试 Rect，或切回默认 stage 验证 block 碰撞。
- X：技能 3，位移约半屏，穿过玩家身体，撞墙/block 停；冷却 8s。
- Z：空槽无操作。
- 切换 Lina/Nyra/Rhea：敌人的 HP/ATK/移速立即重新同步；HUD 名称/血条正确。
- 让玩家进入霸体（Nyra Q/E、Rhea E）后吃印记引爆：伤害照扣、眩晕被免疫。
- F9/reset、KO、F7 切换后：无残留苦无/印记/眩晕/临时状态。
- F6 0.25×/0.5× 检查技能 2 低弹道、技能 3 穿身、印记引爆时序。
- 若使用 flat variant：B 键开关仍正常；背景不变；spawn 不重叠。
- 动画：base、每动作 contact sheet、游戏内预览逐轮审批；最终 missing/fx 均为 0。

---

## 9. 风险与边界

- **动态数值时机**：必须在 player 构造之后再同步；`create_fighter` 不传 player，需 scene 钩子。
  不要在每 tick 重拷 max HP/atk，否则会重置战斗中的伤害/临时变化。
- **印记字段冲突**：不要复用 Nyra 的 `marks` 作为 Shadow Ninja 的印记；独立 `shadow_marks`
  更安全。若复用，`_draw_mark_fx` 的 Nyra 条件会让玩家头上的印记不显示。
- **引爆顺序**：第 4 次命中是“技能自身伤害 + 额外 atk 伤害”两段；先伤害后眩晕；
  `StatusSet.add` 已处理霸体免疫；引爆伤害要乘 `(1 - damage_reduction)`。
- **projectile 不触发 on_hit_success**：技能 2 的眩晕/印记必须在
  `ShadowNinja.on_projectile_hit` 里做；只写 `marks_on_hit` 不会生效。
- **敌人冲刺穿身**：`_separate_fighters` 只看 player 的 `pass_through_enemy`；
  enemy 要用 `ignore_separation`。若穿 terrain，结束要 resolve overlap。
- **AI 苦无跟踪**：必须从 `scene.projectiles` 里筛选自己的 `shadow_kunai`；苦无已消失时
  不要继续等待，否则 AI 会卡在“等苦无”状态。
- **平台/场景**：默认 stage 的 platform 高 400px，普通跳跃够不到；flat variant 是最稳的。
  若选默认 stage，必须明确跳跃 AI 与平台限制。
- **F7 步数**：插入新敌人会改变旧 smoke 的 F7 步数；只改测试假设，不要移动敌人到奇怪位置。
- **范围蔓延**：不要顺手做幻影形态、完整战斗 UI、BGM、商店、等级；本轮只做普通形态。
- **素材缺失**：最终必须有完整普通形态帧 + 苦无 FX；fallback 不能掩盖 missing/fx 计数。

---

## 10. Definition of Done

- [x] §5 的 Q1–Q20 已由用户确认，§6 已填写并补充最终实现记录。
- [x] `shadow_ninja` 的 stats/attacks/animations/roster/debug（variant 或 spawn）全部接入，
  config 校验通过。
- [x] HP/ATK 与当前 character 相同，移速 1.5×；切换 Lina/Nyra/Rhea 后仍正确。
- [x] 技能 1：0.35s 动作 / 0.5s 冷却、atk、近身、高位判定、叠印记。
- [x] 技能 2：5s、1.2atk、低弹道、眩晕 1s、叠印记、被 block 挡住。
- [x] 技能 3：8s、1.5atk、约 640px、穿 player 身体、低判定可跳躲、叠印记。
- [x] 被动：技能 1/2/3 叠印记，最多 3 层；第 4 次额外 atk + 眩晕 1s，重置为 1；
  KO/reset 清空；与 Nyra 印记互不干扰。
- [x] 技能 4 槽位为 null；Z 无操作；AI 不使用技能 4；幻影形态未实现（明确记录为后续）。
- [x] AI 覆盖近/远/低血量；苦无跟踪接冲刺；蹲/跳防御、barrier 跳跃；F8 开关正常。
- [x] 普通形态动画 35 帧 + 2 帧苦无 FX 完成；`shadow_ninja_missing_frames == 0`、
  `shadow_ninja_fx_missing == 0`。
- [x] F7 / V·C·X·Z / F2 / F8 / F9 正常；旧 smoke 全部更新并通过。
- [x] `main.py --smoke-test` exit 0；所有 `shadow_ninja_*` true；默认敌人仍是 Creepy Shooter。
- [x] F1/F2/F6 与预览图确认视觉/判定；没有残留苦无/印记/眩晕。
- [x] 用户确认后，按 AGENTS.md 更新 README/docs/手册；`instruction.docx` 未被修改。
- [x] 未 commit / 未 push。

---

## 11. 实现并确认后才更新的文字

2026-11-06：用户已确认 Shadow Ninja 普通形态，并明确同意写入文档。以下内容已更新：

- `README.md`：Shadow Ninja 普通形态的 HP/ATK/移速复制、三技能、印记、AI、场景、F2 调试。
- `docs/DESIGN_DECISIONS.md`：新增 §Shadow Ninja（普通形态），记录动态数值、印记、技能、
  穿身/block、AI、场景与“技能 4 留待幻影 session”。
- `docs/DEBUG.md`：新 smoke phase/flags、F7 顺序、F1/F2 手动检查。
- `docs/ASSET_PIPELINE.md`：新增 §Shadow Ninja（2026-11-06），记录 base/canvas/pivot/35 帧/
  2 帧苦无 FX/审批图。
- `docs/SHADOW_NINJA_ANIMATION_DESIGN.md`：新增动画设计文档，记录帧表、throw 02 发射帧、
  KO 闭眼、dash 低判定与苦无 FX。
- `docs/NEXT_SESSION_SHADOW_NINJA.md`：顶部状态、§6 最终实现记录、§10 DoD 已回填。
- `Island Survival 基础操作手册.docx`：仅在用户要求时更新。
- `instruction.docx`：**绝不修改**。

---

## 附录 A — 幻影形态（后续 session 的摘要，不计入本轮）

> 详细设计、动作帧表、变身/还原过渡帧和 grill 清单见
> `docs/NEXT_SESSION_SHADOW_NINJA_PHANTOM.md`；本附录只保留摘要。

- 技能 4（15s）变身幻影形态；变身帧 + 幻影期间 **不受任何伤害、免疫一切负面效果、无 hitbox**。
- 变身时刷新/清除对方在 Shadow Ninja 身上叠的印记和负面状态；幻影期间不能被叠印记/被动。
- 幻影形态有 3 个全新动作模型技能，冷却独立计算；每个技能每次变身只能用一次；
  3 个技能全部用完自动解除形态；解除后技能 4 才进入冷却。
- 幻影形象：`Image/Enemy/shadow-ninja-phantom-no-aura-256.png`（另有
  `shadow-ninja-phantom-shadow-256.png`）。
- docx 未给出幻影三技能的名称/数值/动作，后续 session 需要单独 grill 并补全。
- 本轮不要实现任何幻影逻辑；只保留 `skill_slots[3] = null` 和“后续 session”标记。

## 附录 B — 建议的负面/控制规则速查

| 效果 | 当前实现 | Shadow Ninja 相关 |
|---|---|---|
| 眩晕 | `StatusSet.add("stun", duration)`；霸体忽略；头顶黄星 | 技能 2 1s；印记引爆 1s |
| 霸体 | `StatusSet.has("super_armor")`；Rhea/Nyra 的 take_hit 只扣血；`StatusSet.add` 免疫控制 | 引爆伤害照扣，眩晕被免疫 |
| 免伤 | `target.statuses.damage_reduction()` | 引爆伤害乘 `(1 - DR)` |
| 无敌 | `target.invincible` | 不叠印记、不引爆；resolve 直接跳过 |
| 击退 | `take_hit` 的 `knockback`，方向由 attacker.facing 决定 | 技能 1/3 有击退，技能 2 建议 0 |
| 印记 | Nyra：`target.marks` + 1.8atk+10% max HP | Shadow：独立 `shadow_marks`，额外 atk + 1s stun |

## 附录 C — 本次核对过的代码位置

- `game/data/stats.json`：三角色 hp/atk/walk；`combat` 的 hitstun/hitstop。
- `game/roster.py`：`FIGHTER_CLASSES`、`create_fighter`。
- `game/config.py`：`REQUIRED_STATS` / `REQUIRED_ATTACKS` / `REQUIRED_*_CLIPS` /
  `ROSTER_CLASSES` / `ANIMATED_CLASSES` / `PROJECTILE_KINDS`。
- `game/scene.py`：`_rebuild_fighters`（约 232）、`reset`（约 372）、
  `spawn_projectile_from_event`（约 913）、`_draw_mark_fx`（约 1282）、`draw`（约 1320）。
- `game/combat.py`：`resolve_hit`（142）、`resolve_projectile_hit`（194）。
- `game/fighter.py`：`marks`（99）、`take_hit`（165）、`on_hit_success`（251）、
  `reset_common`（496）。
- `game/nyra.py`：`on_hit_success` 的 Nyra 印记（331）。
- `game/scene.py`：`_separate_fighters`（452）。
- `game/stage.py`：`move_x`（356）、`move_fighter`（398）、`spawn`（151）。
- `main.py`：F7/roster_ok（约 2665–2720）、Mech-Crab smoke（约 3505–3813）、
  scene variant（约 3870）、SMOKE（约 3890）、final conjunction（约 4168+）。
- 现有敌人参考：`game/creepy_shooter.py`（AI/投射物）、`game/warrior.py`（近战/冲刺）、
  `game/veno.py` 与 `game/bat.py`（projectile owner 状态）、`game/rhea.py`（冲刺穿身/无敌）。
