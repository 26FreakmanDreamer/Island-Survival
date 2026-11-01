# Next Session — Rhea Thorn 设计与接入

> 日期：2026-10-31（设计）；2026-11-01（实现完成）
> 状态：**已实现并验证**。§5/§7 已回填最终值；素材、数据、代码和 smoke 全部完成，
> `main.py --smoke-test` → exit 0。后续手感/场景微调见 §13。
> 基线：`git` HEAD `ab7d392`（2026-10-30），`main.py --smoke-test` → exit 0。
> 当前分支：`nyra-veno-sandbox`；默认角色 **Lina**，默认敌人 **Creepy Shooter**。
> 权威规格：`instruction.docx`（用户 2026-10-31 更新）。本文只摘录，**不修改 docx**。
> **注意**：`instruction.docx` 在工作区有未提交修改（2026-10-31），比 HEAD `ab7d392` 新；以工作区版本为准，不要 revert/stash/checkout 它。
>
> 阅读顺序：本文 → `instruction.docx` 的“战斗系统 / 毒伤 / Rhea Thorn” → `AGENTS.md` →
> `README.md` → `docs/DESIGN_DECISIONS.md` → `docs/DEBUG.md` → `docs/ASSET_PIPELINE.md` →
> `docs/IMAGE_GENERATION_RULES.md` → `docs/NEXT_SESSION_CHARACTERS.md`（通用接入约定）→
> `game/status.py`、`game/veno.py`、`game/nyra.py`、`game/combat.py`、`game/scene.py`、
> `game/config.py`、`game/data/*.json`、`main.py` 的 smoke。

---

## 30 秒结论

- Rhea 是**毒伤型可玩角色**：Q 上 5s / 3% 最大生命的毒；LMB/RMB 命中把已有毒延长 1s；E 两段冲刺，第一段对已中毒目标额外造成 15% 最大生命。
- 实现已补齐 `extend_poison`（只延长、不新建）、target-max-HP 伤害字段、`hit_group` 两段命中、`ShurikenProjectile` 与六张星形 FX；最终值见 §7，结果见 §13。
- 本文 §4 的 Q1–Q12 是设计时的 grill 记录，最终值以 §7 为准；实现和 smoke 已完成。

---

## 0. 给下一个 session 的开场 prompt（可直接复制）

```text
读取 docs/NEXT_SESSION_RHEA.md，以及 instruction.docx 的“战斗系统 / 毒伤 / Rhea Thorn”段。
本轮先完成 Rhea Thorn 的设计确认，不要先改代码或生成素材：
1) 先运行 .venv/Scripts/python.exe main.py --smoke-test，确认 exit 0；
2) 按本文 §4 的 Q1–Q12 一次性 grill 我，每项给出当前状态、建议值和影响范围；
3) 我确认后，把答案写回本文 §7，再按 §8 的阶段实施；
4) 每个素材阶段先出 base/contact sheet 等我批准；每完成一个代码阶段跑一次 smoke。

重点：Rhea 的毒伤必须遵循 instruction.docx 的“同源延长、异源独立”规则；
Rhea 的被动只延长“敌人已经处于毒伤状态”的毒，不要凭空创建毒伤。
不要修改 instruction.docx、Image/、UI Resources/ 或其他角色/敌人的数值/AI/冷却；
不要 commit，除非我明确要求。不要用 pytest；验证用 --smoke-test、F1/F2 和预览图。
```

---

## 1. instruction.docx 原文摘录（权威规格）

### 1.1 Rhea Thorn

> Rhea Thorn  
> 形象：Image\Character\rhea-thorn-256.png  
> 被动：敌人处于毒伤状态下，使用鼠标左键、右键击中敌人可延长毒伤时间，每次击中敌人延长1s  
> 鼠标左键：手拿手里剑攻击敌人，造成伤害（atk）。动画左右交替，如第一次右手攻击，再次按下鼠标左键则出左手攻击。  
> 鼠标右键：向敌人投掷一枚手里剑（远程攻击）(1.2basic+1.3extra)，手里剑对敌人造成伤害。  
> Q技能：（冷却8s）向敌人投掷一枚带有剧毒的手里剑，造成伤害(1.2atk+8%目标最大生命)，敌人进入毒伤状态（动画，敌人变绿，变紫交替），每秒扣除目标3%的生命值，持续5s  
> E技能：（冷却15s）手持手里剑向敌人冲刺一段距离，造成伤害（0.7basic+0.8extra），冲刺结束后折返，回到冲刺前的位置，造成伤害（0.7basic+0.8extra）。如果敌人处于毒伤状态，额外造成目标15%最大生命值伤害（在冲刺第一段触发）。

### 1.2 毒伤定义与叠加规则

> 毒伤：被毒伤的对象身体会呈现紫、绿交替性变化。扣除最大生命值百分比的hp.  
> 毒伤可叠加。  
> 叠加规则：前提：假如A毒伤了B，即B被A毒伤  
> 如果B在毒伤状态，B再次被A毒伤，则B的毒伤状态延长。比如：一次毒伤的效果是3s。B在毒伤状态下，B被A毒伤，还有2s解除毒伤，而A此时第二次毒伤B，则B的毒伤效果延长为5s，以此类推。  
> 如果B在毒伤状态，B被C毒伤，B现在的毒伤没有C的影响，则C对B有完整的毒伤效果。比如：一次毒伤的效果是3s。B在毒伤状态下，B被A毒伤，还有2s解除毒伤，此时C对B造成毒伤，则B此时剩下A的毒伤效果2s，C的毒伤效果3s。即B要扣除两次血量。

### 1.3 与 Rhea 相关的全局规则

