# Next Session — 场景搭建：Platform / Ladder / Barrier / Block

> 日期：2026-10-27
> 状态：**已完成**。最终实现与布局见下方“完成状态”；§0–§11 保留为开工前的计划与 grill 记录。
>
> **攀爬动画更新（2026-10-28）**：已批准并接入 Lina 普通、Lina 火焰和 Nyra 的背视两帧 climb
> （每帧 0.20s；上层 W 0→1、下层 S 1→0；停住保持当前帧；不水平翻转）。Lina 绘制缩放 1.2×，
> Nyra 1.1×；Nyra 的剑固定在背后。下文 §4/§6/§9/§11 中“walk/idle 占位、不新增动画”的记录已被
> 取代；当前规则以 README、`docs/DESIGN_DECISIONS.md` 的 “Climb animations” 和 `docs/DEBUG.md` 为准。
>
> **攀爬/场景更新（2026-11-01）**
> - Rhea 为第三个可玩角色，climb 两帧背视、双手空手、双手里剑收纳在腰后金条纹绑带；绘制缩放 1.1×。
> - 有顶平台的梯子改为“提前上平台”：脚底到 `platform.top + (platform.bottom - platform.top)/2 - 6`
>   即解除攀爬并吸附到平台顶；B 关闭或梯子无平台时仍保持旧的顶端停留。
> - 梯上受击立即退出攀爬并正常击落；脚底在 platform rect 内则吸附到平台顶；否则坠落。
>   新增 `ladder_fall`：梯上跳跃/被击落时跳过 platform 侧面与底面碰撞直到落地，避免被平台侧推；
>   平台顶落点仍有效。没有受击后的自动重抓。
> - Creepy Shooter 场景删除左侧 `[400,560,90,60]` barrier，仅保留右侧 `[790,560,90,60]`；
>   默认场景仍为左右两个 barrier。`penetrates_blocks` 也不再全为 false：Creepy 技能 2 为 true。
> - 新增 smoke：`ladder_mount_early_ok`、`ladder_jump_overlap_ok`、`creepy_ladder_hit_*`。

> **完成状态（2026-10-27）**
>
> 实际工作区为 `nyra-veno-sandbox`（`203cdf0`），不是 `main`；`instruction.docx` 没有 `UU` 冲突，
> 只有已暂存的修改（`M `）。完成内容：`blocks` 统一 `kind: barrier | platform`；platform 全 AABB
> （顶/侧/底 + B 开启/出生重叠时自动解嵌）；`ladders` 独立且无体积；Lina/Nyra/Rhea 共享攀爬
> （W 上、S 下、Space 跳离、Shift 只下蹲）；B/F1/F2 更新；`penetrates_blocks` 投射物标记
> （Creepy 技能 2 为 true，其余 false）；smoke 覆盖平台/梯子/出生点/穿透。
>
> 当前布局以 `game/data/debug.json` 为准：长平台 `[170,220,479,78]`（surface 220）、
> 短平台 `[796,268,314,78]`（surface 268）、长梯 `[508,220,64,400]`、中梯 `[921,268,64,352]`、
> 地面 barrier `[400,560,90,60]` / `[700,560,90,60]`、玩家出生 x=280、敌人出生 x=600、
> 默认敌人 Creepy Shooter。平台外侧边缘与墙留 80px，可自由走落（无落地伤害）；短梯完全在短平台下方，
> 短平台底部 346，Warrior 可在下方通行。
>
> 下文 §1/§4 的“main / UU 冲突 / 无 Bat”等记录已过时；§6 的 Q1–Q11 是当时的 grill 记录。
> 最终规则以 `docs/DESIGN_DECISIONS.md`（Stage props and climbing）和 `README.md` 为准。

---

## 0. 可直接复制的开场 prompt

