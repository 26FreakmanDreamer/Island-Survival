# Next Session — Mech-Crab 设计与接入

> 日期：2026-11-03（设计）；2026-11-03（实现与文档完成）
> 状态：**已实现并验证**。数据、类、AI、场景 variant、smoke、47 帧角色动画 + 3 帧锁定 FX 与
> 游戏内预览均已完成；`main.py --smoke-test` → **exit 0**（全部 `mech_crab_*` true，
> `mech_crab_missing_frames=0`，`mech_crab_fx_missing=0`）。最终值见 §6；实现细节见
> `docs/DESIGN_DECISIONS.md` §Mech-Crab (2026-11-03)。
> 2026-11-03 用户更新了 docx 的 Mech-Crab 冷却/预警/伤害，代码已同步：charge 5s / 1.0s / 45，
> claw stun 1.2s，leap 8s / 0.8s / 60；laser 不变。
> 基线：`rhea-thorn-integration` HEAD `0e749c1` + 未提交的 Rhea / Bat / 场景改动；
> `.venv/Scripts/python.exe main.py --smoke-test` → **exit 0**（2026-11-03，所有现有 flags 为 true）。
> 工作区：`instruction.docx` 有用户更新；`sketch/mech_crab_scene.jpg` 是未跟踪的场景草图。
> 不要 revert / stash / checkout 这两个文件，也不要修改它们。
> 权威规格：`instruction.docx` 的 Mech-Crab 段（P254–P262）。本文只摘录；**绝不修改 docx**。
> 默认角色 **Lina**，默认敌人 **Creepy Shooter**。
> 阅读顺序：本文 → `instruction.docx` 的 Mech-Crab 段 → `AGENTS.md` → `README.md` →
> `docs/DESIGN_DECISIONS.md` → `docs/DEBUG.md`；如果要生成动画帧，再读
> `docs/IMAGE_GENERATION_RULES.md` 和 `docs/ASSET_PIPELINE.md`。

---

## 0. 给下一个 session 的开场 prompt（可直接复制）

```text
读取 docs/NEXT_SESSION_MECH_CRAB.md、instruction.docx 的 Mech-Crab 段（P254–P262）、
AGENTS.md、README.md、docs/DESIGN_DECISIONS.md、docs/DEBUG.md；如果要生成动画帧，再读
docs/IMAGE_GENERATION_RULES.md 和 docs/ASSET_PIPELINE.md。

先运行 .venv/Scripts/python.exe main.py --smoke-test，确认基线 exit 0，然后按本文 §5
的 Q1–Q12 一次性 grill 我。每项给出当前 docx 原文、建议值和影响范围。我确认后，先把答案写入
本文 §6“已确认决策”，再按 §7 的顺序实施；不要先改代码/JSON/素材。

本轮范围：新增单个 enemy Mech-Crab（HP 400 / ATK 30 / 四个技能 / 无 barrier 专属场景），
包含数据、类、AI、场景 variant、smoke、F1/F2/F6 验证，以及经批准的动画/FX。

不要修改 instruction.docx、Image/、UI Resources/、sketch/、其他角色/敌人、背景/BGM；
不要用 pytest；验证用 --smoke-test、F1/F2/F6 和预览图；不要 commit，除非我明确要求。
```

如果本轮要生成动画帧，追加：

```text
素材按 base → 动作帧 contact sheet → 游戏内预览的顺序逐轮审批；
不要直接把 Image/Enemy/mech-crab-512.png 当运行时帧，也不要把激光/标记烘焙进角色帧。
```

---

## 1. 本轮范围

| 做 | 不做 |
|---|---|
| 新增 Mech-Crab 的 stats / attacks / clips / roster / stage variant | 其他敌人的数值、AI、动画改动 |
| `game/mech_crab.py`：四技能、霸体、技能间隔、AI、受击/KO/reset | Eira、Crooked Witch、Lina Shadowtide 等未实现敌人 |
| 激光、冲撞、砸地、跳跃砸地四个技能与各自 smoke | 角色选择界面、商店、道具、等级 |
| 无 barrier 的专属场景（保留平台/梯子，见 §4.6） | 按敌人切换背景/BGM；当前代码没有音频播放层 |
| F7 / V·C·X·Z / F2 冷却显示 / F1 判定框 | 多体编组规则（docx 是单只“Mech-Crab”） |
| 经用户批准的动画帧与 FX | 未经确认改 README/docs/手册；commit / push |

**关键约束**

- `instruction.docx` 是权威规格，只读；不要 `git add` / `git checkout` / `git stash` 它。
- `Image/` 和 `UI Resources/` 只读；canonical 形象是
  `Image/Enemy/mech-crab-512.png`（512×512 RGBA）。
- `assets/enemies/mech-crab*.png` 是旧图，按 `AGENTS.md` 不作为默认视觉来源。
- `sketch/mech_crab_scene.jpg` 只是布局草图，不是运行时素材；不要 `pygame.image.load` 它当背景。
- 当前工作区有上一轮 Rhea / Bat / 场景的未提交改动；不要顺手提交或回退。
- 没有 `assets/frames/mech_crab/`；没有 Mech-Crab 的运行时帧。`Sound Clip/BGM/mech_crab_battle_music.ogg`
  存在，但当前代码没有 BGM 播放层，本轮不接音频。

---

## 2. instruction.docx 原文与事实

### 2.1 原文（P254–P262）

```text
Mech-Crab
形象：Image\Enemy\mech-crab-512.png
Hp = 400 , atk=30
被动：所有技能释放期间拥有霸体，不会被打断，每个技能间隔1s
技能1：(6s)预警1s（预警动作，螃蟹微微向下蹲，同时眼睛变大），后眼睛大小不变，眼睛发出红色激光（直径约为眼睛的0.8）伤害1.2atk。发射方向，先向上发射，激光朝角色方向转动。期间螃蟹不动。
技能2：(8s)预警1.5s（预警动作，原地机械脚移动），朝角色方向冲撞造成1.3atk伤害。
技能3：(5s)一只钳子变大（0.5s），朝地上砸，造成atk伤害和1.5s眩晕
技能4：(12s)预警1.5s ,选定一个点，用外面一圈为圆红色大叉表示；跳跃至这个点，造成1.8atk伤害。（跳跃期间不计碰撞）
专属场景：无barrier
```