- `atk = basic atk + extra atk`；测试基准 `character hp=100, basic atk=20, extra atk=0`。
- 远程子弹分高/中/低：高可打头、俯身可躲、跳跃不可躲；中可打头、俯身不可躲、跳跃可躲；低可打腿、跳跃可躲、俯身不可躲。高/中/低高度是固定数值，不随角色/敌人变化。
- 负面效果包括击飞、冻结、眩晕、击退、减速、灼烧、毒伤；Purity Seal 解除当前全部负面效果并在 3s 内免疫，Sacred Shield 在 2s 内免疫一切伤害。
- 操作：Q 技能 1（8s）、E 技能 2（15s）；鼠标左键普通攻击 1，右键普通攻击 2；中键目标锁定。
- 战斗界面：蓝色被动条只在有特殊被动进度时显示；Rhea 的被动没有数值条，默认不新增资源条。

---

## 2. 当前实现快照（已核对，2026-10-31）

> 这是设计开始前的快照；实现后的 roster/配置/素材状态见 §7、§13。

### 2.1 角色/roster 架构

- `game/data/roster.json` 的 `characters` 当前顺序是 **Lina → Nyra**；`[` / `]` 按这个顺序循环，`set_character()` 会重建 fighters 并整场重置。
- 默认角色在 `debug.json` 的 `roster.default_character = "lina"`；默认敌人是 `creepy_shooter`。不要为了 Rhea 改默认阵容，除非用户明确要求。
- 可玩角色类必须实现 `update(dt, input_state, target, scene)`；`start_attack()` 里调用 `scene.face_target_if_locked(self, target)` 才支持中键锁定。
- 当前可玩类模板：`game/nyra.py`（无能量、Q/E 冷却、`AttackRuntime`、自定义 `_handle_control` / `_update_attack` / `_execute_queued` / `reset`）。Rhea 应沿用这个结构，而不是 Lina 的 energy/flame 结构。
- 注册点：`game/roster.py` 的 `FIGHTER_CLASSES`；`game/config.py` 的 `ROSTER_CLASSES`、`PLAYABLE_CLASSES`、`ANIMATED_CLASSES`。

### 2.2 毒伤现状

- `game/status.py` 的 `StatusSet` 已经实现了 instruction 的叠加规则：
  - `poisons: list[PoisonInstance]`，每条有 `source`、`remaining`、`dps`、`tick_accum`。
  - `add_poison(source, duration, dps)`：同源已存在 → `remaining += duration` 并更新 dps；异源 → 追加新实例。
  - `StatusSet.update()` 每 `POISON_TICK = 0.5s` 结算一次，`target.apply_dot(dps * 0.5)`；先结算再减剩余时间，保证 5.0s 毒仍有第 10 次完整 tick。
  - `has("poison")` 只要有任一实例即为真；`remove("poison")` / `clear()` 清空全部实例。
  - `describe()` 输出 `poison[source]: remaining`，F2 已能显示。
- 现有 Veno 毒伤（`game/veno.py::on_projectile_hit`）：
  - `source = f"veno_poison:{id(self)}"`，每只 Veno 是独立来源。
  - `dps = target.max_hp * event.status_dps_pct`，事件里 `status_dps_pct = 0.03`，`status_duration = 3.0`。
  - 因此实际是 3%/s、0.5s 一跳、每跳 1.5% 最大生命。
- **不要被 `stats.combat.poison_dps_pct = 0.02` 误导**：它只用于 F11 强制状态演示，不是 Veno 毒伤，也不是 Rhea 毒伤。Rhea 的攻击事件必须显式写 `status_dps_pct: 0.03`。
- `docs/DESIGN_DECISIONS.md` 的 Status effects 段仍写着“Poison: 2% max HP/s”，这是旧文案；以 docx + `veno.py` 的 3% 为准，本轮不要直接照抄该行。
- 中毒表现：`scene._poison_tint()` 对任何 `statuses.has("poison")` 的 fighter 做全身绿/紫交替（每 0.18s），不需要新状态类型或新角色帧。
- `Fighter.apply_dot()` 直接扣 HP，**不经过 damage_reduction**；`invincible` 或已 KO 时直接返回。毒伤可以正常把目标打死并触发 KO。

### 2.3 命中与攻击管线

- 近战命中：`resolve_hit()` → `target.take_hit()` → `attacker.on_hit_success(attack, target, bonus)`。
- 弹体命中：`resolve_projectile_hit()` → `projectile.owner.on_projectile_hit(projectile)`。
- `AttackRuntime` 的 hitbox 事件共用一个 `hit_targets: set[int]`：同一攻击里一个目标只能被命中一次。Rhea 的 E 要“去程 + 回程各命中一次”，不能直接复用这个单集合；需要 `hit_group` 或自定义命中逻辑（见 Q7）。
- `AimedProjectile` 已支持 `status` / `status_duration` / `status_dps_pct` / `penetrates_blocks` 字段，但**没有通用的状态应用逻辑**；Veno 是在自己的 `on_projectile_hit` 里读取这些字段并调用 `statuses.add()`。Rhea 也应照此实现，而不是假设 scene 会自动上毒。
- `scene.spawn_projectile_from_event()` 按 `event["projectile"]` 分支构造弹体；新增 kind 必须同步 `config.PROJECTILE_KINDS` 和 scene 分支，否则会落到默认 Q 波。
- `pass_through_enemy: true` 已在 scene 中通用处理；Rhea 的 E 可以复用。

### 2.4 配置与 smoke 的硬编码

- `game/config.py` 当前硬校验：`REQUIRED_STATS`、`REQUIRED_ATTACKS`、`REQUIRED_NYRA_CLIPS`、`PROJECTILE_KINDS`、各角色 stats/clips/frame_size/pivot。
- `main.py` 的 `previous_character_ok` / `next_character_ok` 现在按 Lina → Nyra → Rhea → Lina 断言（实现后已更新；见 §7/§13）：
  - 若 roster 顺序是 Lina → Nyra → Rhea，`[` 从 Lina 会到 Rhea（不是 Nyra），`]` 从 Rhea 回到 Lina。