```text
先阅读 docs/NEXT_SESSION_SCENE.md、instruction.docx 的“特殊场景及道具说明”段、
AGENTS.md、CODEX-README.md、game/stage.py、game/scene.py、game/input.py、game/lina.py、
game/warrior.py、game/projectile.py、game/config.py、game/debug.py、game/hud.py、
game/data/debug.json、docs/DESIGN_DECISIONS.md 的场景段、docs/DEBUG.md、PLAN.md 的场景段，
以及四张 platform/ladder 图。

本轮目标：新增 platform、ladder，重新归类 barrier/block；完成数据、碰撞、攀爬、渲染、F1/B 和 smoke。
先确认工作区：当前 git status 有 UU instruction.docx 和 506 个已暂存文件；先让我确认分支和冲突处理。
先运行 .venv/Scripts/python.exe main.py --smoke-test，确认基线。
不要直接改代码：先按本文 §6 的 Q1–Q11 grill 我，确认 taxonomy、platform 碰撞、W/攀爬和布局后再实现。

不要 commit；不要 git reset / git checkout -- . / git stash / git clean；
不要动 instruction.docx、Image/、UI Resources/、Sound Clip/、已暂存素材；
不要改其他角色/敌人/默认阵容；不要写 README/docs/手册，除非我明确允许。
```

---

## 1. 开工前必须确认的工作区状态

当前事实（2026-10-27）：

- 当前分支：`main`，HEAD `26db0cf`。
- `git status` 显示 `UU instruction.docx`（未解决的合并冲突），以及 **506 个已暂存文件**（`Sound Clip/`、shadow-ninja 素材、`UI Resources/`、`assets/generated/` 等）。
- Bat / Nyra / Veno 的代码与文档在 **`nyra-veno-sandbox`** 分支（`203cdf0`），**不在当前 main 工作树**。当前 main 只有 Lina / Warrior / Dummy。
- 四张 platform/ladder 图目前是 untracked：
  - `assets/generated/contact_sheets/platform_tropical_long.png`
  - `assets/generated/contact_sheets/platform_tropical_short.png`
  - `assets/generated/contact_sheets/ladder_tropical_wood.png`
  - `assets/generated/contact_sheets/ladder_tropical_wood_short.png`

开工顺序：

1. 先看 `git status`。如果 `instruction.docx` 仍是 `UU`，**停下来让用户解决冲突**；不要自行编辑或 `git add` 它。
2. 确认本轮是在 `main` 上做，还是先把 `nyra-veno-sandbox` 合并/切过去再 scene work。不要自行 merge/rebase。
3. 不要 commit、reset、checkout、stash、clean；已暂存素材必须保持原样。
4. 基线 smoke：

```bat
.venv/Scripts/python.exe main.py --smoke-test
```

---

## 2. 必读文件

### 权威设定

- `instruction.docx` — “特殊场景及道具说明”段（见 §3）；当前有冲突，先确保读的是解决后的版本。
- `AGENTS.md` — 素材与 `Image/` 规则。
- `CODEX-README.md` — Codex 的代码改动/素材约定（如使用 Codex）。

### 场景与碰撞

- `game/stage.py` — `Stage`、`blocks`、`move_x`、`move_fighter`、`body_half`、绘制。
- `game/scene.py` — `_can_stand`、`_step_x`、`_separate_fighters`、`handle_debug_key`（B）。
- `game/fighter.py` — hurtbox、`on_ground`、`stage_body_width`。
- `game/lina.py` + `game/input.py` — 任务开始时跳跃输入、W/Space 都映射到 `jump`；现已实现
  `climb_up`/`climb_down`/`climb_jump`，攀爬状态在 `Fighter`，动画规则见 README/DESIGN。
- `game/warrior.py` — `_block_ahead`（敌人对 block 的 AI）。
- `game/projectile.py` — QWave / AimedProjectile 等对 `stage.blocks` 的碰撞。
- `game/config.py` — `REQUIRED_STAGE`、数据校验。
- `main.py` — `--smoke-test` 的 block 相关检查（`block_lunge_ok`、`q_block_ok`、`blocks_toggle_ok`、`separation_block_ok`）。

### 数据与文档

- `game/data/debug.json` — `stage.blocks` 当前是两组 90×60 地面 block。
- `game/data/stats.json`、`game/data/roster.json` — 移动/跳跃/默认阵容；本轮不要改。
- `docs/DESIGN_DECISIONS.md` — Stage 与 block 碰撞规则。
- `docs/DEBUG.md` — F1/F2/B、smoke 说明。
- `PLAN.md` — 场景/block 的历史设计。
- `README.md` — 当前操作与 block 行为。

