# Next Session — Rhea 技能修订 + 敌人专属场景

> 日期：2026-11-02
> 状态：**交接文档，尚未实现**。本轮只写本文件；代码、JSON、素材均未改动。
> 基线：`rhea-thorn-integration` HEAD `0e749c1`；该提交的 `main.py --smoke-test` 为 exit 0。
> 工作区：`instruction.docx` 有用户 2026-11-02 的更新（未提交）；`sketch/warrior_scene.jpg`
> 是未跟踪的 Warrior 场景草图。不要 revert / stash / checkout，也不要修改这两个文件。
> 权威规格：工作区 `instruction.docx`。本文只摘录；**绝不修改 docx**。
> 默认角色 **Lina**，默认敌人 **Creepy Shooter**。

---

## 0. 给下一个 session 的开场 prompt（可直接复制）

```text
读取 docs/NEXT_SESSION_RHEA_SCENES.md，以及工作区 instruction.docx 的
“Rhea Thorn”“Warrior / Creepy Shooter / Bat / Veno-Spider 场景”段。

本轮只做两件事：
A. 按新规格修订 Rhea：Q 冷却 8→6s；E 冷却 15→10s；LMB/RMB 命中已中毒目标
   额外造成 3% 最大生命伤害；E 第一段伤害改为 0.8basic+1.2extra；
   E 第一段结束后 2s 内可再按 E 折返，不按则不折返；冷却在技能结束后计算。
B. 敌人专属场景：Warrior 新增左右对称场景；Creepy 保持现有场景；
   Bat / Veno-Spider 改为无 barrier / platform / ladder；默认场景留给 Dummy。

先运行 .venv/Scripts/python.exe main.py --smoke-test 确认基线 exit 0。
先按本文 §4.4 和 §5.5 的问题 grill 我，确认边界后再改代码/数据。
不要修改 instruction.docx、Image/、UI Resources/、sketch/、其他角色/敌人；
不要顺手实现 Eira / Shadow Ninja 的 docx 文案变化；
不要 commit，除非我明确要求。不要用 pytest；验证用 --smoke-test、F1/F2/F6 和预览图。
```

---

## 1. 本轮范围

| 做 | 不做 |
|---|---|
| Rhea 的 Q/E 冷却、被动 3%、E 两段伤害与手动折返 | Eira Frostveil、Shadow Ninja 的 docx 文案变化 |
| Rhea 的 smoke / F2 / 手动手感验证 | 角色选择界面、商店、道具、等级、BGM |
| `stage_variants` 增加 Warrior / Bat / Veno；Creepy 保持 | 按敌人切换背景图 / BGM（缺素材，另开任务） |
| `roster.json` 给已有敌人接 `stage_variant` | Mech-Crab、Lina Shadowtide、Crooked Witch 等未实现敌人 |
| 必要时为 E 的等待姿态新增/调整帧（需先审批） | 重画已有 platform / ladder / barrier 素材 |
| 实现验证并获确认后更新文档与手册 | 未经确认改 README/docs/手册；commit |

**关键约束**

- `instruction.docx` 是权威规格，只读；不要用 `git add` / `git checkout` 处理它。
- `Image/` 和 `UI Resources/` 只读；`sketch/warrior_scene.jpg` 只是草图，不是运行时素材。
- 新场景复用现有的 platform / ladder / barrier 素材与高度，不按草图比例重画。
- Rhea 的毒仍遵守“同源延长、异源独立”：被动延长只能作用于 `rhea_poison`，不能新建毒，
  也不能改 Veno 的毒。新加的 3% 伤害是否对任意来源的毒生效，见 §4.4 Q4。

---

## 2. instruction.docx 的本次变化（工作区 vs HEAD）

工作区 docx 相对 `HEAD` 的文本 diff 只有以下几处与本轮相关；另外还有 Eira 和
Shadow Ninja 的文案变化，**不在本轮范围**。

### 2.1 Rhea 新规格原文

> 被动：敌人处于毒伤状态下，使用鼠标左键、右键击中敌人可延长毒伤时间，每次击中敌人延长1s，并额外造成敌人最大生命值3%伤害。
>
> 鼠标左键：手拿手里剑攻击敌人，造成伤害（atk）。动画左右交替，如第一次右手攻击，再次按下鼠标左键则出左手攻击。
>
> 鼠标右键：向敌人投掷一枚手里剑（远程攻击）(1.2basic+1.3extra)，手里剑对敌人造成伤害。
>
> Q技能：（冷却6s）向敌人投掷一枚带有剧毒的手里剑，造成伤害(1.2atk+8%目标最大生命)，敌人进入毒伤状态（动画，敌人变绿，变紫交替），每秒扣除目标3%的生命值，持续5s
>
> E技能：（冷却10s）手持手里剑向敌人冲刺一段距离，造成伤害（0.8basic+1.2extra），冲刺结束后折返，回到冲刺前的位置，造成伤害（0.7basic+0.8extra）。如果敌人处于毒伤状态，额外造成目标15%最大生命值伤害（在冲刺第一段触发）。E技能冲刺和折返期间全程霸体，无视hitbox.
>
> E技能第一段结束后，在2s内可主动按下E折返，如果2s内没有按下，则不折返。技能冷却在整个技能结束后计算。（技能结束指折返结束，或者第一段冲刺结束后2s之后）。

