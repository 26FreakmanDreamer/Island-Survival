# Next Session — Bat 完整设计与接入

> 日期：2026-10-25
> 状态：**动画已完成并安装；2026-10-26 已完成代码/数据接入（最终沙盒：atk 10、5 只、飞行 40–420、sonic-only 随机、俯冲高度门槛）。**
>
> **最终实现覆盖（2026-10-26）**：本文 §3–§8 中的推荐/阶段值如与以下最终值冲突，以本节和 §11 为准：`basic_atk 10`；`count 5`；`spawn_offsets [0,-160,160,-80,80]`；`spawn_heights [180,320,240,380,280]`；`flight min 40 / max 420 / preferred 240 / vertical_speed 300 / bob 24 / bob_rate 1.5`；sonic hitbox `forward 8 / radius 24`；AI 仅 sonic 随机（0–2.5s 初始冷却 + 50% 决策门），dive 确定性且 `_dive_can_reach` 高度门槛，0.55s 群体同技能错峰。
> 基线：`.venv/Scripts/python.exe main.py --smoke-test` → **exit 0**（2026-10-25 已核对）。
> 阅读顺序：本文 → `docs/BAT_ANIMATION_DESIGN.md` → `instruction.docx` 的 Bat 段 → `AGENTS.md`。
> 旧的 `docs/NEXT_SESSION_BAT.md` 仅作历史参考；其中的 128/11 帧方案、front-view、`dive 2.5s / sonic 5.0s` 冷却已被本文取代。

---

## 0. 可直接复制的开场 prompt

```text
先阅读 docs/NEXT_SESSION_BAT_FULL.md、docs/BAT_ANIMATION_DESIGN.md、instruction.docx 的 Bat 段和 AGENTS.md。
本轮目标：完成 Bat 的完整设计与接入（数据 + game/bat.py + SonicWave + scene/config/roster + smoke）。
动画已批准并安装到 assets/frames/bat/，不要重做动画素材，除非我明确要求。

先运行 .venv/Scripts/python.exe main.py --smoke-test，确认基线 exit 0。
先不要改代码或数据：按本文 §4 的 Q1–Q12 逐项 grill 我，每项给出当前值/目标值、影响范围和推荐默认。
确认后再按 §7 分阶段实现；每完成一个阶段跑一次 smoke。

不要 commit；不要 git reset / git checkout -- . / git stash；
不要动 Image/、instruction.docx、UI Resources/；不要改其他敌人；Bat 默认 5 只已按用户要求设置。
```

---

## 1. 权威战斗设定（`instruction.docx` 原文，2026-10-25 提取）

### 1.1 原文

> Bat
> 形象：Image\Enemy\bat-128.png
> Hp =50 atk =20 ,n=5 (测试时生成一只)
> 技能1：（冷却2s）飞向character，进行一次攻击，造成伤害atk
> 技能2：（冷却10s）空中，口中发出超声波，超声波初始方向为bat指向character方向，超声波沿着初始方向飞行。
> 如果碰到character，则对character造成一次伤害1.2atk和1s眩晕效果，然后反弹，沿着character指向bat方向回到发出超声波的bat后消失。
> 如果没有碰到character,当碰到墙壁时反弹，指向bat方向返回，如果返回的过程中碰到character，则对character造成一次伤害和1s眩晕效果，穿过character，回到发出超声波的bat后消失。
> bat在释放这个技能期间不会移动，只会在原地挥动翅膀。
> 被动：蝙蝠可以自由地在空中飞行

### 1.2 数值拆解

| 项 | 值 | 说明 |
|---|---:|---|
| HP | 50 | 与 Veno 相同 |
| ATK | 20 | `basic_atk: 20`、`extra_atk: 0` |
| 数量 | n=5（测试 1 只） | 沙盒先 1 只，正式再开 5 只 |
| 技能 1 | `1.0 × atk = 20` | **冷却 2s**；飞向 character 并攻击一次 |
| 技能 2 | `1.2 × atk = 24` | **冷却 10s**；超声波，命中附加 **1s stun** |
| 被动 | 自由飞行 | 不吃重力，可停留/上下移动 |

> **重要**：`2s / 10s` 是 docx 的权威冷却。旧 handoff 推荐的 `2.5s / 5.0s` 作废；数据与 AI 一律用 `2s / 10s`。

### 1.3 关键规则

1. 技能 2 的初始方向 = **发射瞬间 bat 嘴部 → character** 的直线方向；声波不追踪 player。
2. 去程命中 player：24 伤害 + 1s stun → 转向返回发射者 → 回到 bat 后消失。
3. 去程未命中、撞墙：转向返回发射者；返回途中命中 player：24 + 1s stun，**穿过** player，继续返回 bat 后消失。
4. 每次声波**最多造成一次伤害**；去程命中后，返回时不得再次结算。
5. `bat在释放这个技能期间不会移动，只会在原地挥动翅膀`：
   - **已确认（2026-10-25）**：只锁 **0.65s 施法动作**；声波飞出后 Bat 恢复飞行。
   - 这是对 docx 字面的有意解释；实现前可再核对一次（Q4）。