### 素材

- 四张 contact sheet（见 §1）；尺寸：

| 素材 | 尺寸 | 说明 |
|---|---:|---|
| `platform_tropical_long.png` | 799×160 | 长平台，RGBA 透明 |
| `platform_tropical_short.png` | 524×160 | 短平台，RGBA 透明 |
| `ladder_tropical_wood.png` | 160×448 | 长梯，RGBA 透明 |
| `ladder_tropical_wood_short.png` | 160×274 | 短梯，RGBA 透明 |

- `assets/backgrounds/island-arena-16x9.png` — 当前背景。

---

## 3. instruction.docx 的权威规则（场景段）

原文（2026-10-27 提取）：

> block类：（包括barrier和platform）  
> 除特殊说明，有碰撞箱和体积，角色和技能会正常碰到并产生反应。  
> Barrier：位置：地面或platform上  
> Platform: 图像见 assets\generated\contact_sheets\platform_tropical_long 和 platform_tropical_short  
> Ladder: 角色接近ladder, 按下W会向上攀爬，爬上platform. ladder默认无体积，不会遮挡任何的技能效果。  
> 图像见 assets\generated\contact_sheets\ladder_tropical_wood 和 ladder_tropical_wood_short

操作设定里：`W 向上攀爬`，`Space 向上跳跃`，`S / Shift 卧倒`。

需要保留的解释：

- `block` 是**类别**，至少包含 `barrier` 和 `platform`。
- `barrier` 是实体障碍，可放在地面或 platform 上。
- `ladder` **默认无体积**：不挡角色、不挡技能；只作为攀爬触发器。
- 平台/梯子图片目前是审批源图；运行时是否缩放、裁切、放哪个目录，需要本轮确认。

---

## 4. 当前代码现状

- `Stage.__init__` 读取 `debug.json.stage.blocks`，构造 `list[pygame.Rect]`。
- 当前只有两个地面 block：`[400,560,90,60]`、`[760,560,90,60]`。
- `Stage.move_x`：墙 + block 侧面（空中用 hurtbox 半宽；脚在 block 顶面以上时跳过）。
- `Stage.move_fighter`：重力、地面、block 顶面落地（`land_margin`）。
- `Stage.body_half` / `body_rect`：地面用 `stage_body_width`，空中用 hurtbox 宽。
- `scene._can_stand`、`_step_x`、`_separate_fighters` 都通过 `stage.blocks` 判断站立/分离。
- `warrior._block_ahead` 用 `stage.blocks` 判断前方障碍。
- `projectile.py` 的 QWave / AimedProjectile 用 `stage.blocks` 做 AABB 碰撞。
- `input.py`：任务开始时 `W` 和 `Space` 都映射到 `jump`；现已拆分 climb 动作。
- `lina._start_jump` 只在 `on_ground` 时起跳；攀爬状态现由 `FighterState.CLIMB` / `Fighter` 管理。
- `game/bat.py`、`game/nyra.py`、`game/veno.py` 在当前 main 不存在（在 `nyra-veno-sandbox`）。
- 没有任何 platform / ladder 的运行时数据、渲染或碰撞。

---

## 5. 本轮目标 / 非目标

### 目标

1. 数据层把场景实体分类：`barrier`、`platform`，以及独立的 `ladders`。
2. 当前两组地面 block 按新 taxonomy 重新归类（推荐成为 `barrier`）。
3. 新增 platform 的站立/落地/侧面规则（语义见 Q3）。
4. 新增 ladder：接近后 W 向上攀爬，爬上 platform；ladder 无体积，不挡技能。
5. 渲染 platform/ladder（用四张图），barrier 可继续用占位或素材。
6. F1 能看到 barrier/platform 碰撞框与 ladder 攀爬区；B 开关仍有效。
7. smoke 覆盖：platform 落地、barrier 阻挡、ladder 攀爬、ladder 不挡投射物、无回归。
8. 用四张图搭出第一版可玩场景；坐标可先按 §8 的建议再调。

### 非目标