> **注意**：docx 第一句写“冲刺结束后折返”，后一句写“第一段结束后 2s 内可主动按下 E 折返”，
> 字面存在冲突。本文以更具体的后一句（手动折返）为设计依据；实现前请在 §4.4 Q1 确认。

### 2.2 与当前实现的差异

| 项 | 当前实现 | 新规格 | 影响 |
|---|---|---|---|
| 被动 | 只把已有 `rhea_poison` 延长 1s；不造成额外伤害 | 延长 1s，**并额外造成目标最大生命 3% 伤害** | `game/rhea.py`、`game/combat.py`、`game/projectile.py` |
| Q 冷却 | 8s | **6s** | `game/data/stats.json`、smoke、手册 |
| E 冷却 | 15s | **10s** | `game/data/stats.json`、smoke、手册 |
| E 第一段伤害 | `0.7basic + 0.8extra`（基准 14） | **`0.8basic + 1.2extra`**（基准 16） | `game/data/attacks.json`、`game/combat.py` |
| E 第二段伤害 | `0.7basic + 0.8extra`（基准 14） | 不变（14） | 需要把两段拆成不同倍率 |
| E 折返 | 第一段结束后自动在 0.60–1.00s 折返 | **第一段结束后 2s 内再按 E 才折返**；不按则不折返 | `game/rhea.py` 状态机 |
| E 冷却计时 | 起手时立刻进入 15s 冷却 | **技能结束后才进入 10s 冷却**（折返结束，或第一段结束后 2s） | `game/rhea.py`、HUD、smoke |
| E 霸体 | 0.0–1.0s 全程 `super_armor` | 冲刺和折返期间全程霸体；等待窗口是否霸体见 §4.4 Q3 | `game/rhea.py`、`attacks.json` |
| E “无视hitbox” | 只有 `pass_through_enemy: true`（穿过敌人身体分离）；仍会被 block 挡住；仍可被伤害 | 需要明确它指敌人身体、场景 block，还是完全无敌 | 见 §4.4 Q2 |

### 2.3 场景新描述

docx 在已有敌人下新增/已有的场景说明：

**Warrior（新增）**

> 专属场景：
> 注意场景左右对称

对应 docx 内嵌草图；工作区另有未跟踪的 `sketch/warrior_scene.jpg`，内容与它一致：

- 中央一块 **long platform**；
- 平台正中央下方一条 **long ladder**，从平台顶到地面；
- 地面左右各一个 **barrier**，以场景中心线左右对称；
- 没有 short platform、没有 medium ladder。

**Creepy Shooter（已有，未改文本）**

> 专属场景布置：
> 注意：这个只是草图，高度还是按照原有的数值，不要改变
> platform两边留空隙，足够让角色下落。
> Creepy shooter生成在platform long右侧

当前 Creepy 变体已按这张草图实现（见 §3.2），本轮原则上不改；右侧 barrier 是此前
用户明确保留的，不要因为草图没画出来就删掉。

**Bat（新增）**

> 场景：无barrier，无platform，无ladder

**Veno-Spider（新增）**

> 场景：无barrier，无platform，无ladder

**其他**

- Dummy 没有场景描述；继续使用默认 `stage`。
- Mech-Crab、Lina Shadowtide、Crooked Witch 没有接入，不在本轮处理。
- docx 还有 Eira / Shadow Ninja 的文案变化；不要顺手实现。

---

## 3. 当前实现快照（代码事实）

### 3.1 Rhea

- `game/data/stats.json` 的 `rhea.cooldowns` 现在是 `q: 8.0`、`e: 15.0`。
- `game/data/attacks.json`：
  - `rhea_slash`：1.0/1.0，20 伤害，`extends_poison: true`，event 无额外最大生命字段。
  - `rhea_throw`：1.2/1.3，24 伤害，弹体 `rhea_shuriken`，`extends_poison: true`。
  - `rhea_poison_throw`：1.2/1.2（等于 1.2atk），24 + 8% 最大生命；毒 5s、3%/s；
    `extends_poison: false`；Q 不触发被动 +1。
  - `rhea_dash`：全局 `basic_mult 0.7`、`extra_mult 0.8`；duration 1.0；armor 0.0–1.0；
    `pass_through_enemy: true`；去程 hitbox t=0.06–0.60，group `out`，
    `bonus_vs_poison_max_hp_pct: 0.15`；回程 t=0.60–1.00，group `back`；两段各 14。
- `game/rhea.py`：
  - `_start_e()` 在起手时立刻 `self.e_cd = self.e_cd_max`。
  - `_update_dash_motion()` 固定 0.06–0.60 去程、0.60–1.00 回程。
  - `on_hit_success()` 只调用 `_extend_poison()`，没有额外伤害。
  - `on_projectile_hit()` 处理 Q 上毒或 RMB 延长；没有 3% 伤害。
  - `_update_attack()` 在 runtime.finished 后清状态、`push_apart`、回 idle。