- 新增角色要加 `rhea_missing_frames`，并加入最终 conjunction；不要只打印不参与退出码。
- 现有 smoke 的默认敌人是 Creepy Shooter；Rhea 测试应显式 `scene.set_enemy(...)`，不要依赖默认值。

### 2.5 素材约定

- 可玩角色当前两档：Lina 256×256 / pivot (128,244) / body ~210；Nyra 384×384 / pivot (192,372) / body 214。
- 新角色的 canonical 图在 `Image/Character/rhea-thorn-256.png`，只读；运行时帧必须走 `assets/frames/rhea/`，不能直接读 `Image/`。
- 生成前必须读 `docs/IMAGE_GENERATION_RULES.md`：身体部件前后层、持武器手/握姿、不穿模、尺寸/比例锁；生成后按 contact sheet 逐动作审批，未批准不进游戏。
- 不要逐帧缩放/拉伸角色来适配画布；如果手里剑/动作放不下，先停下问用户，不要裁切武器或缩小人物。

---

## 3. Rhea 的设计定位（建议）

Rhea 是**毒伤型近中距离可玩角色**，与 Nyra 的区别不在爆发，而在“先上毒，再用普攻把毒养长，最后用 E 吃毒伤加成”的循环：

1. Q 上毒（5s，3%/s 最大生命）。
2. LMB / RMB 命中延长毒伤 1s/次，同时造成常规伤害。
3. 毒伤期间用 E 冲刺 + 折返，第一段额外吃 15% 最大生命伤害。
4. 毒伤总伤害是最大生命百分比，因此 Rhea 对高 HP 敌人（Warrior 300、Creepy 200）比低 HP 敌人更有价值；这是 docx 数值的自然结果，不要额外加“对低 HP 补偿”。

设计上要避免两个误区：
- **不要把被动做成“每次普攻重新上 1s 毒”**：docx 写的是“敌人处于毒伤状态下……延长”，没有毒伤时不应凭空产生毒。
- **不要把 Q 的 8% 最大生命和毒伤的 3%/s 合并成一个固定伤害**：Q 是“初始命中 + 持续毒”，E 的 15% 是“第一段命中时的额外伤害”，三者是独立伤害实例。

---

## 4. 必须先确认的问题（Q1–Q12）

> 以下为设计时的建议值，已被 §7 的最终值和后续微调取代；不要按本节旧值实现。

> 下一 session 一次性问完；每项给出建议默认值。用户确认后把答案写进 §7，再开始实现。不要用“看起来差不多”的数值。

| # | 问题 | 建议默认 | 影响 |
|---|---|---|---|
| Q1 | 画布 / pivot / body / hurtbox / roster 顺序 / 默认角色 | 384×384，pivot (192,372)，body 214；hurtbox 56×210 / 56×130；`stage_body_width 100`；Rhea 插在 Nyra 后面；默认仍是 Lina | 素材导入、config、`[`/`]`、smoke |
| Q2 | LMB 左右交替如何做：两个 clip 还是一个 clip 镜像？帧数/判定/击退？ | 一个 `rhea_slash` attack，两个 clip `rhea_slash_r` / `rhea_slash_l`，各 3 帧；成功起手时切换下一手；伤害 `1.0×atk = 20`；hitbox `[28,-165,70,48]`，t=0.08–0.14；knockback 60；0.25s | 动画、数据、交替状态、smoke |
| Q3 | RMB 手里剑的 lane / 速度 / 射程 / 半径 / 是否被 block 挡住 / 命中反馈 | 最终：中 lane；speed 850；range 900；radius 12；被 barrier/platform 挡住；0.35s，t=0.14 发射；伤害 24；knockback 0；贴身判定（见 §7） | projectile 分支、贴图、AI/场景交互 |
| Q4 | Q 毒手里剑的 lane / 速度 / 射程 / 是否穿透 block / 贴图差异 | 与 RMB 同 lane/speed/range/radius；不穿透 block；0.45s，t=0.18 发射；初始伤害 `1.2×atk + 8% 目标最大生命`；毒 5s、3%/s；贴图带绿/紫毒层 | projectile、毒伤、视觉、smoke |
| Q5 | 被动延长的是“Rhea 自己的毒”还是“目标身上的任意毒”？是否有延长上限？Q 命中是否也触发 +1s？ | 只延长 Rhea 自己的 `rhea_poison`；+1s/次，不设上限（按 docx 字面）；Q 不触发 +1s（Q 是重新上毒/同源 +5s） | `StatusSet.extend_poison`、被动钩子、测试 |
| Q6 | E 的冲刺距离 / 总时长 / 折返速度 / 是否霸体 / 是否穿敌 / 碰到墙和 block 怎么处理 | 最终：去程约 594px（0.06–0.60s，1100px/s），0.60–1.00s 折返到 `cast_x`（~600px）；总 1.00s；全程 0.0–1.00s 霸体；穿敌；墙/block 截断；两段各 14 伤害；见 §7 | 自定义位移、hitbox、命中分组、smoke |
| Q7 | E 的两段如何允许同一目标各命中一次？ | 在 `AttackRuntime` 增加 `hit_group`（默认 `"default"`，现有攻击行为不变）；E 的去程/回程各一个 group | `combat.py`、E 数据、回归测试 |
| Q8 | 帧集与帧数 | 最终 33 帧：idle 2、walk 4、jump 2、crouch 1、hurt 2、KO 3、`rhea_slash_r/l` 3+3、`rhea_throw` 3、`rhea_poison_throw` 3、`rhea_dash` 5、climb 2；见 §5.5/§7 | 素材生成、animations、审批 |
| Q9 | HUD / F2 要显示什么 | 复用 Nyra 的 Q/E 冷却显示；无能量/被动条；F2 已能显示 `poison[source]` 剩余时间；可选加 `POISON EXT n` 计数 | HUD、debug、smoke |
| Q10 | 手里剑素材：普通/毒两套贴图、旋转帧数、是否程序化生成、是否加毒雾 FX | 普通钢色 2–3 帧旋转；毒版 2–3 帧绿/紫涂层；程序化像素贴图 + contact sheet 审批；FX 不烘焙进角色帧 | 素材管线、projectile draw、审批 |
| Q11 | smoke 范围：只测 Rhea vs Dummy，还是也测 vs Warrior/Creepy；是否更新角色循环断言 | 新 Rhea phase：vs Creepy Shooter（200 HP，每 0.5s 跳 3 HP，便于整数断言）为主，Warrior（300 HP）做高 HP 对照；更新 `[`/`]` 断言；补 `rhea_missing_frames` | main.py、回归 |
| Q12 | 本轮范围：只设计，还是设计确认后直接做素材+代码 | 推荐沿用 Creepy 的节奏：本轮先确认设计；确认后按“base → 动作帧 → 数据/代码 → smoke/预览”推进 | 计划、时间、审批 |