### 2.2 已明确的事实

| 项 | 值 |
|---|---|
| HP | 400 |
| basic ATK | 30 |
| 技能 1 冷却 / 预警 | 6s / 1.0s |
| 技能 2 冷却 / 预警 | 8s / 1.5s |
| 技能 3 冷却 / 钳子变大 | 5s / 0.5s |
| 技能 4 冷却 / 预警 | 12s / 1.5s |
| 伤害倍率 | 1.2atk / 1.3atk / 1.0atk / 1.8atk = **36 / 39 / 30 / 54** |
| 技能 3 附加 | **1.5s 眩晕** |
| 技能 1 特征 | 从眼睛发射红色激光，直径约为眼睛的 0.8；先向上，再朝角色方向转动；期间螃蟹不动 |
| 技能 4 特征 | 红色圆圈 + 大叉标记目标点；跳跃期间不计碰撞 |
| 被动 | 所有技能释放期间霸体；每个技能间隔 1s |
| 场景 | **无 barrier** |

### 2.3 docx 没有写、必须由本轮设计的内容

- 括号里的 `(6s)` 等是否就是每个技能各自的冷却；冷却从起手还是结束开始计时。
- “每个技能间隔1s”是技能结束后的全局间隔，还是起手之间的间隔；重置后是否有开场延迟。
- 四个技能的动作总时长、激光持续/转向速度/命中次数/射程/是否被平台挡住。
- 冲撞的锁定方向、距离、速度、是否撞墙停止、能否跳过、命中/击退参数。
- 砸地的钳子范围、是否命中空中目标、眩晕是否固定 1.5s。
- 跳跃的选点时机、最大距离、落点是否可以在平台、落地 AoE 半径、是否只在落地结算伤害。
- 是否有普通近战攻击；docx 只列了四个技能。
- AI：**docx 没有 Mech-Crab 的 AI 段**。P236–P240 的“AI：在远处……优先用 2 / 近处优先 3 拉开，再用 1……”属于
  前面的 **Creepy Shooter**（技能 2 远程、技能 3 翻滚、技能 4 回平台），不要误用到 Mech-Crab。
- 敌人数量、spawn、hurtbox、画布/pivot、动画帧数、音效、背景。

### 2.4 场景草图（`sketch/mech_crab_scene.jpg`，1536×960）

草图内容：

- 竞技场左右边界；**没有 barrier**。
- 左侧一块 **long platform**，下方一条 **short ladder**。
- 右侧一块 **short platform**，下方一条 **long ladder**。
- 草图中右侧 short platform 画得比左侧 long platform 高；当前默认 `stage` 恰好相反：
  long platform 在 y=220（更高），short platform 在 y=268。

结论：草图只用于相对布局，不应按像素比例重画。建议沿用默认场景的平台/梯子高度与素材，只删除两个 barrier；
如果用户要求严格按草图的上下关系，则交换两个平台的高度和梯子 `top_y`。见 §5 Q7。

### 2.5 现有资源

- 形象：`Image/Enemy/mech-crab-512.png`（512×512 RGBA，canonical）。
- 旧图：`assets/enemies/mech-crab-v3-512.png` 等；不作为默认来源。
- 运行时帧：**没有** `assets/frames/mech_crab/`。
- BGM：`Sound Clip/BGM/mech_crab_battle_music.ogg` 存在；当前项目没有 BGM 播放代码，本轮不处理。
- 场景草图：`sketch/mech_crab_scene.jpg`（未跟踪，只读参考）。

---

## 3. 当前实现快照（代码事实）

### 3.1 新增一个敌人需要接的地方

| 位置 | 现状 / 需要做什么 |
|---|---|
| `game/roster.py` | `FIGHTER_CLASSES` 注册 class 名 → Python 类；当前有 warrior/veno/bat/creepy_shooter 等 |
| `game/data/roster.json` | 新增 `enemies.mech_crab`：name/class/stats/spawn/stage_variant/clips/frame_size/pivot/frames_dir/fallback/skill_slots/separates/decides_match |
| `game/data/stats.json` | 新增 `mech_crab`：hp/basic_atk/extra_atk/stage_body_width/move/cooldowns/hurtbox/ai |
| `game/data/attacks.json` | 新增四个 attack_id、倍率、duration、hitstun/hitstop/knockback、必要的事件 |
| `game/data/animations.json` | 新增 `mech_crab_clips`、`mech_crab_frame_size`、`mech_crab_pivot` |
| `game/data/debug.json` | `stage_variants.mech_crab`（无 barrier）；`mech_crab_spawn` |
| `game/config.py` | `REQUIRED_STATS`、`REQUIRED_ATTACKS`、`REQUIRED_MECH_CRAB_CLIPS`、`ROSTER_CLASSES`、`ANIMATED_CLASSES`、frame_size/pivot 校验 |
| `game/scene.py` | 通常不需要新分支；如果激光/标记需要自定义效果，才接 `projectiles`/`fx_effects` |
| `game/fx.py` | 激光、冲撞尘土、砸地冲击、红色 X 标记、跳跃落地特效 |
| `main.py` | 新 smoke phase、flags、最终 conjunction；更新 F7 顺序相关断言 |

`game/config.py` 的 `REQUIRED_STAGE` 只要求五个通用 spawn key；`mech_crab_spawn` 只放在
`stage_variants.mech_crab` 里即可，roster 的 `spawn` 会被现有校验检查。

### 3.2 引擎能力与需要补的部分

- `game/combat.py::AttackRuntime` 目前只处理 `hitbox` / `dash` / `projectile` / `fx` 四种事件；
  没有 `laser`、`teleport`、`leap` 事件。未知类型会被忽略。
