# Next Session — Creepy Shooter 设计与接入

> 日期：2026-10-28（2026-10-29 设计确认；2026-10-30 实现与文档完成）
> 状态：**已实现并验证**。素材、数据、代码、smoke 与文档均已完成；`main.py --smoke-test` → exit 0。
> 基线：`.venv/Scripts/python.exe main.py --smoke-test` → exit 0（2026-10-30，全部 `creepy_*` flags True）。
> 阅读顺序：本文 → `instruction.docx` 的 Creepy Shooter 段 → `AGENTS.md` → `README.md` → `docs/DESIGN_DECISIONS.md` → `docs/DEBUG.md` → `docs/ASSET_PIPELINE.md` → `docs/IMAGE_GENERATION_RULES.md`。
>
> **重要**：`instruction.docx` 已于 2026-10-29 更新为 HP 200 / ATK 20 / 四技能 / 专属场景 / AI，是权威规格。§3 的三技能草案与 §4 的 Q1–Q10 均已完成并作废；最终实现值见 §6。

---

## 0. 历史开场 prompt（已完成，仅存档）

```text
先阅读 docs/NEXT_SESSION_CREEPY_SHOOTER.md、instruction.docx 的 Creepy Shooter 段、AGENTS.md、README.md、
docs/DESIGN_DECISIONS.md、docs/DEBUG.md、docs/ASSET_PIPELINE.md、docs/IMAGE_GENERATION_RULES.md，
以及 game/roster.py、game/config.py、game/scene.py、game/projectile.py、game/warrior.py、game/veno.py、game/bat.py、
game/data/stats.json、game/data/attacks.json、game/data/animations.json、game/data/roster.json、game/data/debug.json、main.py 的 smoke。

本轮先完成 Creepy Shooter 的“设计与决策”，不要先改代码或生成素材：
1) 先运行 .venv/Scripts/python.exe main.py --smoke-test，确认 exit 0；
2) 按本文 §4 的 Q1–Q10 一次性 grill 我，每项给出当前状态、建议值和影响范围；
3) 我确认后，先把答案写回本文的“已确认决策”区，再按 §5 阶段实施；
4) 每个素材阶段先出 base/contact sheet 等我批准；每完成一个代码阶段跑一次 smoke。

不要修改 instruction.docx、Image/、UI Resources/ 或其他敌人的数值/AI；不要 commit，除非我明确要求。
不要用 pytest；验证用 --smoke-test、F1/F2 和预览图。
```

---

## 1. instruction 当前原文（2026-10-28 提取）

> Creepy Shooter  
> 形象：Image\Enemy\creepy-shooter-256.png  
> 技能1：射出水平子弹（远程，中），造成伤害  
> 技能2：射出锁定子弹（锁定子弹会自己调整方向，命中character）（可穿透block），造成伤害，无法躲避  
> 技能3：敌人接近时释放。起始为蹲姿，向后翻滚一小段距离，同时发出子弹（远程，中），击中character造成伤害。

### 1.1 明确的事实

| 项 | instruction 信息 | 当前项目状态 |
|---|---|---|
| 形象 | `Image/Enemy/creepy-shooter-256.png` | 只读 canonical 图存在；没有运行时帧 |
| 技能 1 | 水平子弹、远程、中 lane、造成伤害 | 无 Creepy Shooter 实现 |
| 技能 2 | 锁定/自动修正方向、命中 character、穿透 block、无法躲避 | 无 homing projectile 实现 |
| 技能 3 | 近距离触发、蹲姿、向后翻滚、同时/随后发出中 lane 子弹 | 无 roll 动作或位移实现 |
| HP / ATK | **没有写** | 需要设计 |
| 伤害倍率 / 冷却 | **没有写** | 需要设计 |
| 数量 / spawn / AI | **没有写** | 需要设计 |
| 画布 / pivot / 帧数 | **没有写** | 需要设计 |

### 1.2 形象要点（从 canonical 图提取）

- 兜帽狙击手/枪手；黑/深青色兜帽与面罩，露出的眼睛/发光青色细节。
- 深色分层战斗外套、破损斗篷/围巾、腰带/弹药袋、护膝、厚重靴子；青色边缘/发光装饰。
- **一把长步枪**，双手持握：右手扳机、左手托枪；有瞄准镜/枪口细节。
- 侧视战斗帧必须保持同一把枪、同一握姿；枪口方向和枪身比例固定，不能出现第二把枪或枪穿身体。
- 没有指定被动；不要自行加入被动。