### 4.1 仍需用户补的缺失数值

docx 没有写、但实现必须有的值：

- LMB hitbox 的具体范围、击退、hitstun（建议值见 Q2）。
- RMB/Q 手里剑的 lane、速度、射程、半径、是否被 block 挡住（建议值见 Q3/Q4）。
- E 的冲刺距离、折返速度、总时长、是否霸体/无敌、是否穿敌（建议值见 Q6）。
- 帧数与每帧时长、画布/身体高度（建议值见 Q1/Q8）。
- 被动是否只延长 Rhea 的毒、是否有上限、Q 是否触发 +1s（建议值见 Q5）。
- 手里剑的视觉（普通/毒）和是否要毒雾/命中特效（建议值见 Q10）。
- Q/E 冷却从起手还是命中开始计时（建议起手，与 Nyra 一致）；LMB/RMB/Q/E 是否只能地面起手（建议与 Nyra 一致，地面起手；跳跃/受击排队沿用 Nyra 的一格输入队列）。

---

## 5. 最终设计（2026-11-01 已实现）

### 5.1 数值

| 项 | 草案 |
|---|---:|
| HP | 100 |
| basic ATK | 20 |
| extra ATK | 0 |
| atk | 20 |
| stage_body_width | 100 |
| walk / jump_v / gravity | 260 / 760 / 2200 |
| Q 冷却 | 8s |
| E 冷却 | 15s |
| hurtbox | 56×210 standing / 56×130 crouching |
| 画布 / pivot / body | 384×384 / (192,372) / 214 |

### 5.2 四个输入

| 输入 | attack_id | 伤害（atk=20） | 关键规则 |
|---|---|---:|---|
| LMB | `rhea_slash`（clip `rhea_slash_r/l`） | 20 | 左右手交替；命中延长 Rhea 毒 +1s；0.25s，hitbox t=0.08–0.14；击退 60（后续微调） |
| RMB | `rhea_throw` | 24 | 中 lane 手里剑；命中延长 Rhea 毒 +1s；被 block 挡住；0.35s，t=0.14 发射；速度 850、射程 900（后续微调）、半径 12；贴身判定 |
| Q | `rhea_poison_throw` | 24 + 8% 目标最大生命 | 毒手里剑；命中上毒 5s、3%/s；8s CD；0.45s，t=0.18 发射；速度 850、射程 900（后续微调）、半径 12；贴身判定 |
| E | `rhea_dash` | 14 + 14 | 去程/回程各命中一次；去程若目标已中毒，额外 +15% 目标最大生命；15s CD；1.00s；全程 0.0–1.00s 霸体；去程 ~594px、回程 ~600px（后续微调） |

### 5.3 被动

- 名称：未定（docx 未命名）。
- 触发：LMB 或 RMB **实际命中**且目标存活。
- 条件：目标身上存在 `source == "rhea_poison"` 的毒伤实例。
- 效果：该实例 `remaining += 1.0s`；不新增实例，不刷新 dps，不改变其他来源的毒。
- 不在 Q 命中的瞬间额外 +1s；Q 自己的同源重上按 `add_poison` 规则 +5s。
- 不设延长上限（docx 未写）；如果用户要上限，在确认时给具体秒数。

### 5.4 毒伤参数

| 项 | 值 |
|---|---:|
| 来源 id | `rhea_poison`（单玩家；如未来多 Rhea，再改 `rhea_poison:{id}`） |
| 持续时间 | 5.0s |
| 伤害 | 目标最大生命 × 3%/s |
| 结算 | 沿用 `POISON_TICK = 0.5s`，每跳 1.5% 最大生命，5s 共 10 跳 = 15% 最大生命 |
| 同源重上 | `add_poison`：剩余 + 5.0s |
| 被动延长 | `extend_poison`：剩余 + 1.0s/次，仅已有实例 |
| 视觉 | 现有全身绿/紫交替，无需新状态 |

### 5.5 最终帧集（33 帧，已批准）

| clip | 帧数 | durations | 说明 |
|---|---:|---|---|
| idle | 2 | 0.30 / 0.30 | 循环，手持手里剑待机 |
| walk | 4 | 0.12 ×4 | 循环 |
| jump | 2 | 0.20 / 0.20 | 空中 |
| crouch | 1 | 0.30 | |
| hurt | 2 | 0.10 / 0.10 | |
| ko | 3 | 0.25 / 0.20 / 0.25 | 跪姿 / 过渡 / 向右躺倒（用户追加过渡帧） |
| `rhea_slash_r` | 3 | 0.08 / 0.08 / 0.09 | 右手攻击 |
| `rhea_slash_l` | 3 | 0.08 / 0.08 / 0.09 | 左手攻击（用户提供帧，归一化后使用） |
| `rhea_throw` | 3 | 0.10 / 0.08 / 0.17 | 投掷普通手里剑 |
| `rhea_poison_throw` | 3 | 0.12 / 0.10 / 0.23 | 00 为毒星蓄力；01/02 复用普通投掷释放/收势，近手空手 |
| `rhea_dash` | 5 | 0.06 / 0.20 / 0.20 / 0.14 / 0.40 | 起手 / 去程 / 去程末 / 转身 / 折返收势（总 1.00s） |
| climb | 2 | 0.20 / 0.20 | 背面攀爬；双手空手，双手里剑收纳在腰后金条纹绑带 |