6. 被动自由飞行：Bat 始终 `on_ground = False`，不参与地面重力/落地逻辑；是否忽略 blocks 见 Q2。

---

## 2. 已完成：动画与素材（不要重做）

### 2.1 动画决策

| 项 | 结论 |
|---|---|
| 基准 | **side-view base C（流线滑翔）**，`assets/generated/base/bat_side_base.png` |
| 朝向 | 右向 3/4 侧视；运行时按 `facing` 翻转；镜像 pivot x = `77` |
| 源画布 | **384×384** |
| 运行时画布 | **192×192**（`AnimationPlayer` 加载时 384→192） |
| pivot | 源 `(230, 285)` → 运行时 `(115, 143)` |
| hurtbox（建议） | **100×66**，以 x 为中心、底边在 y；代码阶段用 F1/F2 最终确认 |
| 唯一帧数 | **14**：wing 4 + dive 3 + sonic 3 + hurt 1 + stun 1 + ko 2 |
| 身体基准 | 采用动作帧的较大身体；base C 作为造型/比例参考 |
| 过渡帧 | `wing_00_01` = v8 B scaled 1.15×；翼型/白骨与 `wing_00 B` 一致 |
| stun | 空中僵直下垂、不掉落；`stun_00`（自然闭眼） |
| KO | 空中瘫软 → 落地瘫倒；代码在落地时保持/切换第二帧 |

### 2.2 clip 与帧表

| clip | 帧文件（`assets/frames/bat/`） | 时长 | 循环 |
|---|---|---:|---|
| `idle` | `wing/wing_00.png`, `wing/wing_00_01.png`, `wing/wing_01.png`, `wing/wing_02.png`, `wing/wing_01.png`, `wing/wing_00_01.png` | 0.22×6 | 是 |
| `fly` | `wing/wing_00.png`, `wing/wing_00_01.png`, `wing/wing_01.png`, `wing/wing_02.png` | 0.10×4 | 是 |
| `bat_dive` | `bat_dive/bat_dive_00..02.png` | 0.12 / 0.22 / 0.41 | 否 |
| `bat_sonic` | `bat_sonic/bat_sonic_00..02.png` | 0.10 / 0.30 / 0.25 | 否 |
| `hurt` | `hurt/hurt_00.png` | 0.30 | 否 |
| `stun` | `stun/stun_00.png` | 0.30 | 否 |
| `ko` | `ko/ko_00.png`, `ko/ko_01.png` | 0.35 / 0.35 | 否 |

- `idle`/`fly` **共用** 4 张振翅图；`idle` 用乒乓顺序，`fly` 用 4 帧顺序。
- `bat_sonic` 的弹体在 **t=0.24** 从嘴部生成；帧内不烘焙声波环/光效。
- `bat_dive` 的命中窗约 t=0.12–0.34；hitbox 跟随本体。
- 帧文件均为 384×384 RGBA；`animations.json` 的 `bat_frame_size` 为 `[192,192]`，加载时统一 downscale。

### 2.3 资产与工具

- 动画详细设计：`docs/BAT_ANIMATION_DESIGN.md`
- 运行时帧：`assets/frames/bat/`（14 个 PNG，已安装）
- staged 源帧：`assets/generated/staged/bat/side_final/`
- 全量审批表：`assets/generated/contact_sheets/bat_v1/bat_side_full_v1.png`
- wing 循环 GIF：`bat_side_wing_idle_v9.gif` / `bat_side_wing_fly_v9.gif`
- 动作 GIF：`bat_side_bat_dive_v2.gif` / `bat_side_bat_sonic_v2.gif` / `bat_side_bat_hurt_stun_ko_v2.gif`
- 工具：
  - `tools/import_bat_side_frames.py`
  - `tools/contact_sheet_grid.py`
  - `tools/preview_bat_side_wing.py`
  - `tools/preview_bat_side_clips.py`

---

## 3. 下阶段目标与边界

### 3.1 本轮目标

1. 确认 §4 的 Q1–Q12。
2. 完成数据：`stats.json`、`attacks.json`、`animations.json`、`roster.json`、`debug.json`。
3. 完成 `game/bat.py`：自由飞行、AI、俯冲、声波施法锁定、每实例冷却、hurt/stun/KO、reset、facing。
4. 完成 `game/projectile.py::SonicWave`：去程/回程、撞墙、返回 owner、穿过 player、最多一次伤害。
5. 接入 `scene.py` 的飞行生成、sonic 生成/命中特效；`config.py`/`roster.py` 注册。
6. 增加 Bat smoke 检查；确保现有 smoke 全部不回归。
7. 只在确认后再做 5 只编组/平衡；Cave 背景默认不做。
8. 更新 README / DESIGN_DECISIONS / DEBUG / ASSET_PIPELINE 中与 Bat 代码相关的部分。

### 3.2 本轮不做 / 不重做