- `AttackRuntime` 的 `hitbox` 用 `local_box_to_rect`，支持 `anchor: "cast"`（起手位置）或跟随当前
  `fighter.x/y`；不支持旋转线段。
- `resolve_hit()` 不负责给 hitbox 附加状态；它只在伤害后调用
  `attacker.on_hit_success(attack, target, bonus)`。现有 Veno/Bat 的状态是在各自的
  `on_projectile_hit` 里加的。
- `Fighter.take_hit()` 的默认实现会进入 HURT、清攻击、应用击退。`super_armor` 状态本身只阻止
  控制效果（`StatusSet.add` 会拒绝 stun/freeze/slow 等）和 `control_locked()`，**不会自动让
  `take_hit` 不进入 HURT**；Nyra/Warrior 都是在子类里 override `take_hit` 实现霸体。
- `game/scene.py` 的 tick 顺序：玩家 → 敌人 → 分离 → 结算 → 投射物（hitstop 时跳过投射物 update）。
  自定义光束可以作为 `scene.projectiles` 或 `scene.fx_effects` 的一员，但要在 KO/reset 时清理。
- `Stage.move_x()` 会处理墙和 block 侧面；冲撞建议用它，避免穿墙。跳跃要“跳跃期间不计碰撞”，
  则应在技能期间直接插值 `x/y` 并跳过 `move_fighter`，落地时再解析可站立面。
- `Stage.platform_top_at()` 可判断脚下平台；`Stage.segment_hits_blocks()` 可用于激光/AI 的
  line-of-sight 检测（它是私有逻辑的公开封装）。
- `AnimationPlayer` 在帧文件缺失时会回退到 `fallback` 图，但 `missing_paths()` 会列出配置了却不存在
  的帧；现有 smoke 用 `missing_frames` 检查。没有实际帧就不要宣称完成。

### 3.3 F7 / smoke 影响

当前 `roster.json` 的敌人顺序是：

```text
warrior → veno → bat → creepy_shooter → dummy
```

当前 `main.py` 的 F7 断言在 `main.py:2663` 附近：

```text
warrior → veno (f7_cycle_ok)
veno → bat (f7_bat_ok)
bat → creepy_shooter (f7_creepy_ok)
creepy_shooter → dummy (f7_dummy_ok)
```

建议把 `mech_crab` 插在 `creepy_shooter` 之后、`dummy` 之前。这样 warrior→veno 的旧断言不变，
但 `creepy_shooter` 之后要先到 `mech_crab`，再到 `dummy`；必须新增 `f7_mech_crab_ok` 并调整
`f7_dummy_ok` 的步数。

同样需要检查/更新：

- `scene_variant_switch_ok`（`main.py` 约 3500）：加入 `mech_crab` 的 variant/敌人生成检查。
- `platform_spawn_clear_ok`：新 spawn 不能与平台/barrier 相交。
- `default_enemy_ok`：默认敌人仍是 Creepy Shooter，不要让 Mech-Crab 抢默认。
- `roster_ok` / `f7_*` 的最终 conjunction。
- 新增 `mech_crab_missing_frames` / `mech_crab_fx_missing`（如有 FX 文件）。

---

## 4. 建议设计（draft，必须经 §5 grill 确认）

以下数值是让讨论有具体起点，**不是 docx 权威值**；确认后写入 §6，再改代码。

### 4.1 命名与文件

| 项 | 建议值 |
|---|---|
| roster id | `mech_crab` |
| Python 类 | `game/mech_crab.py::MechCrab` |
| stats key | `mech_crab` |
| clips key | `mech_crab_clips` |
| frame size / pivot key | `mech_crab_frame_size` / `mech_crab_pivot` |
| frames dir | `assets/frames/mech_crab/` |
| fallback | `Image/Enemy/mech-crab-512.png` |
| spawn key | `mech_crab_spawn` |
| stage variant | `mech_crab` |
| skill slots（V/C/X/Z） | `mech_laser`, `mech_charge`, `mech_claw_slam`, `mech_leap_slam` |

### 4.2 基础属性草案

```json
"mech_crab": {
  "hp": 400,
  "basic_atk": 30,
  "extra_atk": 0,
  "stage_body_width": 170,
  "move": {"walk": 120, "jump_v": 700, "gravity": 2200},
  "cooldowns": {"laser": 6.0, "charge": 8.0, "claw": 5.0, "leap": 12.0},
  "hurtbox": {"standing": [160, 150], "crouching": [160, 150]},
  "ai": {
    "laser_min_range": 160.0,
    "laser_range": 900.0,
    "charge_min_range": 220.0,
    "charge_range": 520.0,
    "claw_range": 150.0,
    "leap_min_range": 180.0,
    "leap_range": 620.0,
    "level_tolerance": 100.0,
    "decision_interval": 0.15,
    "skill_gap": 1.0
  }
}
```

- `hurtbox 160×150` 只覆盖中央机身/腿，不覆盖两只大钳子的全部视觉宽度；是否把钳子纳入受击要确认。
- `stage_body_width 170` 是墙 clamp/角色分离用，不是 hurtbox。
- `walk 120` 是“重型机械”速度；最终按手感调，不要先调帧。

### 4.3 四个技能草案

| 技能 | attack_id | 冷却 | 预警 | 主动 | 收招 | 总时长（draft） | 伤害 |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 激光 | `mech_laser` | 6.0s | 1.0s | 0.9s | 0.3s | 2.2s | 1.2atk = **36** |
| 2 冲撞 | `mech_charge` | 8.0s | 1.5s | 0.55s | 0.25s | 2.3s | 1.3atk = **39** |
| 3 砸地 | `mech_claw_slam` | 5.0s | 0.5s（钳子变大） | 0.15s | 0.25s | 0.9s | 1.0atk = **30** + **1.5s 眩晕** |
| 4 跳跃砸地 | `mech_leap_slam` | 12.0s | 1.5s | 0.65s（飞行） | 0.2s | 2.35s | 1.8atk = **54** |