### 1.3 现有资源

- 形象：`Image/Enemy/creepy-shooter-256.png`（只读）。
- BGM：`Sound Clip/BGM/creepy_shooter_battle_music.ogg` 已存在。
- 动作音效：**没有** Creepy Shooter 专用 action clips；本轮不处理音频，除非你明确要求。
- 动画 base/帧：**没有**；需要按素材审批流程生成。
- 运行时帧目录：建议 `assets/frames/creepy_shooter/`；不要直接读 `Image/`。

---

## 2. 当前架构（下一 session 的落点）

- 构造：`game/roster.py` 的 `FIGHTER_CLASSES`；数据来自 `roster.json`。
- 数值/攻击：`game/data/stats.json`、`attacks.json`；动画 clip：`animations.json`。
- 敌人 AI 参考：`game/warrior.py`（地面追击/跳跃/远程），`game/veno.py`（地面/远程/状态），`game/bat.py`（飞行/投射物）。
- 投射物：`game/projectile.py` + `game/scene.py::spawn_projectile_from_event`；当前 `PROJECTILE_KINDS` 为
  `q_wave, axe, sword_wave, venom_glob, web_bolt, sonic_wave`，没有直线/homing bullet。
- 场景：`game/scene.py` 通过 roster 构造敌人；`debug.json` 的 `<enemy>_spawn` 提供出生点。
- 配置校验：`game/config.py` 的 `ROSTER_CLASSES`、`ANIMATED_CLASSES`、
  `REQUIRED_*_CLIPS`、`PROJECTILE_KINDS` 和 JSON 校验。
- 调试：F7 切换敌人；V/C/X/Z 触发四个 skill slot；F1 看 hitbox/hurtbox；F2 看状态/冷却/帧。
- 当前没有 `creepy_shooter` 类、stats、attacks、clips、roster 条目或帧。

### 2.1 建议的命名（未确认）

| 项 | 建议值 |
|---|---|
| roster id / class / stats | `creepy_shooter` |
| Python 类 | `game/creepy_shooter.py::CreepyShooter` |
| clips key | `creepy_shooter_clips` |
| frame size / pivot key | `creepy_shooter_frame_size` / `creepy_shooter_pivot` |
| frames dir | `creepy_shooter` |
| spawn key | `creepy_shooter_spawn` |
| runtime frames | `assets/frames/creepy_shooter/` |
| fallback | `Image/Enemy/creepy-shooter-256.png` |
| projectile kinds | `creepy_bullet`, `creepy_homing_bullet` |

---

## 3. 建议的 draft design（已作废）

> **2026-10-29 更新**：instruction.docx 已更新为 HP 200 / ATK 20 / 四技能 / 专属场景 / AI；
> 本节的三技能、HP 180、19 帧等草案全部作废，以 §6 为准。

以下数值是为了让设计讨论有具体起点，**不是 instruction 的权威值**。

### 3.1 基础属性与体积

| 项 | Draft | 理由/备注 |
|---|---:|---|
| HP | 180 | 远程精英，介于 Warrior 300 与 Veno/Bat 50 之间 |
| basic_atk | 20 | 与 Lina/Warrior 同基准，便于伤害对比 |
| extra_atk | 0 | 与其他敌人一致 |
| 画布 | 384×384 | 与 Warrior/Bat/Nyra 同一档，容纳步枪 |
| pivot | (192,372) | 脚底中心，沿用 384 画布 |
| 身体高度 | ~230px | Warrior 同档；如 canonical 比例不合适再校准 |
| hurtbox | 70×230 | 比 Warrior 窄，符合狙击手体型 |
| stage_body_width | 90 | 地面移动/墙 clamp 用；不要和 hurtbox 混淆 |
| 数量 | 1 | instruction 没写 n；先用单只验证 AI/弹体 |
| spawn | x=600, ground | 与现有敌人基准 spawn 一致 |

### 3.2 技能草案与 skill slots