- 不新增角色/敌人/技能；不改 Lina/Warrior 的数值、动画、AI。
- 不改默认阵容；不接 Nyra/Veno/Bat（除非用户先确认分支合并）。
- 不做 ladder AI 寻路（敌人不会爬梯），除非用户明确要求。
- 不重新生成/重画 platform/ladder 素材；不修改 `Image/`。
- 不把 contact sheet 直接当最终运行时路径而不确认。
- 不写 README/docs/手册，除非用户明确允许。

---

## 6. 开工前必须 grill 的问题（Q1–Q11）

### Q1 — 分支与工作区

当前 `main` 有 `UU instruction.docx` 和 506 个已暂存文件；Bat/Nyra/Veno 在 `nyra-veno-sandbox`。本轮 scene work 是在 `main` 上做，还是先合并/切到 `nyra-veno-sandbox`？

➡️ 推荐：**先让用户解决 instruction.docx 冲突并确认分支**；scene work 默认基于 `main`，不自行 merge/rebase。

### Q2 — barrier / platform / block 的归类

当前 `blocks` 是两组地面矩形。建议：

- `block` 作为类别名；
- `kind: "barrier"` = 实体障碍（当前两组地面矩形转为 barrier）；
- `kind: "platform"` = 可站立平台；
- `ladders` 独立列表，不属于 solid collision。

➡️ 推荐：**统一 `blocks` 列表 + `kind`，外加独立 `ladders`**；保留 `Stage.blocks` 作为所有 solid rect 的兼容视图。

### Q3 — platform 碰撞：实体还是单向？

instruction 说 block 类“有碰撞箱和体积”，但 160px 高的平台如果完全实体，会挡住地面通行/角色头部；单向平台更接近平台游戏习惯。

- A. **单向/顶部落地**：只有从上方落下时站在 platform 顶面；侧面和底面不挡角色。
- B. **实体 AABB**：像当前 block 一样，顶面 + 侧面 + 底面都碰撞。
- C. 数据可配 `one_way`，默认 A。

➡️ 推荐 **C，默认单向**：barrier 保持实体，platform 默认单向；如果用户要严格按“体积”解释，再改 B。

补充：单向 platform 仍建议让**投射物撞平台体积**（instruction 说“角色和技能会正常碰到”），只是角色可以从下方/侧面穿过并由顶部落地。这个细节也要在 Q3 一起确认。

### Q4 — W / Space / 攀爬输入

当前 W 和 Space 都是 jump。instruction 写 W 攀爬、Space 跳跃。

➡️ 推荐：**靠近 ladder 且按 W → 攀爬；其他情况 W 仍是跳跃；Space 始终跳跃；S/Shift 在梯子上向下爬**。需要把 `input.py` 的 W held 状态单独暴露，不能只改 buffered jump。

### Q5 — 攀爬状态与梯子顶/底

- ladder 无体积，不挡技能。
- 攀爬时是否忽略 platform/barrier 的 solid 碰撞（否则会被平台顶/侧面卡住）？
- 到顶后如何落到 platform？到底后如何回到地面？

➡️ 推荐：**新增 climbing 状态：贴梯时忽略 solids，按 W/S 垂直移动；到 top_y 时 snap 到 platform 顶面并 `on_ground=True`；到底回到 ground；攻击/受击/眩晕时退出攀爬**。该语义已实现；攀爬动画也已升级为批准的两帧背视 clip（见顶部 2026-10-28 更新）。

### Q6 — AI / 敌人

当前 main 只有 Warrior；Bat/Nyra/Veno 在另一分支。敌人是否需要爬梯/绕平台？

➡️ 推荐：**本轮不做 ladder AI**；Warrior 的 `_block_ahead` 把 barrier/platform 当 solid；不爬梯、不跳平台。不要改敌人数值/AI；如果以后合并 Bat/Veno，另开一轮适配。

### Q7 — 运行时素材路径与缩放

四张图目前在 `assets/generated/contact_sheets/`，是审批源图。运行时是否直接读它，还是复制到 `assets/sprites/stage/`？