> 最终 33 帧；KO 按用户要求为 3 帧；`rhea_dash` 为距离翻倍后重新计时到 1.00s。

---

## 6. 毒伤机制落地细节（重点）

### 6.1 docx 规则 → 引擎行为 → Rhea 实现

| docx 规则 | 现有引擎 | Rhea 应怎么做 |
|---|---|---|
| 毒伤扣“最大生命值百分比” | `dps = target.max_hp * pct`；`apply_dot(dps * 0.5)` | Q 事件写 `status_dps_pct: 0.03`；`on_projectile_hit` 里 `dps = target.max_hp * 0.03` |
| 3%/s，持续 5s | `POISON_TICK = 0.5`，5s = 10 跳 | 不要改 `POISON_TICK`；Rhea 与 Veno 共用 0.5s 结算 |
| 同源再次毒伤 → 延长 | `add_poison` 同源 `remaining += duration` | Q 再次命中同一目标：`add_poison("rhea_poison", 5.0, dps)`，剩余 +5s |
| 异源 → 各自独立、扣两次 | `poisons` 列表，多实例各自 tick | 不要合并来源；Rhea 毒与 Veno 毒可同时存在（测试时直接构造两实例） |
| 被动：毒伤状态下 LMB/RMB 命中 +1s | 没有“只延长、不创建”的接口 | 新增 `StatusSet.extend_poison(source, 1.0) -> bool`；找到才加，找不到返回 False |
| 毒伤视觉：绿/紫交替 | `scene._poison_tint()` 已按 `has("poison")` 处理 | 不新增状态类型/角色帧；Q 弹体本身用毒色贴图 |
| 毒伤是负面效果 | `Purity Seal` / `Sacred Shield` 是 docx 道具；当前沙盒尚未接入道具系统 | 未来接入时：Purity Seal 用 `statuses.remove("poison")` 清空；Sacred Shield 的 invincible 会让 `apply_dot` 跳过 |

### 6.2 数值示例（便于 smoke 断言）

| 目标最大生命 | 3%/s | 0.5s 每跳 | 5s 总毒伤 | +1s 延长 | Q 初始伤害（atk 20） | E 第一段毒加成 |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 3 | 1.5 | 15 | 3 | 24 + 8 = 32 | 15 |
| 200 | 6 | 3 | 30 | 6 | 24 + 16 = 40 | 30 |
| 300 | 9 | 4.5 | 45 | 9 | 24 + 24 = 48 | 45 |

- 5s 毒在 60Hz 下应结算 10 次；由于 `POISON_TICK` 的浮点累加，测试用 `+1e-9` 容差（现有 `StatusSet.update` 已处理）。
- E 的 15% 只在**第一段命中时目标已中毒**才加；如果第一段没中毒、第二段才中毒，不加。
- Q 的 8% 和 E 的 15% 都经过 `take_hit`，会受 `damage_reduction` 影响；毒 tick 走 `apply_dot`，**不受** `damage_reduction` 影响。这是现有引擎行为，需在 smoke 里明确。
- 毒伤可以致死：`apply_dot` 在 HP 归零时切 KO；Q 初始命中把人打死时不应再上毒（`on_projectile_hit` 先检查 `target.hp > 0`）。
- 毒伤在 hitstop 期间冻结：`scene.tick` 在 hitstop 时提前返回，`statuses.update` 不推进；这是现有全局行为，不要为 Rhea 单独改。

### 6.3 实现陷阱

1. **不要用 `add_poison` 实现被动延长**：`add_poison` 在找不到同源时会新建 1s 毒，违背“敌人处于毒伤状态下才延长”。必须新增 `extend_poison`，或先 `any(p.source == ...)` 再改 `remaining`。
2. **不要用 `combat.poison_dps_pct`**：它是 0.02 的 F11 演示值；Rhea 与 Veno 都用事件里的 0.03。
3. **不要只改 `attacks.json` 就以为毒会自动生效**：scene 不会通用应用 `status` 字段，必须在 `Rhea.on_projectile_hit` 里调用 `statuses.add`。
4. **E 不能复用单一 `hit_targets`**：同一目标在去程命中后，回程会被 `AttackRuntime` 的全局 `hit_targets` 挡住；要加 `hit_group` 或自定义两段命中。
5. **E 的 15% 不能在 `on_hit_success` 里补伤害**：`on_hit_success` 在 `take_hit` 之后才调用；应在 `resolve_hit` 计算 damage 时根据 `event` 和 target 状态加，才能正确经过减伤/命中反馈。
6. **Q 的 8% 不能在 `attack_damage` 里硬编码**：它是 projectile event 的 `bonus_target_max_hp_pct`，需要 target 才能算；`spawn_projectile_from_event` 已经有 target，传入即可。
7. **毒源 id 要稳定**：单玩家用 `"rhea_poison"` 即可；如果用 `id(self)`，F2 显示会带一串数字，但更适合同场多 Rhea 的未来场景。先按单玩家确认。
8. **Q 的毒贴图与普通手里剑要区分**：docx 明确“带有剧毒”，不能只用同一张钢色手里剑；至少加绿/紫毒层或毒雾拖尾。

---

## 7. 已确认决策（最终值）

> 2026-11-01 回填；实现与 smoke 已按此完成。后续用户微调列在表后。