| 槽位 | attack_id | 草案 | 伤害（atk=20） | 冷却 | 关键规则 |
|---|---|---|---:|---:|---|
| V / 1 | `creepy_shot` | 水平中 lane 子弹 | 1.0×atk = 20 | 3.0s | 直线、固定水平方向；默认被 block 挡住 |
| C / 2 | `creepy_homing_shot` | 锁定子弹 | 1.2×atk = 24 | 8.0s | 自动修正方向；穿透 block；每目标最多一次；需要“无法躲避”的公平性定义 |
| X / 3 | `creepy_roll_shot` | 近距离后滚 + 开枪 | 1.0×atk = 20 | 6.0s | 触发距离建议 ≤180px；后滚约 140px/0.28s；后滚中/结束时发出中 lane 子弹 |
| Z / 4 | `null` | no-op | — | — | F2 显示 `-` |

**重要设计冲突（Q4）：** instruction 同时写了“锁定、自动调整方向、可穿透 block、无法躲避”。
如果字面实现为无限追踪，玩家可能没有任何反制；如果加入 lifetime/turn rate/可被地形阻挡，虽然更可玩，
但“无法躲避”就需要重新解释。不要在未确认前自行选择。

### 3.3 AI 草案

- 地面远程敌人，不飞行；默认保持 **standoff ≈ 260–320px**。
- 远距离优先 `creepy_homing_shot`；中距离优先 `creepy_shot`；玩家进入 ≤180px 时优先
  `creepy_roll_shot`。
- 只在冷却完成且目标存活时出手；每个 skill slot 独立冷却。
- 不主动加入跳平台/绕后/近战连招；Creepy Shooter 没有近战规格。
- 是否需要：面对 block 时自动换位、是否允许跳上 platform、是否在玩家上平台后停火——Q6。
- F8 关闭 AI；F7 切换到 Creepy Shooter 时整场重置并保持 AI 关闭（沿用现有沙盒约定）。

### 3.4 动画草案

建议源/运行时同画布：**384×384，pivot (192,372)**；右向 3/4 侧视，运行时按 facing 镜像。
先出 approved side base，再生成动作帧；不要直接用 canonical 图当战斗帧。

| clip | 建议帧数 | 用途 |
|---|---:|---|
| `idle` | 2 | 持枪待机，轻微呼吸/枪口姿态 |
| `walk` | 2 或 4 | 保持瞄准/持枪移动 |
| `jump` | 2 | 受击/被击飞时使用；不需要主动跳跃 AI |
| `hurt` | 1 或 2 | 受击 |
| `ko` | 2 | 倒地 |
| `creepy_shot` | 2 | 水平射击，枪口稳定，后坐力 |
| `creepy_homing_shot` | 3 | 锁定/瞄准/发射；枪口可发出青色锁定光 |
| `creepy_roll_shot` | 4 | 蹲姿 → 向后翻滚 → 起身/开枪；翻滚不能穿墙/block |

- 枪口 origin、枪身长度、双手握姿和身体比例必须在 base 阶段锁定；不要在每帧重新适配画布。
- 所有帧 384×384 RGBA；建议先导入 `assets/generated/staged/creepy_shooter/`，contact sheet 审批后再复制到
  `assets/frames/creepy_shooter/`。
- 生成前必须读 `docs/IMAGE_GENERATION_RULES.md`；重点：双手握枪、枪/身体不互穿、同一把枪、身体/头比例锁定、
  右向侧视、透明背景、无阴影/文字/边框/场景。
- 需要用户批准的顺序：**base → 动作帧 contact sheet → 游戏内预览**；不得跳过。

### 3.5 投射物与 VFX 草案

建议新增两种 kind，避免把 Creepy Shooter 硬塞进 Veno 的 `venom_glob` 分支：

| kind | 行为 | 建议实现 |
|---|---|---|
| `creepy_bullet` | 水平、固定方向、中 lane；默认与 block 碰撞 | 可复用 `AimedProjectile` 的直线移动/命中，新增视觉 kind；或轻量 `BulletProjectile` |
| `creepy_homing_bullet` | 锁定目标并缓慢转向；穿透 block；每目标最多命中一次 | 新 `HomingProjectile`：按 turn rate 调整方向，lifetime/range 上限，命中即消失 |

- `config.PROJECTILE_KINDS` 增加两个 kind；`scene.spawn_projectile_from_event` 增加构造分支。
- `attacks.json` 的 projectile 事件提供 `origin_forward` / `origin_height` / `speed` / `range` /
  `hitbox_radius` / `penetrates_blocks`；枪口位置在帧/base 完成后实测校准。