- 不重新生成或重画 14 帧动画；动画已批准。
- 不改其他敌人的数值、判定、冷却、AI；Bat 默认 5 只已按用户要求设置。
- 不动 `Image/`、`instruction.docx`、`UI Resources/`。
- 不 commit；不要 `git reset` / `git checkout -- .` / `git stash`。
- 不用 pytest；验证用 `--smoke-test` + F1/F2 + 预览图。
- 不写日志文件。
- F5 只热重载 JSON/PNG；改 `game/*.py`、`config.py`、`game/fx.py` 常量需要重启 Python。

---

## 4. 开工前必须 grill 的问题（Q1–Q12，带推荐）

> 先一次性问完；用户答完后把结论写回本文 §11，再开始改代码。

### ❓ Q1 — 数量：沙盒 1 只还是直接 5 只

docx：`n=5 (测试时生成一只)`。

➡️ 推荐：**沙盒 `count: 1`**；5 只作为数据开关，等单只飞行/声波/AI 稳定后再单独测 5 只。

---

### ❓ Q2 — 飞行规则

是否完全自由 2D 飞行（无重力、可上下、忽略 blocks），高度范围 60–280px？

➡️ 推荐：**是**。左右墙/顶部/地面仍夹紧；blocks 是地面障碍，飞行越过，不参与碰撞。

---

### ❓ Q3 — 技能 1 的“飞向并攻击”

是一次**俯冲近战**（bat 本体 2D 移动，命中 box 跟随本体），还是发射弹体？

➡️ 推荐：**俯冲近战**。t≈0.05–0.30 朝玩家胸口移动（约 520px/s），hitbox 跟随本体，命中 20 伤害，冷却 **2s**；未命中则冲过头并恢复。不要做成第二个远程技能。

---

### ❓ Q4 — 技能 2 的施法锁定范围

docx 字面是“释放这个技能期间不会移动”；已确认解释为**只锁 0.65s 施法动作**。

➡️ 推荐：**保持 0.65s 施法锁定**；声波飞出后 Bat 恢复飞行。若用户改回字面全程锁定，需要额外循环挥翅帧/更长锁定，并接受 Bat 成为固定靶。

---

### ❓ Q5 — 声波返回与消失

返回目标是**发射者当前位置**还是发射点？Bat 死亡/移出屏幕时怎么处理？stun 的 source 是否每只独立？

➡️ 推荐：追踪 **owner 当前位置**，距离 ≤16px 消失；owner 死亡则再飞 0.5s 或撞边界后消失；`source = "bat_sonic"`（1s 眩晕不叠加，重复命中刷新）。若希望多只 Bat 的眩晕独立计时，再改为每实例唯一 source。

---

### ❓ Q6 — 声波的墙壁、速度、超时

“墙壁”是否包括左右墙、顶部、地面？blocks 算不算？

➡️ 推荐：左右墙 `stage.walls = (90, 1190)` + 顶部 + 地面；**blocks 不算墙**（蝙蝠飞行忽略 blocks，声波也按竞技场边界处理）。速度 `420`，`timeout 8s`，`range 3000` 只作泄漏上限；生命周期由“回到 owner”或超时决定。

---

### ❓ Q7 — AI 参数

docx 只给了冷却 `2s / 10s`，没给距离/站位。

➡️ 推荐：`dive_range 420`、`sonic_min_range 120`、`sonic_range 700`、`standoff 220`、`decision_interval 0.15`；冷却固定 **dive 2.0s / sonic 10.0s**（每实例独立）。5 只时再单独观察，必要时只调冷却，不改 docx 数值。

---

### ❓ Q8 — 画布/pivot/hurtbox

动画已定：源 384 / 运行时 192，pivot 源 `(230,285)` / 运行时 `(115,143)`，镜像 x=`77`。

➡️ 推荐：**hurtbox 100×66**（居中于 x、底边在 y）；`stage_body_width` 建议 **56**（飞行时 wall clamp 用 `hurtbox_width*0.5`）。代码阶段用 F1/F2 看调试框，若命中手感偏大/偏小再微调，但不改帧。

---

### ❓ Q9 — 声波 VFX 与嘴部锚点

声波视觉是否程序化，还是烘焙进帧？

➡️ 推荐：**程序化**同心弧/声波环（紫白 `(210,190,255)`/`(245,235,255)`），帧内不烘焙。嘴部锚点从 `bat_sonic_01.png` 实测：侧视头在右前方，弹体 origin 应有 **forward + height** 偏移（不要沿用旧 front-view 的 `origin_height: 24`）。建议在 `attacks.json` 增加 `origin_forward` 或在 `Bat` 里计算，代码阶段用预览图校准。

---

### ❓ Q10 — F7 顺序 / Cave 场景

Bat 放在 F7 的哪个位置？是否同时接入 `island-bat-cave-arena-16x9.png`？

➡️ 推荐：F7 顺序保持 `Warrior → Veno → Bat → Dummy`（Bat 插在 Veno 后、Dummy 前）；Cave 背景作为独立可选项，本轮不默认接入（Stage 目前没有按敌人切换背景的机制）。