- `game/combat.py`：
  - `attack_damage()` 支持 event 的 `damage` 覆盖，但 event 不能覆盖 `basic_mult` / `extra_mult`。
  - `resolve_hit()` 已支持 `bonus_vs_poison_max_hp_pct`（目标有任意毒时加 `target.max_hp * pct`，
    在减伤前），但该字段目前只写在 E 的去程事件。
  - `resolve_projectile_hit()` 只有 `bonus_target_max_hp_pct`（无条件），没有“目标中毒才加成”的字段。
- `game/projectile.py` 的 `ShurikenProjectile` 有 `bonus_target_max_hp_pct`，没有
  `bonus_vs_poison_max_hp_pct`。
- `game/status.py` 的 `extend_poison(source, duration)` 只延长已存在的同源毒，绝不新建。

### 3.2 场景

当前代码已经具备“按敌人选场景”的最小架构，**不需要新引擎层**：

- `game/data/debug.json` 有 `stage`（默认）和 `stage_variants`。
- `roster.json` 的敌人条目可用 `stage_variant` 指向 `stage_variants` 的 key；
  目前只有 `creepy_shooter` 配了 `"stage_variant": "creepy_shooter"`。
- `Scene._stage_config()`：有 `stage_variant` 就用变体，否则用默认 `stage`。
- `Scene.set_enemy()` / `rebuild()` 会重建 `Stage`，并保留 `blocks_enabled`。
- `game/config.py` 已校验每个 variant 的 `REQUIRED_STAGE` 字段和所有 spawn key。

当前默认 `stage`（Dummy / 未描述敌人使用）：

| 实体 | 数据 |
|---|---|
| 长平台 | `[170, 220, 479, 78]`，surface 220 |
| 短平台 | `[796, 268, 314, 78]`，surface 268 |
| 长梯 | `[508, 220, 64, 400]` |
| 中梯 | `[921, 268, 64, 352]` |
| barrier | `[400, 560, 90, 60]`、`[700, 560, 90, 60]` |

当前 `creepy_shooter` 变体：

| 实体 | 数据 |
|---|---|
| 长平台 | `[601, 220, 479, 78]` |
| 短平台 | `[170, 268, 314, 78]` |
| 长梯 | `[708, 220, 64, 400]` |
| 中梯 | `[295, 268, 64, 352]` |
| barrier | 仅右侧 `[790, 560, 90, 60]`（左侧已按此前要求删除） |
| Creepy 出生 | `[1000, 220]`，在 long platform 右侧 |

---

## 4. Rhea 实现设计

### 4.1 数据改动

`game/data/stats.json`：

```json
"rhea": {
  "cooldowns": {"q": 6.0, "e": 10.0}
}
```

`game/data/attacks.json` 的增量：

| attack | 改动 |
|---|---|
| `rhea_slash` | 命中事件加 `"bonus_vs_poison_max_hp_pct": 0.03` |
| `rhea_throw` | 弹体事件加 `"bonus_vs_poison_max_hp_pct": 0.03` |
| `rhea_poison_throw` | 不加 3%；Q 仍 1.2atk + 8%，毒 5s/3%，8s→6s 冷却 |
| `rhea_dash` | 去程 event：`basic_mult: 0.8`、`extra_mult: 1.2`；回程 event：`basic_mult: 0.7`、`extra_mult: 0.8`；去程保留 `bonus_vs_poison_max_hp_pct: 0.15` |

**两段不同倍率的实现方式**

当前 `attack_damage()` 只看 attack 级别的 `basic_mult` / `extra_mult`。建议扩展为：
event 里若有 `basic_mult` / `extra_mult`，优先用 event 的值；否则回落到 attack 级。
这样 `rhea_dash` 的 attack 级仍可保留 0.7/0.8 作为兜底，去程 event 覆盖为 0.8/1.2。
不要用 event 的绝对 `damage` 快照，否则 extra atk 成长后不跟随。

### 4.2 被动：3% 最大生命额外伤害

**LMB**

- 在 `rhea_slash` 的 hitbox event 上加 `bonus_vs_poison_max_hp_pct: 0.03`。
- `resolve_hit()` 已有逻辑：目标 `statuses.has("poison")` 时，
  `damage += target.max_hp * 0.03`，然后才走 `damage_reduction`。
- 这段伤害属于本次命中，不新增 hitstop / knockback / 弹体。

**RMB**

- 在 `rhea_throw` 的 projectile event 上加 `bonus_vs_poison_max_hp_pct: 0.03`。
- `ShurikenProjectile.__init__` 增加同名字段；`scene.spawn_projectile_from_event()` 透传。
- `resolve_projectile_hit()` 增加条件：目标有任意毒时加 `target.max_hp * pct`，再走减伤。
- 不要用现有的 `bonus_target_max_hp_pct`：那个是无条件加成，会在未中毒目标上也生效。

