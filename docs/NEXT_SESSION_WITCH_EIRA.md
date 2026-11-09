# Next Session — Crooked Witch 与 Eira Frostveil 接入

> 日期：2026-11-08
> 状态：**角色动画已全部通过美术确认；代码、数据、运行时帧、AI、smoke 尚未接入。**
> 本文是下一个 session 的交接文档、实现清单和 grill 清单，可直接使用。
>
> 基线：分支 `rhea-thorn-integration`，HEAD `f04b158`（Shadow Ninja 幻影形态已提交）。
> 当前工作区有未提交的 Eira 基准图、Eira/Crooked Witch 接触表、动画设计文档和用户对
> `instruction.docx` 的修改；不要 commit/push，不要回滚用户修改。
>
> 权威规格：`instruction.docx` 的 Eira 段（P198–P207）和 Enemy / Crooked Witch 段
> （P271–P280，专属场景图在 P281–P282）。本文只摘录，**绝不修改 docx**。
>
> 动画规格：`docs/EIRA_FROSTVEIL_ANIMATION_DESIGN.md` 和
> `docs/CROOKED_WITCH_ANIMATION_DESIGN.md`。这两份文档里的帧表、版本、时长、base 已确认；
> 本轮只做接入，不重画、不换版本、不改动作。
>
> 默认角色仍是 **Lina**，默认敌人仍是 **Creepy Shooter**。本轮新增：
> **Eira = 可玩角色**（`[` / `]` 轮换），**Crooked Witch = F7 敌人**。

---

## 0. 给下一个 session 的开场 prompt（可直接复制）

```text
读取 docs/NEXT_SESSION_WITCH_EIRA.md、docs/EIRA_FROSTVEIL_ANIMATION_DESIGN.md、
docs/CROOKED_WITCH_ANIMATION_DESIGN.md、instruction.docx 的 Eira 段（P198–P207）和
Crooked Witch 段（P271–P280，含 P281–P282 的专属场景图）、AGENTS.md、README.md、
docs/DESIGN_DECISIONS.md、docs/DEBUG.md、docs/ASSET_PIPELINE.md；
处理素材前再读 docs/IMAGE_GENERATION_RULES.md。

先运行 .venv/Scripts/python.exe main.py --smoke-test，确认基线 exit 0。

本轮只做“接入”：Eira 的 48 个角色帧和 Crooked Witch 的人物/FX 已经批准，不要重新生成、
改版本、改动作或改帧数；只做运行时导入、数据、代码、AI、调试、smoke 和游戏内预览。
按本文 §6 的 Q1–Q18 一次性 grill 我；★ 项必须确认，○ 项如果没有异议就按建议值。
我确认后先把答案回填 §7，再按 §8 的顺序实施；未确认前不要改代码/JSON/运行时素材。

约束：不修改 instruction.docx、Image/、UI Resources/、sketch/、其他角色/敌人、背景/BGM；
不用 pytest；验证用 --smoke-test、F1/F2/F6/F7/F8/F9 和游戏内预览；
不要 commit/push，除非我明确要求。文档更新等实现和验证完成后按 AGENTS.md 再问一次。
```

---

## 1. 本轮范围

### 1.1 做

- **Eira（可玩角色）**：LMB 雪球、RMB 杖击、Q 穿透冰片、E 选区冰球、冰冻值被动、
  冰冻/减速/冻结演出、攀爬、基础移动、HUD/调试、F7 角色轮换、smoke。
- **Crooked Witch（F7 敌人）**：瞬移被动、一次性治疗、闪电、冰锥、药瓶/毒区、火雨、
  专属场景、AI、HUD/调试、F7 敌人轮换、smoke。
- 两套角色帧/FX 从 `assets/generated/contact_sheets/` 导入到 `assets/frames/`，接入
  `stats.json` / `attacks.json` / `animations.json` / `roster.json` / `debug.json` /
  `config.py` / 新类 / `scene.py` / `status.py` / `combat.py` / `projectile.py` /
  `fx.py` / `debug.py` / `main.py`。
- 游戏内预览：Eira 对 Dummy 的四技能 + 冻结测试；Crooked Witch 的瞬移/治疗/四技能。

### 1.2 不做

- 不重画、不重排、不换版本任何已批准的 Eira / Crooked Witch 帧。
- 不修改 Lina / Nyra / Rhea / Shadow Ninja / 其他敌人 / 背景 / BGM。
- 不做全游戏 UI、商店、等级、存档、剧情；不新增与本次无关的系统。
- 不改 `instruction.docx`、`Image/`、`UI Resources/`、`sketch/`。
- 不用 pytest；不 commit/push，除非用户明确要求。
- 不在实现和验证完成前更新 README / DESIGN_DECISIONS / DEBUG / ASSET_PIPELINE。
  动画设计文档的已确认帧表也不要改；实现细节写进新文档（用户确认后再写）。

---

## 2. 当前仓库快照（代码事实）

### 2.1 已经完成、可参考的同类实现

| 能力 | 位置 | 备注 |
|---|---|---|
| 可玩角色输入/移动/攀爬 | `game/lina.py`、`game/nyra.py`、`game/rhea.py`；`game/fighter.py` | Lina 有能量/变身，Nyra/Rhea 是更接近 Eira 的模板 |
| 敌人 AI/技能 | `game/warrior.py`、`game/creepy_shooter.py`、`game/mech_crab.py`、`game/shadow_ninja.py` | Mech-Crab 的远程/近战/阶段机；Shadow Ninja 的 custom timeline/无敌/无 hitbox |
| 状态 | `game/status.py` | **已支持** `freeze`、`slow`、`burn`、`poison`、`stun`、`super_armor`、`damage_reduction`；**没有** `vulnerable` |
| 伤害 | `game/combat.py` `resolve_hit` / `resolve_projectile_hit` | 先算 `damage_reduction`；易伤需要新增乘区 |
| 投射物 | `game/projectile.py` | `ShurikenProjectile` 已有 `pierces_targets` / `hit_target_ids` / `penetrates_blocks` |
| 动画 | `game/animation.py` | `set_clip` / `set_frame` / `missing_paths`；`flame_clips` 是第二套表，Eira/Witch 不需要 |
| 场景/敌人轮换 | `game/scene.py` | F7 按 `roster.json` 的 `enemies` 顺序轮换；`[`/`]` 按 `characters` 顺序 |
| 输入 | `game/input.py`；`main.py` 事件循环 | LMB=`punch`，RMB=`kick`，Q=`q`，E=`e`；**没有鼠标世界坐标** |
| 调试 | `game/debug.py`；`scene.handle_debug_key` | F1 hurtbox，F2 面板，F6 时间，F7 敌人，F8 AI，F9 重置，V/C/X/Z 技能槽 |
| smoke | `main.py:52` `_smoke_test` | Phase A–I；Phase I 是 Shadow Ninja 幻影形态；最后统一 `and` 所有 flags |

### 2.2 目前不存在的东西

- 没有 `game/eira.py`、`game/crooked_witch.py`。
- 没有 `assets/frames/eira/`、`assets/frames/crooked_witch/`。
- `stats.json`、`attacks.json`、`animations.json`、`roster.json`、`debug.json`、`config.py`
  都没有 Eira / Crooked Witch 的条目。
- 没有 Eira / Crooked Witch 的 smoke flags。
- `PLAYABLE_CLASSES` 目前是 `("lina", "nyra", "rhea")`；`ROSTER_CLASSES` /
  `ANIMATED_CLASSES` 有 9 个类，不含 Eira / Crooked Witch。

### 2.3 当前 F7 / 角色顺序

- F7 敌人顺序（`roster.json` 顺序）：
  Warrior → Veno → Bat → Creepy Shooter → Mech-Crab → Shadow Ninja → Dummy。
- 可玩角色顺序（`roster.json` 顺序）：
  Lina → Nyra → Rhea。
- 本轮建议：Eira 追加到 Rhea 之后；Crooked Witch 追加到 Shadow Ninja 之后、Dummy 之前。
  这样 F7 变为 `... → Shadow Ninja → Crooked Witch → Dummy`，角色轮换变为
  `Lina ↔ Nyra ↔ Rhea ↔ Eira`。

### 2.4 可以复用的关键机制

- `scene.targets_for()` 已经会过滤 `phantom_form`；本轮建议扩展为同时过滤
  `getattr(target, "no_hitbox", False)`，用于 Witch 的治疗/火雨/瞬移隐藏段。
- `ShurikenProjectile` 的 `pierces_targets` / `hit_target_ids` 可直接用于 Eira Q 的穿透。
- `StatusSet.slow_factor()` 已在 Lina / Nyra / Rhea / Warrior / Veno / Bat 的移动中调用；
  Eira 和 Witch 也必须调用，否则减速不生效。
- `StatusSet.control_locked()` 已包含 `freeze`；冰冻状态可以直接复用，但需要独立的
  冰壳/碎冰演出。
- `main.py` 的 smoke 用固定 tick + 直接改字段验证；Eira / Witch 的定时器要能被 smoke
  手动推进，不要依赖真实时间。

---

## 3. 已批准素材清单

### 3.1 Eira Frostveil（48 个角色帧）

**Base**

- 侧身：`assets/generated/base/eira_side_base.png`（RGBA 1254×1254）。
- 背身攀爬：`assets/generated/base/eira_back_base.png`（RGBA 1254×1254）。
- 原始形象：`Image/Character/eira-frostveil-256.png`（只作身份参考，不要直接当运行时帧）。

**已确认版本与帧表**

> 下表源路径省略 `assets/generated/contact_sheets/` 前缀；例如 `eira_idle/...` 即
> `assets/generated/contact_sheets/eira_idle/...`。

| 动作 | 版本 | 帧数 | 每帧时长 | 源文件夹 / 文件 | 备注 |
|---|---|---:|---|---|---|
| `idle` | v1 | 4 | 0.20 | `contact_sheets/eira_idle/eira_idle_v1_00..03.png` | 循环 |
| `walk` | **v2** | 6 | 0.12 | `eira_walk/eira_walk_v2_00..05.png` | 循环 |
| `jump` | **v6** | 2 | 0.20 | `eira_jump/eira_jump_v6_00..01.png` | 上升/下落两帧，不循环 |
| `crouch` | v1 | 1 | — | `eira_crouch/eira_crouch_v1_00.png` | 保持；裁到高位弹道下方 |
| `climb` | **v3** | 4 | 0.12 | `eira_climb/eira_climb_v3_00..03.png` | 背身；登梯循环 |
| `hurt` | v1 | 2 | 0.10 | `eira_hurt/eira_hurt_v1_00..01.png` | 胸肩后顿→回稳 |
| `stun` | v1 | 1 | — | `eira_stun/eira_stun_v1_00.png` | 保持；星星独立 |
| `ko` | **v4** | 4 | 0.15 / 0.20 / 0.25 / 0.30 | `eira_ko/eira_ko_v4_00..03.png` | 末帧保持 |
| `snowball` | v1 | 4 | 0.10 / 0.10 / 0.08 / 0.16 | `eira_snowball/eira_snowball_v1_00..03.png` | 0.44s；02 帧发射（t=0.20） |
| `staff_strike` | **v2** | 5 | 0.10 / 0.10 / 0.08 / 0.08 / 0.18 | `eira_staff_strike/eira_staff_strike_v2_00..04.png` | 0.54s；02–03 共用 0.20–0.36 近战判定 |
| `ice_shard` | v1 | 5 | 0.12 / 0.10 / 0.08 / 0.08 / 0.18 | `eira_ice_shard/eira_ice_shard_v1_00..04.png` | 0.56s；02 帧发射（t=0.22） |
| `e_raise` | v1 | 3 | 0.12 / 0.14 / 0.14 | `eira_e_raise/eira_e_raise_v1_00..02.png` | 0.40s |
| `e_hold` | v1 | 2 | 0.18 | `eira_e_hold/eira_e_hold_v1_00..01.png` | 循环，等 LMB 选区 |
| `e_release` | v1 | 3 | 0.08 / 0.10 / 0.12 | `eira_e_release/eira_e_release_v1_00..02.png` | 0.30s；选定后 0.08s 生成冰球 |
| `e_recover` | v1 | 2 | 0.12 / 0.18 | `eira_e_recover/eira_e_recover_v1_00..01.png` | 0.30s；选定后 0.60s 回 idle |