**伤害写法**：像 Warrior 一样用 `basic_mult` / `extra_mult` 同倍率（例如激光 1.2/1.2），
让 `basic_atk + extra_atk` 共同成长；不要写死 `${damage}` 绝对值。

**技能 1 激光（建议）**

- 起手位置锁定，施法期间 `x/y` 不动；身体朝向保持起手朝向，只有光束/眼睛转动。
- 眼睛为发射原点；光束直径从眼睛尺寸推导，建议游戏内约 14px（最终按 base 帧校准）。
- 1.0s 预警后，从**正上方**（屏幕 y 负方向）开始，以约 240°/s 的最短弧转向目标中心；
  持续 0.9s；每个目标每次施法最多命中一次，36 伤害。
- 被平台/barrier 挡住；可命中平台上的玩家；玩家可移动/跳跃躲开。
- 实现建议：新增一个 `MechLaserBeam` 效果对象（`owner/angle/origin/alive/hit_targets`），
  由 `MechCrab` 在 attack runtime 的 1.0–1.9s 区间更新；用线段 + 厚度与目标 hurtbox 做碰撞；
  命中后调用 `resolve_hit()`，不要复用普通 projectile 的“弹道命中”逻辑。
- 不要在 `attacks.json` 里假装它是普通 `projectile`；除非确认要新增 `PROJECTILE_KINDS`。

**技能 2 冲撞（建议）**

- 1.5s 预警时原地机械脚移动；方向在**预警开始时**锁定（玩家可侧移躲开）。
- 冲撞 0.55s、700px/s（约 385px），用 `stage.move_x()` 移动，撞墙/平台侧面停止。
- 命中一次 39；击退约 140，hitstun 0.3；可被跳跃躲过；施法全程霸体。
- 如果撞到玩家是否停下，见 Q4；建议继续冲完固定距离，避免“贴脸无限追”。

**技能 3 砸地（建议）**

- 面向前方的一只钳子变大 0.5s，然后砸地；命中前方约 `200×140` 的区域，30 伤害 + 1.5s 眩晕。
- 只命中前方，不命中背后；高度 140，跳起可躲；目标有 super armor 时眩晕被忽略（现有规则）。
- 实现建议：hitbox event 在 t=0.5–0.65；在 `MechCrab.on_hit_success()` 里对
  `mech_claw_slam` 的命中目标 `statuses.add("stun", 1.5, source="mech_claw_slam")`，
  避免改 `resolve_hit` 的通用状态管线；如果用户希望所有 hitbox 都能带状态，再另开通用改动。

**技能 4 跳跃砸地（建议）**

- 1.5s 预警开始时选定一个点（建议按玩家当前位置/附近可站立点），显示红色圆圈 + 大叉；
  标记固定，玩家可以离开标记躲避。
- 0.65s 内从当前位置跳到标记点；飞行期间忽略平台/barrier 碰撞（是否也忽略角色碰撞/受击，
  见 Q6）；落地时结算 54 伤害，落地 AoE 半径约 100。
- 落点若在平台顶，则落在平台 `surface_y`；否则落到地面。飞行结束必须解析成可站立面，
  不能停在平台侧面/内部。
- 实现建议：`MechCrab._update_attack()` 在 1.5–2.15s 直接插值 `x/y`，跳过 `move_fighter`；
  落地时用 `platform_top_at()`/`ground_y` 决定 y，并调用一次落地命中检测。
- 标记画在 `fx_effects` 或 `MechCrab.draw()`；不要烘焙进角色帧。

**攻击通用参数草案**

| attack | hitstun | knockback | hitstop | 备注 |
|---|---:|---:|---:|---|
| `mech_laser` | 0.15 | 0 | 0.05 | 单次命中 |
| `mech_charge` | 0.30 | 140 | 0.07 | 撞墙停止 |
| `mech_claw_slam` | 0.30 | 100 | 0.08 | 附加 1.5s stun |
| `mech_leap_slam` | 0.35 | 180 | 0.08 | 落地 AoE |

### 4.4 霸体与“每个技能间隔1s”

- 四个技能从起手到收招全程霸体。建议在 `start_attack()` 加 `super_armor` 状态（duration = 技能总时长），
  并像 `Nyra.take_hit()` 一样 override：伤害照扣、flash、HP 到 0 进入 KO，但不进入 HURT、
  不应用击退/击飞/眩晕/冻结/减速。
- 不无敌：激光/冲撞/砸地/跳跃都能造成伤害；毒/燃烧等 DOT 仍正常结算。
- `skill_gap` 建议在技能结束时设为 1.0s；AI 在 `skill_gap > 0` 时不开始新技能。
- 每次技能结束清 `super_armor` / runtime；KO、reset、set_enemy 也清。
- `force_attack()` 用于 smoke：清空四个冷却和 `skill_gap`，允许强制起手（沿用 Creepy/Warrior 的做法）。

### 4.5 AI 草案（docx 没有 AI，以下只是起点）

按优先级：

| 条件 | 行为 |
|---|---|
| 玩家在平台/不同高度，且 `leap` 可用 | 跳到玩家附近的可站立点（平台或地面） |
| `distance <= claw_range` | `mech_claw_slam` |
| `charge_min_range <= distance <= charge_range` | `mech_charge` |
| `distance >= laser_min_range` 且有 line-of-sight | `mech_laser` |
| `distance > leap_min_range` 且 `leap` 可用 | `mech_leap_slam` 接近 |
| 都不满足 | 朝玩家走；距离很近且同高度则停住面向玩家 |
| 四个技能都在冷却 / 技能间隔中 | 朝玩家走（远）或停住（近），不发明普通攻击 |

- 不做普通近战：docx 只列了四个技能；是否允许“无技能时普通拳/钳击”必须确认。
- 不做爬梯：没有 climb 动作；玩家上平台时用 4 技能/等待。
- 被击落到地面、玩家在上方且 `leap` 可用时，可以优先用 4 回平台（类似 Creepy 的 AI 逻辑）；
  这是提案，必须确认。