**触发条件与顺序**

- 目标在命中瞬间已有毒（任意来源）→ 3% 伤害生效。
- 延长仍然只调用 `statuses.extend_poison("rhea_poison", 1.0)`；目标只有 Veno 毒时
  3% 伤害可以有，但毒不延长（这是当前“同源延长、异源独立”的延续，需 §4.4 Q4 确认）。
- 目标没有毒 → 没有 3%，也不新建毒。
- 目标无敌 / 已 KO → 不结算；RMB 弹体被 block 挡住时不命中。
- 3% 在减伤前加入；如果目标有 50% 减伤，实际额外伤害是 `max_hp * 0.03 * 0.5`。
- Q 和 E 不触发这 3%（被动只写 LMB/RMB）；E 仍只有去程的 15%。

**数值基准**

| 场景 | 旧 | 新 |
|---|---:|---:|
| LMB 命中 200 HP 已中毒目标 | 20 | 26 |
| LMB 命中 300 HP 已中毒目标 | 20 | 29 |
| LMB 命中 1000 HP 已中毒目标 | 20 | 50 |
| RMB 命中 200 HP 已中毒目标 | 24 | 30 |
| RMB 命中 300 HP 已中毒目标 | 24 | 33 |
| RMB 命中 1000 HP 已中毒目标 | 24 | 54 |
| 50% 减伤下的 LMB / RMB（200 HP） | 10 / 12 | 13 / 15 |

### 4.3 E：手动折返

这是本轮最大的行为改动，建议把 E 明确拆成三段：

1. **去程**：0.00–0.60s，`rhea_dash` 现有去程位移（1100px/s）与 `out` hitbox。
2. **等待窗口**：第一段结束后 2.0s。此时不再自动折返；可按 E 触发折返。
3. **回程**：按 E 后以 1500px/s 回到 `cast_x`，`back` hitbox 生效。

**推荐的状态机**

- `_start_e()` 只启动 `rhea_dash`，**不要**立刻设 `e_cd = 10`。
- `_update_dash_motion()` 在 runtime.time 到 0.60 后暂停 runtime 的推进，进入等待窗口；
  等待计时最多 2.0s。
- 等待期间如果收到 E 输入：进入回程，恢复 runtime 推进（或单独推进回程计时），
  回程 hitbox 生效；到达 `cast_x` 或 runtime 结束时收尾。
- 等待 2.0s 内没有 E：不折返，直接结束技能，角色留在第一段结束的位置。
- 技能真正结束时才 `self.e_cd = self.e_cd_max`（10.0），并清 attack runtime / armor /
  queued action，调用 `scene.push_apart()`，回 idle。
- 等待期间 `e_cd` 应为 0；HUD 不能把它显示成“可再次起手”的普通就绪状态，建议显示
  折返提示或把 E 徽章置为“技能进行中”。具体表现见 §4.4 Q5。
- `reset()` / `set_character()` / `set_enemy()` / KO / 非霸体受击时，必须清掉等待与回程状态，
  不能留下 `rhea_dash` 的 `pass_through_enemy` 或暂停的 runtime。

**动画**

- 当前 `rhea_dash` 是 5 帧、总 1.0s，帧时长 `[0.06, 0.20, 0.20, 0.14, 0.40]`；
  0.60s 正好是最后一帧（回程/转身帧）的起点。
- 等待窗口建议先保持去程结束的姿态（测试 frame 3 或 frame 4，0 起；以实际观感为准），
  回程时再播放转身/折返帧。若现有帧在 2s 静止时明显不自然，再加一张 wait 帧，
  但必须先出 contact sheet 审批，不能直接进游戏。
- 不要为了让等待更长而拉长已有帧的 duration；这会让整个 dash 的手感变慢。

**霸体与“无视hitbox”**

- 当前 `armor_from: 0.0` / `armor_until: 1.0` 是在起手时加一个 1s 的 `super_armor`；
  如果等待 2s，1s 后霸体会消失，折返时可能没有霸体，不满足“折返期间全程霸体”。
- 建议按阶段管理：去程和回程加 `super_armor`，等待窗口按 §4.4 Q3 的决定处理；
  不要简单把 `armor_until` 拉到 2.6s，否则等待窗口也会免疫控制。
- “无视hitbox”当前只实现了 `pass_through_enemy: true`（不与敌人身体分离），
  **不**等于穿墙，也不等于无敌；`stage.move_x()` 仍会被 block 侧面挡住，
  `take_hit()` 仍会扣血。新规格的准确含义必须先确认（§4.4 Q2）。

**数值基准（E 两段）**

| 目标 / 条件 | 旧总伤害 | 新总伤害 |
|---|---:|---:|
| 无中毒，200 HP | 28（14+14） | 30（16+14） |
| 已中毒，200 HP | 58（14+30+14） | 60（16+30+14） |
| 已中毒，300 HP | 73（14+45+14） | 75（16+45+14） |
| 已中毒 + 50% 减伤，200 HP | 29 | 30 |
| 已中毒 + 50% 减伤，300 HP | 36.5 | 37.5 |

