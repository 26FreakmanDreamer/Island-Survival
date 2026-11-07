# Next Session — Shadow Ninja 第二形态（幻影形态）设计与接入

> 日期：2026-11-06
> 状态：**实现中；设计已确认**。本文是交接文档和 grill 清单。
> **2026-11-07 更新**：idle/walk v2、transform v2（**11 帧 / 1.36s**）、revert v2（**6 帧 / 0.60s**）、P1 影爪 v2、P2 影缚（v1 施法 + v2 缠绕）、P3（**attack / vanish v2**，其余 v1）均已接入运行时；所有 62 个角色帧与 FX 已安装，**smoke exit 0**。动画细节以 `docs/SHADOW_NINJA_PHANTOM_ANIMATION_DESIGN.md` 为准。本文 §4.2/§6/§7/附录 C 中旧的 4+4 帧、35 帧、1.20s/0.40s 数字是历史设计稿。
> 基线：分支 `rhea-thorn-integration`，HEAD `207b8c3`（普通形态 + Crooked Witch 素材已提交）；
> 本轮新增本文（未提交），并在 `docs/NEXT_SESSION_SHADOW_NINJA.md` 附录 A 加了一行链接；
> `tmp/` 保持未跟踪（中间审核图，不要提交）。
> 权威规格：`instruction.docx` 的 Shadow Ninja 段（P294–P311）；本文只摘录，**绝不修改 docx**。
> 本轮目标：技能 4 变身**幻影形态**，三个**全新动作模型**的幻影技能，以及独立的
> **变身过渡帧**和**还原过渡帧**。普通形态的 35 帧保持不变，不拿普通帧凑幻影动作。
> 默认角色 **Lina**，默认敌人仍是 **Creepy Shooter**；Shadow Ninja 仍是 F7 的单个 enemy。
> 阅读顺序：本文 → `docs/NEXT_SESSION_SHADOW_NINJA.md` 附录 A → `instruction.docx` 的
> Shadow Ninja 段 → `AGENTS.md` → `README.md` → `docs/DESIGN_DECISIONS.md` →
> `docs/DEBUG.md` → `docs/ASSET_PIPELINE.md`；生成素材前再读
> `docs/IMAGE_GENERATION_RULES.md`。

---

## 0. 给下一个 session 的开场 prompt（可直接复制）

```text
读取 docs/NEXT_SESSION_SHADOW_NINJA_PHANTOM.md、docs/NEXT_SESSION_SHADOW_NINJA.md 附录 A、
instruction.docx 的 Shadow Ninja 段（P294–P311）、AGENTS.md、README.md、
docs/DESIGN_DECISIONS.md、docs/DEBUG.md、docs/ASSET_PIPELINE.md；
如果要生成动画帧，再读 docs/IMAGE_GENERATION_RULES.md。

先运行 .venv/Scripts/python.exe main.py --smoke-test，确认基线 exit 0，然后按本文 §6 的
Q1–Q19 一次性 grill 我。每项给出当前 docx 原文、建议值和影响范围。我确认后，先把答案写入
本文 §7“已确认决策”，再按 §8 的顺序实施；不要先改代码/JSON/素材。

本轮范围：只做 Shadow Ninja 的“第二形态/幻影形态”（技能 4）、三个全新动作模型的幻影技能、
变身过渡帧和还原过渡帧。普通形态的 35 帧、苦无 FX、印记和 AI 不重做。幻影形态必须是
全新的动作模型，不能复用/镜像/换色普通形态的技能帧；变身和还原各有一组独立绘制的过渡帧，
不能把变身帧倒放当还原帧，也不能只做单帧淡入淡出。

约束：不要修改 instruction.docx、Image/、UI Resources/、sketch/、其他角色/敌人、背景/BGM；
不要用 pytest；验证用 --smoke-test、F1/F2/F6 和预览图；不要 commit/push，除非我明确要求。
素材按 base → 动作帧 contact sheet → 游戏内预览的顺序逐轮审批；不要直接把
Image/Enemy/shadow-ninja-phantom-no-aura-256.png 当运行时帧，也不要把技能 FX、雨刃、
影缚触手烘焙进角色帧。
```

---

## 1. 本轮范围

### 1.1 做

- 技能 4 `shadow_phantom_form`：15s 冷却，冷却**在还原结束后**才开始；变身期间（含变身帧）
  无敌、免疫负面、清除自身印记/负面、不可被叠印记/被动、无 hitbox。
- 幻影形态三个**全新动作模型**的技能，每个每次变身只能使用一次；三个都用完自动还原。
- 独立的**变身过渡帧**（normal → phantom）和**还原过渡帧**（phantom → normal）。
- 幻影形态的 idle / walk / jump（新形象、新动作），以及三个技能的角色帧。
- 幻影技能的数据、hitbox/投射物、FX、AI、F1/F2 调试、smoke Phase I。
- 普通形态与幻影形态之间的状态清理、冷却、AI 回退、F7/F9 重置。

### 1.2 不做

- 不重做普通形态的 35 帧、苦无 FX、印记、普通 AI。
- 不新增敌人槽位；Shadow Ninja 仍是 F7 的单个 enemy，默认敌人不变。
- 不做幻影形态的 hurt/KO/crouch/stun 帧：幻影无敌且无 hitbox，受伤/倒地仍由还原后的
  普通形态表现（如果调试需要，可后续补 fallback，但不在本轮范围）。
- 不做全游戏战斗 UI、商店、食物、等级、金币、存档、BGM/背景切换。
- 不改 `instruction.docx`、`Image/`、`UI Resources/`、`sketch/`、其他角色/敌人。
- 不做 pytest；不 commit/push，除非用户明确要求。

---

## 2. instruction.docx 原文与事实

### 2.1 幻影形态原文（P302–P305）

> 技能4：（15s）变身幻影形态，
> 形象：`Image\Enemy\shadow-ninja-phantom-no-aura-256.png`
> 幻影形态期间（包括变身帧）不会受到任何伤害，免疫一切负面效果，刷新对方在自己身上叠的印记和
> 负面状态，幻影形态不可让对方叠印记，或者任何被动，无hitbox。
> 幻影形态的每个技能拥有全新的动作模型，且技能冷却独立计算。幻影形态每个技能只能使用一次，
> 3个技能全部使用完毕自动解除形态。解除形态后此技能才进入冷却。

### 2.2 AI 原文（P307–P311，含普通形态）

> 距离较近时优先2控制+1靠近攻击；如果2冷却，直接1攻击；多叠被动。
> 距离较远，可先2，等到2的暗影离目标很近（期间可以向目标移动），则释放3逼近，之后使用1。
> 也可以直接3突进，再使用2，1.
> 在距离近时，如果血量较低，也可以3技能拉开距离，等待技能冷却，多用远程控制。
> 当血量较低，或者将会受到大量伤害时，优先使用4变身。变身期间AI如上。

### 2.3 docx 已定 / 未定