**Eira 独立 FX（不烘焙进角色帧）**

| 用途 | 文件 | 帧数/时长 | 备注 |
|---|---|---|---|
| 雪球释放 | `eira_snowball_v1_fx_release.png` | 1 / 0.06s | 杖尖闪光 |
| 雪球弹体 | `eira_snowball_v1_fx_projectile.png` | 1 | pivot 184,64 |
| 雪球命中 | `eira_snowball_v1_fx_impact_00..03.png` | 4 / 0.04/0.05/0.06/0.07 | pivot 128,128 |
| 冰片蓄光 | `eira_ice_shard_v1_fx_charge_00..02.png` | 3 / 0.03/0.03/0.04 | pivot 84,112 |
| 冰片释放 | `eira_ice_shard_v1_fx_release_00..01.png` | 2 / 0.03/0.03 | pivot 92,68 |
| 冰片弹体 | `eira_ice_shard_v1_fx_projectile.png` | 1 | pivot 170,56；tip 242,56；三角尖端朝前 |
| 冰片普通命中 | `eira_ice_shard_v1_fx_hit_00..03.png` | 4 / 0.04/0.05/0.06/0.07 | pivot 108,96 |
| 冰片冻结命中 | `eira_ice_shard_v1_fx_frozen_hit_00..03.png` | 4 / 0.04/0.05/0.06/0.07 | pivot 120,116；范围更大 |
| 杖击弧光 | `eira_staff_strike_v2_fx_02.png`、`_03.png` | 2 | 与 0.20–0.36 判定同步 |
| E 蓄光 | `eira_e_release_v1_fx_charge_00..02.png` | 3 / 0.09/0.09/0.10 | pivot 96,128 |
| E 冰球 | `eira_e_release_v4_fx_ball.png` | 1 | pivot 256,256；art radius 219；完整直到触地 |
| E 下坠尾迹 | `eira_e_release_v1_fx_fall_trail.png` | 1 | pivot 160,302 |
| E 普通命中 | `eira_e_release_v1_fx_hit_00..02.png` | 3 / 0.05/0.07/0.10 | pivot 128,112 |
| E 冻结命中 | `eira_e_release_v1_fx_frozen_hit_00..02.png` | 3 / 0.05/0.07/0.10 | pivot 144,128 |
| E 落地 | `eira_e_release_v1_fx_ground_00..03.png` | 4 / 0.05/0.07/0.09/0.12 | pivot 288,246 |
| E 小碎片 | `eira_e_release_v1_fx_fragment_00..02.png` | 3 | pivot 26,26；从命中/触地起 3s |
| E 四块大冰 | `eira_e_release_v2_fx_chunk_00..03.png` | 4 | pivot 208,176；触地后约 0.74s 落定；3s |

**关键 manifest**

- `eira_snowball/eira_snowball_v1_manifest.json`
- `eira_ice_shard/eira_ice_shard_v1_manifest.json`
- `eira_e_release/eira_e_release_v4_manifest.json`
- `eira_e_release/eira_e_release_v2_manifest.json`（四块大冰）
- E 的完整时序：`e_raise` 0.40s → `e_hold` 循环等 LMB → 选定 → 0.08s 后冰球生成 →
  `e_release` 0.30s → `e_recover` 0.30s（选定后 0.60s 回 idle）。

### 3.2 Crooked Witch（人物 + FX）

**Base**

- 唯一参考：`assets/generated/contact_sheets/crooked_witch_base/crooked_witch_base_v4_02.png`
  （RGBA 1254×1254）。旧 A–D、v2、v3、v4_01 只留档，不再作为生成基准。
- 原始形象：`Image/Enemy/crooked-witch-256.png`（身份参考，不要直接当运行时帧）。

**已确认人物版本与帧表**

> 下表源路径省略 `assets/generated/contact_sheets/` 前缀；例如 `crooked_witch_idle/...`
> 即 `assets/generated/contact_sheets/crooked_witch_idle/...`。

| 动作 | 版本/源文件 | 帧数 | 每帧时长 | 备注 |
|---|---|---:|---|---|
| `idle` | `crooked_witch_idle_v1_00..03.png` | 4 | 0.18 | 0.72s 循环 |
| `walk` | `crooked_witch_walk_v1_00..04.png` + `crooked_witch_walk_v3_05.png` | 6 | 0.16 | 0.96s 循环；只有 05 用 v3 |
| `fly` | `crooked_witch_fly_v3_00..05.png` | 6 | 0.18 | 00/01 起飞；**02/03 循环**；04/05 返回落地 |
| `teleport_out` | `crooked_witch_teleport_out_v1_00..02.png` | 3 | 0.10 | 0.30s；人物完整、不缩小 |
| `teleport_in` | `crooked_witch_teleport_in_v1_00..02.png` | 3 | 0.10 | 0.30s；02 落到 v4_02 base |
| `hurt` | `crooked_witch_hurt_v2_00.png` + `crooked_witch_hurt_v1_01.png` | 2 | 0.10 | 0.20s |
| `ko` | `crooked_witch_ko_v1_00..02.png` + `crooked_witch_ko_v2_03.png` | 4 | 0.15/0.20/0.20/0.20 | 0.75s；末帧保持 |
| `heal` | 逻辑 00–05：`heal_v3_00`、`heal_v5_01`、`heal_v4_01`、`heal_v2_02`、`heal_v2_03`、`heal_v1_04` | 6 | 0.20/0.20/0.20/2.50/2.50/0.20 | 合计 5.8s；03/04 是 5s 维持；法杖是独立悬浮道具 |
| `lightning_forward` | `crooked_witch_lightning_v2_00..03.png` | 4 | 0.15/0.15/0.10/0.20 | 0.60s；02 帧（t=0.30）发射 |
| `lightning_up` | `crooked_witch_lightning_up_v1_00..03.png` | 4 | 0.15/0.15/0.10/0.20 | 同上，斜上 |
| `lightning_down` | `crooked_witch_lightning_down_v5_00..03.png` | 4 | 0.15/0.15/0.10/0.20 | 同上，斜下 |
| `ice_spike` | `crooked_witch_ice_spike_v1_00..03.png` | 4 | 0.15/0.15/0.10/0.20 | 0.60s；02 帧（t=0.30）放预警圈 |
| `potion` | `crooked_witch_potion_v2_00..03.png` | 4 | 0.15/0.15/0.15/0.20 | 0.65s；02 帧（t=0.30）召出药瓶 |
| `fire_rain` | 00：`crooked_witch_fire_rain_v2_00.png`；01–04：`crooked_witch_fire_rain_v6_01..04.png` | 5 | 见下 | 00 侧身悬浮，01 转向，02 正面双手，03 杖置身前，04 高举；04 维持并叠加 v7 光柱 |

**治疗完整时序（已确认的 6.2s 施法段）**

- 飞到中央后：逻辑 00→01→02，每帧 0.20s（0.60s）。
- 逻辑 03/04 张臂维持 **5.0s**；每秒一轮 `heal_fx_v2`，共 5 轮；每秒结算 6% 最大生命。
- 7.50–7.90s 悬浮法杖回手；7.90–8.10s 逻辑 05 重新握杖；之后接 fly 返回。
- 法杖：`crooked_witch_heal_staff_prop_v1.png`，独立绘制/悬浮，不烘焙进人物帧。

**火雨时序**

- 飞到中央 → 00→01→02→03→04（v2 sheet 的节奏：0.22/0.26/0.25/0.26/0.40s；
  若与已确认的完整预览冲突，以完整预览和 `fire_rain_v6_sheet` 为准）。
- 04 维持；`v7_pulse` 45 帧：00–23 每帧 0.04s（0.96s 淡入蓄亮），24 为 0.04s 峰值，
  25–44 每帧 0.02s（0.4s 淡入光柱），44 为固定保持帧。
- 火球每 **0.8s** 一颗，共 10 颗；每颗生成时取目标当前 x，随后竖直下落。
- 火雨人物帧 01/02 画布 1536×1536，03/04 为 1536×1792；**不要逐帧缩放人物**。

**Crooked Witch 独立 FX**

| 用途 | 文件 | 帧数/时长 | 备注 |
|---|---|---|---|
| 瞬移消失 | `crooked_witch_teleport_fx_v1_out_00..05.png` | 6 / 0.10 | 紫金法环；与人物分层 |
| 瞬移出现 | `crooked_witch_teleport_fx_v1_in_00..05.png` | 6 / 0.10 | 紫金法环 |
| 治疗 | `crooked_witch_heal_fx_v2_00..19.png` | 20 / 0.05 = 1s/轮，共 5 轮 | 从腰部升到头颈，绿色加深；不要飘过帽顶 |
| 闪电（前/上/下） | `crooked_witch_lightning_fx_v2_{forward,up,down}_00..05.png` | 各 6 / 0.06×3 + 0.08/0.10/0.10 = 0.46s | 从实际杖尖发出；00–02 是新增起电段 |
| 冰锥预警 | `crooked_witch_ice_warning_v1_00..04.png` | 5 / 0.20 = 1s | 蓝圈；满 1s 后接冰锥 |
| 冰锥 | `crooked_witch_ice_spike_fx_v1_00..06.png` | 7 / 约 0.10 | 破地→生长→峰值→碎裂→消散 |
| 药瓶弹体 | `crooked_witch_potion_projectile_v1_00..02.png` | 3 | 00→01→02→01 轻摆 |
| 药瓶碎裂 | `crooked_witch_potion_break_v1_00..03.png` | 4 | 直击/落地/路径尽头 |
| 毒区 | `crooked_witch_poison_pool_v1_00..03.png` | 4 | 00 初生，01/02 循环，03 退场；寿命待定 |
| 火雨施法 | `crooked_witch_fire_rain_v7_pulse_00..44.png` | 45 | 512×1280；杖顶连接点 256,1216 |
| 火球 | `crooked_witch_fireball_v1_00.png` | 1 | 尾焰上拖 |
| 火球落地/命中 | `crooked_witch_fire_impact_v1_00..03.png` | 4 / 0.08/0.10/0.12/0.14 | 爆开、火星消散 |

**专属场景（docx P281–P282）**

- 专属场景图是 1267×792 的白底线稿：**左右各一个 short platform，各接一条 long ladder，
  没有 barrier，画面左右对称**。
- 建议运行配置（待 Q12 确认）：

```json
"crooked_witch": {
  "ground_y": 620,
  "walls": [90, 1190],
  "lane_heights": {"high": 180, "fist": 142, "mid": 120, "low": 60},
  "land_margin": 8,
  "blocks": [
    {"kind": "platform", "rect": [158, 220, 314, 78], "surface_y": 220,
     "sprite": "platform_tropical_short.png", "sprite_rect": [158, 206, 314, 96]},
    {"kind": "platform", "rect": [808, 220, 314, 78], "surface_y": 220,
     "sprite": "platform_tropical_short.png", "sprite_rect": [808, 206, 314, 96]}
  ],
  "ladders": [
    {"rect": [420, 220, 64, 400], "top_y": 220, "bottom_y": 620,
     "sprite": "ladder_tropical_wood.png", "sprite_rect": [388, 220, 128, 400]},
    {"rect": [796, 220, 64, 400], "top_y": 220, "bottom_y": 620,
     "sprite": "ladder_tropical_wood.png", "sprite_rect": [764, 220, 128, 400]}
  ],
  "player_spawn": [280, 620],
  "dummy_spawn": [600, 620],
  "warrior_spawn": [600, 620],
  "veno_spawn": [820, 620],
  "bat_spawn": [820, 470],
  "crooked_witch_spawn": [965, 220],
  "teleport_points": [[315, 220], [965, 220], [315, 620], [965, 620]]
}
```

- 四点含义：左平台上、右平台上、左平台正下方地面、右平台正下方地面。
- `Stage` 目前只把 `*_spawn` 收进 `spawns`；需要新增 `self.teleport_points =
  [tuple(p) for p in stage_cfg.get("teleport_points", [])]`，不要写死在 Witch 类里。