> 旧 E 第一段 14；新第一段 16。第二段始终 14；15% 只加在第一段。

### 4.4 必须先确认的问题

**Q1 — 等待窗口里角色能不能动？**

- A. 锁定：第一段结束后角色保持 dash 收招姿态，最多 2s，只能按 E 折返或等窗口结束。
- B. 自由：回到普通控制，可走/跳/普攻，E 在 2s 内仍可触发折返；一旦使用其他技能/受击，
  折返窗口取消。
- 推荐先按 **A** 做，状态机最简单，也最符合“技能结束指第一段结束后 2s”的表述；
  但手感偏惩罚。若选 B，需要定义“折返窗口与普通攻击/受击/跳跃的优先级”。
- 还要定义去程中提前按 E 的处理：建议只缓存到第一段结束，不提前折返；
  如果不缓存，则在第一段结束前忽略这次 E。

**Q2 — “无视hitbox”具体指什么？**

- A. 只穿过敌人身体（当前 `pass_through_enemy`），仍被 barrier/platform 挡住，仍会受伤。
- B. 连 block/terrain 的碰撞也忽略，冲刺可穿过 barrier/platform。
- C. 完全不进入敌方攻击判定（近似无敌）。
- 当前实现是 A + 霸体。推荐先确认再动 `stage.move_x` / `take_hit`；不要凭猜测做 C。

**Q3 — 等待窗口是否霸体？**

- 规格写“冲刺和折返期间全程霸体”，字面不包含等待窗口。推荐等待窗口**不**霸体，
  但这样会被打断；如果用户希望整个技能期间都霸体，需明确。
- 还要定义：等待窗口被打断（进入 HURT / KO）时，折返窗口是否立即取消、E 冷却是否开始。

**Q4 — 3% 的“毒伤状态”是否包含 Veno 的毒？**

- 被动原文只写“敌人处于毒伤状态下”，没有限定来源；当前 E 的 15% 用的是任意毒。
- 推荐：3% 伤害对任意来源的毒生效；延长仍然只作用于 `rhea_poison`。
- 若用户希望“只有 Rhea 自己的毒才触发 3%”，则改用 `target.statuses` 中是否存在
  `source == "rhea_poison"` 的判断，需要新增查询方法或遍历 `poisons`。

**Q5 — 等待窗口的 HUD / 输入提示**

- 等待期间 `e_cd == 0`，HUD 会显示 E 可用；但此时 E 是“折返”而不是“重新起手”。
- 建议在 HUD 上显示 `E RETURN` 或在 E 徽章上加等待倒计时；如果不想改 HUD，
  至少保证按 E 不会误触发第二次 dash。
- 需要确认是否要把“第一段结束后 2s”的倒计时显示给玩家。

**Q6 — 折返的命中与收尾**

- 折返 hitbox 仍只命中一次（group `back`）；如果等待期间目标移动，回程命中按实际位置判定。
- 回程被 block/wall 截断时，技能在当前位置结束，冷却仍然开始；不要求一定回到 `cast_x`。
- 第一段没有命中、目标已死、或目标在等待期间死亡，是否仍允许折返？推荐允许（纯位移），
  但需确认。

**Q7 — 第一段伤害倍率**

- 推荐 event 级 `basic_mult` / `extra_mult`，不要写死 `damage` 绝对值；
  否则 extra atk 成长后第一段不跟随。
- 需要确认 `0.8basic + 1.2extra` 是否就是字面意思（不是 0.8atk + 0.4extra 之类的换算）。

---

## 5. 敌人专属场景

### 5.1 现有架构够用

不需要新增 `Scene` 子类或新引擎；沿用：

- `debug.json.stage_variants.<key>` 存一份完整 stage 配置；
- `roster.json` 的敌人条目加 `"stage_variant": "<key>"`；
- `Scene._stage_config()` 自动选择；`set_enemy()` 已会重建 `Stage` 并保留 `blocks_enabled`；
- `config.py` 已校验 variant 的必需字段和 spawn key。

本轮只加数据、roster 映射、smoke 和必要的文档。

### 5.2 新变体数据草案

所有变体都沿用现有的 `ground_y: 620`、`walls: [90, 1190]`、`lane_heights`、
`land_margin: 8`、以及五个 spawn key。草图只用于相对布局，不按像素比例缩放素材。

**Warrior（新增，左右对称）**