| 项目 | docx 状态 | 对本轮的含义 |
|---|---|---|
| 变身冷却 | **15s** | 冷却从“解除形态后”开始，不是变身开始时 |
| 幻影形象 | `shadow-ninja-phantom-no-aura-256.png` | 作为幻影 base；另一张 `shadow-ninja-phantom-shadow-256.png` 只作 aura/参考 |
| 变身帧无敌 | **是**，包括变身帧 | 变身第 0 帧就 `invincible=True`，不能等动画结束 |
| 负面/印记清理 | **是**，清除对方在自己身上叠的印记和负面状态 | 清 `marks`、`shadow_marks`、`statuses`、hitstun/KB/flash |
| 不可被叠印记/被动 | **是** | 玩家攻击不能命中幻影；已有印记在变身时清掉 |
| 无 hitbox | **是** | 玩家的近战/投射物应穿过，不消耗、不造成伤害、不挂状态 |
| 三个全新动作模型 | **是** | 不能复用普通形态的 slash/throw/dash 帧 |
| 技能冷却独立 | **是**，但 docx 未给具体秒数 | 与普通技能独立；每个技能每次变身只能用一次 |
| 每个技能只能用一次 | **是** | 用“已使用”标记即可，不一定要显示倒计时 |
| 三个用完自动解除 | **是** | 第三个技能动作结束后进入还原过渡 |
| 解除后才进入冷却 | **是** | 还原结束才设 `transform_cd = 15` |
| 变身 AI 触发 | 低血量或“将会受到大量伤害” | 需要一个可解释的伤害预估 |
| 幻影三技能名称/数值/动作 | **未给** | 本文 §4.3 给推荐方案，必须 grill 确认 |
| 变身/还原时长、过渡帧数 | **未给** | 本文建议 4+4 帧、各 0.40s，必须确认 |
| 还原期间是否无敌 | **未明确** | 本文建议还原全程仍无敌；见 Q6 |
| 幻影期间移动/跳跃/碰撞 | **未给** | 本文建议沿用 1.5× 移速和跳跃物理、保留身体分离 |
| 普通技能冷却是否暂停 | **未给** | 本文建议继续走；见 Q9 |
| 玩家身上的既有印记是否保留 | **未给** | 本文建议保留；变身只清 Shadow Ninja 自己身上的 |
| 幻影技能是否叠印记 | **未给** | 本文建议不叠；被动只属于普通形态技能 1/2/3 |
| 变身能否在受击/空中使用 | **未给** | 本文建议 IDLE/WALK/AIR 可用，HURT/KO 不可；见 Q5 |

---

## 3. 当前实现快照（代码事实）

### 3.1 普通形态已经完成

- `game/shadow_ninja.py`：`ShadowNinja(Fighter)`，普通形态 3 技能 + AI + 印记。
- `game/data/stats.json`：`shadow_ninja` 的 HP/ATK 复制、1.5× 移速、hurtbox、AI 字段。
- `game/data/attacks.json`：`shadow_kunai_slash` / `shadow_kunai_throw` / `shadow_dash`。
- `game/data/animations.json`：`shadow_ninja_clips` 35 帧 + `shadow_ninja_frame_size` /
  `shadow_ninja_pivot`。
- `game/data/roster.json`：`skill_slots = ["shadow_kunai_slash", "shadow_kunai_throw",
  "shadow_dash", null]`；`frames_dir = "shadow_ninja"`；`fallback` 指向普通形态图。
- `assets/frames/shadow_ninja/`：35 帧 + `fx/shadow_kunai_00..01.png`。
- smoke Phase H：所有 `shadow_ninja_*` flags 为 true；`shadow_ninja_missing_frames == 0`；
  `shadow_ninja_fx_missing == 0`。
- 当前 `skill_slots[3]` 是 `null`，F2 显示 `-`，Z 无效，AI 不变身。

### 3.2 可复用的代码

| 能力 | 位置 | 说明 |
|---|---|---|
| 变身状态 | `game/fighter.py:14` `FighterState.TRANSFORM` | 目前只有 Lina 使用；Shadow Ninja 可直接复用 |
| 无敌 | `game/fighter.py:98` `invincible`；`take_hit` `:171` | `take_hit` / `resolve_hit` / `resolve_projectile_hit` 都会提前返回 |
| 印记字段 | `game/fighter.py:99-105` | `marks`、`shadow_marks` 及 burst 字段；变身时清零 |
| 状态清理 | `game/status.py` `StatusSet.clear()`；`game/fighter.py:508` `reset_common` | 变身时清 `statuses` |
| 攻击运行时 | `game/combat.py` `AttackRuntime` | 幻影技能继续用 hitbox/projectile 事件 |
| 投射物基类 | `game/projectile.py` `ShurikenProjectile` / `SonicWave` | 影缚可复用 `ShurikenProjectile`；影雨需要新的下落弹类 |
| 命中 FX | `game/scene.py:841` `spawn_hit_fx`；`RingBurstFx` | 幻影命中可用紫色 ring/particles，不必先做贴图 |
| 调试键 | `game/scene.py:66` `SKILL_KEYS`；`:1306` | V/C/X/Z → slot 0/1/2/3；`force_skill` 在 `game/fighter.py:269` |
| F2 面板 | `game/debug.py:185` | 目前显示 4 个 slot 和冷却；需要加幻影专用行 |
| smoke | `main.py:3822` Phase H | 新增 Phase I，保留 Phase H 全部断言 |

### 3.3 必须新增/改造的部分

- `ShadowNinja` 自己管理 `NORMAL → TRANSFORM_IN → PHANTOM → REVERT_OUT → NORMAL` 状态机。
- `AnimationPlayer` 的第二套 clip table：目前叫 `flame_clips`，被 Lina 使用；幻影可复用这个
  机制（roster 里 `"flame_clips": "shadow_ninja_phantom_clips"`），或把它泛化成 `alt_clips`。
  推荐先复用现有机制，减少对 Lina 的改动；代码注释写清“flame 是历史命名，对 Shadow Ninja
  表示 phantom”。
- 幻影专用 clip：`transform`（normal 表）+ `phantom/revert`（phantom 表）+ 3 个技能。
- 幻影专用 attack 数据、投射物 kind、FX、AI、F2 显示、smoke Phase I。
- 玩家的攻击对幻影“无 hitbox”的处理：推荐在 `scene.targets_for()` 过滤
  `getattr(target, "phantom_form", False)`，让近战/投射物直接穿过；同时保留 `invincible`
  作为脚本伤害的第二道保险。

---

## 4. 推荐设计（全部数字都是建议值，必须 grill 确认）

### 4.1 形态状态机

```text
NORMAL
  │  技能 4 可用，且 AI/调试触发
  ▼
TRANSFORM_IN（0.40s，4 帧，从第 0 帧起无敌）
  │  动画结束
  ▼
PHANTOM（无敌、无 hitbox、3 个技能各一次）
  │  第三个技能的动作结束
  ▼
REVERT_OUT（0.40s，4 帧，建议全程无敌）
  │  动画结束
  ▼
NORMAL（transform_cd = 15s）
```

推荐字段：