➡️ 推荐：**确认后复制到 `assets/sprites/stage/`（或 `assets/frames/stage/`）**，运行时不要依赖 generated；保留原图；不缩放/裁切除非 F1 校准后确认。`sprite_rect` 与 `collision_rect` 分开。

### Q8 — 场景布局

见 §8 的第一版建议。需要用户确认平台高度、左右位置、梯子位置、barrier 位置。

➡️ 推荐：先按 §8 搭一版，用 F1/F2 看碰撞与攀爬，再调坐标；不要在未确认前改 `instruction.docx`。

### Q9 — F1 / B 语义

- B 当前开关所有 `blocks` 的绘制 + 碰撞。
- ladder 无体积，是否受 B 影响？

➡️ 推荐：**B 继续开关 block 类（barrier + platform）的绘制/碰撞；ladder 始终绘制（无碰撞），F1 额外画 ladder 攀爬区/顶底标记**。

### Q10 — 数据校验与 smoke

- `config.REQUIRED_STAGE` 目前要求 `blocks`。
- 新数据需要校验 `kind`、`rect`、`ladders` 字段。
- 现有 smoke 的 block 检查（`block_lunge_ok`、`q_block_ok`、`blocks_toggle_ok`、`separation_block_ok`）不能回归。

➡️ 推荐：新增 `platform_land_ok`、`barrier_block_ok`、`ladder_climb_ok`、`ladder_no_block_ok`、`platform_spawn_clear_ok`；现有 flags 保持 True。

### Q11 — 文档

本轮只写代码/smoke/场景数据；README、DESIGN_DECISIONS、DEBUG、手册等**先不写**。等设计确认后，再问用户是否写入文档。

➡️ 推荐：**遵守“没有明确允许不写文档”**。

---

## 7. 推荐数据设计（待 Q1–Q5 确认）

`game/data/debug.json` 的 `stage` 建议：

```json
"blocks": [
  {"kind": "barrier", "rect": [400, 560, 90, 60]},
  {"kind": "barrier", "rect": [760, 560, 90, 60]},
  {"kind": "barrier", "rect": [500, 200, 90, 60]},
  {"kind": "barrier", "rect": [1050, 240, 90, 60]},
  {"kind": "platform", "rect": [100, 260, 639, 104],
   "sprite": "platform_tropical_long",
   "sprite_rect": [100, 236, 639, 128],
   "surface_y": 260, "one_way": true},
  {"kind": "platform", "rect": [751, 300, 419, 104],
   "sprite": "platform_tropical_short",
   "sprite_rect": [751, 276, 419, 128],
   "surface_y": 300, "one_way": true}
],
"ladders": [
  {"rect": [172, 260, 64, 360], "top_y": 260, "bottom_y": 620,
   "sprite": "ladder_tropical_wood",
   "sprite_rect": [140, 260, 128, 358]},
  {"rect": [862, 300, 64, 320], "top_y": 300, "bottom_y": 620,
   "sprite": "ladder_tropical_wood_short",
   "sprite_rect": [800, 300, 187, 320]}
]
```

字段说明：

- `rect`：碰撞/触发矩形；barrier/platform 的 solid；ladder 的攀爬触发区（建议 64px 宽，不是整张 160px 图）。
- `sprite`：运行时 PNG 名（确认后复制到运行时目录）。
- `sprite_rect`：绘制矩形；与碰撞分开，方便平台顶面与图片草皮对齐。
- `surface_y`：可站立顶面；platform 顶部草皮通常不是图片 y=0，需要 F1 校准（建议先留 20–30px 余量）。
- `one_way`：platform 是否单向；barrier 不使用。
- `ladders`：独立列表；`top_y`/`bottom_y` 是攀爬端点；不加入 `Stage.blocks`/solids。

实现建议：