### 3.3 运行时画布 / pivot / body（建议值）

| 角色 | 画布 | pivot | body | hurtbox | 说明 |
|---|---|---|---:|---|---|
| Eira | 384×384 | (192,372) | 214 | 站立 56×210，蹲下 56×130 | 与 Rhea/Shadow Ninja 同规格；举杖帧若放不下，**停下问用户**，不要缩小人物 |
| Crooked Witch | 640×640 | (320,628) | 230 | 站立 56×210，蹲下 56×210 | 与 Mech-Crab 同画布；帽檐/高举法杖较高，640 是建议值；放不下先问 |

- Eira 的 `climb` 使用背身 base；`Fighter.climb_draw_scale` 默认 1.2，Eira 可能需要单独
  调整；接入时在游戏内对比站立帧，确认后写 `self.climb_draw_scale`。
- Witch 没有 jump / crouch / climb；`fly` 只用于治疗和火雨；普通移动只用 `walk`。
- 所有帧必须保持同一 base 的头身比、脚底基线、法杖/帽子尺寸；不要按每帧 alpha bbox
  自动缩放。`tools/import_frames.py` 出现 `FIT` 就是自动缩小，**不要接受**，停下来问用户。

### 3.4 运行时目录与导入

建议运行时路径：

```text
assets/frames/eira/<clip>/<clip>_00.png ...
assets/frames/eira/fx/<fx_name>_00.png ...
assets/frames/crooked_witch/<clip>/<clip>_00.png ...
assets/frames/crooked_witch/fx/<fx_name>_00.png ...
```

导入命令模板（先 `--dry-run`，检查没有 `FIT`/`MISSING`）：

```bash
.venv/Scripts/python.exe tools/import_frames.py \
  --action idle \
  --src assets/generated/contact_sheets/eira_idle \
  --base assets/generated/base/eira_side_base.png \
  --body-height 214 --canvas 384 --pivot-x 192 --pivot-y 372 \
  --order eira_idle_v1_00.png,eira_idle_v1_01.png,eira_idle_v1_02.png,eira_idle_v1_03.png \
  --expect 4 --anchor feet \
  --out assets/frames/eira/idle --dry-run
```

- 混合版本用 `--order` 明确列出源文件（walk、heal、lightning、fire_rain 等）。
- 角色帧导入后用 `tools/contact_sheet.py` 复核脚底/头顶/法杖，再在游戏内预览。
- FX 不需要归一化到 384/640；按 manifest 的 pivot 和原生尺寸复制到 `fx/`，由 FX 类缩放绘制。
- 不要用 `Image/Character/...` 或 `Image/Enemy/...` 直接当运行时帧；fallback 仍指向原图。

---

## 4. 机制规格

### 4.1 Eira Frostveil（可玩角色）

**基础数值（docx 未给，建议值，Q1 确认）**

- HP 100，`basic_atk` 20，`extra_atk` 0；`move.walk` 240，`jump_v` 760，`gravity` 2200；
  `stage_body_width` 100；hurtbox 56×210 / 56×130。
- 冷却：Q 3.0s，E 12.0s（docx 明确）。
- Eira 没有能量/变身；不要复用 Lina 的 `flame_time`。

**被动：冰冻值**

- **每个敌人独立**计算；Eira 在目标身上存一个 0–99 的冰冻值（建议 `target.eira_freeze`，
  重置/换角色时清 0）。
- 攻击命中增加对应冰冻值：LMB +20，RMB +20，Q +30，E +50。
- 冰冻值 ≥100：目标 **冻结 2.0s**，冰冻值清零；冻结期间**停止积累**，解冻后恢复。
- 获得冰冻值时，对**被攻击目标**施加等量百分比减速：
  - 例如 +20 → 20% 减速，`slow` 的 `value` 用 **0.8**（`slow_factor` 返回乘数）；
  - +30 → 0.7；+50 → 0.5。
- 建议合并规则（Q5）：保留**最强减速**，每次获得冰冻值时刷新持续时间；不叠加多个 slow。
- 减速持续时间建议 2.0s；与冻结 2.0s 对齐，冻结结束后自然解除；如果用户要更长，改配置。
- 冻结期间不再获得冰冻值，也不再施加新的减速；解冻后从 0 开始重新积累。
- 冻结是 `StatusSet` 的 `freeze`（已在 `CONTROL_EFFECTS`）；`super_armor` 免疫控制，
  但伤害照常结算；`slow` 也被 `IMMUNE_EFFECTS` 免疫。
- 冻结演出：目标保持当前姿势 + 半透明冰壳；解冻时播放碎冰。**目前没有已批准的冰壳图**
  （Q6）；不要用角色帧冒充，建议程序化冰蓝覆盖 + 复用 `frozen_hit` 碎冰，或先问用户是否补图。

**LMB 雪球**

- 动作 `snowball` 0.44s；t=0.20 从杖尖蓝晶中心发射高位水平雪球。
- 雪球伤害建议 1.0 atk（20），+20 冰冻值；命中后播 4 帧雪屑。
- 高位（lane high）：站立可中，蹲下可躲；遇到平台/障碍按通用规则消失（不穿 block）。
- 雪球只命中第一个敌人；命中后消失。

**RMB 杖击**

- 动作 `staff_strike` 0.54s；02–03 帧共用 **0.20–0.36s** 一次近战判定。
- 伤害建议 1.2 atk（24），+20 冰冻值；同一目标只结算一次。
- 近程；判定盒建议 `[18,-165,90,105]`（相对脚底），击退 50，hitstop 0.05。
- 杖弧用 `eira_staff_strike_v2_fx_02/03`，不烘焙进人物帧。

**Q 冰片**

- 动作 `ice_shard` 0.56s；t=0.22 发射高位三角冰片。
- 冷却 3.0s；冰片**穿透敌人**，对每个敌人只结算一次；遇到平台/障碍消失（不穿 block）。
- 伤害建议 1.5 atk（30），+30 冰冻值；对**已冻结**目标额外 +50% 伤害（45）。
- 顺序：**先看冻结 → 伤害 → 积累冰冻值**；触发冻结的这一击按命中前状态算，不享受额外伤害。
- 普通命中播 `hit` 4 帧，冻结命中播 `frozen_hit` 4 帧；冰片继续飞行。

**E 巨型冰球**

- 冷却 12.0s；动作：`e_raise` 0.40s → `e_hold` 循环 → LMB 选区 → `e_release` 0.30s +
  `e_recover` 0.30s（选定后 0.60s 回 idle）。
- 举杖后屏幕显示原文：`Click the left mouse to choose an area.`；建议顶部居中。
- 细竖线提示当前鼠标世界 x；LMB 确定 x 后隐藏提示；只选水平方向。
- 选定后 **0.08s** 在上方生成冰球；冰球沿锁定 x 竖直下落，从最高点到地面约 **1.0s**。
- 冰球**不会被 block 阻挡**（穿过平台/障碍）；**命中敌人不会消失**，继续下落，可命中多个敌人。
- 每个敌人只结算一次；伤害建议 3.0 atk（60），+50 冰冻值；已冻结目标额外 +100%（120）。
- 顺序同样是：先看冻结 → 伤害 → 积累冰冻值；冻结目标不再加冰冻值。
- 命中敌人：播 `hit` / `frozen_hit`，主球继续下落；冰屑从命中起显示 3s。
- 触地：主球出现深色裂纹约 0.06s → 分成四块大冰（v2 chunk），向两侧弹开并落定；
  大冰和冰屑从触地起显示 3s。**只有大冰球造成伤害；四块大冰是演出，不额外结算。**
- 冰球落点是 `stage.ground_y`，不是平台顶；不要让它停在平台上。
- E 的取消/冷却/吟唱期间是否可被攻击见 Q4；默认建议：吟唱期间可被攻击，受伤取消 E 并
  进入完整 12s 冷却；RMB 可取消；超过 8s 未选区自动取消。

**Eira 输入/状态机建议**

- 用 `FighterState.ATTACK` + 自定义子阶段（`e_phase = raise/hold/release/recover`），不要新增
  `FighterState` 枚举，避免影响所有角色。
- `E` 进入举杖；`e_hold` 期间只处理 LMB 选区和取消，不移动/不普通攻击。
- LMB 选区需要 `scene.mouse_x`（世界坐标；当前 1280×720 无滚动，屏幕 x 即世界 x）。
  在 `main.py` 的 `MOUSEBUTTONDOWN` / `MOUSEMOTION` 更新；smoke 直接设 `scene.mouse_x`。
- `Eira.take_hit` 被击中时清 E 子阶段和冰球蓄力；`reset` 清 `eira_freeze`、减速、E 状态。
- 攀爬：复用 `Fighter.try_start_climb` / `_update_climb`，`climb` 用背身 v3；确认
  `climb_draw_scale` 后写死。

**Eira 打击回调**

- 伤害和冻结积累分开，避免重复扣血：
  1. 伤害在 `resolve_hit` / `resolve_projectile_hit` / E 冰球自定义 helper 里结算；
     如果目标**命中前**已冻结，按 Q2 的倍率在**扣血前**乘 `1 + bonus_vs_frozen`；
  2. 扣血之后再调 `Eira.apply_freeze(target, amount, was_frozen)`，只负责：
     - 如果 `was_frozen`：不积累、不加新减速；
     - 否则 `target.eira_freeze += amount`；施加/刷新最强 slow；
     - 如果 ≥100：`target.statuses.add("freeze", 2.0)`，`target.eira_freeze = 0`。
- LMB/RMB 用 `on_hit_success` / `on_projectile_hit` 调它；Q 的穿透对每个目标调它；
  E 冰球对每个命中目标调它。
- Q 的“已冻结额外伤害”用 `bonus_vs_frozen` 字段（在扣血前乘）；E 的“已冻结额外大量伤害”
  在 E 冰球的自定义 helper 里扣血前乘；**不要在 `on_hit_success` 里补伤害**（那时已经
  `take_hit` 了）。

### 4.2 Crooked Witch（F7 敌人）

**基础数值**

- HP 400，ATK 30（docx 明确）；`basic_atk` 30，`extra_atk` 0。
- 移动：walk；没有 jump / crouch / climb；普通移动不飞；`fly` 只用于治疗/火雨。
- hurtbox 建议 56×210，`stage_body_width` 100（Q17 可改）。
- 她的技能标题括号 2s / 5s / 8s / 15s **没有明写 CD**；建议当作冷却使用（Q9），
  冷却从技能开始施放时计时。

**被动：瞬移（8s）**

- 四个固定点（专属场景）：左平台上、右平台上、左平台正下方地面、右平台正下方地面。
- 触发：
  - 受到伤害时优先瞬移（如果被动可用）；
  - 瞬移后 8s 内没有受到伤害，自动瞬移到另一个位置。
- 目标点：从四个点里**排除距离最近的点**，在其余三个里随机；不要选当前点。
- 建议解释（Q3）：8s 是瞬移的冷却/间隔；受伤时若冷却已好就立即瞬移；若 8s 内没受伤，
  冷却好了也自动瞬移。这样“优先受伤触发”和“8s 没受伤再传”都能成立。
- 瞬移表现：`teleport_out` 3×0.10 → 位置切换 → `teleport_in` 3×0.10；FX 各 6×0.10。
  建议整段（消失到出现）`invincible=True`、`no_hitbox=True`、不画人物或画法环；
  出现在新位置后恢复可被击中。若用户希望瞬移不是无敌，改 Q3。
- 治疗/火雨期间不瞬移；被控制/冻结时不瞬移（或先解除控制再传，按 Q3）。

**治疗（只触发一次，强制）**

- 第一次 HP **低于 50%** 时强制触发；打断当前动作；整个治疗+往返期间
  `invincible=True`、`no_hitbox=True`、不受控制。
- 飞到屏幕中央（建议 x=640；高度见 Q12/Q4），双手张开，绿色粒子。
- 每秒恢复 **6% 最大生命**，持续 **5s**，每秒结算：5 次 × 24 = 120 HP（30% 最大生命），
  不超过 max HP。建议在到达中央后开始第 1 秒，t=1..5 各结算一次。