| 字段 | 含义 |
|---|---|
| `phantom_form: bool` | 幻影形态是否激活（从变身第 0 帧到还原最后一帧） |
| `reverting: bool` | 正在播放还原过渡 |
| `transform_cd: float` | 技能 4 冷却；幻影期间保持 0，还原结束设为 15 |
| `transform_cd_max: float` | 15.0，来自 stats |
| `phantom_used: dict[str, bool]` | 三个幻影技能是否已使用 |
| `skill_gap: float` | 普通/幻影技能之间的 0.2s 间隔（复用现有字段） |
| `phantom_plan` | 可选的 AI 当前顺序，不是必须 |

关键规则：

- 幻影形态沿用变身前的 HP/ATK/1.5× 移速，不再复制玩家、不回血；变身本身不改变数值。
- 变身第 0 帧：`invincible=True`、`phantom_form=True`、清 `marks` / `shadow_marks` /
  `mark_burst_time/damage` / `shadow_mark_burst_time/damage` / `statuses` / `hitstun` /
  KB / flash、`vx=0`；不等待动画结束。
- 变身期间不执行普通 AI、不开始普通攻击；动画结束切到 phantom clip table。
- 幻影期间 `targets_for(player)` 不返回它；玩家攻击/投射物穿过，不消耗、不挂状态。
- 幻影期间在 `update` 最前面 `if self.phantom_form: self.statuses.clear()` 作为兜底，
  保证变身/幻影/还原期间 F11/脚本直接加状态也无法生效。
- 幻影期间普通技能冷却继续走；幻影技能用“已使用”标记，不和普通冷却混用。
- 第三个幻影技能的动作结束后进入 REVERT_OUT；还原结束才 `invincible=False`、
  `phantom_form=False`、`transform_cd=15`。
- F9 / F7 / KO / 场景重建：直接清回 NORMAL，不播过渡，不留下幻影状态。

### 4.2 变身过渡帧与还原过渡帧

**要求：两组都是独立绘制的 4 帧，不是把变身帧倒放，也不是单帧淡入淡出。**

#### 变身过渡 `transform`（normal clip table）

| 帧 | 时长 | 画面 | 游戏逻辑 |
|---|---:|---|---|
| 00 | 0.10s | 普通形态 idle，脚边紫色影雾开始聚集；苦无还在手中 | `invincible=True`、`phantom_form=True`、清印记/状态；面向目标 |
| 01 | 0.10s | 身体微微后仰，头发被影雾托起，苦无开始溶解成紫色粒子 | `vx=0`；不攻击；可继续受重力 |
| 02 | 0.10s | 轮廓拉长，眼睛发光，影雾包住全身；苦无只剩轮廓 | 仍无 hitbox；不要烘焙技能 FX |
| 03 | 0.10s | 幻影形态的 idle 姿势，影雾落定；武器完全消失 | 动画结束：`anim.set_variant("flame")`（内部名，见 §5.6），切 phantom idle |

#### 还原过渡 `phantom/revert`（phantom clip table）

| 帧 | 时长 | 画面 | 游戏逻辑 |
|---|---:|---|---|
| 00 | 0.10s | 幻影 idle，影雾翻涌，头发/触须收回 | 仍 `invincible=True`、`phantom_form=True` |
| 01 | 0.10s | 身体压缩，紫色轮廓变淡，影雾向脚下收束 | `vx=0`；不攻击 |
| 02 | 0.10s | 普通形态的轮廓重新出现，苦无在手中凝形 | 仍无敌；不要出现两把苦无 |
| 03 | 0.10s | 普通形态 idle，残余影雾散去 | 动画结束：`set_variant("normal")`、`invincible=False`、`phantom_form=False`、`transform_cd=15` |

补充：

- 两组过渡都必须保持**同一身体尺寸/头身比/脚底基线**；变身时不能把角色缩小来塞进画布。
- 变身帧 00 是普通形态姿势，03 是幻影姿势；还原帧 00 是幻影姿势，03 是普通姿势。
  中间帧要表现“轮廓/材质/头发/影雾”的变化，不是简单换色。
- 苦无只在普通形态出现；变身 01–03 可以表现它溶解，但幻影帧里不能有苦无。
- 如果希望更电影化，可以加到 5–6 帧/边；但不得用倒放或单帧淡入淡出替代。

### 4.3 幻影三技能（推荐方案）

三个技能都使用**全新的动作模型**，不复用普通形态的 slash/throw/dash 帧；每个每次变身
只能使用一次；不叠加普通形态的印记（推荐；见 Q8）。

| 槽 | id | 名称 | 动作模型 | 伤害 | 几何/控制 | 5 帧动作 |
|---|---|---|---|---|---|---|
| P1 | `shadow_phantom_rend` | 影爪（Shadow Rend） | 头发与近侧手臂合成一条长影爪，向前横扫；角色帧只画挥击，长爪是独立 FX | 1.0 atk | 高判定 `[20,-195,240,55]`（下沿 140px，蹲下可躲）；t=0.18–0.36；击退 80；hitstun 0.2；hitstop 0.06 | 00 收势蓄力 → 01 影雾聚手 → 02 横扫 → 03 收势 → 04 回 idle |
| P2 | `shadow_phantom_rain` | 影雨（Shadow Rain） | 双臂抬起，头发张开，三个影刃从目标上方落下；角色帧只画施法，雨刃是独立投射物 | 0.5 atk × 3（全中 1.5） | 目标 x 偏移 `[-80, 0, +80]`；从上方 420px 落下，速度 900，半径 16；有 0.3–0.4s 地面预警；可横向移动躲开；平台/barrier 可挡 | 00 抬臂 → 01 影门开启 → 02 影刃下落 → 03 冲击 → 04 回 idle |
| P3 | `shadow_phantom_bind` | 影缚（Shadow Bind） | 幻影俯身触地，影雾触手沿地面冲向目标，缠住定身；角色帧只画触地，触手是独立投射物/FX | 0.3 atk + 1.2s 眩晕 | 低车道；速度 900；射程 700；半径 20；不穿 block；跳跃可躲、蹲下会被打中 | 00 俯身 → 01 触手展开 → 02 前冲 → 03 缠住 → 04 回 idle |

P3 默认只做定身/眩晕，不做拉拽位移；拉拽会涉及目标位置和地形碰撞，若确实需要，另开
Q 并单独测试。P2 的雨刃也不做追踪，落点固定，玩家可以走位躲。

第三个技能已经生成的雨刃/触手在还原后可以继续完成，不因还原而消失；它们仍不叠印记。
如果用户希望“一还原就清空剩余投射物”，在 `_start_revert` 里清掉 owner 为 Shadow Ninja
的幻影投射物即可，但这是另一个决策，需确认。

推荐数值的理由：

- P1 是稳定的近/中距离收尾，1.0 atk；高判定让玩家可以蹲下躲，和普通形态技能 1 的读法一致。
- P2 是远距离压制，最多 1.5 atk，但三段分开、可走位躲，不保证全中。
- P3 是控制起手，伤害低但 1.2s 眩晕，能把 P1/P2 串起来；跳跃可躲，给玩家反制。
- 三个技能全中约 2.8 atk（以 20 atk 计约 56 伤害），加上幻影无敌和 3 次限制，
  作为 15s 大招是强但不至于一套秒杀。
- 如果用户觉得太强/太弱，优先调 P2 的单段伤害和 P3 的眩晕时长，不动 P1 的判定高度。