```json
"warrior": {
  "ground_y": 620,
  "walls": [90, 1190],
  "lane_heights": {"high": 180, "fist": 142, "mid": 120, "low": 60},
  "land_margin": 8,
  "blocks": [
    {"kind": "barrier", "rect": [400, 560, 90, 60]},
    {"kind": "barrier", "rect": [790, 560, 90, 60]},
    {
      "kind": "platform",
      "rect": [400, 220, 479, 78],
      "surface_y": 220,
      "sprite": "platform_tropical_long.png",
      "sprite_rect": [400, 206, 479, 96]
    }
  ],
  "ladders": [
    {
      "rect": [608, 220, 64, 400],
      "top_y": 220,
      "bottom_y": 620,
      "sprite": "ladder_tropical_wood.png",
      "sprite_rect": [576, 220, 128, 400]
    }
  ],
  "player_spawn": [280, 620],
  "dummy_spawn": [600, 620],
  "warrior_spawn": [600, 620],
  "veno_spawn": [600, 620],
  "bat_spawn": [600, 470]
}
```

对称性核对（场景中心 x=640）：

- 长平台中心：`400 + 479/2 = 639.5`；
- 长梯中心：`608 + 64/2 = 640`；
- barrier 中心：445 / 835，和为 1280，关于 640 对称；
- 没有 short platform / medium ladder，符合草图。

> 坐标是建议起点；如果用户希望 barrier 更靠外/更靠里，先确认再调，不要改平台/梯子的高度。

**Bat（新增，空场景）**

```json
"bat": {
  "ground_y": 620,
  "walls": [90, 1190],
  "lane_heights": {"high": 180, "fist": 142, "mid": 120, "low": 60},
  "land_margin": 8,
  "blocks": [],
  "ladders": [],
  "player_spawn": [280, 620],
  "dummy_spawn": [600, 620],
  "warrior_spawn": [600, 620],
  "veno_spawn": [600, 620],
  "bat_spawn": [600, 470]
}
```

**Veno-Spider（新增，空场景）**

与 `bat` 相同的 `blocks: []` / `ladders: []`；spawn 可直接复用同一组。
键名用 roster 的 `veno`（不是 `veno_spider`），保持一致。

**Creepy Shooter（保持）**

- 继续使用现有 `stage_variants.creepy_shooter`；
- 长平台 `[601,220,479,78]`、短平台 `[170,268,314,78]`、长梯 `[708,220,64,400]`、
  中梯 `[295,268,64,352]`、右侧 barrier `[790,560,90,60]`；
- Creepy 出生 `[1000,220]` 在 long platform 右侧，符合新 docx 文本；
- 不要因为草图没画 barrier 就删掉右侧 barrier；左侧已在之前删除。

**Dummy / 未描述敌人**

- 继续使用默认 `stage`（现有非对称布局），不要给 Dummy 加 `stage_variant`；
- 如果未来某个敌人没有场景，`_stage_config()` 自然回落到默认 `stage`。

### 5.3 roster / config 改动

`game/data/roster.json`：

```json
"warrior": { "stage_variant": "warrior", ... },
"veno":    { "stage_variant": "veno", ... },
"bat":     { "stage_variant": "bat", ... },
"creepy_shooter": { "stage_variant": "creepy_shooter", ... }
```

- 每个变体必须包含 `REQUIRED_STAGE` 的五个 spawn key；`creepy_shooter_spawn` 只给
  Creepy 变体，其他变体不需要。
- `config.py` 不需要新增字段校验；现有 `stage_variants` 循环会校验每个 variant。
- 可加一条轻量校验：所有带 `stage_variant` 的敌人都能在 `stage_variants` 找到对应 key；
  现有 roster 校验已经做了这件事。

### 5.4 smoke 需要覆盖

- `warrior_stage_ok`：
  - `len(scene.stage.platforms) == 1`，rect 为 `[400,220,479,78]`；
  - `len(scene.stage.ladders) == 1`，rect 为 `[608,220,64,400]`；
  - barriers 为 `[400,560,90,60]`、`[790,560,90,60]`；
  - 平台中心 ≈640，梯子中心 =640，两个 barrier 中心关于 640 对称。
- `bat_stage_ok`：`not scene.stage.blocks`、`not scene.stage.ladders`，Bat 仍 5 只、空中。
- `veno_stage_ok`：空 blocks/ladders，Veno 仍 3 只、hover 正常。
- `creepy_stage_ok`：保持现有断言（长平台 601、短平台 170、右侧 barrier）。
- `scene_variant_switch_ok`：依次 `set_enemy("warrior" / "creepy_shooter" / "bat" / "veno" / "dummy")`，
  每次检查舞台实体和敌人生成；切场景不影响 `blocks_enabled`。
- 更新现有 `creepy_stage_switch_ok`（`main.py` 约 3107 行）：目前它假设
  `set_enemy("warrior")` 后 `platforms[0].left == 170`；Warrior 变体后应改为 400，
  或改名为 `warrior_stage_switch_ok` 并加入最终 conjunction。
- 跑完整 smoke 后，检查所有依赖默认场景位置的旧断言（尤其 Warrior 相位、block 测试、
  ladder 测试）是否仍成立；Warrior 变体会改变 `scene.stage.platforms/barriers`。

### 5.5 必须先确认的问题

**Q1 — Warrior 坐标是否按 §5.2 的草案？**