---

### ❓ Q11 — 5 只编组/平衡

正式 n=5 时，5 只同时放声波压力很大；是否需要独立平衡？

➡️ 推荐：沙盒先 1 只；5 只时用 `count: 5` + `spawn_offsets`/`spawn_modes`，每只独立冷却；先测 5 只的声波重叠、眩晕刷新、群体 AI，再决定是否调冷却/仇恨。不要为了 5 只改单只 docx 伤害。

---

### ❓ Q12 — 本轮范围 / 文档

本轮是否做到“数据 + 代码 + smoke + 文档”，但不 commit、不做 Cave、不做 5 只平衡？

➡️ 推荐：**是**。先完成单只 Bat 全链路（飞行→俯冲→声波→返回→hurt/stun/KO），smoke 全绿；5 只和 Cave 作为后续独立阶段。

---

## 5. 数据设计（推荐默认，待 §4 确认后微调）

### 5.1 `game/data/stats.json` → `bat`

```json
"bat": {
  "hp": 50,
  "basic_atk": 10,
  "extra_atk": 0,
  "stage_body_width": 56,
  "move": { "walk": 300, "jump_v": 0, "gravity": 2200 },
  "hurtbox": { "standing": [100, 66], "crouching": [100, 66] },
  "flight": {
    "min_height": 40,
    "max_height": 420,
    "preferred_height": 240,
    "vertical_speed": 300,
    "bob": 24,
    "bob_rate": 1.5
  },
  "ai": {
    "dive_range": 420,
    "sonic_min_range": 120,
    "sonic_range": 700,
    "standoff": 220,
    "decision_interval": 0.15
  },
  "cooldowns": { "dive": 2.0, "sonic": 10.0 }
}
```

- `basic_atk` **10** 是用户 2026-10-26 指定的沙盒值（docx 原文为 20）；dive 10 = 1.0×10，sonic 12 = 1.2×10。
- `move.gravity` 2200 只用于 KO 坠落；飞行路径不调用重力，所以不用 0。
- `cooldowns` 必须用 docx 的 **2.0 / 10.0**，不要沿用旧推荐。
- `hurtbox` 用 side-view 的 100×66；旧 front-view 的 60×56 作废。
- `stage_body_width` 56 只影响 wall/block 的移动 body；Bat 飞行时 `body_half` 会走 `hurtbox_width*0.5`。
- 5 只默认出生/巡航高度见 roster `spawn_heights`；`preferred_height` 240 只作无 heights 时的回退。