幻影技能的实现方式：

- P1：`type: "hitbox"`，长爪 FX 用独立贴图或 `SlashEffect`；角色帧不拉长身体。
- P2：新增 `ShadowRainBlade` 下落投射物（可参考 `SonicWave` 的 `ux/uy` 思路，但不要回旋）；
  在 `scene.spawn_projectile_from_event` 增加 `shadow_phantom_rain` 分支，一次生成 3 个；
  地面预警用独立 FX（2 帧或程序化圆环）。
- P3：新增 `ShadowBindProjectile(ShurikenProjectile)`，`kind="shadow_phantom_bind"`，
  `visual_kind` 用触手贴图/程序化触手；命中后由 `ShadowNinja.on_projectile_hit` 加
  `stun 1.2s`；不叠印记。
- 三个技能都不调用 `_add_shadow_mark`；`on_hit_success` / `on_projectile_hit` 用 attack id /
  kind 白名单，避免误叠。

### 4.4 幻影 AI

**变身触发**（在 `_think` 的最前面，优先于普通防御/攻击）：

- `transform_cd <= 0` 且不在幻影/变身中；
- `hp <= max_hp * low_hp_pct`（沿用 0.4），或 `_incoming_damage(scene) >= max_hp * 0.25`；
- 玩家还活着、match 未结束；
- 满足时 `start_transform()`，不再执行普通技能。

`_incoming_damage(scene)` 建议：

- 扫描玩家当前 `attack_runtime` 的 hitbox 事件和玩家拥有的投射物；
- 用 `attack_damage(player, attack, event)` 或 `projectile.damage` 估算；
- 只统计在 `threat_range` 内、方向朝向自己的威胁；
- 取最大值，和 `max_hp * 0.25` 比较；
- 这是启发式，不要求帧级精确；smoke 用固定场景验证。

**幻影期间**：

- 不执行普通 `_try_defense`（无敌，不需要蹲/跳）；可以保留 barrier hop / 跳跃移动。
- 近距离（`<= close_range`）：P3 影缚 → P1 影爪 → P2 影雨。
- P1 的判定到 260px；AI 在 `claw_range` 内即可用 P1，不必只等 `close_range`。
- 远距离：P2 影雨 → 靠近后用 P3 → P1；如果 P3/P1 还差距离，走向目标。
- 只剩 P1 且距离 > 260：走向目标（幻影无敌，可以安全接近）；必要时跳跃/barrier hop。
- 每个技能后设 `skill_gap = 0.2`；第三个技能动作结束自动还原，不再开始新技能。
- 目标死亡 / match over：停止，不还原也可以；F9 重置时清状态。
- 安全兜底：如果 10s 内无法使用剩余技能（例如目标不可达），强制还原；该兜底需要用户确认。

### 4.5 帧预算与素材布局

推荐 **35 个新角色帧**（叠加在普通形态 35 帧之上，总计 70 帧）：

| clip | 帧数 | 时长 | 位置 |
|---|---:|---|---|
| `transform`（变身过渡） | 4 | 4 × 0.10 = 0.40s | `assets/frames/shadow_ninja/transform/`（normal 表） |
| `phantom/idle` | 4 | 4 × 0.30 = 1.20s loop | `assets/frames/shadow_ninja/phantom/idle/` |
| `phantom/walk` | 6 | 6 × 0.10 = 0.60s loop | `assets/frames/shadow_ninja/phantom/walk/` |
| `phantom/jump` | 2 | 2 × 0.20 = 0.40s | `assets/frames/shadow_ninja/phantom/jump/` |
| `phantom/shadow_phantom_rend` | 5 | 5 × 0.09 = 0.45s | `assets/frames/shadow_ninja/phantom/shadow_phantom_rend/` |
| `phantom/shadow_phantom_rain` | 5 | 5 × 0.10 = 0.50s | `assets/frames/shadow_ninja/phantom/shadow_phantom_rain/` |
| `phantom/shadow_phantom_bind` | 5 | 5 × 0.10 = 0.50s | `assets/frames/shadow_ninja/phantom/shadow_phantom_bind/` |
| `phantom/revert`（还原过渡） | 4 | 4 × 0.10 = 0.40s | `assets/frames/shadow_ninja/phantom/revert/`（phantom 表） |
| **合计** | **35** | | |

如果某个技能 5 帧不够表达动作，可加到 6 帧（总计 38），但必须重新确认时长和
attacks.json 的 `duration` 一致；不要用缩放/拉伸凑帧数。

**独立 FX（不烘焙进角色帧）**：

- 变身/还原：紫色 burst/ring + 影雾，2–3 帧或程序化 FX；角色帧本身要能读出形态变化，
  FX 只是增强。
- P1 影爪：3 帧紫色长爪轨迹，独立绘制，允许超出角色帧的 384 画布。
- P2 影雨：地面预警 2 帧 + 下落影刃 2–3 帧 + 命中 burst 2 帧。
- P3 影缚：地面触手 3–4 帧 + 目标身上的束缚 ring 2 帧。
- 所有 FX 放 `assets/frames/shadow_ninja/phantom/fx/`；角色帧里不出现雨刃/触手/印记/眩晕星。

**base / 画布 / pivot / 体高**：

- 幻影 base：`Image/Enemy/shadow-ninja-phantom-no-aura-256.png`；和普通形态一样使用
  **右向完全侧视**（不要 3/4 侧视），运行时只翻转朝左；
  `shadow-ninja-phantom-shadow-256.png` 只作为 aura/影雾参考，不作为身体 base。
- 运行时画布：`384×384`；pivot `(192,372)`；body `214`；`stage_body_width 100`；
  物理 hurtbox 沿用 `56×210`（幻影期间战斗 hitbox 关闭，但移动/分离仍需要身体宽度）。
- 幻影的长发和脚下影雾会撑大 alpha bbox；**不要**把整个 bbox 自动缩到 214。
  以“头顶到脚底/影雾接地”为 body 214，固定 scale，允许影雾在 pivot 下方/周围；如果
  384 画布放不下，先停下来问用户，不要缩小人物或裁掉头发。
- 变身/还原帧也必须用同一画布、pivot、body 214；普通形态和幻影形态的头顶/脚底基线对齐。
- 素材审批顺序：phantom base → 每个动作的 contact sheet → 游戏内预览 → 安装到
  `assets/frames/shadow_ninja/`；每轮都要用户确认后才进入下一步。

### 4.6 调试 / HUD

- F1：幻影期间不画敌方 hurtbox（红色框），但继续画技能 hitbox；变身/还原期间也不画。
- F2：
  - 普通形态：`S4 shadow_phantom_form 0.0s`（可用）；
  - 幻影期间：`PHANTOM ACTIVE 1/3 USED`、`S1 READY/USED`、`S2 READY/USED`、
    `S3 READY/USED`；
  - 还原后：`PHANTOM CD 15.0s`；
  - 保留 `SHADOW MARKS n/3` 行。
- V/C/X：普通形态对应普通技能 1/2/3；幻影期间改为强制幻影技能 1/2/3（调试用）。
  Z：普通形态强制变身；幻影期间 no-op。