- `decision_interval = 0.15`；F8 关闭 AI；F7 选中后 AI 默认关闭（沿用沙盒约定）。
- line-of-sight 用 `stage.segment_hits_blocks()` 从眼睛到目标中心；被平台挡住时改走位或冲撞。

### 4.6 场景草案

建议直接复用默认 `stage` 的两个平台/两条梯子，仅删除两个 barrier：

```json
"mech_crab": {
  "ground_y": 620,
  "walls": [90, 1190],
  "lane_heights": {"high": 180, "fist": 142, "mid": 120, "low": 60},
  "land_margin": 8,
  "blocks": [
    {
      "kind": "platform",
      "rect": [170, 220, 479, 78],
      "surface_y": 220,
      "sprite": "platform_tropical_long.png",
      "sprite_rect": [170, 206, 479, 96]
    },
    {
      "kind": "platform",
      "rect": [796, 268, 314, 78],
      "surface_y": 268,
      "sprite": "platform_tropical_short.png",
      "sprite_rect": [796, 254, 314, 96]
    }
  ],
  "ladders": [
    {
      "rect": [508, 220, 64, 400],
      "top_y": 220,
      "bottom_y": 620,
      "sprite": "ladder_tropical_wood.png",
      "sprite_rect": [476, 220, 128, 400]
    },
    {
      "rect": [921, 268, 64, 352],
      "top_y": 268,
      "bottom_y": 620,
      "sprite": "ladder_tropical_wood_medium.png",
      "sprite_rect": [873, 268, 160, 352]
    }
  ],
  "player_spawn": [280, 620],
  "dummy_spawn": [600, 620],
  "warrior_spawn": [600, 620],
  "veno_spawn": [820, 620],
  "bat_spawn": [820, 470],
  "mech_crab_spawn": [1000, 620]
}
```

- `mech_crab_spawn` 建议右侧地面 `[1000, 620]`；如果希望它开局站在短平台上，用 `[1000, 268]`，
  但必须先确认 4 技能的落地/平台规则。
- 草图右侧 short platform 画得更高；本草案保持默认高度（long 220 / short 268）。若要严格按草图，
  交换两个平台与梯子的 `surface_y`/`top_y`，但这会影响所有平台素材的对齐，需单独确认。
- 不新增背景/BGM；`Stage` 仍用固定背景。

### 4.7 动画 / FX 草案

建议运行时画布 **384×384，pivot (192,372)**，身体高度约 250，与 Warrior/Creepy 同一档；
最终按 approved side base 校准。脚本生成的帧必须走 `tools/import_frames.py` / `tools/contact_sheet.py`。

| clip | 建议帧数 | 内容 |
|---|---:|---|
| `idle` | 2–4 | 机械待机，核心/眼睛轻微呼吸，钳子不穿身体 |
| `walk` | 4–6 | 原地机械脚交替，身体重心稳定 |
| `jump` | 2 | 被击飞/下落用；不主动跳（除技能 4） |
| `hurt` | 2 | 受击闪烁/后仰 |
| `ko` | 3 | 倒地、核心熄灭 |
| `mech_laser` | 4 | 下蹲+眼睛变大（2）→ 发射（1）→ 收势（1）；眼睛变大后保持 |
| `mech_charge` | 4 | 机械脚原地移动（2）→ 冲撞姿态（1）→ 收势（1） |
| `mech_claw_slam` | 4 | 钳子变大（2）→ 砸地（1）→ 收势（1） |
| `mech_leap_slam` | 5 | 蹲伏（1）→ 起跳（1）→ 空中（1）→ 落地（1）→ 收势（1） |

- 眼睛变大、钳子变大是角色帧的一部分；激光、红色 X 标记、落地冲击、冲撞尘土是独立 FX，
  不要烘焙进角色帧。
- 生成前读 `docs/IMAGE_GENERATION_RULES.md`：同一副钳子/同一身体比例、无穿模、无第二只钳子、
  透明背景、无阴影/文字/边框/场景；右向 3/4 侧视，运行时镜像。
- 审批顺序：**base → 动作帧 contact sheet → 游戏内预览**；不得跳过。
- 如果本轮不生成帧，可以用 `fallback` 静态图先打通逻辑，但 `mech_crab_missing_frames` 不会为 0，
  不能把“逻辑通了”当成完成；最终必须有帧或用户明确接受占位。

### 4.8 数据 / 代码接入清单

1. `game/data/stats.json`：`mech_crab` 的 hp/atk/move/cooldowns/hurtbox/stage_body_width/ai。
2. `game/data/attacks.json`：四个 attack_id、倍率、duration、hitstun/hitstop/knockback、hitbox events。
3. `game/data/animations.json`：`mech_crab_clips`、`mech_crab_frame_size`、`mech_crab_pivot`。
4. `game/data/roster.json`：`enemies.mech_crab`，class/stats/spawn/stage_variant/clips/frame_size/pivot/
   frames_dir/fallback/skill_slots/separates/decides_match。
5. `game/data/debug.json`：`stage_variants.mech_crab` + `mech_crab_spawn`。
6. `game/config.py`：`REQUIRED_STATS`、`REQUIRED_ATTACKS`、`REQUIRED_MECH_CRAB_CLIPS`、
   `ROSTER_CLASSES`、`ANIMATED_CLASSES`、frame_size/pivot 校验；只有新增 projectile kind 时才改
   `PROJECTILE_KINDS`。
7. `game/roster.py`：import/注册 `MechCrab`。
8. `game/mech_crab.py`：AI、四技能、霸体、冷却/间隔、受击/KO/reset、`force_attack`、`skill_remaining`。
9. `game/fx.py` / `game/scene.py`：激光/标记/落地 FX，以及必要的 effect 更新/绘制/清理。
10. `main.py`：smoke phase、flags、最终 conjunction、F7 顺序断言。
11. 最后才更新 README/docs/手册；按 `AGENTS.md` 先问一次是否写入。