- `Stage.block_specs` 保存带 `kind` 的原始数据；`Stage.barriers`、`Stage.platforms` 保存分类视图；`Stage.ladders` 保存攀爬数据。
- **角色侧向碰撞**用 `Stage.side_solids`：barrier +（如果选实体 platform）platform 的侧面；单向 platform 不放进 `move_x` 的侧面列表。
- **角色落地**用 barrier 顶面 + platform 的 `surface_y`；单向 platform 只在 `move_fighter` 的下落分支处理，不能放进 `move_x`。
- **投射物**用 `Stage.projectile_solids`：barrier + platform 体积（如果 Q3 确认为“技能会碰到”）；ladder 永远排除。
- 旧 `Stage.blocks` 保留为 barrier 的兼容 rect 列表，避免把单向 platform 误当成实体侧面；旧调用点逐步迁移到 `side_solids` / `landing_surfaces` / `projectile_solids`。
- ladder 不加入任何 solid 列表；投射物代码不需要知道 ladder。

---

## 8. 第一版场景布局（建议，先用 F1 校准）

| 对象 | 建议位置/尺寸（第一版） | 说明 |
|---|---|---|
| 地面 | `ground_y=620`，墙 `90/1190` | 不变 |
| Barrier 1 | `[400,560,90,60]` | 当前 block 转为 barrier |
| Barrier 2 | `[760,560,90,60]` | 当前 block 转为 barrier |
| 长平台 | 原生 799×160 → 第一版按 0.8 缩放到 639×128；`sprite_rect=[100,236,639,128]`；`surface_y=260`；碰撞 `[100,260,639,104]` | 先单向；草皮上方 24px 是装饰 |
| 长梯 | 原生 160×448 → 第一版按 0.8 缩放到 128×358；`sprite_rect=[140,260,128,358]`；攀爬区 `[172,260,64,360]`；`top_y=260`，`bottom_y=620` | 触发区 64px 宽，不是整张 160px |
| 短平台 | 原生 524×160 → 第一版按 0.8 缩放到 419×128；`sprite_rect=[751,276,419,128]`；`surface_y=300`；碰撞 `[751,300,419,104]` | 先单向；与长平台并排，不重叠 |
| 短梯 | 原生 160×274 → 第一版缩放到 187×320；`sprite_rect=[800,300,187,320]`；攀爬区 `[862,300,64,320]`；`top_y=300`，`bottom_y=620` | 短梯需要小幅放大；也可改用长梯缩放 |
| 长平台 barrier | `[500,200,90,60]` | 底边贴 long platform 的 `surface_y=260` |
| 短平台 barrier | `[1050,240,90,60]` | 底边贴 short platform 的 `surface_y=300` |

注意：

- 这些坐标只是第一版，必须用 F1 看碰撞框、用游戏实际攀爬确认；不要直接当成最终布局。
- 第一版把两张平台按 0.8 缩放并排放在 x=100..739 与 751..1170，避免两张原生图在 1100px 竞技场内互相重叠；如果用户不允许缩放，改为只放一张平台或调整高度，不要硬塞。
- 平台高度让地面角色可以从下方通过（长平台底 364、短平台底 404；角色头顶约 410）；如果 platform 选实体（Q3 B），仍需检查跳跃时头部碰撞。
- 长梯在 x≈172–236，短梯在 x≈862–926；地面 barrier 在 400–490 / 760–850，互不重叠；短平台 barrier 放在 1050，避开短梯出口。
- 角色出生点：Lina x=280、敌人 x=1000；确保出生点不在 barrier/platform/ladder 的 solid 内。
- 平台/梯子图片不要覆盖 HUD/调试面板；F2 面板在右侧，必要时把短平台往左移。

---

## 9. 实施顺序（建议 A–F）

1. **A 基线/确认**：解决 `instruction.docx` 冲突、确认分支、跑 smoke exit 0；按 Q1–Q11 grill 用户。
2. **B 数据/Stage**：加 `block_specs`/`barriers`/`platforms`/`ladders`；保留 `Stage.blocks` 兼容；更新 `config.py` 校验。
3. **C 碰撞**：barrier 保持 solid；platform 按确认的 one-way/solid 实现落地；ladder 排除出 solids。
4. **D 攀爬**：`input.py` 分离 W climb；Lina 增加 climbing 状态、W/S 上下、top/bottom snap；攀爬动画已在后续批准并接入（两帧背视）。
5. **E 渲染/F1/B/场景**：画四张图；F1 画 barrier/platform 碰撞框 + ladder 攀爬区；B 开关 block 类；按 §8 搭第一版。
6. **F smoke/收尾**：新增检查、跑 smoke、F1/F2 手动验证；文档只在用户允许后写。