| 问题 | 最终决定 |
|---|---|
| Q1 画布/身体/roster | 384×384、pivot (192,372)、body 214；Lina → Nyra → Rhea；默认角色 Lina、默认敌人 Creepy Shooter 不变 |
| Q2 LMB | `rhea_slash`；20；右手/左手交替（首次右手，成功起手才切换）；0.25s；hitbox `[28,-165,70,48]` t=0.08–0.14；命中延长 `rhea_poison` +1s；后续微调击退 60 |
| Q3 RMB | `rhea_throw`；24；3 帧 0.35s，t=0.14 发射；中 lane、速度 850、射程 900（后续微调）、半径 12；单体、被 block 挡住；命中 +1s；无冷却；贴身判定 |
| Q4 Q | `rhea_poison_throw`；24 + 8% 目标最大生命（命中时按实际目标结算）；0.45s，t=0.18；毒 5.0s、3%/s、0.5s 跳；同源 +5s、异源独立；8s CD；Q 不触发 +1s；初始命中致死不上毒；射程 900、贴身判定 |
| Q5 被动延长 | 只延长已有 `rhea_poison` +1.0s；不创建、不刷新 dps、不影响 Veno 毒；每目标每次攻击一次；无上限 |
| Q6 E | `rhea_dash`；14+14；1.00s；去程 1100px/s 0.06–0.60（~594px），回程 1500px/s 0.60–1.00 回 `cast_x`（~600px）；全程霸体 0.0–1.00s；15s CD；首段对任意来源中毒 +15% 最大生命；零击退；穿敌、墙/block 截断、结束 `push_apart` |
| Q7 两段命中 | `AttackRuntime.hit_targets` 改为按 `hit_group` 分组；E 去程 `out`、回程 `back`，各命中一次；其他攻击默认 `default`，行为不变 |
| Q8 帧集 | 33 帧：idle 2、walk 4、jump 2、crouch 1、hurt 2、KO 3（0.25/0.20/0.25）、slash_r 3、slash_l 3、throw 3、poison_throw 3、dash 5、climb 2；climb 双手空手、手里剑收纳 |
| Q9 HUD/F2 | 复用 Q/E 冷却徽章；无能量/被动条；F2 显示 `CHAR rhea 3/3`、`poison[rhea_poison]`；无 `POISON EXT` |
| Q10 手里剑素材 | 6 张 64×64：钢色/毒色各 3 帧旋转；弹体 `rhea_shuriken`/`rhea_poison_shuriken`；毒弹绿紫贴图 + 程序化毒雾拖尾；E 程序化残影 |
| Q11 smoke | 新增 Rhea phase；Creepy 200 / Warrior 300 / Dummy；数值断言按 §6.2；`rhea_missing_frames=0`、`rhea_fx_missing=0`、`default_hit_group_ok` 进最终 conjunction |
| Q12 本轮范围 | 只接入 Rhea 与本轮用户要求的手感/场景修正；不改其他角色/敌人数值/AI；不 commit |

**实现后的用户微调（2026-11-01）**
- LMB 增加轻微击退 60；RMB/Q/E 仍为零击退。
- RMB/Q 极限射程 700 → 900；新增贴身判定：以 Rhea 受击框外扩 24px 检查相邻敌人，命中直接结算完整伤害/毒，星体不再飞出、不二次命中。
- E 距离翻倍、速度不变：去程 ~594px、回程 ~600px，总时长 0.60 → 1.00s，动画/判定/霸体窗口同步。
- 梯上行为：受击立即退出攀爬并正常击落；脚底在 platform hitbox 内则吸附到平台顶（顶端不再掉地面）；梯上跳跃/坠落跳过 platform 侧面/底面碰撞直到落地；攀爬在平台中点略往上（`top+(bottom-top)/2-6`）提前上平台。
- Creepy Shooter 场景删除左侧 `[400,560,90,60]` barrier，仅保留右侧 `[790,560,90,60]`。

---

## 8. 实施清单（确认后）

### 8.1 数据

1. `game/data/stats.json`：增加 `rhea`（HP 100、basic 20、extra 0、move、cooldowns q/e、hurtbox、stage_body_width）。
2. `game/data/attacks.json`：增加 `rhea_slash`、`rhea_throw`、`rhea_poison_throw`、`rhea_dash`；attack id 与 clip 名/自定义 clip 规则一致。
3. `game/data/animations.json`：增加 `rhea_clips`、`rhea_frame_size`、`rhea_pivot`。
4. `game/data/roster.json`：在 `characters` 的 Nyra 后插入 Rhea 条目：
   ```json
   "rhea": {
     "name": "Rhea Thorn",
     "class": "rhea",
     "stats": "rhea",
     "spawn": "player_spawn",
     "clips": "rhea_clips",
     "frame_size": "rhea_frame_size",
     "pivot": "rhea_pivot",
     "frames_dir": "rhea",
     "fallback": "Image/Character/rhea-thorn-256.png"
   }
   ```
5. `game/data/debug.json`：`player_spawn` 已有，不需要新 spawn；默认角色不改。

### 8.2 代码

1. `game/rhea.py`：新建 `Rhea(Fighter)`，按 Nyra 的结构实现 `update`、`_handle_control`、`_update_attack`、`start_attack`、`reset`、`on_hit_success`、`on_projectile_hit`。
2. LMB 交替：`self.slash_right` 在每次成功起手时切换；`start_attack("rhea_slash")` 后把 `anim` clip 设为 `rhea_slash_r/l`。或者用两个 attack id；二选一，按 Q2 确认。
3. Q/RMB：RMB 无冷却；Q 在起手时设 8s 冷却，projectile event 带 `status/status_duration/status_dps_pct/bonus_target_max_hp_pct`。
4. E：`_dash_step()` 自定义去程/折返（参考 `CreepyShooter._roll_step` 的窗口式移动）；记录 `dash_start_x`；`stage.move_x` 处理墙/block；结束时回到起点附近。
5. 被动：`on_hit_success` 检查 `attack.get("extends_poison")`；`on_projectile_hit` 检查 `projectile.extends_poison`（由 event 传入）；两者都调用 `target.statuses.extend_poison(self.poison_source, 1.0)`，且要求 `target.hp > 0`。
6. `game/status.py`：新增 `extend_poison(source, duration) -> bool`。
7. `game/combat.py`：
   - `AttackRuntime.hit_targets` 改为按 `event["hit_group"]` 分组（默认 `"default"`，现有攻击不变）。
   - `attack_damage(..., target=None)` 支持 `bonus_target_max_hp_pct`（Q 的 8%）；`resolve_hit` 额外支持 `bonus_vs_poison_max_hp_pct`（E 第一段的 15%，target 已存在）。保持现有调用兼容。