- `game/fx.py` 增加青色曳光/锁定环/命中特效；不要把弹体或枪口火光烘焙进角色帧。
- 水平子弹默认应被 block 挡住；homing 子弹按 instruction 穿透 block。两者都要在 smoke 中分别验证。
- 不处理 Creepy Shooter 专用 action audio；BGM 已存在，但当前音频接入不在本轮范围。

### 3.6 数据/代码接入清单（确认后）

1. `game/data/stats.json`：`creepy_shooter` 的 hp/atk/move/cooldowns/hurtbox/stage_body_width/ai。
2. `game/data/attacks.json`：三个 attack_id、伤害倍率、duration、hitstun/hitstop/knockback、projectile events。
3. `game/data/animations.json`：`creepy_shooter_clips`、`creepy_shooter_frame_size`、`creepy_shooter_pivot`。
4. `game/data/roster.json`：enemies.creepy_shooter（class/stats/spawn/clips/frame_size/pivot/frames_dir/fallback/
   skill_slots/separates/decides_match；是否 count 见 Q2）。
5. `game/data/debug.json`：`creepy_shooter_spawn`；F7 顺序建议放在 Bat 后、Dummy 前（Q2）。
6. `game/config.py`：`REQUIRED_CREEPY_SHOOTER_CLIPS`、`ROSTER_CLASSES`、`ANIMATED_CLASSES`、
   `REQUIRED_STAGE`、`PROJECTILE_KINDS` 和 JSON 校验。
7. `game/roster.py`：import/注册 `CreepyShooter`。
8. `game/creepy_shooter.py`：AI、三个技能、roll 位移、冷却、hurt/KO、reset、`force_attack`、`skill_remaining`。
9. `game/projectile.py`：直线/homing 弹体；命中、block、穿透、cleanup。
10. `game/scene.py`：projectile spawn 分支、AI/敌人切换、F2 所需字段（如无特殊 mode 可复用通用行）。
11. `main.py`：smoke 检查与 flags；现有 `missing_frames`/roster 检查。
12. 最后才更新 README/DESIGN/DEBUG/ASSET_PIPELINE；且按项目规则先问用户是否写文档。

### 3.7 建议 smoke flags

| flag | 验证内容 |
|---|---|
| `creepy_present` | roster 能构造、F7 能选中、fallback 不崩 |
| `creepy_shot_ok` | 技能 1 命中、伤害、冷却 |
| `creepy_homing_ok` | 锁定/转向、穿透 block、每目标最多一次、冷却 |
| `creepy_roll_ok` | 近距离触发、后滚距离、墙/block 不穿透、射击伤害、冷却 |
| `creepy_slots_ok` | V/C/X/Z 槽位与空槽 no-op；F2 显示 |
| `creepy_missing_frames` | 所有 clip 文件存在 |
| `creepy_win_ok` | KO 后可正常 WIN/重开 |
| `creepy_cleanup_ok` | 弹体命中/超时/换场后不泄漏 |

F1 手动检查：中 lane 弹体、homing 轨迹、roll 位移、hurtbox/stage body、block 阻挡/穿透。
F2 手动检查：三个技能冷却、当前 attack/clip/frame、AI 开关、目标距离/冷却。

---

## 4. 开工前必须 grill 的问题（Q1–Q10，已完成，见 §6）

> 本节仅存档当时的提问与建议；最终答案已写入 §6，数值以 §6 为准。

### ❓ Q1 — HP / ATK 基准

instruction 没有写 HP/ATK。建议 **HP 180、basic_atk 20、extra_atk 0**，作为远程精英；
如果你希望更脆/更肉，给出 HP 和 ATK。

➡️ 推荐：**HP 180 / ATK 20 / extra 0**；先按 20 计算三条技能伤害。

### ❓ Q2 — 数量、spawn、F7 顺序

instruction 没写 `n`。建议 **count: 1**，spawn x=600，F7 顺序
`Warrior → Veno ×3 → Bat ×5 → Creepy Shooter → Dummy`；默认敌人仍是 Warrior。

➡️ 推荐：单只；F7 放在 Bat 后、Dummy 前；不改默认敌人。

### ❓ Q3 — 技能 1 的伤害/冷却/弹速/阻挡

建议 **1.0×atk=20、冷却 3.0s、speed 760、range 720、mid lane、radius 12**；
**默认被 block 挡住**（instruction 只对技能 2 写了穿透 block）。