---

## 5. 开工前必须 grill 的问题

### Q1 — 冷却与“每个技能间隔1s”

- docx：`(6s)/(8s)/(5s)/(12s)`，另写“每个技能间隔1s”。
- 建议：括号是每个技能各自的冷却；冷却从**起手**开始计时（与 Creepy/Warrior 现有实现一致）；
  “间隔1s”是技能**结束**后的全局 1s，期间不能起新技能；reset 后不额外加开场延迟。
- 需确认：冷却从起手还是收尾算；“1s”从技能结束算还是从起手算；是否允许普通近战
  （docx 没有普攻，建议只靠四技能）。

### Q2 — 霸体范围

- 建议：四个技能从起手到收招全程霸体；伤害照常扣，但不进入 HURT、不被击退/击飞/眩晕/冻结/减速；
  KO 仍可打断；不无敌；毒/燃烧等 DOT 仍结算。
- 需确认：预警和收招是否都算“技能释放期间”；是否防止 KO；是否对持续伤害也霸体（建议只防控制）。

### Q3 — 激光

- 建议：眼睛为发射点；光束直径按眼睛 0.8 推导、游戏内约 14px；1.0s 后从正上方开始，
  以约 240°/s 最短弧转向目标中心，持续 0.9s；每目标每次施法只命中一次，36 伤害；
  被平台/barrier 挡住；可击中平台上的玩家；施法期间螃蟹 x/y 不动、身体朝向不变。
- 需确认：转向速度/是否锁定后继续跟踪；持续多久；是否穿透 block；是否每 0.2s 多段伤害；
  眼睛变大是否持续到技能结束；玩家在背后时是否也能转过去。

### Q4 — 冲撞

- 建议：1.5s 预警，方向在预警**开始**时锁定；700px/s 冲 0.55s（约 385px），撞墙/平台侧面停止；
  命中一次 39，击退 140，hitstun 0.3；可被跳跃躲过；施法全程霸体。
- 需确认：方向锁定时点；距离/速度；撞到玩家是否停下；是否穿过玩家；能否跳过；
  是否被平台/barrier 挡住；冷却从何时算。

### Q5 — 砸地

- 建议：面向前方的一只钳子变大 0.5s，然后砸地；命中前方约 200×140，30 伤害 + 1.5s 眩晕；
  只命中前方，高度 140，跳跃可躲；目标有 super armor 时眩晕被忽略。
- 需确认：单侧还是双侧/环形；范围；是否命中空中；眩晕是否固定 1.5s（不受减伤影响）。

### Q6 — 跳跃砸地

- 建议：1.5s 预警开始时选定玩家当前位置/附近可站立点，红色圆圈 + 大叉固定；0.65s 跳到点，
  飞行期间忽略碰撞；落地 AoE 半径约 100，54 伤害；点在平台上则落平台顶，否则地面；
  玩家可以离开标记躲避。
- 需确认：选点在预警开始还是结束；是否跟踪玩家；最大距离；落点平台规则；是否只在落地结算伤害；
  “跳跃期间不计碰撞”是否也意味着不接角色碰撞/不受伤害；是否能越过平台；是否允许用它回到平台。

### Q7 — 场景

- docx 只写“无barrier”；草图有 long platform（左）+ short platform（右）+ 两条梯子，
  但草图把 short platform 画得更高，默认场景是 long platform 更高。
- 建议：沿用默认平台/梯子高度，只删除两个 barrier；`mech_crab_spawn` 用右侧地面 `[1000,620]`。
- 需确认：是否保留现有高度；是否严格按草图交换上下关系；出生点在地面还是短平台；
  是否需要新背景（建议不新增，背景/BGM 另开任务）。

### Q8 — AI

- docx **没有** Mech-Crab 的 AI 段；P236–P240 的 AI 属于 Creepy Shooter，不要误用。
- 建议优先级：玩家在平台/不同高度且 4 可用 → 跳到附近；近身 → 3；中距离 → 2；远距离有视线 → 1；
  否则走位。四个技能都冷却时只走位，不发明普通攻击。
- 需确认：优先级；是否允许用 4 回平台；全冷却时是追击还是停住；玩家上平台时是否等待；
  是否需要普通近战；F8/F7 的 AI 默认关闭行为。

### Q9 — 身体、hurtbox、画布

- 建议：384×384，pivot (192,372)，身体高度约 250；hurtbox 中央机身 160×150；
  `stage_body_width` 170。最终用 F1 校准。
- 需确认：是否接受中央 hurtbox 不覆盖两只钳子的全部视觉宽度；是否要更大的身体/画布。

### Q10 — 动画与 FX

- 建议：约 22–30 帧（idle 2–4、walk 4–6、jump 2、hurt 2、ko 3、laser 4、charge 4、claw 4、leap 5）；
  眼睛变大和钳子变大画进角色帧；激光/红色 X/落地冲击/尘土做独立 FX；审批顺序 base → contact sheet →
  游戏内预览。
- 需确认：帧预算；本轮是否生成帧；是否接受先用静态 fallback 占位（不能算完成）；
  激光/标记是否允许程序化绘制，还是也要贴图。

### Q11 — 数量、命名、F7

- 建议：单只（`count` 缺省 = 1），不复用多体规则；id `mech_crab`；四个 attack_id 如 §4.1；
  skill slots V/C/X/Z 按 docx 技能 1–4；F7 插在 `creepy_shooter` 之后、`dummy` 之前。
- 需确认：是否确实单只；命名是否接受；F7 顺序是否接受（会影响 `f7_dummy_ok` 的步数）。

### Q12 — 未在 docx 中的平衡值

- 建议：walk 120；激光 900 射程 / 240°/s；冲撞 700px/s、0.55s；跳跃 0.65s / 落地半径 100；
  击退/hitstun 见 §4.3 表；冷却起手计时。
- 需确认：这些先作为首版，允许在 F1/F2/F6 实测后只调数据、不改帧；哪些值必须严格不变。

---

## 6. 已确认决策