8. `game/projectile.py`：新增 `ShurikenProjectile`（或扩展 `AimedProjectile` 的 kind/visual branch），支持旋转绘制、block 碰撞、毒版贴图，并携带 `extends_poison` 字段。
9. `game/scene.py`：新增 `rhea_shuriken` / `rhea_poison_shuriken` 分支；cast/impact FX 用钢色/毒色；不要影响现有 projectile。
10. `game/roster.py`：import/注册 `Rhea`。
11. `game/config.py`：`REQUIRED_STATS` + `rhea`；`REQUIRED_ATTACKS` + 四个 attack；`REQUIRED_RHEA_CLIPS`；`ROSTER_CLASSES`/`PLAYABLE_CLASSES`/`ANIMATED_CLASSES` + `rhea`；`PROJECTILE_KINDS` + 手里剑 kind；stats/clips/frame_size/pivot 校验。
12. `game/hud.py` / `game/debug.py`：Q/E 已通用，通常不需要改；如果加 `POISON EXT` 计数，再补。
13. `main.py`：新增 Rhea smoke phase；更新 `[`/`]` 断言；加 `rhea_missing_frames=0` 并加入最终 conjunction。

### 8.3 素材

1. 从 `Image/Character/rhea-thorn-256.png` 生成 right-facing side base；遵守 `docs/IMAGE_GENERATION_RULES.md`；base 候选 contact sheet → 用户批准。
2. 按 §5.5 生成动作帧；每套 contact sheet 审批；不重画已批准帧。
3. 手里剑：普通钢色旋转帧 + 毒版绿/紫涂层帧；程序化像素贴图，contact sheet 审批后放 `assets/frames/rhea/fx/`。
4. 导入路径：`assets/generated/staged/rhea/<action>/` → 批准后复制到 `assets/frames/rhea/<action>/`。
5. 不要在角色帧里烘焙手里剑飞行、毒雾或命中特效；这些走 `game/projectile.py` / `game/fx.py`。

---

## 9. 验收

### 9.1 smoke flags（已实现）

- `rhea_present`、`rhea_roster_order_ok`、`rhea_default_ok`：名字/HP 100/ATK 20/stats、顺序
  Lina→Nyra→Rhea、默认 Lina/Creepy 不变。
- `rhea_knockback_ok`：LMB 60；RMB/Q/E 零击退。
- `rhea_lmb_ok`：LMB 20；`rhea_slash_r → l → r` 交替；RMB/Q/E 不影响；LMB 击退实际生效。
- `rhea_passive_ok`：已有 `rhea_poison` +1s；同攻击每目标一次；无上限；无毒不创建；Veno 毒不受影响；实际 LMB 延长。
- `rhea_rmb_ok`：RMB 24；钢星 kind/visual_kind、中 lane y=500、850/900/12；cast/impact FX；命中 +1s。
- `rhea_q_ok` / `rhea_q_300_ok` / `rhea_q_dummy_ok`：Q 初始 40/48/104；毒 6/9/30 dps、5.0s、10 跳；200 HP 总 70（毒 30）；Q 不触发 +1；F2 `poison[rhea_poison]`。
- `rhea_q_dr_ok`：50% 减伤初始 20（200 HP）、毒总 30、dps 6。
- `rhea_q_stack_ok`：2s 同源 Q → 7.0s；异源 Veno + Rhea 两实例独立。
- `rhea_q_kill_ok`：Q 初始击杀不上毒且 WIN。
- `rhea_close_range_ok` / `rhea_range_ok`：贴身（敌人身后 10px）RMB 24、Q 104+毒；玩家 300 / 敌人 1100 仍命中；两 attack 数据 range 900。
- `rhea_dash_ok`：14+14、去程 ~594px、回 `cast_x`、穿敌、`push_apart`、e_cd >13、facing 不变。
- `rhea_e_poison_ok` / `rhea_e_poison_300_ok`：200 HP 58；300 HP 73；首段 15% 只一次。
- `rhea_e_dr_ok`：E 中毒 +50% DR 200 HP 29、300 HP 36.5。
- `rhea_e_armor_ok`：0.0–1.00s 全程霸体、伤害照常、状态/位置不被打断。
- `rhea_e_block_ok` / `rhea_projectile_block_ok`：E 被墙/block 截断；RMB/Q 被 block 吸收。
- `rhea_cleanup_ok`：reset 后 projectile、毒实例、Q/E 冷却清空。
- `rhea_climb_ok`：Rhea 背视 climb、2 帧、1.1×。
- `rhea_missing_frames == 0`、`rhea_fx_missing == 0`。
- `rhea_switch_ai_off_ok`、`default_hit_group_ok`（Nyra 多段仍只命中一次）。

### 9.2 手动检查

- `[` / `]` 切到 Rhea，F2 显示 `CHAR rhea 3/3`、Q/E 冷却、目标 `poison[rhea_poison]` 剩余时间。
- F1 看 LMB/RMB/Q/E 判定框；E 去程/回程框与角色位置一致。
- 对 Warrior（300 HP）走完整循环：Q → 毒 tick → LMB/RMB 延长 → E 第一段吃 15% → 毒结束；用 F6 慢放核对 0.5s 跳。
- 对 Dummy 测无 AI 的纯伤害；对 Creepy/Veno 测多来源毒伤/场景交互。
- `Purity Seal` / `Sacred Shield` 在战斗中验证毒伤清除/免疫（若本轮接入道具）。
- 切换角色/F9/F5 后毒实例和手里剑清理干净。
- 素材：base → 每个动作 contact sheet → 游戏内预览，逐级审批。