➡️ 推荐：20 / 3.0s / 直线 / 被 block 挡住；如果希望更高频，最低不要低于 2.5s。

### ❓ Q4 — 技能 2 “无法躲避”的准确语义

这是最重要的设计决定。锁定弹如果无限追踪，就没有反制；但 instruction 明确写“无法躲避、穿透 block”。
可选方案：

- **A. 字面强追踪**：高转向率、长 lifetime，直到命中；不可被地形挡住；只受冷却限制。
- **B. 可玩性强追踪**：有限 lifetime/turn rate，玩家可以用 dash/无敌帧/距离甩掉；仍穿透 block。
- **C. 折中**：锁定后强制命中一次，但可被 KO/受击/场景换场清除，或只在屏幕内追踪。

➡️ 推荐：**C** 的折中先做——锁定后高转向率、穿透 block、每目标最多一次，但给 projectile 一个
lifetime 和“施法者被 KO/受击时中断”的规则；具体数值在 Q4 确认。不要直接做无限追踪。

### ❓ Q5 — 技能 3 的翻滚规则

instruction 只写“近距离、蹲姿、向后翻滚、发出子弹”。需要确认：

- 触发距离：建议 ≤180px。
- 后滚距离/时间：建议 140px / 0.28s；方向为远离目标；遇到墙/block 停止。
- 是否有 i-frames：建议 **无 i-frames**（instruction 没写霸体/无敌）；如果要翻滚躲伤害，需明确持续时间。
- 开枪时机：建议在 roll 结束/接近结束时 t≈0.22s 发出，mid lane，1.0×atk=20，冷却 6.0s。
- 是否能在空中/受击中触发：建议仅地面、非受击/非 KO、非攻击中。

➡️ 推荐：180px 触发；140px/0.28s；无 i-frames；t≈0.22s 开枪；20 伤害；6.0s 冷却；墙/block 阻挡。

### ❓ Q6 — AI 距离、优先级、blocks

建议：standoff 260–320px；远距离 homing → 中距离 straight → 近距离 roll-shot；
不主动跳平台、不做近战；AI 关闭时保持 idle。是否允许它 walk 调整距离？
是否在玩家上 platform 后只换位/停火？是否在 block 后自动绕行？

➡️ 推荐：允许地面 walk 调整；不跳平台；不做 block 绕行 AI；玩家上平台时保持距离并继续用
homing（如果 Q4 允许）；这些都可后续再增强。

### ❓ Q7 — 画布/pivot/hurtbox/身体高度

建议 **384×384 / pivot (192,372) / body ~230 / hurtbox 70×230 / stage_body_width 90**。
也可以选择 214px 身体（与 Nyra 同档）或 200px；先看 canonical 比例和步枪完整度。

➡️ 推荐：384 / 192,372 / body 230 / hurtbox 70×230；如果步枪/兜帽导致画布溢出，优先扩画布或调
base 构图，不要缩小人物。

### ❓ Q8 — 帧数与审批

建议最小集：idle 2、walk 2、jump 2、hurt 2、ko 2、`creepy_shot` 2、`creepy_homing_shot` 3、
`creepy_roll_shot` 4，共 19 帧；如果 roll 需要更清晰，扩展到 5 帧。
必须按 **base → 帧 contact sheet → 游戏内预览** 逐级审批；不要一次生成全部后直接接入。

➡️ 推荐：先 19 帧最小集；每套 contact sheet 审批后再导入；不重画已批准帧。

### ❓ Q9 — 枪口锚点与弹体 VFX

枪口 origin 应在 base/帧完成后用像素测量，写入 `origin_forward`/`origin_height`；
不要在代码里硬编码一个和帧不符的偏移。Skill 1 建议青色短曳光；Skill 2 建议青色锁定环/缓慢追踪光球；
命中特效与枪口光不能烘焙进角色帧。

➡️ 推荐：先做程序化弹体/曳光，帧内只保留枪口姿态；命中/施法 FX 在 `game/fx.py`。

### ❓ Q10 — 本轮范围与文档

本轮是否只做“设计与决策”，还是同时完成 base/帧和代码？
建议顺序：Q1–Q10 确认 → base → 帧审批 → 数据/代码 → smoke/F1/F2 → 最后问是否写文档。

➡️ 推荐：**本轮先设计确认，再做素材/实现**；素材每阶段停下审批；文档等用户明确同意后再写。

---