- 结束后飞回**触发时的原位置**；回程同样无敌/无 hitbox。记录 `heal_return_pos`。
- 治疗方案见 §3.2 的 6.2s 时序；法杖独立悬浮，治疗 FX 每秒一轮共 5 轮。
- `heal_used` 每场一次；F7/F9/reset 清回 false。

**技能 1：闪电（2s）**

- 动作 0.60s；02 帧（t=0.30）发射；1.2 atk = 36。
- 三种情况：
  1. 目标与 Witch **同一高度**：向前方水平发射高位闪电（远、高）；
  2. 不同高度，且 x 不相近：闪电初方向为 Witch 指向目标的方向，之后沿该方向直线前进；
     会被 block 阻挡；
  3. 不同高度且 x 相近，或闪电会被 block 阻挡：**不释放**。
- “同一高度”建议用脚底 y 差 ≤ 80px；“x 相近”建议 ≤ 140px；被 block 阻挡用
  `stage.segment_hits_blocks(staff_tip, endpoint)` 预判；如果线段碰到平台/障碍则不施放。
- 命中造成 36 伤害，并给目标 **20 易伤**，最多 3 层；先结算伤害（按攻击前的易伤层数），
  再叠加一层。建议每层 +20% 受到伤害，持续 6s，新层刷新全部层数的持续时间（Q5）。
- 易伤是新的 `vulnerable` 状态：`StatusSet` 新增 `vulnerable_amount()`；
  `resolve_hit` / `resolve_projectile_hit` 在 `damage_reduction` 后乘 `1 + vulnerable_amount()`。
  易伤不是控制，不被 `super_armor` 免疫。
- 闪电是高速直线投射物，不是瞬发 hitscan；用 `lightning_fx_v2` 的 6 帧演出；三种方向
  分别对应三条人物 clip / 三个 FX 方向。

**技能 2：冰锥（5s）**

- 动作 0.60s；02 帧（t=0.30）在选定点放蓝色预警圈；预警圈满 **1.0s** 后冰锥破地。
- 选点：与目标**同一高度**的地面或 platform，目标附近、**靠近 Witch 一侧**。
  建议：从目标脚底向 Witch 方向偏移 80px，夹到该 surface 的可用范围；没有合法 surface
  就不释放（或退化为目标脚下，Q6）。
- 预警圈 5×0.20s；冰锥 FX 7 帧；冰锥出现时对圈内目标造成 **atk = 30** 伤害 +
  **冻结 1.5s**；先伤害后冻结。冻结使用同一个 `freeze` 状态；Eira 也会被冻。
- 预警期间玩家可以走出圈；冰锥判定建议半径 60–70px，覆盖圈的大部分。
- 这是一个独立的 `IceSpikeHazard`： Witch 动作结束后继续存在，1s 后触发；不要只靠
  `AttackRuntime` 的 duration。

**技能 3：药瓶（8s）**

- 动作 0.65s；02 帧（t=0.30）在杖尖前召出药瓶。
- Witch 在 platform 上：药瓶受重力，向前下方抛物线，落到地面/platform 后碎裂。
- Witch 在地面：药瓶沿低位水平方向前进（远程、低），到路径尽头或撞到 block 后碎裂。
- 直击目标：0.8 atk = 24 伤害 + 毒伤 + 减速；**不生成毒区**。
  - 毒伤建议：3% 最大生命，持续 3s（总伤害 12 HP；`dps = 12/3 = 4`），每 0.5s 结算；
  - 减速 30%，持续 3s。
- 未命中（落地/路径尽头）：生成绿色毒区；玩家踩入后：
  - 毒伤 2% 最大生命，持续 3s（总伤害 8 HP；`dps = 8/3`），每 0.5s 结算；
  - 减速 20%，持续 3s；
  - 毒区寿命建议 6s（Q7）；玩家在毒区内时刷新毒伤/减速到 3s。
- 药瓶弹体 3 帧轻摆；碎裂 4 帧；毒区 4 帧循环。直击/落地的破碎 FX 都要播。
- 毒伤用 `StatusSet.add_poison(source="witch_potion", duration=3.0, dps=...)`；
  减速用 `statuses.add("slow", 3.0, value=0.7/0.8)`；命中/毒区用不同 source 或同一 source，
  但不要把直击毒和毒区毒叠加到超过 3s（Q7 确认合并规则）。

**技能 4：火雨（15s）**

- 整个技能期间 `invincible=True`、`no_hitbox=True`、不受控制；飞到屏幕中央，举杖，
  召 10 颗火球后飞回原位；回程同样无敌/无 hitbox。
- 火球每 **0.8s** 一颗，共 10 颗；生成时取目标当前 x，之后竖直下落，**不追踪**目标横向移动。
- 火球无视 block，直到到达地面或命中目标才消失；命中造成 **1.2 atk = 36** + 灼烧。
- 灼烧数值 docx 未定；建议复用 `stats.combat.burn_dps=5.0`、`burn_duration=3.0`
  （Q8）；如果觉得太弱，改 Witch 专用 burn，不动 Lina。
- 技能时长约 15.3s（飞入 ~1.2 + 举杖/蓄力 ~? + 10×0.8 + 收杖/飞回）；冷却从施放开始计时，
  还是结束后计时见 Q8。建议从施放开始（与现有敌人一致）。
- 火雨施法光柱用 v7 pulse 45 帧；04 维持时保持光柱；火球/落地 FX 独立。

**AI 建议（Q10）**

- 优先级：治疗（<50%，只一次）> 瞬移（被动）> 技能 4（冷却好且玩家不在极近）>
  技能 3（在 platform 上优先）> 技能 1（有合法直线）> 技能 2（有合法 surface）> 走向目标。
- 普通移动只走；不能跳/蹲/爬；上下平台靠瞬移；到平台边缘不要自己跳下，除非目标在下方
  且技能需要。
- 技能 1 的“会被 block 阻挡”要在施放前算；不合法就不放，避免空放。
- 技能 3 在 platform 上优先；在地面时也可用，但命中率低。
- 技能 4 是长无敌大招；AI 不要在玩家刚死/match over 后开始。
- 受击瞬移的优先级高于当前攻击：如果正在施法且被动可用，是否打断施法瞬移见 Q3；
  建议只在小硬直/受击后瞬移，不打断治疗/火雨。

**Witch 状态/演出**

- `no_hitbox=True` 时 `scene.targets_for` 过滤她，玩家的近战/投射物穿过、不被消耗；
  `invincible=True` 作为第二道保险。
- 瞬移隐藏段建议 `hidden=True`，`Fighter.draw` 跳过人物；法环 FX 独立绘制。
- 治疗/火雨期间不要画 hurtbox（F1）；可以画技能范围/预警。
- 伏击/受击：普通状态可被冻结/眩晕/击退；治疗/火雨期间 `statuses.clear()` 兜底，
  参考 Shadow Ninja 幻影形态的写法。
- 治疗结束回到原位时，如果原位被玩家占据，用 `stage.resolve_overlap` 或就近偏移。

---

## 5. 按文件的接入方案

### 5.1 `game/data/stats.json`

新增：

```json
"eira": {
  "hp": 100,
  "basic_atk": 20,
  "extra_atk": 0,
  "stage_body_width": 100,
  "move": {"walk": 240, "jump_v": 760, "gravity": 2200},
  "cooldowns": {"q": 3.0, "e": 12.0},
  "hurtbox": {"standing": [56, 210], "crouching": [56, 130]},
  "freeze": {"threshold": 100, "duration": 2.0, "slow_duration": 2.0,
             "snowball": 20, "staff": 20, "shard": 30, "ball": 50},
  "ice_ball": {"fall_speed": 740.0, "radius": 80.0, "ground_shard_lifetime": 3.0}
},
"crooked_witch": {
  "hp": 400,
  "basic_atk": 30,
  "extra_atk": 0,
  "stage_body_width": 100,
  "move": {"walk": 150, "jump_v": 700, "gravity": 2200},
  "cooldowns": {"lightning": 2.0, "ice_spike": 5.0, "potion": 8.0, "fire_rain": 15.0},
  "hurtbox": {"standing": [56, 210], "crouching": [56, 210]},
  "teleport": {"cooldown": 8.0, "out_time": 0.30, "in_time": 0.30, "invincible": true},
  "heal": {"threshold_pct": 0.5, "heal_pct_per_sec": 0.06, "duration": 5.0,
           "center_x": 640.0, "center_altitude": 260.0},
  "lightning": {"same_height_tolerance": 80.0, "close_x": 140.0,
                "vulnerable_pct": 0.20, "vulnerable_duration": 6.0,
                "vulnerable_max_stacks": 3},
  "ice_spike": {"warning_time": 1.0, "spot_offset": 80.0, "radius": 65.0,
                "freeze_duration": 1.5},
  "potion": {"hit_poison_pct": 0.03, "zone_poison_pct": 0.02,
             "poison_duration": 3.0, "hit_slow": 0.30, "zone_slow": 0.20,
             "zone_lifetime": 6.0},
  "fire_rain": {"count": 10, "interval": 0.8, "center_x": 640.0,
                "center_altitude": 260.0, "burn_dps": 5.0, "burn_duration": 3.0}
}
```

- 数值都是建议值；`combat` 不动。
- Eira 的 `freeze` 数值可以写进 stats，也可以写死常量；建议写进 stats，smoke 好改。
- Witch 的 `center_altitude` 是“屏幕中央飞行高度”（脚底离地多少），需与动画/场景匹配。

### 5.2 `game/data/attacks.json`

新增（建议值）：

| id | duration | 伤害 | 事件 |
|---|---:|---|---|
| `eira_snowball` | 0.44 | 1.0 atk | projectile t=0.20, `eira_snowball`, lane high, speed 850, range 900, radius 14, knockback 30；命中 +20 冰冻 |
| `eira_staff_strike` | 0.54 | 1.2 atk | hitbox 0.20–0.36, box `[18,-165,90,105]`, knockback 50, hitstop 0.05；命中 +20 冰冻 |
| `eira_ice_shard` | 0.56 | 1.5 atk | projectile t=0.22, `eira_ice_shard`, lane high, speed 950, range 900, radius 14, pierces targets, no block penetration；+30 冰冻；冻结时 +50% 伤害 |
| `eira_ice_ball` | 0.60 | 3.0 atk | 无标准事件；Eira 自定义 E 状态在选定后 0.08s 生成 `IceBall`；+50 冰冻；冻结时 +100% 伤害 |
| `witch_lightning_forward` | 0.60 | 1.2 atk | projectile t=0.30, `witch_lightning_forward`, 高位水平，远；命中后 +1 层易伤 |
| `witch_lightning_up` | 0.60 | 1.2 atk | projectile t=0.30, `witch_lightning_up`, 斜上；命中后 +1 层易伤 |
| `witch_lightning_down` | 0.60 | 1.2 atk | projectile t=0.30, `witch_lightning_down`, 斜下；命中后 +1 层易伤 |
| `witch_ice_spike` | 0.60 | 1.0 atk | 自定义：t=0.30 生成 `IceSpikeHazard`（1s 预警 + 冰锥）；伤害 + 冻结 1.5s |
| `witch_potion` | 0.65 | 0.8 atk | 自定义：t=0.30 生成 `WitchPotionProjectile`；直击毒/减速，未命中毒区 |
| `witch_fire_rain` | 15.32 | 1.2 atk/颗 | 自定义长状态机；10 颗火球，每 0.8s；灼烧 |

- 现有 `attack_damage` 支持 `basic_mult`/`extra_mult`；Eira 用 `basic_mult`，Witch 用
  `basic_mult`/`extra_mult` 同值即可。
- 易伤/冻结的顺序在 `on_hit_success` / `on_projectile_hit` / Hazard 回调里保证：
  伤害先结算，再加状态。
- 如果实现三个 `witch_lightning_*` 攻击，`skill_slots[0]` 可以写一个逻辑 id
  `witch_lightning`，由 `CrookedWitch.force_attack` 按当前高度/x 选择具体攻击；或者
  `skill_slots[0]` 写 `witch_lightning_forward`，AI 自己选。F2 显示建议用逻辑名。

### 5.3 `game/data/animations.json`