> 此表覆盖 §4 的 draft；`instruction.docx` 仍是最高权威。最终实现细节与 smoke flags 见
> `docs/DESIGN_DECISIONS.md` §Mech-Crab (2026-11-03)。

| 问题 | 决策 | 日期 |
|---|---|---|
| Q1 冷却 / 1s 间隔 | 冷却从起手计时：laser 6 / charge 5 / claw 5 / leap 8；技能结束另加 1s 全局 `skill_gap` | 2026-11-03 |
| Q2 霸体范围 | 四技能 warning+active+recovery 全程霸体；伤害照扣，HP=0 仍 KO 并清理光束/标记 | 2026-11-03 |
| Q3 激光 | 中央核心发射；1.0s 预警；正上方起手；90°/s；1.5s；1.2×=36；每目标每次施法仅一次；被平台/barrier 挡住；施法期间螃蟹不动 | 2026-11-03 |
| Q4 冲撞 | 1.0s 预警锁向；700px/s×0.55s；1.5×=45；knockback 140；撞墙停；5s 冷却 | 2026-11-03 |
| Q5 砸地 | 0.5s 预警/钳子变大；1.0×=30；knockback 100；1.2s 眩晕；5s 冷却；玩家侧钳 | 2026-11-03 |
| Q6 跳跃 | 0.8s 预警；固定落点；0.65s 飞行忽略地形；落地 2.0×=60；AoE 半径 100；8s 冷却 | 2026-11-03 |
| Q7 场景 | 无 barrier；长平台 `[170,268,479,78]` surface 268；短平台 `[796,220,314,78]` surface 220；梯子 `[508,268,64,352]` / `[921,220,64,400]`；spawn `[1000,620]` | 2026-11-03 |
| Q8 AI | 异层/高处→跳；近身→砸地；中距→冲撞；远距有视线→激光；否则走位；不普攻/不爬梯；decision 0.15；技能间隔 1s | 2026-11-03 |
| Q9 身体 / hurtbox | 正面 640×640，pivot (320,628)，体高 230；hurtbox 160×150；`stage_body_width` 170；6 腿+2 钳 | 2026-11-03 |
| Q10 动画 / FX | 47 帧角色 + 3 帧锁定 FX；逐动作 contact sheet + 游戏内预览审批；锁定为用户提供的 `mech_crab_lock_anim_v1_00..02`，运行时 205×205（0.8×），0.22/0.18/0.40s，末帧保持到落地；血条/名称上移 230px | 2026-11-03 |
| Q11 数量 / F7 | 单只；F7 顺序 warrior→veno→bat→creepy_shooter→mech_crab→dummy；默认仍是 Creepy Shooter；V/C/X/Z = laser/charge/claw/leap | 2026-11-03 |
| Q12 平衡值 | HP 400 / basic 30 / extra 0；walk 120；jump_v 700；gravity 2200；数值已按用户 2026-11-03 的 docx 更新同步 | 2026-11-03 |

---

## 7. 建议实施顺序

1. **基线**：确认工作区；`main.py --smoke-test` exit 0；不要动未提交的 Rhea/Bat/场景改动。
2. **Grill**：按 §5 Q1–Q12 问完，答案写入 §6；确认前不改代码/JSON/素材。
3. **素材（若本轮做）**：approved front base → 动作帧 contact sheet → 游戏内预览；每轮等用户批准。
4. **数据/注册骨架**：stats、attacks（先占位 timing）、animations、roster、debug variant、config、
   `MechCrab` 类、F7 插入；跑 smoke，先让 `mech_crab_present` / `mech_crab_stage_ok` /
   `mech_crab_slots_ok` 通过。
5. **霸体 + 1s 技能间隔**：四个技能先统一走 `start_attack`/`take_hit`/`skill_gap`；
   smoke 验证伤害照扣但不打断、KO 仍有效、技能间隔 1s。
6. **技能 1 激光**：光束对象、转向、遮挡、单次命中；smoke + F1/F2 预览。
7. **技能 2 冲撞**：预警锁向、位移、撞墙停止、命中；smoke + F1/F2。
8. **技能 3 砸地**：钳子变大 timing、hitbox、眩晕；smoke + F1/F2。
9. **技能 4 跳跃**：标记、插值飞行、忽略碰撞、平台落地、AoE；smoke + F1/F2。
10. **AI**：优先级、视线、玩家上平台、回平台；F8 开关；跑 10–15s 实战观察。
11. **整合**：F7 顺序、`scene_variant_switch_ok`、`platform_spawn_clear_ok`、WIN/KO/reset 清理。
12. **完整回归**：完整 smoke、F1/F2/F6、预览图/contact sheet；确认无旧场景/弹体残留。
13. **文档**：实现并获用户确认后，按 `AGENTS.md` 问一次是否写入 README/docs/手册。

---

## 8. smoke / 手动验证清单

### 8.1 建议新增 flags

| flag | 验证内容 |
|---|---|
| `mech_crab_present` | roster 能构造；HP 400 / atk 30；四个 skill slots 正确 |
| `mech_crab_stage_ok` | 无 barrier；两个平台/两条梯子与 variant 一致；spawn 正确 |
| `mech_crab_armor_ok` | 四个技能期间受击只扣血、不进入 HURT/不被击退/眩晕；KO 仍可打断 |
| `mech_crab_laser_ok` | 1.0s 预警、从上方开始转向、单次 36 伤害、被 block 挡住、冷却 6s |
| `mech_crab_charge_ok` | 1.5s 预警、位移距离、撞墙停止、39 伤害、冷却 8s |
| `mech_crab_claw_ok` | 0.5s 钳子变大、30 伤害、1.5s 眩晕、冷却 5s |
| `mech_crab_leap_ok` | 1.5s 预警、标记固定、飞行忽略碰撞、落地 54、平台落地、冷却 12s |
| `mech_crab_gap_ok` | 技能结束后 1s 内不开始下一个技能；不同技能不重叠 |
| `mech_crab_slots_ok` | V/C/X/Z 与四个 attack_id 一致；空槽安全 |
| `mech_crab_win_ok` | KO 后 WIN/重开正常 |
| `mech_crab_cleanup_ok` | 激光/标记/FX 在 KO、reset、set_enemy 后清空，不残留伤害 |
| `mech_crab_missing_frames` | 所有配置 clip 文件存在（最终必须 0） |
| `mech_crab_fx_missing` | 独立 FX 文件存在（如有贴图 FX） |