## 5. 实施阶段（已完成）

### 阶段 A — 数据与命名

- 固定 id/class/stats/clips/spawn 名称。
- 先加 stats/attacks/animations/roster/debug/config 的空壳或在最终值确认后一次加。
- 运行 smoke，确认新 roster 条目不会让现有敌人回归。

### 阶段 B — 素材

1. 从 `Image/Enemy/creepy-shooter-256.png` 生成 right-facing side base；遵守
   `docs/IMAGE_GENERATION_RULES.md` 的双手握枪/比例/透明/无场景规则。
2. base 候选 contact sheet → 用户批准。
3. 生成 idle/walk/jump/hurt/KO + 三个技能帧；contact sheet → 用户批准。
4. 导入 `assets/frames/creepy_shooter/`；不要逐帧自动缩放，先看 `--body-height` 校准。

### 阶段 C — 代码/弹体

- `game/creepy_shooter.py`：AI/技能/roll/冷却/F8/reset。
- `game/projectile.py`：直线/homing 弹体；穿透/阻挡/命中一次/cleanup。
- `game/scene.py`：spawn/命中 FX；`game/config.py` + `roster.py` 注册。
- `game/data/*.json` 最终数值。

### 阶段 D — 验证

- `main.py --smoke-test` exit 0；新增 flags 全 True；现有 flags 不回归。
- F7 切换、F8 AI、V/C/X/Z、F1/F2、F9/F5。
- 游戏内预览：中 lane 命中、homing 追踪/穿透、roll 不穿墙、KO/WIN。

### 阶段 E — 文档

- 只有用户明确同意后，更新 README / DESIGN_DECISIONS / DEBUG / ASSET_PIPELINE。
- 不修改 `instruction.docx`；不 commit，除非用户要求。

---

## 6. 已确认决策（2026-10-29 确认；2026-10-30 实现）

> `instruction.docx` 已于 2026-10-29 更新：HP 200 / ATK 20 / 四个技能 / 专属场景 / AI。
> 本节优先于 §3 的草案；§3 的三技能、19 帧、HP 180 等内容作废。
>
> 已确认的完整实施计划见计划文件
> `C:\Users\litia\.claude\plans\docs-next-session-creepy-shooter-md-ses-temporal-sunbeam.md`。