新增 `eira_clips` 和 `crooked_witch_clips`，帧路径相对各自的 `frames_dir`。

Eira：

```json
"eira_clips": {
  "idle": {"loop": true, "frames": ["idle/idle_00.png", "..."], "durations": [0.20, 0.20, 0.20, 0.20]},
  "walk": {"loop": true, "frames": ["walk/walk_00.png", "..."], "durations": [0.12, 0.12, 0.12, 0.12, 0.12, 0.12]},
  "jump": {"loop": false, "frames": ["jump/jump_00.png", "jump/jump_01.png"], "durations": [0.20, 0.20]},
  "crouch": {"loop": true, "frames": ["crouch/crouch_00.png"], "durations": [0.20]},
  "climb": {"loop": true, "frames": ["climb/climb_00.png", "..."], "durations": [0.12, 0.12, 0.12, 0.12]},
  "hurt": {"loop": false, "frames": ["hurt/hurt_00.png", "hurt/hurt_01.png"], "durations": [0.10, 0.10]},
  "stun": {"loop": true, "frames": ["stun/stun_00.png"], "durations": [0.20]},
  "ko": {"loop": false, "frames": ["ko/ko_00.png", "..."], "durations": [0.15, 0.20, 0.25, 0.30]},
  "snowball": {"loop": false, "frames": ["snowball/snowball_00.png", "..."], "durations": [0.10, 0.10, 0.08, 0.16]},
  "staff_strike": {"loop": false, "frames": ["staff_strike/staff_strike_00.png", "..."], "durations": [0.10, 0.10, 0.08, 0.08, 0.18]},
  "ice_shard": {"loop": false, "frames": ["ice_shard/ice_shard_00.png", "..."], "durations": [0.12, 0.10, 0.08, 0.08, 0.18]},
  "e_raise": {"loop": false, "frames": ["e_raise/e_raise_00.png", "..."], "durations": [0.12, 0.14, 0.14]},
  "e_hold": {"loop": true, "frames": ["e_hold/e_hold_00.png", "e_hold/e_hold_01.png"], "durations": [0.18, 0.18]},
  "e_release": {"loop": false, "frames": ["e_release/e_release_00.png", "..."], "durations": [0.08, 0.10, 0.12]},
  "e_recover": {"loop": false, "frames": ["e_recover/e_recover_00.png", "e_recover/e_recover_01.png"], "durations": [0.12, 0.18]}
}
```

同时新增 `eira_frame_size: [384,384]`、`eira_pivot: [192,372]`。

Crooked Witch（建议拆分 fly，以便 02/03 循环）：

```json
"crooked_witch_clips": {
  "idle": {"loop": true, "frames": ["idle/idle_00.png", "..."], "durations": [0.18, 0.18, 0.18, 0.18]},
  "walk": {"loop": true, "frames": ["walk/walk_00.png", "..."], "durations": [0.16, 0.16, 0.16, 0.16, 0.16, 0.16]},
  "fly_takeoff": {"loop": false, "frames": ["fly/fly_00.png", "fly/fly_01.png"], "durations": [0.18, 0.18]},
  "fly_loop": {"loop": true, "frames": ["fly/fly_02.png", "fly/fly_03.png"], "durations": [0.18, 0.18]},
  "fly_land": {"loop": false, "frames": ["fly/fly_04.png", "fly/fly_05.png"], "durations": [0.18, 0.18]},
  "teleport_out": {"loop": false, "frames": ["teleport_out/teleport_out_00.png", "..."], "durations": [0.10, 0.10, 0.10]},
  "teleport_in": {"loop": false, "frames": ["teleport_in/teleport_in_00.png", "..."], "durations": [0.10, 0.10, 0.10]},
  "hurt": {"loop": false, "frames": ["hurt/hurt_00.png", "hurt/hurt_01.png"], "durations": [0.10, 0.10]},
  "ko": {"loop": false, "frames": ["ko/ko_00.png", "..."], "durations": [0.15, 0.20, 0.20, 0.20]},
  "heal": {"loop": false, "frames": ["heal/heal_00.png", "..."], "durations": [0.20, 0.20, 0.20, 2.50, 2.50, 0.20]},
  "lightning_forward": {"loop": false, "frames": ["lightning_forward/..._00.png", "..."], "durations": [0.15, 0.15, 0.10, 0.20]},
  "lightning_up": {"loop": false, "frames": ["lightning_up/..._00.png", "..."], "durations": [0.15, 0.15, 0.10, 0.20]},
  "lightning_down": {"loop": false, "frames": ["lightning_down/..._00.png", "..."], "durations": [0.15, 0.15, 0.10, 0.20]},
  "ice_spike": {"loop": false, "frames": ["ice_spike/ice_spike_00.png", "..."], "durations": [0.15, 0.15, 0.10, 0.20]},
  "potion": {"loop": false, "frames": ["potion/potion_00.png", "..."], "durations": [0.15, 0.15, 0.15, 0.20]},
  "fire_rain_intro": {"loop": false, "frames": ["fire_rain/fire_rain_00.png", "..."], "durations": [0.22, 0.26, 0.25, 0.26, 0.40]},
  "fire_rain_hold": {"loop": true, "frames": ["fire_rain/fire_rain_03.png", "fire_rain/fire_rain_04.png"], "durations": [0.40, 0.40]}
}
```

同时新增 `crooked_witch_frame_size: [640,640]`、`crooked_witch_pivot: [320,628]`。

- 如果 `AnimationPlayer` 的一个 clip 不能表达 5s 维持，`heal` 可以在 Witch 类里用
  `set_clip` + `set_frame` 手动控制；`animations.json` 仍然保留 6 帧供 `missing_paths`。
- 火雨 intro 的 0.22/0.26/0.25/0.26/0.40 来自 v2 sheet；如果完整预览更权威，以完整预览为准。
- 不要动 `shadow_ninja_*` / `lina` / 其他现有 clip 表。

### 5.4 `game/data/roster.json`

- `characters` 追加 Eira（Rhea 之后）：

```json
"eira": {
  "name": "Eira Frostveil",
  "class": "eira",
  "stats": "eira",
  "spawn": "player_spawn",
  "clips": "eira_clips",
  "frame_size": "eira_frame_size",
  "pivot": "eira_pivot",
  "frames_dir": "eira",
  "fallback": "Image/Character/eira-frostveil-256.png"
}
```

- `enemies` 追加 Crooked Witch（Shadow Ninja 之后、Dummy 之前）：

```json
"crooked_witch": {
  "name": "Crooked Witch",
  "class": "crooked_witch",
  "stats": "crooked_witch",
  "spawn": "crooked_witch_spawn",
  "stage_variant": "crooked_witch",
  "clips": "crooked_witch_clips",
  "frame_size": "crooked_witch_frame_size",
  "pivot": "crooked_witch_pivot",
  "frames_dir": "crooked_witch",
  "fallback": "Image/Enemy/crooked-witch-256.png",
  "skill_slots": ["witch_lightning", "witch_ice_spike", "witch_potion", "witch_fire_rain"],
  "separates": true,
  "decides_match": true
}
```

- `skill_slots[0]` 用逻辑名 `witch_lightning` 时，`force_skill` / F2 要能映射到具体方向；
  或者写 `witch_lightning_forward` 并在 `CrookedWitch.force_attack` 里按几何选方向。
  建议保留逻辑名，避免 F2 显示随高度跳变。

### 5.5 `game/data/debug.json`

- `stage_variants.crooked_witch` 加 §3.2 的配置（含 `teleport_points`）。
- `Stage.__init__` 增加 `self.teleport_points`。
- `scenarios` 可选加 `eira_freeze_demo` / `witch_low_hp`，不做也行。
- `roster.default_character` 保持 `lina`，`default_enemy` 保持 `creepy_shooter`。

### 5.6 `game/config.py`

- `REQUIRED_STATS` 加 `eira`、`crooked_witch`。
- `REQUIRED_ATTACKS` 加 §5.2 的全部 id（`witch_lightning` 逻辑名 + 三个方向，或只加实际 id）。
- 新增 `REQUIRED_EIRA_CLIPS`：15 个 clip。
- 新增 `REQUIRED_CROOKED_WITCH_CLIPS`：idle、walk、fly_takeoff、fly_loop、fly_land、
  teleport_out、teleport_in、hurt、ko、heal、lightning_forward、lightning_up、
  lightning_down、ice_spike、potion、fire_rain_intro、fire_rain_hold。
- `PROJECTILE_KINDS` 加 `eira_snowball`、`eira_ice_shard`、`witch_lightning_forward`、
  `witch_lightning_up`、`witch_lightning_down`、`witch_potion`、`witch_fireball`
  （具体命名可统一）。
- `ROSTER_CLASSES` 加 `eira`、`crooked_witch`；`PLAYABLE_CLASSES` 加 `eira`；
  `ANIMATED_CLASSES` 加两者。
- 校验：`eira_clips` / `crooked_witch_clips` 存在；每个 clip 的 `frames`/`durations`
  数量一致；`eira_frame_size`/`eira_pivot`、`crooked_witch_frame_size`/
  `crooked_witch_pivot` 存在；关键时长与 `attacks.json` 一致（可选）。
- 不要给 `eira`/`crooked_witch` 加 `flame_clips`；`build_animation` 的 `flame_clips`
  只给 Lina 和 Shadow Ninja。

### 5.7 `game/roster.py`

- import `Eira`、`CrookedWitch`。
- `FIGHTER_CLASSES` 加 `"eira": Eira`、`"crooked_witch": CrookedWitch`。
- `build_animation` 不需要改；Eira/Witch 用 `clips`，不用 `flame_clips`。

### 5.8 `game/eira.py`（新类）

建议字段：

- `q_cd`、`e_cd`、`q_cd_max`、`e_cd_max`。
- `e_phase`（`None`/`"raise"`/`"hold"`/`"release"`/`"recover"`）、`e_phase_time`、
  `e_selected_x`、`e_targeting`、`e_hold_time`、`e_spawn_pending`、`e_ball_spawned`。
- `freeze_cfg`；不需要在角色身上存 per-target 冰冻值（建议存在目标上）。
- `climb_draw_scale`（确认后设置）。

`update` 顺序建议：

1. `update_common(dt)`；冷却递减。
2. KO/HURT/control_locked 分支（冰冻/眩晕/击退时不能施法）；如果 E 被打断，清 E 状态。
3. 如果 `e_phase` 非空：走 `_update_e`，不处理普通移动/攻击。
4. 攀爬分支（`try_start_climb` / `_update_climb`）。
5. 普通输入：E > Q > LMB > RMB > jump；E 在冷却/状态不允许时忽略。
6. 移动/蹲下/空中；所有移动乘 `statuses.slow_factor()`。
7. 动画 idle/walk/jump/crouch；`anim.update(dt)`。

`_update_e` 建议：

- `raise`：播 `e_raise`；0.40s 后进入 `hold`，`e_targeting=True`；显示提示/竖线。
- `hold`：播 `e_hold` 循环；每 tick 检查 `input_state.buffer.consume("punch")`：
  - 有 LMB：`e_selected_x = clamp(scene.mouse_x, walls)`；`e_targeting=False`；
    进入 `release`；`e_spawn_pending=0.08`；清掉缓冲里的 punch。
  - RMB 取消：进入 `recover`，E 冷却设为满（或按 Q4）。
  - 超过 8s 未选：自动取消（Q4）。
- `release`：播 `e_release`；`e_spawn_pending` 到 0 时生成 `IceBall`（在 scene.hazards）；
  0.30s 后进入 `recover`。
- `recover`：播 `e_recover`；0.30s 后回 idle，`e_phase=None`；E 冷却按 Q4 设置。
- 受伤：`take_hit` 里清 E 状态；如果已经生成冰球，让冰球继续下落。

`on_hit_success` / `on_projectile_hit`：

- 只对 Eira 自己的攻击生效；伤害已经由 `resolve_hit` / `resolve_projectile_hit` /
  E 冰球 helper 结算；回调只调 `apply_freeze(target, amount, was_frozen)`。
- `was_frozen` 必须在**扣血前**记录；Q 的 `bonus_vs_frozen` 在扣血前乘，E 冰球在
  自定义 helper 里扣血前乘；LMB/RMB 没有冻结额外伤害。