- F6 0.25×/0.5×：检查变身/还原 0.4s、P1/P2/P3 的 timing、无敌窗口。
- F7：切走再切回，幻影状态必须清干净；F9/R：回到普通形态 idle，无冷却/印记/状态残留。
- F8：打开 AI，观察低血量/大伤害触发和三个技能的释放顺序。

---

## 5. 按文件的接入方案

### 5.1 `game/data/stats.json`

在 `shadow_ninja` 增加（建议值，待确认）：

```json
"cooldowns": {
  "slash": 0.5,
  "throw": 5.0,
  "dash": 8.0,
  "phantom_form": 15.0
},
"phantom": {
  "damage_threshold_pct": 0.25,
  "claw_range": 260.0,
  "safety_timeout": 10.0
}
```

`low_hp_pct`（0.4）和 `skill_gap`（0.2）直接复用现有 `ai` 字段，不重复配置。
`phantom.uses = 3` 也可以不写死，直接从三个 attack id 的长度得出。

### 5.2 `game/data/attacks.json`

新增：

| id | duration | 伤害 | 事件 |
|---|---:|---|---|
| `shadow_phantom_form` | 0.40 | 0 | 无事件；`start_transform` 专用，不做 AttackRuntime |
| `shadow_phantom_rend` | 0.45 | 1.0 atk | hitbox t=0.18–0.36，box `[20,-195,240,55]`，knockback 80，hitstun 0.2，hitstop 0.06，hit_fx `shadow_phantom_rend_hit` |
| `shadow_phantom_rain` | 0.50 | 0.5 atk ×3 | projectile `shadow_phantom_rain`，t=0.24，count 3，offsets `[-80,0,80]`，spawn_height 420，speed 900，radius 16，hitstun 0.15，hitstop 0.04 |
| `shadow_phantom_bind` | 0.50 | 0.3 atk | projectile `shadow_phantom_bind`，t=0.20，lane low，speed 900，range 700，radius 20，status stun 1.2，不穿 block |

`basic_mult` 和 `extra_mult` 用相同值；`energy_gain` 0；幻影技能不加印记。

### 5.3 `game/data/animations.json`

新增 `shadow_ninja_phantom_clips`：

```json
"idle":                      { "loop": true,  "frames": [...], "durations": [0.30, 0.30, 0.30, 0.30] },
"walk":                      { "loop": true,  "frames": [...], "durations": [0.10, 0.10, 0.10, 0.10, 0.10, 0.10] },
"jump":                      { "loop": false, "frames": [...], "durations": [0.20, 0.20] },
"shadow_phantom_rend":       { "loop": false, "frames": [...], "durations": [0.09, 0.09, 0.09, 0.09, 0.09] },
"shadow_phantom_rain":       { "loop": false, "frames": [...], "durations": [0.10, 0.10, 0.10, 0.10, 0.10] },
"shadow_phantom_bind":       { "loop": false, "frames": [...], "durations": [0.10, 0.10, 0.10, 0.10, 0.10] },
"revert":                    { "loop": false, "frames": [...], "durations": [0.10, 0.10, 0.10, 0.10] }
```

在 `shadow_ninja_clips` 增加 `transform`（4 × 0.10）；不要动已有 35 帧的路径。

`roster.json` 的 Shadow Ninja 增加：

```json
"flame_clips": "shadow_ninja_phantom_clips",
"skill_slots": ["shadow_kunai_slash", "shadow_kunai_throw", "shadow_dash", "shadow_phantom_form"]
```

`flame_clips` 是现有 `AnimationPlayer` 的第二套 table 字段；如果本轮把它泛化成
`alt_clips`，需要同步改 Lina 的 roster 和 `roster.py`，风险更高，建议先用现有字段并注释。
`fallback` 仍是普通形态图；幻影帧缺失时会退回普通图，最终 smoke 必须是
`shadow_ninja_phantom_missing_frames == 0`。

### 5.4 `game/config.py`

- `REQUIRED_ATTACKS` 增加 `shadow_phantom_form`、`shadow_phantom_rend`、
  `shadow_phantom_rain`、`shadow_phantom_bind`。
- `REQUIRED_SHADOW_NINJA_CLIPS` 增加 `transform`。
- 新增 `REQUIRED_SHADOW_NINJA_PHANTOM_CLIPS`，校验第二套 table 的帧/时长数量和
  `shadow_ninja_phantom_clips` 的存在。
- 校验 `transform` / `revert` 的 clip 总时长与 `shadow_phantom_form` / 幻影技能 duration
  一致；`shadow_phantom_rend` 0.45、`shadow_phantom_rain` 0.50、`shadow_phantom_bind` 0.50。
- `PROJECTILE_KINDS` 增加 `shadow_phantom_rain`、`shadow_phantom_bind`。
- 保持 `ANIMATED_CLASSES` / `ROSTER_CLASSES` 不变（仍是同一个 `shadow_ninja`）。

### 5.5 `game/shadow_ninja.py`

新增/修改：

- `__init__`：`phantom_form=False`、`reverting=False`、`transform_cd=0.0`、
  `transform_cd_max=cfg["cooldowns"]["phantom_form"]`、`phantom_used={...}`、
  `phantom_gap=0.0`、`phantom_safety=0.0`。
- `start_transform(self, scene=None) -> bool`：检查 `hp>0`、`not phantom_form`、
  `transform_cd<=0`、状态允许；设置 `state=TRANSFORM`、`invincible=True`、`phantom_form=True`、
  重置 `phantom_used` 全 false、清印记/状态/hitstun/KB/flash、`vx=0`、
  `anim.set_variant("normal")`、`anim.set_clip("transform", reset=True)`；
  `attack_runtime=None`、`attack_id=None`。
  注意：当前眩晕分支会把 `state` 设为 `IDLE`；如果不想让 AI 在眩晕中变身，必须额外检查
  `self.statuses.control_locked()`，不能只靠 `state`。
- `_update_transform(dt)`：`vx=0`；`anim.update(dt)`；继续调用 `stage.move_fighter`
  （空中变身会自然下落）；`anim.finished` 时：
  - 如果 `reverting`：`set_variant("normal")`、`set_clip("idle")`、`invincible=False`、
    `phantom_form=False`、`reverting=False`、`transform_cd=transform_cd_max`、`state=IDLE`；
  - 否则：`set_variant("flame")`（内部名）、`set_clip("idle")`、`state=IDLE`。
- `_start_revert()`：`reverting=True`、`state=TRANSFORM`、`vx=0`、`attack_runtime=None`、
  `attack_id=None`、`anim.set_variant("flame")`（内部名）、
  `anim.set_clip("revert", reset=True)`。
- `update` 最前面处理 `state == TRANSFORM`；幻影期间跳过普通 `statuses.control_locked`、
  `HURT`、`CROUCH`、普通 AI 分支；进入 `_think_phantom`。`update` 最前面加
  `if self.phantom_form: self.statuses.clear()`，覆盖变身/幻影/还原三个阶段，
  作为免疫 F11/脚本状态的兜底。
- `start_attack`：如果 `phantom_form`，只允许三个幻影 attack id；设置对应的
  `phantom_used[id]=True`，不设普通冷却；其他逻辑复用。