### 5.2 `game/data/attacks.json`

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
    { "t": 0.12, "until": 0.34, "type": "hitbox", "box": [0, -70, 90, 70], "knockback": 160, "hit_fx": "bat_dive_hit" }
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
      "origin_height": 30,
      "origin_forward": 46,
      "speed": 420,
      "range": 3000,
      "hitbox_forward": 8,
      "hitbox_radius": 24,
      "status": "stun",
      "status_duration": 1.0
    }
  ]
}
```

- `box`/`origin_height`/`origin_forward` 是 side-view 的推荐起点；代码阶段按 `bat_dive_01.png` / `bat_sonic_01.png` 的嘴/爪位置校准。
- `range: 3000` 只是防泄漏上限；实际由“回到 owner”或 `timeout 8s` 结束。
- 声波伤害 **12** = `1.2 × 10`；stun 1s 由 `Bat.on_projectile_hit` 施加（参考 `Veno.on_projectile_hit`）。
- `hitbox_forward 8` / `hitbox_radius 24` 是前向圆判定（圆心沿运动方向偏移 8px、半径 24），包住 Wi-Fi 最外层弧；回程方向同时驱动图样和 hitbox。

### 5.3 `game/data/animations.json`

```json
"bat_frame_size": [192, 192],
"bat_pivot": [115, 143],
"bat_clips": {
  "idle": {
    "loop": true,
    "frames": ["wing/wing_00.png", "wing/wing_00_01.png", "wing/wing_01.png", "wing/wing_02.png", "wing/wing_01.png", "wing/wing_00_01.png"],
    "durations": [0.22, 0.22, 0.22, 0.22, 0.22, 0.22]
  },
  "fly": {
    "loop": true,
    "frames": ["wing/wing_00.png", "wing/wing_00_01.png", "wing/wing_01.png", "wing/wing_02.png"],
    "durations": [0.10, 0.10, 0.10, 0.10]
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
  "hurt": { "loop": false, "frames": ["hurt/hurt_00.png"], "durations": [0.30] },
  "stun": { "loop": false, "frames": ["stun/stun_00.png"], "durations": [0.30] },
  "ko": {
    "loop": false,
    "frames": ["ko/ko_00.png", "ko/ko_01.png"],
    "durations": [0.35, 0.35]
  }
}
```

- 源 PNG 是 384×384；`AnimationPlayer` 按 `bat_frame_size` downscale 到 192。不要另做缩放。
- `idle`/`fly` 引用共享 `wing/` 帧；不要复制成两套文件。
- `idle` 的 6 步是 00 → 过渡 → 01 → 02 → 01 → 过渡，循环。

### 5.4 `game/data/roster.json` → `enemies.bat`

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
  "count": 5,
  "spawn_offsets": [0, -160, 160, -80, 80],
  "spawn_heights": [180, 320, 240, 380, 280]
}
```

- `flying: true` 是新字段；`scene._place_enemies` 用它分支（不要只改 `bat_spawn.y`）。
- 默认 **5 只**：`spawn_offsets` 控制 x，`spawn_heights` 控制出生/巡航高度；`_place_enemies` 会写入每只的 `cruise_height`。
- `enemy_count_override` 会屏蔽 offsets/heights，单只 smoke 使用 `bat_spawn` 的 y=470（alt 150）。
- F7 顺序由 `roster.json` 的 `enemies` 顺序决定；按 Q10 放在 Veno 后、Dummy 前。

### 5.5 `game/data/debug.json`

```json
"bat_spawn": [1000, 470]
```

- `ground_y = 620`，470 = 离地约 150px。它是基础/单只 spawn；默认 5 只用 roster 的 `spawn_heights`。
- side-view 的 pivot 是身体底边；`enemy.y = 470` 即身体底边在 470。

---

## 6. 代码设计

### 6.1 `game/bat.py`

参考 `game/veno.py`（飞行/AI/每实例冷却）与 `game/warrior.py`（技能槽/force_attack）。

- 构造函数：
  - 读 `stats["bat"]`，设置 `basic_atk/atk`、`stage_body_width`、hurtbox、`walk_speed`、flight/AI/cooldown 字段。
  - `self.on_ground = False`、`self.mode = "fly"`、`self.facing = -1`（enemy 默认）或按目标更新。
  - `self.dive_cd`、`self.sonic_cd` **每实例独立**；`show_health_bar = True`。
- `update(dt, scene)`：
  - `update_common(dt)`；冷却递减。
  - KO/HURT/ATTACK/control lock 分支（参考 Veno）。
  - 自由飞行：目标点 = 玩家 x ± `standoff`、`preferred_height` + sine bob；按速度上限同时移动 x/y；用 `stage.walls` 夹紧 x，用 `flight.min_height/max_height` 夹紧 y；**不要**走带重力的 `move_fighter` 默认路径；飞行忽略 blocks。
  - AI：距离/冷却满足时选择 `bat_dive` 或 `bat_sonic`；否则保持 standoff/高度。
  - 受击/眩晕：`take_hit` 后不要让一次击飞把 Bat 送出场景；对 `vy`/`kb_vx` 做衰减并夹紧飞行高度，或短 stagger 后回位。
- `start_attack(attack_id, scene, target)`：面向玩家、设置 runtime、对应冷却；`bat_dive`/`bat_sonic` 分别设置。
- `_update_attack(dt)`：在 `runtime.update(dt)` 之外，对 `bat_dive` 做自定义 2D 位移（t≈0.05–0.30 朝玩家胸口，约 520px/s，之后减速/停住）；hitbox 跟随本体。不要在通用 `AttackRuntime` 里加蝙蝠逻辑。
- `bat_sonic` 施法锁定：只在 `AttackRuntime` 的 0.65s 内锁飞行；动作结束后恢复 `fly`。
- `on_projectile_hit(projectile)`：`sonic_wave` + `status == "stun"` → `target.statuses.add("stun", 1.0, source="bat_sonic")`。参考 `Veno.on_projectile_hit`。
- Bat 自身被眩晕时：`update` 检测 `statuses.has("stun")`，切到 `stun` clip（1 帧保持）；与“声波让 player 眩晕”是两条路径，不要混淆。
- `force_attack(scene, target, attack_id)` / `skill_remaining(attack_id)` / `reset()`：与 Veno 一致；`reset()` 末尾恢复 `on_ground=False`、出生高度、`mode="fly"`。
- `draw()`：如需 hover/飞行姿态可直接 `super().draw()`；side-view 帧由 `facing` 翻转，pivot 已居中在身体，hurtbox 不需要偏移。
- KO：`ko` clip 两帧；空中保持 `ko_00`，落地后保持/切到 `ko_01`（代码阶段用动画播放器切换或两个 clip；不要只靠 0.7s 自动播完导致在空中出现落地帧）。

### 6.2 `game/projectile.py::SonicWave`

字段/状态机：

```text
fields:
  owner, x, y, ux, uy, speed, radius, damage, hitstun, hitstop
  status = "stun", status_duration = 1.0
  visual_kind = "bat_sonic", hit_color = (210,190,255)
  phase = "out" | "return"
  hit_out = False, hit_return = False
  age, timeout = 8.0
  alive = True

update(dt, scene):
  age += dt; if age > timeout: alive = False
  if phase == "out":
    move along (ux, uy)
    if 撞到左/右墙 / 顶部 / 地面:
      phase = "return"; 指向 owner 当前位置
    elif 命中 player（targets_for(owner)）:
      hit_out = True
      resolve_projectile_hit(scene, self)   # 24 + 1s stun
      hit_return = True                     # 去程已命中：同一次声波不再结算回程伤害
      phase = "return"; 指向 owner 当前位置
  else:
    朝 owner 当前位置移动
    若距离 <= step 或 <= 16px: alive = False
    elif not hit_return and 命中 player:
      hit_return = True
      resolve_projectile_hit(scene, self)   # 24 + 1s stun，穿过，不消失
```

- 去程/回程都不要因为命中 player 而 `alive = False`；只有回到 owner 或超时才消失。
- 去程命中必须置 `hit_return = True`，否则弹体叠在 player hurtbox 内会在 return 分支立刻再结算一次（48 伤害）。
- 墙面判断：左右墙 `stage.walls`、`y <= 0 + radius`、`y >= ground_y - radius`；blocks 不算墙（Q6）。
- `direction` 用于击退方向；声波 `knockback = 0`（docx 只给 stun），`hitstun = 0.1`。
- `visual_kind = "bat_sonic"`、`hit_color` 紫白；`draw()` 用程序化同心弧/声波环。
- owner 死亡/移出屏幕：按 Q5（推荐再飞 0.5s 或撞边界后消失）。
- 在 `scene.spawn_projectile_from_event` 增加 `sonic_wave` 分支；在 `spawn_projectile_cast_fx` / `spawn_projectile_impact` 增加程序化特效；`game/config.py` 的 `PROJECTILE_KINDS` 加 `"sonic_wave"`。

### 6.3 `game/scene.py`

- `_place_enemies`：当前无条件 `on_ground=True` / `y=base_y` / `mode="ground"`。增加飞行分支：

```python
if getattr(enemy, "flying", False) or self.enemy_spec.get("flying"):
    enemy.y = base_y
    enemy.on_ground = False
    enemy.mode = "fly"
else:
    ... 现有地面/hover 逻辑
```

- `base_y` 来自 `bat_spawn`；`count`/`spawn_offsets` 复用现有 group 逻辑。
- Bat 飞行忽略 blocks：移动逻辑里不要调用会挡 block 的 `stage.move_x`，或在 `Bat._move` 内只做墙面夹紧。
- `spawn_projectile_from_event`：增加 `sonic_wave` 分支；origin 用 `origin_forward`/`origin_height`，方向从嘴部到 player 中心。
- `spawn_projectile_cast_fx` / `spawn_projectile_impact` / `spawn_hit_fx`：声波环/命中环；`bat_dive` 命中特效可选。

### 6.4 `game/config.py` / `game/roster.py`

至少增加：

- `REQUIRED_STATS += ("bat",)`
- `REQUIRED_ATTACKS += ("bat_dive","bat_sonic")`
- `REQUIRED_STAGE += ("bat_spawn",)`
- `ROSTER_CLASSES += ("bat",)`
- `ANIMATED_CLASSES += ("bat",)`
- `PROJECTILE_KINDS += ("sonic_wave",)`
- `REQUIRED_BAT_CLIPS`（`idle`, `fly`, `bat_dive`, `bat_sonic`, `hurt`, `stun`, `ko`）及 `animations.json` 校验。
- `stats.bat` 校验：hp/basic_atk/extra_atk/stage_body_width/move/hurtbox/flight/ai/cooldowns；`flight.min_height <= preferred <= max_height`。
- `game/roster.py`：`from .bat import Bat`；`FIGHTER_CLASSES["bat"] = Bat`。

---

## 7. 实施顺序（阶段 A–F）

1. **A 基线 + 确认**：跑 smoke exit 0；按 §4 Q1–Q12 grill，用户确认后写回 §11。
2. **B 数据/注册**：stats/attacks/animations/roster/debug + config/roster + `scene._place_enemies` 飞行分支；用 canonical fallback/已装帧先让 Bat 出现。smoke：`bat_present`、`bat_missing_frames=0`。
3. **C Bat 飞行/AI/俯冲**：`game/bat.py` 的飞行、standoff、dive、冷却 2s、facing、reset；smoke：`bat_flight_ok`、`bat_dive_ok`、`bat_slots_ok`。
4. **D SonicWave**：状态机、撞墙、返回 owner、穿过、stun 1s、单次伤害；scene 生成/特效；smoke：`bat_sonic_ok`、`bat_sonic_return_ok`、`bat_sonic_wall_return_ok`、`bat_sonic_lock_ok`。
5. **E hurt/stun/KO/组**：Bat 自身眩晕、KO 落地切换、5 只编组（若 Q1/Q11 确认）；smoke：`bat_group_ok`。
6. **F 文档/收尾**：README / DESIGN_DECISIONS / DEBUG / ASSET_PIPELINE；最终 smoke 全绿；不 commit。

每阶段结束：
```bat
.venv/Scripts/python.exe main.py --smoke-test
```
现有字段不得回归。

---

## 8. Smoke / 验证清单

### 8.1 基线

```bat
.venv/Scripts/python.exe main.py --smoke-test
```
预期 exit 0；现有 `missing_frames=0` 等字段全绿。

### 8.2 建议新增检查

| 检查 | 预期 |
|---|---|
| `bat_present` | name="Bat"、HP=50、atk=10、`skill_slots=["bat_dive","bat_sonic",null,null]` |
| `bat_dive_ok` | 一次俯冲命中造成 **10** 伤害 |
| `bat_dive_hit_fx_ok` | 俯冲命中派发 `bat_dive_hit` FX |
| `bat_sonic_ok` | 声波命中造成 **12** 伤害 + `statuses.has("stun")`，stun 约 1s |
| `bat_sonic_return_ok` | 去程命中后 phase 切到 return，最终回到发射者并 `alive=False` |
| `bat_sonic_wall_return_ok` | 去程未命中 → 撞墙 → 回程命中玩家（12 + stun）→ 穿过 → 回到 bat 消失 |
| `bat_sonic_hitbox_ok` | 前向圆 +8/r24 能碰到旧 36×36 之外的弧前缘 |
| `bat_sonic_lock_ok` | 施法 0.65s 内 bat 的 x/y 不变；之后恢复飞行 |
| `bat_flight_ok` | 无重力：连续 tick 后仍 `on_ground=False` 且高度在 `[40,420]`；水平移动正常 |
| `bat_slots_ok` | V/C 触发俯冲/声波；X/Z no-op |
| `bat_missing_frames` | **0**（14 帧已安装） |
| `bat_group_ok`（count=5） | 5 只按不同 x/y 生成；独立冷却；全部死亡后 `match_over == "WIN"`（子检查 `bat_group_spawn_ok` / `cooldowns` / `win`） |

### 8.3 测试隔离

- 单只 Bat 测试前设置 `scene.enemy_count_override = 1`，测完恢复；参考 Veno 单只检查。
- 声波测试临时关闭 blocks（`scene.stage.blocks_enabled = False`），测完恢复。
- 直接调用 `bat.force_attack(scene, player, "bat_sonic")` 让弹道可控；再用 `scene.tick(FIXED_DT)` 推进。
- 墙面反弹测试把 Bat 放在靠近 `stage.walls` 的位置，让声波朝外发射，玩家站在返回路径上。
- 确认 `fx_cleanup_ok` 与现有 projectile 清理不被 Bat 破坏；超时/回程必须保证弹体最终 `alive=False`。

---

## 9. 文件清单（预计）

**新增**

- `game/bat.py`
- `game/projectile.py::SonicWave`（类，位于现有文件内）
- `docs/NEXT_SESSION_BAT_FULL.md`（本文）

**修改**

- `game/data/stats.json`、`attacks.json`、`animations.json`、`roster.json`、`debug.json`
- `game/config.py`、`game/roster.py`、`game/scene.py`、`game/projectile.py`、`game/fx.py`
- `main.py`（Bat smoke phase）
- `README.md`、`docs/DESIGN_DECISIONS.md`、`docs/DEBUG.md`、`docs/ASSET_PIPELINE.md`

**已存在，不要重做**

- `assets/frames/bat/`（14 帧）
- `docs/BAT_ANIMATION_DESIGN.md`
- `assets/generated/...` 的审批产物

**不要动**

- `Image/`、`instruction.docx`、`UI Resources/`
- 其他敌人的数值/帧/默认阵容，除非用户明确要求

---

## 10. Guardrails（当前项目约定）

- **不要 commit**，除非用户明确要求。
- **不要** `git reset` / `git checkout -- .` / `git stash`；工作区有大量未提交改动。
- `Image/` 是 canonical 视觉源，只读；不要覆盖。
- `instruction.docx`、`UI Resources/` 不要动。
- 新素材必须：读取 `docs/IMAGE_GENERATION_RULES.md` → 生成到 `assets/generated/raw/...` → contact sheet → 用户批准 → 复制到 `assets/frames/...`。**Bat 动画已批准，不要重新生成。**
- 不要用 pytest；验证用 `--smoke-test` + F1/F2 + 预览图。
- 不要写日志文件。
- F5 只热重载 JSON/PNG；改 `game/*.py`、`config.py`、`game/fx.py` 常量需要重启 Python。
- 默认对局是 Lina vs 5 Bats（用户 2026-10-26 指定）；不要再改其他敌人或默认阵容。
- 不要改其他敌人的伤害/判定/冷却/AI。

---

## 11. 本次 session 结论（下个 session 填写）

```text
Q1 数量：默认对局 5 只（debug.roster.default_enemy="bat"、roster bat.count=5）；F7 顺序 Warrior→Veno→Bat→Dummy；spawn_offsets [0,-160,160,-80,80]，spawn_heights [180,320,240,380,280]。
Q2 飞行：自由 2D、无重力；高度 40–420，preferred 240，bob 24 @1.5 rad/s，vertical_speed 300；x 夹 stage.walls；5 只巡航在各自出生高度。用户 override：block 不忽略（本体与声波都按真实矩形碰撞）。
Q3 技能 1：俯冲近战，10 伤害，冷却 2s；方向在攻击开始时锁定（不追踪），hitbox 跟随本体；`_dive_can_reach` 用实际 hitbox 路径判断当前高度/距离能否命中，不能则继续飞行；dive 不使用随机。
Q4 技能 2 锁定：只锁 0.65s 施法动作；声波飞出后 Bat 恢复飞行。
Q5 返回/消失：追踪 owner 当前位置，≤16px 消失；owner 死亡后再飞最多 0.5s；每次声波最多一次伤害；stun source "bat_sonic"（覆盖刷新，不叠加）；回程方向同时驱动图样与 hitbox。
Q6 墙壁/速度/超时：左右墙/顶部/地面 + **block 实际矩形**反弹；speed 420；timeout 8s；range 3000 只作泄漏上限。
Q7 AI/冷却：dive 2.0s / sonic 10.0s，每实例独立；dive_range 420、sonic_min_range 120、sonic_range 700、standoff 220、decision_interval 0.15。**random 只控制 sonic**（0–2.5s 随机初始冷却 + 50% 决策释放）；dive 确定性且高度门槛；0.55s 群体同技能错峰。
Q8 hurtbox/pivot：hurtbox 100×66（x 居中、底边在 y）、runtime pivot (115,143)、stage_body_width 56；preferred 240。
Q9 声波 VFX/嘴部锚点：程序化 Wi-Fi 三层弧 + 发射点 + 拖尾；origin_forward 46、origin_height 30；hitbox 前向圆 +8/r24，随实际运动方向（含回程）。
Q10 F7/Cave：Bat 插在 Veno 后、Dummy 前；Cave 背景本轮不接入。
Q11 5 只编组：count=5；spawn_offsets + spawn_heights；独立冷却；`bat_group_*` smoke；群体平衡/手感待实测。sonic 只随机、dive 高度门槛已缓解同刻同技能与高空空俯冲。
Q12 范围/文档：数据 + game/bat.py + SonicWave + scene/config/roster + smoke + 文档；不 commit；未动 Image/、instruction.docx、UI Resources/、其他敌人。

已完成：
- game/bat.py（飞行/高度/AI/俯冲高度门槛/施法锁定/冷却/hurt/stun/KO/reset）
- game/projectile.py::SonicWave（去程/回程/墙+block 反弹/前向圆 hitbox/单次伤害/owner 追踪/回程方向）
- stats/attacks/animations/roster/debug + config/roster/scene 注册
- 5 只默认编组、spawn_heights、独立冷却、群体 smoke
- scene 飞行生成/高度、sonic 生成/cast/impact FX、bat_dive_hit FX
- main.py Bat smoke；F7 顺序更新；docs 更新

smoke：.venv/Scripts/python.exe main.py --smoke-test → exit 0；bat_* flags 全 True（present/default/flight/dive/dive_fx/slots/hurt/stun/ko/win/sonic/cast/impact/hitbox/return/wall_return/block_return/lock/count/group_spawn/group_cooldowns/group_win/missing），现有 flags 不回归。

未完成/风险：
- 5 只实际平衡/手感（atk 10、冷却、巡航高度、sonic 随机概率仍可调）。
- 巡航高度 180–380 时 Lina 地面拳/踢大多够不到，需要跳跃或趁俯冲窗口；若手感不对优先调 spawn_heights/flight.preferred_height，不改帧。
- block 只有 60px 高；正常巡航在其上方，低空/俯冲/下压声波才碰到。
- docx 原文 atk 20、n=5；沙盒按用户要求使用 atk 10、count 5（instruction.docx 未改动）。
- Bat Cave 背景未接入。
```

---

## 12. 相关文件索引

- 动画设计：`docs/BAT_ANIMATION_DESIGN.md`
- 旧 handoff（历史）：`docs/NEXT_SESSION_BAT.md`
- 权威设定：`instruction.docx` 的 Bat 段
- 视觉源：`Image/Enemy/bat-128.png`、`Image/Enemy/Posters/bat-poster.png`
- 运行时帧：`assets/frames/bat/`
- 敌人类参考：`game/veno.py`（飞行/AI/每实例冷却）、`game/warrior.py`（技能槽/force_attack）
- 弹体参考：`game/projectile.py`（`AimedProjectile`、`AxeThrow`）
- 场景入口：`game/scene.py`（`_place_enemies`、`spawn_projectile_from_event`、`spawn_projectile_impact`、`spawn_hit_fx`）
- 伤害公式：`game/combat.py::attack_damage`
- 数据校验：`game/config.py`
- 通用新增敌人指南：`docs/NEXT_SESSION_CHARACTERS.md`
- 素材流程：`docs/ASSET_PIPELINE.md`
- 生图规则：`docs/IMAGE_GENERATION_RULES.md`