- **不要在回调里重复扣血**，也不要在回调里补冻结额外伤害。

`reset`：

- 清 q/e 冷却、E 子阶段、`e_targeting`、`e_selected_x`、`e_spawn_pending`。
- 清所有敌人的 `eira_freeze`（遍历 `scene.enemies` 或 `reset` 时清目标字段）。
- `anim.set_clip("idle", reset=True)`；不要动 `flame_clips`。

### 5.9 `game/crooked_witch.py`（新类）

建议字段：

- `mode` / `phase`：`idle`、`walk`、`teleport_out`、`teleport_in`、`heal_in`、
  `heal_hold`、`heal_out`、`fire_rain_in`、`fire_rain_cast`、`fire_rain_out`、`attack`。
- `teleport_cd`、`teleport_points`、`teleport_index`、`teleport_from`、`teleport_to`。
- `heal_used`、`heal_return_pos`、`heal_tick`、`heal_time`。
- `lightning_cd`、`ice_cd`、`potion_cd`、`fire_cd`；`skill_gap`、`decision_cd`。
- `fire_rain_time`、`fire_rain_spawned`、`fire_rain_origin`。
- `no_hitbox`、`hidden`、`invincible` 的组合；治疗/火雨全程 `invincible/no_hitbox`。

`update` 建议：

1. `update_common(dt)`；冷却递减；如果在治疗/火雨，`statuses.clear()` 兜底。
2. KO/HURT/control_locked：普通状态可被控制；治疗/火雨跳过。
3. 治疗触发检查：`not heal_used and hp < max_hp*0.5` → 强制 `_start_heal()`。
4. 按 `phase` 走 custom update：
   - teleport out/in：定时切位置/动画/隐藏；结束后回 idle。
   - heal：fly_takeoff → fly_loop 到中心 → heal 6 帧（5s 维持 + 每秒 tick）→ fly_land；
     回原位；全程无敌/无 hitbox。
   - fire_rain：fly 到中心 → intro 5 帧 → hold + v7 pulse → 每 0.8s 生成火球 ×10 →
     0.2s 保持 → 收杖 → fly 回原位；全程无敌/无 hitbox。
   - attack：`AttackRuntime` 或自定义；闪电/冰锥/药瓶。
5. 否则 `_think`（AI）+ `_move`（walk）+ 动画。

`_think` 建议：

- 被动瞬移优先：如果 `teleport_cd <= 0` 且（刚受伤或 8s 无伤），开始瞬移；治疗/火雨不传。
- 治疗 > 火雨 > 药瓶（在 platform）> 闪电 > 冰锥 > 走向目标。
- 每个技能后 `skill_gap`；不要连续空放。
- 闪电前用 `_can_lightning()` 检查高度/x/block；不合法就不放。
- 冰锥前用 `_find_ice_spot()` 检查 surface；没有就不放。
- 药瓶在 platform 上优先；地面也可用。
- 火雨只在 cd 好、玩家存活、match 未结束时开始。

`on_projectile_hit`：

- 闪电：伤害已在 `resolve_projectile_hit` 结算；这里给 `target.statuses.add("vulnerable", ...)`，
  层数 = min(3, 当前层数 + 1)，value = 0.2 × 层数，duration = 6s。
- 药瓶：伤害已结算；这里加毒伤/减速；直击不生成毒区（由投掷物自己处理 on_expire）。
- 火球：伤害已结算；这里加 burn。

`take_hit`：

- 治疗/火雨/瞬移隐藏段：`no_hitbox` 已经让玩家打不到；`invincible` 兜底。
- 普通状态：基类 `take_hit`；如果 `not heal_used and hp < 50%`，强制治疗（可在
  `update` 下一帧触发，避免在 `take_hit` 里改状态）。
- 受伤瞬移：在 `take_hit` 或下一帧检查 `teleport_cd <= 0`；不要打断治疗/火雨。

`reset`：

- 清所有 phase、冷却、heal_used、heal_return_pos、teleport index、火球/毒区（由 scene
  清 hazards）、`no_hitbox/hidden/invincible`；回 idle。

### 5.10 `game/status.py`

- 新增 `vulnerable` 到 `ALL_EFFECTS`（可选）。
- 新增 `vulnerable_amount()`：读取 `effects["vulnerable"].value`，返回 0.0–0.6。
- `describe()` 让 vulnerable/slow 显示百分比；不要影响现有 status 行。
- `slow` 合并：可以在 `CrookedWitch` / `Eira` 的辅助函数里处理“保留最强、刷新时长”；
  也可以给 `StatusSet` 加 `add_slow(value, duration)`，避免覆盖更强减速。
- `freeze` 已在 `CONTROL_EFFECTS`；不需要改。
- `burn`/`poison` 现有 tick 规则（burn 0.2s，poison 0.5s）可直接用。

### 5.11 `game/combat.py`

- `resolve_hit` 和 `resolve_projectile_hit`：
  - 在 `damage_reduction` 后乘 `(1.0 + target.statuses.vulnerable_amount())`；
  - 如果事件/投射物有 `bonus_vs_frozen` 且 `target.statuses.has("freeze")`，在扣血前
    乘 `(1.0 + bonus_vs_frozen)`；Eira Q 用这个，E 冰球用自定义 helper。
- `resolve_projectile_hit` 不应重复改变 `projectile.target` 的语义；Eira Q 穿透时每个
  目标都走一次，`on_projectile_hit` 拿到的 target 是当前目标。
- `attack_damage` 不改；Eira/Witch 的数值放 `basic_mult`/`extra_mult`。
- `last_hit` 保持原样；可选加 `status`/`frozen` 信息，方便调试。

### 5.12 `game/projectile.py`

建议新增/复用：

- `EiraSnowballProjectile(ShurikenProjectile)`：kind `eira_snowball`，高位，单体，
  命中后消失；绘制 `eira_snowball_v1_fx_projectile.png`。
- `EiraIceShardProjectile(ShurikenProjectile)`：kind `eira_ice_shard`，高位，`pierces_targets=True`，
  `penetrates_blocks=False`；`bonus_vs_frozen=0.5`；绘制三角冰片（tip 朝前）。
- `WitchLightningProjectile`：kind `witch_lightning_*`，高速直线，`penetrates_blocks=False`，
  命中后消失；绘制 6 帧闪电 FX；`on_projectile_hit` 加易伤。
- `WitchPotionProjectile`：平台版重力抛物线、地面版低位水平；`penetrates_blocks=False`；
  命中/落地/路径尽头碎裂；未命中生成毒区；绘制 3 帧药瓶。
- `WitchFireball(FallingProjectile)`：从目标 x 的上方竖直下落，`penetrates_blocks=True`，
  命中/地面消失；命中加 burn；绘制火球 + 落地 FX。
- `IceSpikeHazard`、`PoisonZone`、`IceBall`：建议放 `scene.hazards`（见 §5.13），
  不要硬塞进 `projectiles`，因为它们有预警/持续/多目标/落地行为。

注意：

- `ShurikenProjectile._close_range_hit` 会在近距离提前命中；Eira 雪球/冰片如果不想
  近身自动命中，确认/关闭这个行为，或调整生成距离。
- `ShurikenProjectile.update` 在 `max_range` 或撞 block 时 `alive=False`；Eira Q 不穿 block。
- 火球/药瓶的 `y >= ground_y` 消失逻辑要保留；火球无视 block，不要被平台提前挡住。

### 5.13 `game/scene.py`

- `targets_for`：在玩家攻击的过滤里加 `not getattr(target, "no_hitbox", False)`；
  保留 `phantom_form`。Witch 治疗/火雨/瞬移隐藏段用 `no_hitbox`。
- 新增 `self.hazards: list`，`_rebuild_fighters` / `reset` 清空；`tick` 更新并清理；
  `draw` 在角色之后/之前按图层绘制（E 冰球在角色前，预警圈在地面层）。
- `spawn_projectile_from_event`：不要把所有新技能都塞进这个巨型分支；Eira/Witch 的
  custom 技能可以在类里直接 `scene.projectiles.append(...)` / `scene.hazards.append(...)`。
  如果走数据事件，新增对应 kind 分支。
- `spawn_hit_fx`：新增 `eira_staff_hit`、`eira_snowball_hit`、`eira_ice_shard_hit`、
  `eira_ice_shard_frozen_hit`、`eira_ice_ball_hit`、`eira_ice_ball_frozen_hit`、
  `witch_lightning_hit`、`witch_ice_spike_hit`、`witch_fireball_hit` 等；贴图 FX 用
  独立类，不要把 4/6 帧特效硬编码成程序化 ring。
- `spawn_projectile_cast_fx` / `spawn_projectile_impact`：按 kind 播放杖尖蓄光、闪电、
  药瓶碎裂、火球落地等。
- `_draw_status_fx`：增加冻结冰壳/减速视觉；不要把冰壳烘焙进角色帧。
- `draw`：Eira E 选区提示（英文原文）+ 竖线；Witch 冰锥预警圈/毒区/火雨火球。
- `mouse_x`：在 `ArenaScene.__init__` 设 `self.mouse_x = SCREEN_W * 0.5`；main 事件循环
  更新；smoke 直接设。
- `handle_debug_key`：F7 顺序自动跟随 roster；V/C/X/Z 对 Witch 强制 4 个技能；Eira 的
  V/C/X/Z 可选（可映射 LMB/RMB/Q/E），不影响 F1/F2/F6/F8/F9。
- `_separate_fighters`：Witch 与玩家正常分离；治疗/火雨/瞬移隐藏段可以跳过分离，避免
  把无敌的 Witch 推走。
- `_pick_primary` / `_place_enemies`：Witch 只有一个，正常；`teleport_points` 由 Stage 提供。

### 5.14 `game/fighter.py`

- `Fighter.draw` 目前跳过 `phantom_hidden`；建议扩展为
  `getattr(self, "phantom_hidden", False) or getattr(self, "hidden", False)`。
- 可选：给 `Fighter` 加 `no_hitbox = False` 类属性，Witch/Eira 覆盖；`targets_for` 用
  `getattr` 即可，不强制。
- `take_hit` / `apply_dot` 的 `invincible` 检查保留；Witch 治疗/火雨的无敌靠它 + no_hitbox。
- `reset_common` 清 `statuses`、hitstun、KB；Eira/Witch 的 `reset` 调它后再清自己的字段。

### 5.15 `game/input.py` / `main.py`

- 不需要改按键映射：LMB=`punch`、RMB=`kick`、Q=`q`、E=`e`。
- 需要在 `main.py` 的 `MOUSEBUTTONDOWN` 更新 `scene.mouse_x = event.pos[0]`；建议也处理
  `MOUSEMOTION`，让 E 的竖线跟随鼠标。
- Eira 的 E 选区在 `_update_e` 里消费 `punch`；不要在 `scene.input.mouse_down` 里全局拦截，
  否则会影响其他角色。
- 暂停/焦点丢失/重置时清 E 选区状态；`scene.input.clear()` 已有。
- `main.py` 的 smoke 直接设 `scene.mouse_x`，不要依赖 pygame 鼠标。

### 5.16 `game/debug.py` / `main.py` smoke

F1：

- Witch 治疗/火雨/瞬移隐藏段不画 hurtbox；普通状态画。
- Eira 命中盒、E 冰球半径、Witch 冰锥预警圈/毒区、火球下落线可以画。
- `no_hitbox` 的过滤与 phantom 一致。

F2 建议新增：

- Eira：`EIRA FREEZE <target> 60/100`、`FROZEN 1.2s`、`SLOW 30%`、`E TARGETING x=...`、
  `Q 2.1s`、`E 8.4s`。
- Witch：`WITCH HEAL READY/USED`、`TELEPORT 3.2s`、`L 1.1s / I 4.0s / P 7.2s / F 14.0s`、
  `PHASE heal_hold`、`VULN 2 stacks (+40%)`、`NO HITBOX`。
- 现有 `SHADOW MARKS`、`PHANTOM` 行保留，不要回退。

F6：0.25×/0.5× 检查 Eira E 0.40/0.30/0.30、Witch 闪电 0.60、冰锥 1s 预警、治疗 5s、
火雨 0.8s×10。