每阶段结束：

```bat
.venv/Scripts/python.exe main.py --smoke-test
```

---

## 10. Smoke / 验证清单

- 基线：现有 `missing_frames=0`、`block_lunge_ok`、`q_block_ok`、`blocks_toggle_ok`、`separation_block_ok` 不回归。
- `barrier_block_ok`：地面移动/攻击前踏被 barrier 挡住。
- `platform_land_ok`：从上方落到 platform，停在 `surface_y`；不穿模。
- `platform_side_ok`（若选择实体 platform）：侧面碰撞符合确认的语义。
- `ladder_climb_ok`：贴梯按 W 上升；有平台时在平台中点略往上提前吸附上 platform；S/Shift 可下爬。
- `lina_climb_anim_ok` / `lina_climb_facing_ok` / `lina_flame_climb_anim_ok` /
  `nyra_climb_anim_ok`：两帧背视、0.20s/帧、上楼 0→1、下楼 1→0、停住保持、退出恢复 facing；
  火焰版使用 `flame/climb`，Nyra 剑固定在背后。
- `ladder_no_block_ok`：投射物穿过 ladder；ladder 不影响技能。
- `platform_spawn_clear_ok`：Lina/Warrior 出生点不与 solid 重叠。
- `fx_cleanup_ok` 不回归：新增碰撞不造成投射物泄漏。
- F1：barrier/platform 碰撞框、ladder 攀爬区/顶底标记可见。
- F2：显示 ladder 状态（是否攀爬、top/bottom）或至少不崩溃。
- B：开关 barrier+platform 的绘制/碰撞；ladder 保持可画/可爬（按 Q9 确认）。

---

## 11. 禁止做的事

- **不要**修改 `instruction.docx`（当前还是 `UU` 冲突；先让用户解决）；不要修改 `Image/`、`UI Resources/`、`Sound Clip/`。
- **不要** `git commit`、`git reset`、`git checkout -- .`、`git stash`、`git clean`；当前有 506 个已暂存文件，任何清理都可能丢素材。
- **不要**自行 merge/rebase/切换分支；先确认 `main` vs `nyra-veno-sandbox`。
- **不要**改其他角色/敌人的数值、动画、AI、默认阵容；场景工作只碰 stage/scene/input/player climb/相关 smoke。
- **不要**在没有确认前把 platform 设为 one-way 或 solid；这是本轮最重要的语义决定。
- **不要**把 ladder 加入 solid/碰撞列表；instruction 明确“默认无体积，不遮挡任何技能效果”。
- **不要**直接从 `assets/generated/contact_sheets/` 读取运行时图；先确认复制到运行时目录。
- **不要**重新生成/重画 platform/ladder；不要覆盖 contact sheet 或 `Image/`。
- **不要**重画已批准的 climb 帧（Lina 普通/火焰、Nyra）；如要修改，先按素材审批流程询问用户。
- 文档已在用户批准后更新（2026-10-28 的 climb 设计）；后续文档修改仍需用户确认，且不要修改
  `instruction.docx`。
- **不要**用 pytest；不要写日志文件；验证用 `--smoke-test` + F1/F2。

---

## 12. 文件索引

- 权威场景规则：`instruction.docx`“特殊场景及道具说明”
- 当前 Stage：`game/stage.py`
- 场景/站立/分离：`game/scene.py`
- 玩家跳跃/移动：`game/lina.py`、`game/input.py`
- 敌人 block AI：`game/warrior.py`
- 投射物 block 碰撞：`game/projectile.py`
- 数据：`game/data/debug.json`、`game/data/stats.json`
- 校验：`game/config.py`
- 调试：`game/debug.py`、`game/hud.py`、`docs/DEBUG.md`
- Smoke：`main.py`
- 设计历史：`docs/DESIGN_DECISIONS.md`、`PLAN.md`
- 素材：`assets/generated/contact_sheets/platform_tropical_*.png`、`ladder_tropical_wood*.png`
- 背景：`assets/backgrounds/island-arena-16x9.png`