---

## 10. 禁止做的事

- 不要修改 `instruction.docx`、`Image/`、`UI Resources/`、其他角色/敌人的数值/AI/冷却。
- 不要把 Rhea 的被动实现成“每次普攻自动上 1s 毒”；先检查已有毒。
- 不要用 `add_poison` 做被动延长；必须只在已有实例上 `extend_poison`。
- 不要用 `combat.poison_dps_pct`（0.02）做 Rhea 毒伤；用事件里的 0.03。
- 不要让 Q 的 8% 或 E 的 15% 绕过 `take_hit` 的减伤/命中反馈；毒 tick 才走 `apply_dot`。
- 不要让 E 去程命中后回程打不到同一目标（加 `hit_group` 或自定义两段）。
- 不要在没有用户确认时改默认角色/默认敌人；不要为了 Rhea 改 `debug.json` 的默认阵容。
- 不要逐帧缩放/拉伸人物适配画布；不要把 FX 烘焙进角色帧。
- 不要用 pytest、不要写日志文件；不要 commit，除非用户明确要求。
- 不要在未确认设计前更新 README/DESIGN/DEBUG/ASSET_PIPELINE；实现并验证后按 `AGENTS.md` 问一次是否写文档。

---

## 11. 快速文件索引

| 用途 | 路径 |
|---|---|
| 权威规格 | `instruction.docx`（战斗系统 / Rhea / 毒伤） |
| 可玩角色模板 | `game/nyra.py`、`game/lina.py` |
| 毒伤状态 | `game/status.py`（`StatusSet`、`POISON_TICK`、`describe`） |
| 毒伤先例 | `game/veno.py`（`poison_source`、`on_projectile_hit`） |
| 命中管线 | `game/combat.py`（`resolve_hit`、`resolve_projectile_hit`、`AttackRuntime`） |
| 弹体 | `game/projectile.py`（`AimedProjectile`、`SonicWave`、Creepy bullets） |
| 场景/弹体构造 | `game/scene.py`（`spawn_projectile_from_event`、`_poison_tint`） |
| 数据 | `game/data/stats.json`、`attacks.json`、`animations.json`、`roster.json`、`debug.json` |
| 配置校验 | `game/config.py`（`REQUIRED_*`、`PLAYABLE_CLASSES`、`PROJECTILE_KINDS`） |
| 构造注册 | `game/roster.py`（`FIGHTER_CLASSES`） |
| HUD/F2 | `game/hud.py`、`game/debug.py` |
| smoke | `main.py`（`_smoke_test`、角色循环断言、最终 conjunction） |
| 素材规则 | `docs/IMAGE_GENERATION_RULES.md`、`docs/ASSET_PIPELINE.md` |
| 通用角色接入 | `docs/NEXT_SESSION_CHARACTERS.md` |
| canonical 图 | `Image/Character/rhea-thorn-256.png` |
| 运行时帧目标 | `assets/frames/rhea/<action>/` + `assets/frames/rhea/fx/` |

---

## 12. Definition of Done

- [x] 用户确认了 Q1–Q12，§7 已填。
- [x] Rhea 能被 `[` / `]` 选中；默认角色/敌人未被意外改变。
- [x] LMB 左右交替、RMB 手里剑、Q 毒手里剑、E 去程/折返全部符合 §7。
- [x] 毒伤同源延长、异源独立、0.5s 结算、5s/3% 全部通过 smoke。
- [x] 被动只在已有 Rhea 毒上 +1s；无毒时不创建。
- [x] E 两段各命中一次，第一段毒伤额外 15% 只触发一次。
- [x] `rhea_missing_frames=0`、`rhea_fx_missing=0`，`main.py --smoke-test` exit 0。
- [x] 素材 base、每个动作、手里剑 contact sheet 均经用户批准。
- [x] 用户在 2026-11-01 明确要求“将所有改动写入文档”，README/DESIGN/DEBUG/ASSET_PIPELINE
  及本文件已同步。

---

## 13. 实现结果（2026-11-01）

- 代码：`game/rhea.py`（`Rhea(Fighter)`）；`game/status.py`（`extend_poison`）；
  `game/combat.py`（`hit_group`、`bonus_vs_poison_max_hp_pct`、projectile max-HP bonus）；
  `game/projectile.py`（`ShurikenProjectile`、close-range body check）；`game/scene.py`
  （shuriken branches + cast/impact FX）；`game/roster.py` / `game/config.py` / `game/data/*.json`。
- 素材：`assets/frames/rhea/` 33 帧 + `assets/frames/rhea/fx/` 6 张 64×64；审批过的 base 为
  `rhea_side_base.png` / `rhea_back_base.png`。
- 验证：`main.py --smoke-test` exit 0；全部 Rhea flags True；`rhea_missing_frames=0`、
  `rhea_fx_missing=0`、`default_hit_group_ok=True`。
- 后续用户微调：LMB 击退 60；RMB/Q range 900 + 贴身判定；E 距离 2× / 1.00s / 全程霸体；
  梯上受击/跳跃/提前上平台规则；Creepy 场景删除左 barrier。详见 §7 表后的“实现后的用户微调”。
- 文档状态：`README.md`、`docs/DESIGN_DECISIONS.md`、`docs/DEBUG.md`、
  `docs/ASSET_PIPELINE.md`、`docs/NEXT_SESSION_CREEPY_SHOOTER.md`、`docs/NEXT_SESSION_SCENE.md`
  已同步本轮改动。