F7/F8/F9/R：切换/重置后清 Eira E 状态、Witch phase/冷却/治疗/毒区/火球/瞬移；
F8 切换 Witch 的 `ai_enabled`。

smoke 建议新增 Phase J（Crooked Witch）和 Phase K（Eira），放在 Phase I 之后。
最少 flags：

Crooked Witch：

- `crooked_witch_present`：class、stats、slots、stage variant、`teleport_points` 4 个。
- `crooked_witch_stats_ok`：HP 400、ATK 30、walk/hurtbox。
- `crooked_witch_teleport_ok`：受伤触发；目标点排除最近点；8s 无伤自动传；隐藏段
  no_hitbox/invincible；重置清冷却。
- `crooked_witch_heal_ok`：<50% 强制一次；5 次 × 6%；无敌/无 hitbox；回原位；第二次不触发。
- `crooked_witch_lightning_ok`：同高前向；异高斜向；x 相近不施放；block 阻挡不施放；
  1.2 atk；易伤先伤害后加层，3 层上限。
- `crooked_witch_ice_spike_ok`：预警 1s；atk + 1.5s freeze；走出圈可躲；平台/地面选点。
- `crooked_witch_potion_ok`：平台抛物线/地面低平；直击 0.8 atk + 3% 毒 + 30% 慢，无区；
  未命中生成毒区，2% 毒 + 20% 慢；毒区寿命/刷新。
- `crooked_witch_fire_rain_ok`：无敌/无 hitbox；10 颗 ×0.8s；x 锁定；穿 block；1.2 atk+burn；
  回原位。
- `crooked_witch_ai_ok`：优先级、冷却、platform 药瓶、合法闪电/冰锥。
- `crooked_witch_reset_ok` / `crooked_witch_missing_frames == 0` /
  `crooked_witch_fx_missing == 0`。

Eira：

- `eira_present`：class、stats、15 clips、48 帧、`[`/`]` 可选、默认角色仍 Lina。
- `eira_lmb_ok`：雪球高位、1.0 atk、+20 冰冻、蹲下可躲。
- `eira_rmb_ok`：近战 1.2 atk、+20 冰冻、0.20–0.36 一次判定。
- `eira_q_ok`：3s 冷却、穿透、1.5 atk、+30、冻结额外 +50%、先冻结判定后伤害后积累。
- `eira_e_ok`：12s、0.40 raise、hold 等 LMB、提示/竖线、0.08s 生成、约 1s 落地、
  穿 block、多目标、3.0 atk、+50、冻结额外 +100%、3s 碎片、0.60s 回 idle。
- `eira_freeze_ok`：100 → 2s freeze 清零；冻结期间不积累；解冻后恢复；slow 等量；
  最强 slow 合并；每个敌人独立。
- `eira_climb_ok`：背身 4 帧、上下梯、被打断落地。
- `eira_reset_ok` / `eira_missing_frames == 0` / `eira_fx_missing == 0`。

通用：

- 所有旧 Phase A–I flags 保持 true；`default_character_ok` / `default_enemy_ok` 保持 true；
- `main.py --smoke-test` exit 0；
- `eira_missing_frames == 0`、`eira_fx_missing == 0`、
  `crooked_witch_missing_frames == 0`、`crooked_witch_fx_missing == 0`。

---

## 6. 待确认决策（下一个 session 一次性 grill）

> ★ = 必须确认；○ = 没异议就按建议值。每个问题都给出 docx 状态、建议和影响。

| # | 问题 | docx 状态 | 建议/默认 | 影响 |
|---|---|---|---|---|
| Q1 ★ | Eira 的 HP / ATK / 移速 | docx 只给技能，没有数值 | HP 100、ATK 20、walk 240、jump 760 | 平衡、smoke |
| Q2 ★ | Eira 的伤害系数与冻结额外伤害 | docx 只说“伤害/额外伤害/大量伤害” | LMB 1.0 / RMB 1.2 / Q 1.5 / E 3.0；Q 冻结 +50%，E 冻结 +100% | 全部数值 |
| Q3 ★ | Eira 的运行时画布/pivot/body | 未定 | 384×384 / 192,372 / body 214；E 举杖放不下就停下问 | 全部帧导入 |
| Q4 ★ | E 的取消、超时、冷却起点、吟唱是否可被打断 | docx 未定 | 吟唱可被攻击；受伤/RMB 取消；8s 未选自动取消；12s 从施放开始 | 手感、soft-lock |
| Q5 ○ | 减速持续时间/合并、冻结额外伤害的判定 | docx 只说等量减速、先冻结后伤害后积累 | slow 2.0s，最强减速，刷新时长；Q/E 冻结额外伤害按命中前状态 | 状态实现 |
| Q6 ★ | 冻结冰壳/碎冰 VFX | 动画设计文档要求独立冰壳，但没有已批准图 | 程序化半透明冰壳 + 复用 frozen_hit 碎冰；或补图 | 视觉、素材 |
| Q7 ○ | E 冰球的运行时半径/起始高度/落地 | docx 只说约 1s、穿 block、不消失 | 半径 80，start y=-120，1.0s 到 ground，命中多目标 | 视觉/判定 |
| Q8 ★ | Witch 的运行时画布/pivot/body | 未定 | 640×640 / 320,628 / body 230；帽/杖放不下就停下问 | 全部帧导入 |
| Q9 ★ | Witch 专属场景的布局/出生点/四点 | docx 有专属场景图 | 两个 short platform + 两条 long ladder；出生右平台；四点见 §3.2 | 场景/瞬移 |
| Q10 ★ | 瞬移的触发/冷却/无敌/打断 | docx 说受伤优先、8s 无伤再传、排除最近点 | 8s 冷却；受伤且冷却好立即传；8s 无伤自动传；瞬移段无敌/no_hitbox；不打断治疗/火雨 | 核心 AI |
| Q11 ○ | 治疗的治疗量/结算/回位 | docx 明确 6%/s ×5、一次、无敌无 hitbox | 到中心后 t=1..5 各 24 HP；回触发位置；上限 max HP | 平衡/时序 |
| Q12 ○ | 闪电的同高/x 相近阈值、易伤时长 | docx 只给 20 易伤 3 层 | 同高 80px、x 相近 140px；易伤 6s；每层 +20% | 命中/AI |
| Q13 ○ | 冰锥选点偏移/判定半径 | docx 说目标附近、靠 Witch 侧、同高 surface | 向 Witch 偏移 80px，半径 65px；无 surface 不放 | AI/命中 |
| Q14 ★ | 药瓶毒伤是“总 2%/3% 持续 3s”还是“每秒 2%/3%” | docx 措辞有歧义 | 总伤害 2%/3% over 3s；毒区 6s；直击毒 30% 慢、毒区 20% 慢 | 平衡 |
| Q15 ○ | 火雨的冷却起点/灼烧数值 | docx 未明确 CD；灼烧未给 | 冷却从施放开始；复用 burn 5 dps / 3s；10 颗 ×0.8s | 平衡/时序 |
| Q16 ○ | 技能 2/5/8/15s 是否就是冷却 | docx 标题只有括号 | 当作冷却，施放开始计时 | 技能循环 |
| Q17 ○ | Witch 的 hurtbox / body width | docx 未给 | 56×210 / stage_body_width 100 | 碰撞/AI |
| Q18 ○ | Witch AI 优先级 | docx 只给部分偏好 | 治疗 > 火雨 > 平台药瓶 > 闪电 > 冰锥 > 走近 | 战斗节奏 |

已由 docx 固定、不需要 grill 的：

- Eira：冰冻值每个敌人独立、100 冻结 2s 并清零、冻结期间停止积累、等量减速；LMB 雪球
  高/远/20；RMB 近/20；Q 3s/三角/高/穿透/30/冻结额外伤害/先看冻结；E 12s/举杖吟唱/
  左键选区/只选水平/约 1s/穿 block/命中不消失/50/冻结额外大量伤害/3s 碎片。
- Witch：HP 400 / ATK 30；瞬移四点、排除最近点、8s 无伤再传、受伤优先；治疗一次、
  <50%、6%/s×5、无敌无控无 hitbox、飞屏幕中间、回原位；闪电 1.2atk + 20 易伤 3 层、
  同高/异高/相近/block 规则、先伤害后易伤；冰锥 5s 标题、预警 1s、atk + 1.5s 冻结、
  同高地面/platform、靠 Witch 侧；药瓶平台重力/地面低平、直击 0.8atk + 3% 毒 3s +
  30% 慢、未命中毒区 2% 毒 3s + 20% 慢、直击不留区；火雨 15s 标题、无敌无控无 hitbox、
  飞中央、10 颗 ×0.8s、生成时取目标 x、竖直、无视 block、1.2atk + 灼烧、回原位。

---

## 7. 已确认决策（grill 后回填）

| # | 决策 | 用户答案 | 日期 |
|---|---|---|---|
| Q1 | Eira HP/ATK/移速 | 待确认 | |
| Q2 | Eira 伤害/冻结额外伤害 | 待确认 | |
| Q3 | Eira 画布/pivot/body | 待确认 | |
| Q4 | E 取消/超时/冷却/打断 | 待确认 | |
| Q5 | 减速/冻结额外伤害判定 | 待确认 | |
| Q6 | 冻结冰壳 VFX | 待确认 | |
| Q7 | E 冰球半径/起始/落地 | 待确认 | |
| Q8 | Witch 画布/pivot/body | 待确认 | |
| Q9 | Witch 场景/出生/四点 | 待确认 | |
| Q10 | 瞬移触发/冷却/无敌 | 待确认 | |
| Q11 | 治疗结算/回位 | 待确认 | |
| Q12 | 闪电阈值/易伤时长 | 待确认 | |
| Q13 | 冰锥选点/半径 | 待确认 | |
| Q14 | 药瓶毒伤总量/毒区寿命 | 待确认 | |
| Q15 | 火雨冷却/灼烧 | 待确认 | |
| Q16 | 2/5/8/15s 是否 CD | 待确认 | |
| Q17 | Witch hurtbox | 待确认 | |
| Q18 | Witch AI 优先级 | 待确认 | |

---

## 8. 实现顺序

1. **基线**：`main.py --smoke-test` exit 0；确认当前工作区只有用户未提交的素材/文档；
   不要动已提交的其他角色/敌人。
2. **Grill**：按 §6 一次性确认，回填 §7；★ 项没有答案前不要写代码/JSON。
3. **数据骨架**：`stats.json`、`attacks.json`、`animations.json`、`roster.json`、
   `debug.json`、`config.py`、`roster.py`；先用缺失帧跑，确认配置校验能指出缺图。
4. **导入 Eira**：base → idle/walk/jump/crouch/climb/hurt/stun/ko → 四技能 → E 四段；
   先 `--dry-run` 检查 FIT，再安装；contact sheet/game preview 复核。
5. **Eira 代码**：被动/冰冻/减速、LMB/RMB/Q、E 选区/冰球、HUD、F7 角色轮换、
   F1/F2/F6/F9、smoke Phase K（Eira）。
6. **导入 Witch**：base → idle/walk/fly/teleport/hurt/ko/heal → 闪电/冰锥/药瓶/火雨；
   检查 640 画布、1536/1792 帧、帽/杖是否被裁。
7. **Witch 代码**：瞬移、治疗、闪电、冰锥、药瓶/毒区、火雨、AI、场景、HUD、
   F1/F2/F6/F8/F9、smoke Phase J（Witch）。
8. **状态扩展**：`vulnerable`、`damage_taken_multiplier`、slow 合并、冻结冰壳；
   先 Eira 的 freeze/slow，再 Witch 的 vulnerable/freeze/poison/burn。
9. **调试/smoke**：新增 flags，保持所有旧 flags true；`main.py --smoke-test` exit 0；
   四个缺失计数为 0。
10. **游戏内预览**：Eira vs Dummy（四技能、冻结、E 选区、冰球落地/碎片）；Witch 对
    Lina/Rhea（瞬移、治疗、闪电易伤、冰锥预警、药瓶毒区、火雨）。给用户看。