| 问题 | 最终决定 |
|---|---|
| 规格来源 | `instruction.docx`（2026-10-29）为权威；§3 草案作废 |
| HP / ATK | 200 / 20 / extra 0 |
| 数量 / 默认 / F7 | count 1；启动默认 `creepy_shooter`；F7 = Warrior → Veno×3 → Bat×5 → Creepy Shooter → Dummy |
| 技能 1 `creepy_shot` | 1s CD；水平中 lane；1.5×atk = 30；被 block 挡住；0.45s，t=0.18；speed 980 / range 900 / radius 9；子弹从枪口 163px 高 / 129px 前生成（射击帧实测 `origin_height 163` / `origin_forward 129`），不再按 lane 高度出生 |
| 技能 2 `creepy_homing_shot` | 8s CD；1s 前摇可被受击/KO 打断（CD 仍生效）；前摇期间在玩家身上绘制用户自绘的 3 帧锁定准星（0.30/0.40/0.30s，128px）；发射后无限转向、穿透 block/platform、20 伤害、单次命中、8s 寿命、speed 520 / radius 14；1.55s，t=1.0；枪口 143/111 出生；发射后不再受施法者 KO 影响 |
| 技能 3 `creepy_roll_shot` | 10s CD；≤180px 触发；蹲姿 → 后滚 140px/0.28s（墙/block 截断；platform 边缘**不拦截**，滚出边缘会下落）、无 i-frames → t=0.30 中 lane 射击 → 蹲姿 → 站起；24 伤害；0.90s；speed 900 / range 700 / radius 9；枪口 120/100 |
| 技能 4 `creepy_jump_shot` | 10s CD；仅当 platform 可达且站在有效起跳点；自动选最近 platform（surface 220/268 两档跳高）、同一 `jump_shot` 动画；1.10s；约半身高 t=0.10 向下射击；24 伤害；下方 ±45° 锥内瞄准玩家，否则垂直向下；被 block 挡住；speed 900 / range 600 / radius 12；枪口 120/100；无 platform → `force_attack` 返回 False；最右地面起跳点 1136（long platform 右移后可跳） |
| AI | 近 ≤180 用技能 3；远 ≥320 用技能 1；180–320 用技能 1；直线被 block/platform 挡住或高度差 >60px 用技能 2；技能 2 只在被挡/换层/技能 1 未就绪时使用；被打到地面 → 走向最近 platform 起跳点，技能间隙用 4 回平台，期间用 1/2 攻击；地面 barrier 挡路用 hop（`jump_v×1.15` 垂直、`walk×2.0` 水平，可跨 90px barrier）；在 platform 上被逼近时后滚，滚出边缘会掉下去 |
| 弹道 | 严格水平、相对射手脚底的中 lane；技能 2 负责跨层与穿透 |
| 专属场景 | 镜像现有关卡的平台/梯子：long platform 右（surface 220，x 601–1080）、short platform 左（surface 268，x 170–484）、仅右侧 ground barrier x=790（左侧 x=400 已按用户要求于 2026-11-01 删除）、梯子同步镜像；不加额外掩体；Creepy 生成 long platform 右端 (1000, 220)；player (280, 620)，其余敌人 (600, 620)；选中该敌人时自动切换 stage variant，B 开关保留 |
| 画布 / 身体 | 384×384，pivot (192,372)；body 214；hurtbox 56×210 / 56×130（不含步枪）；stage_body_width 100 |
| 帧数 | 29：idle 2、walk 4、crouch 1、jump 2、hurt 2、ko 2、`creepy_shot` 2、`creepy_homing_shot` 4、`creepy_roll_shot` 6、`creepy_jump_shot` 4；roll 按 0.9×（body 193）导入 |
| 子弹贴图 | 普通弹青色曳光 2 帧（32×12）；锁定弹紫青弹体 3 帧（40×24），不再是锁定环；程序化像素贴图，接触表审批；枪口/命中 FX 走 `game/fx.py`；锁定准星使用用户自绘 `creepy_lock_fx_v4` 3 帧，按 128px NEAREST 安装 |
| 审批 | base → 动作接触表 → 游戏内预览；每阶段停下等用户确认 |
| 验证 | `--smoke-test` exit 0（全部 `creepy_*` flags True）+ F1/F2 + 游戏内预览 01–09 |
| 文档 | 已按用户确认更新 README / DESIGN_DECISIONS / DEBUG / ASSET_PIPELINE 与本文件的最终值（2026-10-30；2026-11-01 补充左 barrier 删除与梯上受击规则） |

> `creepy_roll_shot` 为 6 帧：crouch 0.14 / tuck 0.13 / 倒立紧蜷 0.13 / 双膝跪地前倾 0.10 / crouch-fire 0.18 / stand 0.22（总 0.90s）。
> 按 0.9×（`--body-height 193`）导入；最后站立帧约 211px，与 Lina（约 210px）同体格。此前的 1.10×/约 234px 尺寸例外已取消。

### 6.1 最终实现记录（2026-10-30）