- `_finish_attack`：幻影技能结束后 `skill_gap=0.2`；如果三个 `phantom_used` 都为 true，
  调 `_start_revert()`；否则回 phantom idle。
- `on_hit_success` / `on_projectile_hit`：幻影技能不调 `_add_shadow_mark`；
  `shadow_phantom_bind` 命中时加 `stun 1.2s`；`shadow_phantom_rain` 不加状态。
- `force_skill`：普通形态 slot 3 → `start_transform`；幻影形态 slot 0/1/2 → 对应幻影技能；
  slot 3 no-op。
- `skill_remaining("shadow_phantom_form")`：幻影/变身中返回 0.0；否则返回 `transform_cd`。
- `reset`：`phantom_form=False`、`reverting=False`、`invincible=False`、`transform_cd=0`、
  `phantom_used` 全 false、`anim.set_variant("normal")`、`anim.set_clip("idle")`。
- `take_hit`：幻影期间 `super().take_hit` 会因 `invincible` 返回 False；保留这个兜底。
- `_think`：在最前面检查变身触发；`_think_phantom` 独立实现，不调用普通 `_try_defense`
  的 crouch 分支（可以复用 barrier hop / jump）。

### 5.6 `game/animation.py`

- 现有 `AnimationPlayer` 的第二套 table 已经够用：`set_variant("flame")` 会切到
  `flame_clips`；对 Shadow Ninja 来说这就是 phantom 表。建议先复用，不重命名。
  `set_variant` 目前只识别 `"normal"` / `"flame"`；**不要写 `set_variant("phantom")`**，
  否则会落回 default table。若确实要改内部名，必须同时泛化 `AnimationPlayer`、Lina 和
  Shadow Ninja，本轮不建议。
- `Fighter.draw` 的 `flame_time` 判断对 Shadow Ninja 是 `False`，所以 phantom variant 仍会
  正常绘制；不要给 Shadow Ninja 加 `flame_time`，否则会触发 Lina 的伤害加成语义。
- 如果后续要泛化，新增 `alt_clips` / `alt_variant` 并把 Lina 一起迁移；这是可选重构，
  不应阻塞本轮功能。

### 5.7 `game/combat.py` / `game/scene.py`

- `scene.targets_for()`：过滤 `getattr(target, "phantom_form", False)`，让玩家攻击/投射物
  穿过幻影；`resolve_hit` / `resolve_projectile_hit` 的 `invincible` 检查保留。
- `spawn_projectile_from_event`：新增 `shadow_phantom_rain`（一次生成 3 个下落弹）和
  `shadow_phantom_bind`（低车道触手）分支。
- 新增 `ShadowRainBlade`（下落弹）和 `ShadowBindProjectile(ShurikenProjectile)`；
  下落弹要处理平台/barrier 碰撞、目标命中、越界清理；影缚复用 `ShurikenProjectile` 的
  block/wall 逻辑。
- `spawn_projectile_cast_fx` / `spawn_projectile_impact` / `spawn_hit_fx`：新增幻影技能
  的紫色 FX 分支；命中 FX 可以先用 `RingBurstFx` + particles，不必等贴图。
- `_draw_shadow_mark_fx`：保持不变；幻影技能不产生新印记。
- `_separate_fighters`：幻影仍保留身体分离；如果用户要求“完全无形”，再考虑
  `ignore_separation`，但默认不做。
- F1 绘制：`game/debug.py` 的 enemy hurtbox 在 `phantom_form` 时跳过。

### 5.8 `game/debug.py`

- `SHADOW MARKS` 行保留。
- 新增幻影行，例如：
  - `PHANTOM ACTIVE 2/3  S1 USED  S2 READY  S3 READY`
  - `PHANTOM CD 15.0s`（还原后）
  - `PHANTOM TRANSFORM 0.20s`（过渡中）
- 普通形态的 `S4` 行显示 `shadow_phantom_form` 的剩余冷却；幻影期间显示 ACTIVE，不显示秒数。

### 5.9 `main.py` smoke Phase I

新增 Phase I（放在 Phase H 之后，F7 仍用 `shadow_ninja`，不新增敌人）：

建议 flags：

- `shadow_ninja_phantom_present`：slot 4 是 `shadow_phantom_form`；三个幻影 attack 存在。
- `shadow_ninja_phantom_transform_ok`：强制 Z 后进入 TRANSFORM，0.40s 后 variant=phantom。
- `shadow_ninja_phantom_invincible_ok`：变身第 0 帧起 `take_hit(999)` 不掉血；
  玩家近战/投射物不能命中；`invincible` 在还原结束前保持。
- `shadow_ninja_phantom_clear_ok`：变身前给自身挂 `marks`/`shadow_marks`/`stun`/`poison`，
  变身后全部清零。
- `shadow_ninja_phantom_marks_separate_ok`：玩家身上的普通形态印记在变身/还原后仍保留。
- `shadow_ninja_phantom_no_mark_ok`：幻影期间玩家攻击不产生印记/被动；幻影技能不叠印记。
- `shadow_ninja_phantom_rend_ok`：P1 命中，1.0 atk，高判定；蹲下玩家可躲。
- `shadow_ninja_phantom_rain_ok`：P2 生成 3 个下落弹；命中伤害/清理正确；平台可挡。
- `shadow_ninja_phantom_bind_ok`：P3 低车道命中，0.3 atk + 1.2s 眩晕；跳跃可躲。
- `shadow_ninja_phantom_once_ok`：每个技能只能用一次；第二次强制返回 False。
- `shadow_ninja_phantom_auto_revert_ok`：第三个技能动作结束后进入 REVERT，0.40s 后
  variant=normal、`phantom_form=False`、`invincible=False`。
- `shadow_ninja_phantom_cd_ok`：幻影期间 `transform_cd==0`；还原后 ==15；不能立刻再变身。
- `shadow_ninja_phantom_ai_ok`：低血量或大伤害触发变身；幻影 AI 依次使用三个技能并还原。
- `shadow_ninja_phantom_reset_ok`：F9/F7/reset 后无幻影状态、无投射物、无印记/状态。
- `shadow_ninja_phantom_missing_frames==0`、`shadow_ninja_phantom_fx_missing==0`。
- 所有旧 `shadow_ninja_*` flags 保持 true；`default_enemy_ok` 保持 true。

Phase H 的 `shadow_ninja_present` 需要把 slot 4 的期望从 `None` 改为
`"shadow_phantom_form"`；`shadow_ninja_slots_ok` 里原来“Z 无效”的断言要改成
“Z 触发变身”。其它普通形态断言不要回退。

### 5.10 手动验证

1. F7 选 Shadow Ninja；F8 开 AI；把敌方 HP 打到 40% 以下，观察变身。
2. F1：变身/幻影期间不画敌方 hurtbox；P1/P2/P3 的 hitbox/投射物可见；普通形态 hurtbox 仍正常。
3. F2：普通形态 S4 冷却；幻影期间 `PHANTOM ACTIVE n/3`；还原后 `PHANTOM CD 15s`。
4. V/C/X：普通形态技能 1/2/3；幻影期间依次强制 P1/P2/P3；第三次后自动还原。
5. Z：普通形态强制变身；幻影期间 no-op。
6. F6 0.25×/0.5×：变身 0.4s 无敌从第 0 帧开始；还原 0.4s；P1 蹲下可躲；P3 跳跃可躲。
7. 让玩家在变身瞬间攻击：不应造成伤害/印记/状态；投射物应穿过。
8. 变身前给 Shadow Ninja 挂 Nyra/Rhea 的印记/毒/眩晕：变身后全部清掉；玩家身上的
   普通形态印记保留。