- 草案使用现有 long platform 宽度 479、居中 `[400,220]`，barrier 445/835 对称。
- 草图不是比例图；如果用户希望平台更宽/更窄，需要先确认，因为宽度会影响 `sprite_rect`
  和 barrier 间距。高度沿用 220/620，不改。

**Q2 — Creepy 右侧 barrier 是否保留？**

- 现状：只剩右侧 `[790,560,90,60]`；此前用户明确要求删除左侧。
- 新草图没有画 barrier，但文本没有要求删除右侧；默认保留，除非用户明确改。

**Q3 — 默认场景是否保留给 Dummy？**

- 推荐保留；Dummy 没有场景描述，继续用默认 `stage`。
- 如果用户希望 Dummy 也用 Warrior 的对称场景，需要明确，否则不要改默认值。

**Q4 — 背景 / BGM 是否本轮处理？**

- instruction 的“战斗进入”段写了按 enemy 切换背景和 BGM；但本轮只有布局草图，
  没有新背景/BGM 素材。建议本轮**只做碰撞布局**，背景/BGM 另开任务。
- 如果要换背景，需要先准备素材并走审批，不要直接把草图当背景。

**Q5 — F7 切换时是否保留 B 开关？**

- 当前 `set_enemy()` 会保留 `blocks_enabled`；新变体沿用该行为。smoke 要覆盖
  “关闭 blocks 后切换敌人，仍然是关闭状态”。

**Q6 — 场景预览**

- 建议每个变体出一张 F1 判定框截图或预览图：Warrior 对称布局、Bat/Veno 空场、
  Creepy 现状；不需要重新生成美术素材。

---

## 6. 建议实施顺序

1. **基线**：`main.py --smoke-test` exit 0；确认工作区 docx / sketch 不被改动。
2. **先做 Rhea 数据与 3% 被动**（不碰 E 状态机）：
   - stats 冷却、attacks 字段、event 倍率、projectile 字段；
   - 同步更新 smoke 中 E 的伤害/冷却期望，但保留“自动折返”流程；
   - 跑 smoke，确认数据改动没有破坏其它角色。
3. **改 E 为手动折返**：
   - `game/rhea.py` 状态机、冷却、动画、HUD；
   - 重写 E 的 smoke；
   - 手动 F1/F2/F6 看等待姿态和折返。
4. **场景数据**：
   - `debug.json` 加 Warrior / Bat / Veno；Warrior 先按草案；
   - `roster.json` 接 `stage_variant`；
   - 更新/新增 scene smoke。
5. **回归**：完整 smoke、F7 循环、`[`/`]` 切角色、F9 重置、B 开关。
6. **确认后写文档**：README / DESIGN_DECISIONS / DEBUG / ASSET_PIPELINE（如新增帧）/
   NEXT_SESSION_RHEA / NEXT_SESSION_SCENE / 基础操作手册；按 AGENTS.md 先问一次是否写入。
7. **提交**：只有用户明确说 commit 才提交；不要 push。

---

## 7. smoke 更新清单

### 7.1 Rhea 数值

| 测试 | 旧期望 | 新期望 |
|---|---|---|
| `rhea_present` | q/e 冷却未检查 | 增加 `q_cd_max == 6.0`、`e_cd_max == 10.0` |
| LMB 三连（无中毒） | 60 | 60（不变） |
| LMB 命中已中毒 200 HP | 20 | 26 |
| LMB 命中已中毒 300 HP | 20 | 29 |
| RMB 命中已中毒 200 HP | 24（HP 176） | 30（HP 170） |
| RMB 命中已中毒 300 HP | 24 | 33 |
| Q 初始伤害 200 HP | 40 | 40（不变） |
| Q 5s 毒总伤 200 HP | 30（总 70） | 30（总 70，不变） |
| Q 初始 300 HP | 48 | 48（不变） |
| Q 冷却 | `>0` | 额外检查 `q_cd_max == 6` |
| E 无中毒总伤 | 28 | 30 |
| E 已中毒 200 HP | 58 | 60 |
| E 已中毒 300 HP | 73 | 75 |
| E 已中毒 + 50% DR 200 | 29 | 30 |
| E 已中毒 + 50% DR 300 | 36.5 | 37.5 |
| E 冷却 | `>13.0` | 结束后 `e_cd > 8.0`（10s 冷却，测试时刻按实际调整） |

### 7.2 E 手动折返

新增/改写：

- **起手不进入冷却**：按 E 后到第一段结束，`rhea.e_cd == 0`，`attack_id == "rhea_dash"`。
- **等待窗口**：第一段结束后 2s 内不按 E，角色停在去程结束位置，不回 `cast_x`；
  2s 后技能结束，`e_cd > 0`。
- **主动折返**：等待窗口内再按 E，角色回到 `cast_x`，`back` 组命中一次，
  技能结束后 `e_cd > 0`。