### 8.2 必须同步更新的旧测试

- `f7_cycle_ok` / `f7_bat_ok` / `f7_creepy_ok` / `f7_dummy_ok`：插入 `mech_crab` 后调整步数，
  新增 `f7_mech_crab_ok`。
- `scene_variant_switch_ok`：加入 Mech-Crab 的 variant 检查。
- `platform_spawn_clear_ok`：新 spawn 不与平台/barrier 相交。
- 最终 conjunction：所有新 flag 为 true 才 exit 0；任何一个 false 都不能算完成。

### 8.3 手动检查

- F1：hurtbox、激光线段/厚度、冲撞 hitbox、砸地 hitbox、跳跃落点 AoE。
- F2：四个技能冷却、当前 attack/clip/frame、AI 开关、`skill_gap`、激光角度/落点（如加了调试字段）。
- F7：顺序 warrior → veno → bat → creepy_shooter → mech_crab → dummy；每次切换场景/敌人都正确。
- F8：AI 关闭后不会自己起手；F9 reset 不残留光束/标记/霸体。
- F6 / 0.25×：观察预警、激光转向、跳跃轨迹和落地时机。
- 预览：每个技能一张 F1/F2 截图；如生成帧，出 contact sheet 和游戏内预览。

---

## 9. 风险与边界

- **激光残留**：光束必须在技能结束、KO、reset、set_enemy 时销毁；否则会留在场景里继续命中。
- **激光遮挡/厚度**：线段碰撞要按光束半径膨胀 hurtbox；block 检测要用线段而不是只测端点，
  否则玩家站在平台边缘会被误判。
- **跳跃落地**：飞行期间忽略碰撞，落地必须解析到平台顶或地面，不能卡进平台侧面；
  目标点在平台边缘/墙外时要 clamp 或改选可站立点。
- **冲撞卡墙**：用 `stage.move_x()` 而不是直接改 x；撞墙后要正常进入收招/冷却。
- **霸体与 KO**：霸体只防控制，不防伤害；HP 到 0 必须进 KO，并清掉攻击 runtime/光束。
- **技能间隔语义**：冷却从起手还是结束算、1s 间隔从何时算，会影响实际 DPS；确认后固定，不要中途混用。
- **F7 顺序**：新增敌人会改变现有 F7 smoke 的步数；只改测试假设，不要为了旧测试把新敌人放到奇怪的位置。
- **素材缺失**：没有帧时 `AnimationPlayer` 会回退到 canonical 静态图；不能让 fallback 掩盖
  `missing_frames`，最终完成必须有帧或用户明确接受占位。
- **不要碰**：其他敌人/角色、`instruction.docx`、`Image/`、`UI Resources/`、`sketch/`、背景/BGM；
  未经明确要求不 commit/push。

---

## 10. Definition of Done

- [x] §5 的 Q1–Q12 已由用户确认，§6 已填写。
- [x] `mech_crab` 的 stats/attacks/animations/roster/debug variant 全部接入，config 校验通过。
- [x] 四技能伤害为 36 / 45 / 30+1.2s stun / 60；冷却 6/5/5/8s；技能间隔 1s。
- [x] 四技能全程霸体：伤害照扣、不被控制、KO 仍可打断。
- [x] 激光从中央核心发出、先向上再转向角色、单次命中、可被平台/barrier 挡住。
- [x] 冲撞有 1.0s 预警、方向锁定、700px/s×0.55s、撞墙停。
- [x] 砸地有 0.5s 钳子变大、前方 200×140、30 + 1.2s 眩晕。
- [x] 跳跃有 0.8s 预警、用户绘制三帧锁定图像（0.22/0.18/0.40s，末帧保持）、飞行忽略碰撞、落地 60、平台落点。
- [x] 专属场景无 barrier；平台/梯子/spawn 与 §6 一致。
- [x] F7 / V·C·X·Z / F2 / F8 / F9 正常；旧 smoke 全部更新并通过。
- [x] `main.py --smoke-test` exit 0；`mech_crab_*` flags 全为 true；`mech_crab_missing_frames == 0`、`mech_crab_fx_missing == 0`。
- [x] F1/F2/F6 与预览图确认视觉/判定；没有残留光束/标记/霸体。
- [x] 用户确认后，才按 AGENTS.md 询问是否更新 README/docs/手册；`instruction.docx` 未被修改。
- [x] 未 commit / 未 push（本轮未要求）。

---

## 11. 实现并确认后才更新的文字

按 `AGENTS.md`：先实现和验证，用户确认设计后**问一次**是否写入；不要自动改。

- [x] `README.md`：Mech-Crab 的 HP/ATK、四技能、霸体/间隔、场景、F2 调试、血条上移与锁定图像。
- [x] `docs/DESIGN_DECISIONS.md`：新增 §Mech-Crab (2026-11-03)，含招式语义、激光/跳跃碰撞、AI、场景 variant、血条 lift 与锁定 FX。
- [x] `docs/DEBUG.md`：Phase G、新 smoke flags、F1/F2 手动检查、F7 顺序。
- [x] `docs/ASSET_PIPELINE.md`：新增 §Mech-Crab (2026-11-03)，记录 canvas/pivot/帧清单、导入参数和审批图。
- [x] `docs/NEXT_SESSION_MECH_CRAB.md`：顶部状态、§6、§10 已回填（2026-11-03）。
- [ ] `Island Survival 基础操作手册.docx`：仅在用户要求时更新。
- [x] `instruction.docx`：**绝不修改**（本轮未修改）。