11. **文档**：实现和验证完成、用户确认后，按 AGENTS.md 只问一次是否把接入细节写进
    README / DESIGN_DECISIONS / DEBUG / ASSET_PIPELINE，或新建
    `docs/EIRA_IMPLEMENTATION.md` / `docs/CROOKED_WITCH_IMPLEMENTATION.md`。
    `instruction.docx` 永远不改；动画设计文档的已确认帧表不改。

---

## 9. 手动验收

### Eira

1. `[`/`]` 切到 Eira；F7 选 Dummy / Creepy Shooter；走/跳/蹲/爬梯正常，背身 climb 不缩小。
2. LMB 雪球高位命中，+20 冰冻；蹲下可躲；雪球命中后消失。
3. RMB 杖击 0.20–0.36 命中一次，+20；杖弧 FX 正确。
4. Q 3s 冷却；冰片穿透多个敌人；每个目标 +30；冻结目标额外伤害；撞 block 消失。
5. 连续命中到 100：目标冻结 2s、冰冻值清零；冻结期间继续打不再积累、不再加慢；
   解冻后重新积累；减速百分比与获得值一致。
6. E：举杖 0.40s → 提示文字 → 竖线跟随鼠标 → LMB 选区 → 0.08s 生成冰球 →
   约 1s 落地；穿过平台/敌人；命中多个敌人；已冻结目标额外伤害；+50；触地四块大冰 +
   碎片 3s；0.60s 回 idle；12s 冷却。
7. E 吟唱被攻击：按 Q4 取消/冷却；RMB 取消；8s 超时。
8. F1 看命中盒/冰球/预警；F2 看 freeze/slow/冷却/E targeting；F6 慢放检查时序；
   F9/R 清 E 状态、冰冻值、减速、冰球/碎片。

### Crooked Witch

1. F7 选 Crooked Witch；专属场景有两个 short platform + 两条 long ladder；出生点正确。
2. 普通状态：idle/walk/hurt/ko；无 jump/crouch/climb；平台/地面移动正常。
3. 瞬移：受伤触发；目标点排除最近点；8s 无伤自动传；隐藏段打不到/投射物穿过；
   出现后可打；F2 显示冷却/下个点。
4. 治疗：打到 <50% 强制一次；飞到中央；5 次 ×6%；全程无敌/无 hitbox；回原位；
   第二次 <50% 不再触发。
5. 闪电：同高前向；异高斜向；x 相近不施放；block 前不施放；1.2 atk；易伤先伤害后加层；
   3 层上限；易伤图标/伤害增加正确。
6. 冰锥：蓝圈 1s；圈内 atk + 1.5s freeze；走出圈可躲；平台/地面选点正确。
7. 药瓶：平台抛物线/地面低平；直击 0.8 atk + 3% 毒 3s + 30% 慢、无区；未命中毒区
   2% 毒 3s + 20% 慢；毒区寿命/刷新；踩入/离开正确。
8. 火雨：飞到中央；10 颗 ×0.8s；每颗取目标当前 x；竖直、穿 block、落地/命中消失；
   1.2 atk + 灼烧；全程无敌/无 hitbox；回原位。
9. F1 hurtbox 在治疗/火雨/瞬移隐藏段不画；F2 显示 phase/冷却/易伤/无敌；F6 慢放；
   F8 AI；F9/R 清 phase/冷却/治疗/毒区/火球。

### 通用

- `main.py --smoke-test` exit 0。
- 旧 Phase A–I 全部 flags 保持 true；`default_character_ok` / `default_enemy_ok` true。
- `eira_missing_frames == 0`、`eira_fx_missing == 0`、
  `crooked_witch_missing_frames == 0`、`crooked_witch_fx_missing == 0`。
- 未修改 `instruction.docx`、`Image/`、`UI Resources/`、`sketch/`、其他角色/敌人、背景/BGM。

---

## 10. 验收清单（DoD）

- [ ] Eira 是可玩角色，`[`/`]` 可切；LMB/RMB/Q/E/被动/攀爬全部工作。
- [ ] Eira 的冰冻值每个敌人独立；100 → 2s 冻结并清零；冻结期间停止积累；等量减速；
      冻结冰壳/碎冰演出正确。
- [ ] Eira Q 穿透、E 选区/冰球穿 block/多目标/约 1s 落地/3s 碎片；Y 顺序正确。
- [ ] Eira 的 15 个 clip 与 48 帧全部安装；missing_frames/fx_missing 为 0。
- [ ] Crooked Witch 是 F7 敌人；专属场景/四点/出生点正确；HP 400/ATK 30。
- [ ] 瞬移（受伤优先、8s 无伤、排除最近点、无敌/no_hitbox）正确。
- [ ] 治疗（一次、<50%、6%×5、无敌无 hitbox、回原位）正确。
- [ ] 闪电（同高/异高/相近/block、1.2 atk、20 易伤 3 层、先伤害后加层）正确。
- [ ] 冰锥（同高 surface、靠 Witch 侧、1s 预警、atk + 1.5s freeze）正确。
- [ ] 药瓶（平台/地面、直击/毒区、0.8 atk、3%/2% 毒、30%/20% 慢、zone 规则）正确。
- [ ] 火雨（无敌无 hitbox、10×0.8s、x 锁定、竖直、穿 block、1.2 atk + 灼烧、回位）正确。
- [ ] Witch AI 能循环使用技能；F8 可关；不会卡在平台/边缘/空放。
- [ ] F1/F2/F6/F7/F8/F9 全部可用；F2 显示 Eira freeze/E targeting、Witch phase/易伤/冷却。
- [ ] `main.py --smoke-test` exit 0；所有旧 flags 不回退；四个新 missing 计数为 0。
- [ ] 用户确认后，按 AGENTS.md 问一次是否更新文字/文档；`instruction.docx` 未改。
- [ ] 未 commit/push（除非用户明确要求）。

---

## 11. 约束与提醒

- **动画已批准，不要重画。** 需要新图（例如冻结冰壳）时先问用户；不要用角色帧/旧版本凑。
- `instruction.docx` 是权威规格，**永远不要修改**；当前工作区已有用户修改，不要回滚。
- 不修改 `Image/`、`UI Resources/`、`sketch/`、其他角色/敌人、背景/BGM。
- 不用 pytest；验证用 `--smoke-test`、F1/F2/F6/F7/F8/F9 和游戏内预览。
- 素材导入先 `--dry-run`；出现 `FIT`/`MISSING` 停下来问，不要自动缩小人物。
- 不要 commit/push，除非用户明确要求。
- 文档更新等实现和验证完成后，按 AGENTS.md 只问一次；用户同意后才写。
- 本文的数字中，docx 已明确的优先；标“建议”的是待 grill 的默认值，不要当成最终规格。

---

## 附录 A — 代码位置（HEAD f04b158）

- `game/config.py`：`REQUIRED_STATS` 21；`REQUIRED_ATTACKS` 22；`REQUIRED_*_CLIPS` 36–76；
  `ROSTER_CLASSES` / `PLAYABLE_CLASSES` / `ANIMATED_CLASSES` 77–80；
  `PROJECTILE_KINDS` 81；`JsonStore._validate` 132。
- `game/roster.py`：`FIGHTER_CLASSES` 18；`build_animation` 32；`create_fighter` 56。
- `game/status.py`：`CONTROL_EFFECTS` 7；`IMMUNE_EFFECTS` 8；`ALL_EFFECTS` 9；
  `slow_factor` 131；`damage_reduction` 127；`control_locked` 122。
- `game/combat.py`：`attack_damage` 8；`AttackRuntime` 43；`resolve_hit` 142；
  `resolve_projectile_hit` 194。
- `game/scene.py`：`_rebuild_fighters` 235；`_stage_config` 282；`set_character` 308；
  `set_enemy` 317；`cycle_character` 329；`targets_for` 366；`reset` 391；
  `_separate_fighters` 472；`spawn_projectile_cast_fx` 587；`spawn_projectile_impact` 746；
  `spawn_hit_fx` 896；`spawn_projectile_from_event` 1071；`handle_debug_key` 1401；
  `_draw_status_fx` 1495；`draw` 1585。
- `game/fighter.py`：`FighterState` 14；`Fighter` 34；`update_common` 142；`take_hit` 171；
  `force_skill` 269；`try_start_climb` 313；`reset_common` 508；`draw` 594。
- `game/animation.py`：`AnimationPlayer` 12；`set_clip` 60；`set_frame` 73；
  `missing_paths` 103。
- `game/input.py`：`InputState` 62；`mouse_down` 110。
- `game/debug.py`：F2 panel 185（`_lines` 92）。
- `main.py`：`_smoke_test` 52；Phase I 4288；事件循环 5140；最终 conjunction 5030 附近。
- `tools/import_frames.py`：`main` 81；`--base`/`--body-height`/`--canvas`/`--pivot-x`/
  `--pivot-y`/`--order`/`--anchor`/`--dry-run`。
- `tools/contact_sheet.py`：`main` 27。

## 附录 B — 源文件 → 运行时 clip 对照

### Eira

| 运行时 clip | 源文件 |
|---|---|
| `idle` | `eira_idle_v1_00..03.png` |
| `walk` | `eira_walk_v2_00..05.png` |
| `jump` | `eira_jump_v6_00..01.png` |
| `crouch` | `eira_crouch_v1_00.png` |
| `climb` | `eira_climb_v3_00..03.png` |
| `hurt` | `eira_hurt_v1_00..01.png` |
| `stun` | `eira_stun_v1_00.png` |
| `ko` | `eira_ko_v4_00..03.png` |
| `snowball` | `eira_snowball_v1_00..03.png` |
| `staff_strike` | `eira_staff_strike_v2_00..04.png` |
| `ice_shard` | `eira_ice_shard_v1_00..04.png` |
| `e_raise` | `eira_e_raise_v1_00..02.png` |
| `e_hold` | `eira_e_hold_v1_00..01.png` |
| `e_release` | `eira_e_release_v1_00..02.png` |
| `e_recover` | `eira_e_recover_v1_00..01.png` |

### Crooked Witch

| 运行时 clip | 源文件 |
|---|---|
| `idle` | `crooked_witch_idle_v1_00..03.png` |
| `walk` | `crooked_witch_walk_v1_00..04.png` + `crooked_witch_walk_v3_05.png` |
| `fly_takeoff` | `crooked_witch_fly_v3_00..01.png` |
| `fly_loop` | `crooked_witch_fly_v3_02..03.png` |
| `fly_land` | `crooked_witch_fly_v3_04..05.png` |
| `teleport_out` | `crooked_witch_teleport_out_v1_00..02.png` |
| `teleport_in` | `crooked_witch_teleport_in_v1_00..02.png` |
| `hurt` | `crooked_witch_hurt_v2_00.png` + `crooked_witch_hurt_v1_01.png` |
| `ko` | `crooked_witch_ko_v1_00..02.png` + `crooked_witch_ko_v2_03.png` |
| `heal` | `heal_v3_00` + `heal_v5_01` + `heal_v4_01` + `heal_v2_02` + `heal_v2_03` + `heal_v1_04` |
| `lightning_forward` | `crooked_witch_lightning_v2_00..03.png` |
| `lightning_up` | `crooked_witch_lightning_up_v1_00..03.png` |
| `lightning_down` | `crooked_witch_lightning_down_v5_00..03.png` |
| `ice_spike` | `crooked_witch_ice_spike_v1_00..03.png` |
| `potion` | `crooked_witch_potion_v2_00..03.png` |
| `fire_rain_intro` | `fire_rain_v2_00` + `fire_rain_v6_01..04` |
| `fire_rain_hold` | `fire_rain_v6_03..04` |

## 附录 C — 与 docx 的边界

- 本文所有“建议/默认”都不是 docx 原文；docx 已明确的数值/行为（HP/ATK、冷却、伤害倍率
  中明确写出的、冻结/易伤/毒/灼烧规则、治疗 6%×5、火雨 10×0.8 等）优先。
- 动画设计文档里的“已确认”指美术/动作确认，不等于技能逻辑/数值确认；不要用动画文档
  覆盖 docx。
- 需要补的规则写进 Markdown，不要改 `instruction.docx`。