9. 三次幻影技能用完后自动还原；还原后普通技能可用，技能 4 冷却 15s。
10. F9/R/F7 切换：无幻影残影、无雨刃/触手、无冷却/状态、无 variant 错位。
11. 超霸体（Nyra Q/E、Rhea E）：P3 的眩晕被免疫，伤害仍结算；P1/P2 伤害正常。
12. 帧数/FX：`shadow_ninja_phantom_missing_frames == 0`、`shadow_ninja_phantom_fx_missing == 0`。

---

## 6. 待确认决策（下一个 session 逐项 grill）

| # | 问题 | 建议 | 影响 |
|---|---|---|---|
| Q1 | 幻影三技能的名称/动作方向 | 影爪（长爪横扫）/ 影雨（三段落刃）/ 影缚（地面触手定身） | 决定全部动作帧和 FX |
| Q2 | 三技能伤害/控制 | P1 1.0 atk；P2 0.5×3；P3 0.3 + 1.2s 眩晕 | 决定平衡和 smoke 数值 |
| Q3 | 幻影技能是否叠普通印记 | **不叠**；被动只属于普通技能 1/2/3 | 影响 `on_hit_success` / `on_projectile_hit` |
| Q4 | 变身 AI 触发 | HP ≤ 40% 或预估伤害 ≥ 25% max HP；玩家存活 | 影响 AI 和 smoke |
| Q5 | 变身可用状态 | IDLE/WALK/AIR；HURT/KO/ATTACK 不可；眩晕中是否允许需确认（眩晕分支是 IDLE，必须显式检查） | 影响 AI 反应和逃逸强度 |
| Q6 | 还原期间是否无敌 | **建议全程无敌**；还原最后帧才解除 | 决定玩家能否惩罚还原 |
| Q7 | 变身/还原时长 | 各 4 帧 × 0.10s = 0.40s | 决定帧预算和手感 |
| Q8 | 幻影技能是否产生印记 | **不产生**；玩家身上的旧印记保留 | 影响被动交互 |
| Q9 | 普通技能冷却是否在幻影期间继续 | **继续走**；幻影技能独立 | 影响还原后的压力 |
| Q10 | 幻影移动/跳跃 | 沿用 1.5× 移速、跳跃/barrier hop；无蹲下 | 影响 AI 和帧表 |
| Q11 | 空中变身 | 允许；保留重力；变身帧不移动 | 影响边缘情况 |
| Q12 | 技能“用掉”的时机 | 施法开始就算用掉，未命中也不返还 | 影响 AI 和玩家策略 |
| Q13 | 第三个技能未命中 | 仍然算用掉；动作结束后照常还原 | 影响 AI 收尾 |
| Q14 | 幻影是否有时间上限 | 无上限，只看 3 个技能；可选 10s 安全兜底 | 影响不可达场景 |
| Q15 | 幻影身体碰撞 | 保留 `separates` 身体分离；无战斗 hitbox | 影响走位/重叠 |
| Q16 | 帧预算 | 35 个新帧（4 变身 + 4 idle + 6 walk + 2 jump + 5×3 技能 + 4 还原） | 决定素材工作量 |
| Q17 | 幻影技能是否显示冷却秒数 | 只显示 READY/USED；不显示秒数 | 影响 F2 |
| Q18 | 变身冷却起点 | 还原动画结束才设 15s | 影响技能 4 可用时间 |
| Q19 | 还原时是否清空未完成的幻影投射物 | 建议保留，让已用的技能完成 | 影响第三技能收尾和残留物清理 |

已经由 docx 固定、不需要再 grill 的：15s、幻影形象、变身帧无敌、清自身印记/负面、
不可被叠印记/被动、无 hitbox、三个全新动作模型、每个技能一次、三个用完自动还原、
还原后才进冷却、低血量/大伤害优先变身。

---

## 7. 已确认决策（等用户确认后回填）

| # | 决策 | 用户答案 | 日期 |
|---|---|---|---|
| Q1 | 幻影三技能名称/动作 | 待确认 | |
| Q2 | 伤害/控制数值 | 待确认 | |
| Q3 | 是否叠印记 | 待确认 | |
| Q4 | AI 变身触发 | 待确认 | |
| Q5 | 变身可用状态 | 待确认 | |
| Q6 | 还原无敌 | 待确认 | |
| Q7 | 过渡时长/帧数 | 待确认 | |
| Q8 | 幻影技能印记 | 待确认 | |
| Q9 | 普通冷却是否继续 | 待确认 | |
| Q10 | 移动/跳跃 | 待确认 | |
| Q11 | 空中变身 | 待确认 | |
| Q12 | 技能用掉时机 | 待确认 | |
| Q13 | 第三技能未命中 | 待确认 | |
| Q14 | 时间上限/兜底 | 待确认 | |
| Q15 | 身体碰撞 | 待确认 | |
| Q16 | 帧预算 | 待确认 | |
| Q17 | F2 显示 | 待确认 | |
| Q18 | 冷却起点 | 待确认 | |
| Q19 | 还原时清空幻影投射物 | 待确认 | |

---

## 8. 实现顺序

1. **基线**：`main.py --smoke-test` exit 0；确认工作区只有 `tmp/` 未跟踪；不要动已提交的
   普通形态 35 帧。
2. **设计 grill**：按 §6 逐项确认，把答案回填 §7；未确认前不改代码/素材。
3. **数据骨架**：stats / attacks / animations / roster / config；幻影帧可以先用占位图，
   但最终必须是批准过的独立帧。
4. **状态机**：`TRANSFORM_IN → PHANTOM → REVERT_OUT`；无敌、清印记/状态、variant 切换、
   冷却起点、reset。
5. **无 hitbox / 无印记**：`targets_for` 过滤、F1 跳过 hurtbox、`invincible` 兜底、
   玩家攻击/投射物穿透测试。
6. **三个幻影技能**：P1 hitbox、P2 下落弹、P3 触手；每个一次、第三技能后自动还原；
   先做机制和程序化 FX，再替换批准贴图。
7. **AI**：变身触发、幻影技能顺序、追击/跳跃/barrier hop、还原后回普通 AI。
8. **调试/ smoke**：F2 幻影行、V/C/X/Z 映射、Phase I flags、旧 flags 不回退。
9. **素材**：phantom base → 变身/还原 contact sheet → idle/walk/jump → 三个技能 contact sheet
   → 游戏内预览 → 安装；每轮用户确认。
10. **最终验证**：`main.py --smoke-test` exit 0；`shadow_ninja_phantom_missing_frames==0`、
    `shadow_ninja_phantom_fx_missing==0`；F1/F2/F6/F7/F9 手动检查。