- **代码**：`game/creepy_shooter.py::CreepyShooter`；`game/projectile.py` 新增 `CreepyBullet`、`CreepyHomingBullet`、`CreepyDownBullet`；`game/stage.py` 新增 `platform_top_at`、`segment_hits_blocks`；`game/scene.py` 按 `roster.json` 的 `stage_variant` 选择场景并在 `set_enemy` 时重建 Stage（保留 B 开关）。
- **数据**：`stats.json` 的 `creepy_shooter`；`attacks.json` 的四个 attack；`animations.json` 的 `creepy_shooter_frame_size`/`creepy_shooter_pivot`/`creepy_shooter_clips`；`roster.json` 的 Creepy 条目；`debug.json` 的 `stage_variants.creepy_shooter` 与 `default_enemy`。
- **场景变体**：long platform rect `[601,220,479,78]`（sprite `[601,206,479,96]`），short platform `[170,268,314,78]`（sprite `[170,254,314,96]`）；仅 right barrier `[790,560,90,60]`（left `[400,560,90,60]` 已于 2026-11-01 删除）；long ladder `[708,220,64,400]`（sprite `[676,220,128,400]`），short ladder `[295,268,64,352]`（sprite `[247,268,160,352]`）。
- **枪口锚点**：技能 1 为 163/129；技能 2/4 为 143/111 与 120/100；场景按 `attacker.x + direction*origin_forward`、`attacker.y - origin_height` 生成，弹体 y 不再走 `lane_y`。子弹贴图在 `assets/frames/creepy_shooter/fx/`（`creepy_bullet_00/01.png`、`creepy_homing_bullet_00/01/02.png`）。
- **锁定准星**：用户自绘 `assets/generated/contact_sheets/creepy_lock_fx_v4/creepy_lock_00..02.png`（724×724），以 NEAREST 缩放到 128×128 安装为 `assets/frames/creepy_shooter/fx/creepy_lock_00..02.png`；运行时按 0.30s / 0.70s 两个阈值切换大/小/大（对应 0.30/0.40/0.30s 三帧），绘制在目标胸口中心，仅视觉、不参与命中。`tools/generate_creepy_lock_fx.py` 的旧程序化版本仅保留作对照，运行时不再使用。
- **素材**：base 为 `assets/generated/base/creepy_shooter_side_base.png`；29 帧在 `assets/frames/creepy_shooter/`（idle/walk/crouch/jump/hurt/ko/`creepy_shot`/`creepy_homing_shot`/`creepy_roll_shot`/`creepy_jump_shot`）；接触表与游戏内预览在 `assets/generated/contact_sheets/`。
- **验证 flags**：`creepy_present`、`creepy_stage_ok`、`creepy_shot_ok`、`creepy_homing_ok`、`creepy_lock_ok`、`creepy_roll_ok`、`creepy_roll_edge`、`creepy_jump_ok`、`creepy_jump_long/short/right/none`、`creepy_ai_ok`、`creepy_ai_hop`、`creepy_slots_ok`、`creepy_win_ok`、`creepy_cleanup_ok`、`creepy_stage_switch_ok`、`creepy_ladder_hit_mid_ok`、`creepy_ladder_hit_platform_ok`、`creepy_ladder_hit_top_ok`、`creepy_ladder_hit_ok`、`creepy_missing_frames=0`、`creepy_fx_missing=0`。
- **已知取舍**：技能 1 严格水平，站 platform 上打不到地面玩家是有意设计，跨层交给技能 2；右侧地面 barrier（y 560–620）低于平地中 lane，所以平地 1/3 技能会从 barrier 上方飞过，test 用 `barrier.centery` 直接生成弹体验证阻挡；roll 无 i-frames；技能 2 的弹体在发射后不因施法者 KO 消失。2026-11-01 额外验证梯子受击：中段击落不横向推挤、脚底在 platform 内吸附到平台顶、顶端中弹落到平台。
- **2026-11-01 变更**：删除 Creepy 场景左侧 `[400,560,90,60]` barrier，仅保留右侧 `[790,560,90,60]`；同步更新 `debug.json` 与本文件。

---

## 7. 禁止做的事

- 不要修改 `instruction.docx`、`Image/`、`UI Resources/`、其他敌人的数值/AI/冷却。
- 不要把草案数值直接当最终值；没有确认前不要生成整套素材或提交代码。
- 不要用无限追踪 + 无 lifetime 的 homing 直接实现 Q4；先确认“无法躲避”的边界。
- 不要把 block 穿透加到技能 1；instruction 只对技能 2 写了穿透。
- 不要逐帧缩放/拉伸人物来适配画布；不要用平滑重采样修补比例错误。
- 不要直接读 `assets/generated/` 作为运行时素材；批准后复制到 `assets/frames/`。
- 不要 commit / git reset / git checkout -- . / git stash；不要用 pytest；不要写日志文件。
- 不要在没有确认时改 README/DESIGN/DEBUG；文档只在用户明确允许后更新。

---

## 8. 关键文件索引

- 规格：`instruction.docx`（Creepy Shooter 段）
- 构造/注册：`game/roster.py`、`game/config.py`
- 场景/弹体：`game/scene.py`、`game/projectile.py`、`game/fx.py`
- 敌人模板：`game/warrior.py`、`game/veno.py`、`game/bat.py`
- 数据：`game/data/stats.json`、`attacks.json`、`animations.json`、`roster.json`、`debug.json`
- smoke：`main.py`
- 素材规则：`docs/IMAGE_GENERATION_RULES.md`、`docs/ASSET_PIPELINE.md`
- canonical：`Image/Enemy/creepy-shooter-256.png`
- BGM：`Sound Clip/BGM/creepy_shooter_battle_music.ogg`
- 建议运行时目录：`assets/frames/creepy_shooter/`