- **两段各命中一次**：同一目标在去程/回程各命中一次；两段伤害 16 + 14。
- **首段 15%**：只对已中毒目标、只在去程触发；回程不加。
- **霸体**：去程和回程期间 `super_armor` 生效；等待窗口按 Q3 的决定测。
- **“无视hitbox”**：按 Q2 的最终解释测；若保留当前 A 解释，则仍测 block 截断。
- **清理**：KO / 非霸体受击 / reset / set_character / set_enemy 后，等待状态、
  `rhea_dash` runtime、`pass_through_enemy`、`e_cd` 都不残留。

### 7.3 场景

- `warrior_stage_ok`、`bat_stage_ok`、`veno_stage_ok`、`scene_variant_switch_ok`
- 现有 `creepy_stage_ok` 不变；`creepy_stage_switch_ok` 更新为 Warrior 变体断言。
- 最终 conjunction 加所有新 flag；任何一个 false 都让 smoke exit 非 0。

---

## 8. 文档 / 手册（实现并确认后）

按 `AGENTS.md`：先完成实现和验证，确认设计后**问一次**是否写入文字；不要自动改。

需要更新的位置：

- `README.md`：Rhea 的 Q/E 冷却、被动 3%、E 手动折返；场景切换。
- `docs/DESIGN_DECISIONS.md`：Rhea 的 E 两段与等待窗口、3% 被动、场景 variant 选择规则。
- `docs/DEBUG.md`：新增 smoke flag、F1/F2/F6 检查方法；场景 variant 的调试。
- `docs/ASSET_PIPELINE.md`：只有新增 E wait 帧时才更新；没有新素材就跳过。
- `docs/NEXT_SESSION_RHEA.md`：在顶部标注“技能已按 2026-11-02 docx 修订”，链接本文。
- `docs/NEXT_SESSION_SCENE.md`：补充 Warrior / Bat / Veno / Creepy 的 variant 表。
- `Island Survival 基础操作手册.docx`：4.3 Rhea 的 Q/E 冷却、被动、E 手动折返；
  Creepy/Warrior/Bat/Veno 场景说明；版本日期。
- `instruction.docx`：**绝不修改**。

---

## 9. 风险与边界

- **E 状态机**：暂停 `AttackRuntime`、等待窗口、回程、冷却延后四件事必须一起清干净；
  任何一条路径漏掉都会留下 `pass_through_enemy` 或无法再次起手。
- **霸体时长**：当前 armor 是起手加 1s 的定时效果；改成按阶段管理后，要确认
  `take_hit()` 的 KO 分支、`statuses.add("super_armor")` 的覆盖/刷新行为。
- **等待窗口受击**：如果等待不霸体，受击会进入 HURT；要定义折返窗口是否取消、
  冷却是否开始，避免“被打断但 E 仍在冷却”或“被打断还能免费折返”两种极端。
- **3% 与延长顺序**：3% 在 `resolve_hit` 里按命中前毒状态结算；延长在 `on_hit_success`
  里发生。不要为了 3% 在命中前提前加毒，也不要在 `on_hit_success` 里二次扣血。
- **RMB 弹体字段**：新增字段要同时改 `ShurikenProjectile`、`scene.spawn_projectile_from_event`、
  `resolve_projectile_hit` 和 smoke；漏一处会导致 3% 不生效或对无毒目标生效。
- **场景切换**：Warrior 变体会改变 `stage.platforms` / `barriers`，旧 smoke 可能假设
  默认布局；先跑完整 smoke，逐个修断言，不要只改 `creepy_stage_switch_ok`。
- **空场景**：Bat/Veno 的 `blocks` / `ladders` 为空，`Stage.draw`、`ladder_for`、
  `move_x` 都必须能处理空列表；现有代码看起来可以，但要用 smoke 覆盖。
- **草图不是运行时素材**：`sketch/warrior_scene.jpg` 只用于布局参考，不要 `pygame.image.load`
  它当背景，也不要提交/修改。
- **不要碰的范围**：Eira / Shadow Ninja、其他敌人、背景/BGM、`Image/`、`UI Resources/`、
  `instruction.docx`。

---

## 10. Definition of Done

- [ ] Rhea：Q 冷却 6s、E 冷却 10s；LMB/RMB 对已中毒目标额外 3% 最大生命。
- [ ] Rhea：E 第一段 0.8basic+1.2extra、第二段 0.7basic+0.8extra；15% 只在首段。
- [ ] Rhea：E 第一段结束后 2s 内可再按 E 折返；不按则不折返；冷却在技能结束后开始。
- [ ] Rhea：E 冲刺/折返霸体与“无视hitbox”按用户确认的解释实现。
- [ ] 场景：Warrior 对称布局；Creepy 保持现状；Bat/Veno 空场景；Dummy 默认场景。
- [ ] F7 / `[` / `]` / F9 / B 开关下场景和敌人一致；切场景不残留旧实体。
- [ ] `main.py --smoke-test` exit 0；新增 smoke flag 全为 true。
- [ ] F1/F2/F6 手动验证 Rhea E 的等待/折返、3% 伤害和场景布局。
- [ ] 用户确认后，才更新 README/docs/手册；`instruction.docx` 未被修改。
- [ ] 未经用户明确要求不 commit、不 push。