11. **文档**：实现和验证完成后，按 AGENTS.md 问一次是否写入 README / DESIGN_DECISIONS /
    DEBUG / ASSET_PIPELINE，以及新建
    `docs/SHADOW_NINJA_PHANTOM_ANIMATION_DESIGN.md`；用户同意后再写。
    `instruction.docx` 永远不改。

---

## 9. 验收清单（DoD）

- [ ] 技能 4 变身幻影；15s 冷却在还原结束后才开始。
- [ ] 变身第 0 帧起无敌；变身/幻影期间不受伤害、不中负面、不能被叠印记/被动。
- [ ] 变身清除 Shadow Ninja 自己身上的印记/负面/hitstun/KB；玩家身上的旧印记保留。
- [ ] 幻影期间无战斗 hitbox；玩家近战/投射物穿过，不消耗、不挂状态；F1 不画敌方 hurtbox。
- [ ] 三个幻影技能都是全新动作模型，不复用普通形态的 slash/throw/dash 帧。
- [ ] 每个幻影技能每次变身只能用一次；三个用完自动还原。
- [ ] 变身过渡 4 帧、还原过渡 4 帧，均为独立绘制；不是倒放/单帧淡入淡出。
- [ ] 幻影 idle/walk/jump 也是新形象/新动作；长爪/雨刃/触手是独立 FX，不烘焙进角色帧。
- [ ] 幻影技能不叠普通印记；P3 的眩晕与霸体交互正确；P1 蹲下可躲；P3 跳跃可躲。
- [ ] AI 在低血量或大伤害时变身；幻影期间按顺序使用三技能；第三技能后还原；
      还原后回普通 AI，技能 4 冷却中不再变身。
- [ ] F1/F2/F6/F7/F9/V/C/X/Z 全部可用；F2 显示 PHANTOM ACTIVE/USED/CD；F9 清干净。
- [ ] `shadow_ninja_phantom_missing_frames == 0`、`shadow_ninja_phantom_fx_missing == 0`；
      所有旧 `shadow_ninja_*` flags 和 `default_enemy_ok` 保持 true。
- [ ] `main.py --smoke-test` exit 0。
- [ ] 未修改 `instruction.docx`、`Image/`、`UI Resources/`、`sketch/`；未 commit/push
      （除非用户明确要求）。

---

## 附录 A — 相关代码位置（HEAD 207b8c3）

- `game/shadow_ninja.py`：`ShadowNinja` 11；`update` 87；`_think` 205；`start_attack` 382；
  `on_hit_success` 480；`on_projectile_hit` 490；`_add_shadow_mark` 506；`reset` 538。
- `game/fighter.py`：`FighterState` 14；`invincible` 98；`update_common` 142；`take_hit` 171；
  `apply_dot` 226；`force_skill` 269；`reset_common` 508；`draw` 595。
- `game/animation.py`：`AnimationPlayer` 13；`set_variant` 49；`set_clip` 61；`missing_paths` 103。
- `game/lina.py`：`take_hit` 74；`update` 95；`start_transform` 377；`_start_revert` 392。
- `game/combat.py`：`resolve_hit` 142；`resolve_projectile_hit` 194。
- `game/scene.py`：`targets_for` 362；`_separate_fighters` 460；`spawn_projectile_cast_fx` 577；
  `spawn_projectile_impact` 713；`spawn_hit_fx` 841；`spawn_projectile_from_event` 974；
  `_draw_shadow_mark_fx` 1406；debug key 1306。
- `game/debug.py`：F2 panel 185；`SHADOW MARKS` 140。
- `game/config.py`：`REQUIRED_ATTACKS` 22；`REQUIRED_SHADOW_NINJA_CLIPS` 64；
  shadow clip validation 448。
- `main.py`：Phase H 3822；`shadow_ninja_present` 3853；final conjunction 4626。
- `docs/NEXT_SESSION_SHADOW_NINJA.md` 附录 A：幻影形态摘要。
- `docs/SHADOW_NINJA_ANIMATION_DESIGN.md`：普通形态帧表/审批记录，幻影不要改它的已批准帧。

## 附录 B — 幻影素材生成提示词要点

生成前读 `docs/IMAGE_GENERATION_RULES.md` 和 `docs/ASSET_PIPELINE.md`；每次生成都要检查：

- base：`Image/Enemy/shadow-ninja-phantom-no-aura-256.png`；保持深紫/黑剪影、发光眼、
  长发、脚下影雾；`shadow-ninja-phantom-shadow-256.png` 只作 aura/影雾参考。
- 右向**完全侧视**（和普通形态一致，不要 3/4 侧视），运行时只翻转；透明背景，
  无文字/边框/场景/影子。
- 固定 body 214、画布 384×384、pivot 192,372；不要按每帧 alpha bbox 自动缩放；
  长发/影雾变大时保持身体比例，必要时扩大留白或重生成，不要缩小人物。
- 幻影没有武器；手是爪/掌/触手，不要出现苦无、刀、法杖。近侧手臂/头发在前，远侧在后；
  头发/影雾不穿过脸、脖子、手臂、躯干；影雾不吞掉腿。
- 变身/还原帧：普通形态的苦无可以溶解，但幻影帧不能有苦无；两套过渡帧独立绘制，
  不能倒放；头顶/脚底基线与普通形态对齐。
- 技能帧：P1 只画挥击，长爪轨迹是独立 FX；P2 只画施法，雨刃是独立投射物；P3 只画触地，
  触手是独立投射物/FX；不要把技能 FX 烘焙进角色帧。
- 每个动作出 contact sheet，按 100%/200% 检查遮挡、穿模、手指数、头发/影雾层次；
  用户确认后才安装到 `assets/frames/shadow_ninja/`。

## 附录 C — 与普通形态的边界

| 项目 | 普通形态 | 幻影形态 |
|---|---|---|
| 形象 | `shadow-ninja-256.png` / approved base | `shadow-ninja-phantom-no-aura-256.png` |
| 武器 | 苦无 | 无武器；长发/影雾/触手 |
| 技能 | 苦无近刺、低苦无、冲刺 | 影爪、影雨、影缚（全新动作） |
| 印记 | 技能 1/2/3 叠印记，第 4 次引爆 | 不叠印记；旧印记在玩家身上保留 |
| 受伤 | 正常 hurt/KO | 无敌、无 hitbox、无 hurt/KO 帧 |
| 冷却 | slash 0.5 / throw 5 / dash 8 | 每技能每次变身一次；技能 4 还原后 15s |
| 控制 | 可被眩晕/击退/负面 | 免疫负面；变身时清自身状态 |
| 动作帧 | 35 帧 + 2 苦无 FX | 35 个新帧 + 技能 FX/投射物 |
| AI | 普通三技能/防御/barrier hop | 低血/大伤害变身；三技能顺序；自动还原 |

---

### 最后提醒

- 本文是**设计稿**，不是已实现行为的说明；不要在实现和用户确认前把它当成最终规格。
- 所有未在 docx 中出现的数字、名称、动作和帧数都需要 §6 的 grill 确认。
- `instruction.docx` 是权威规格，**永远不要修改**；需要补的内容写进 Markdown。
