# Next Session — Veno-Spider & Lina Q 技能特效

> 日期：2026-10-23
> 用途：下个 session 的聚焦 handoff，可直接复制 §0 的 prompt 使用。
> 默认范围：**只改视觉特效**；不改伤害、判定、时序、冷却、AI、默认阵容。
> 生成任何图片前先读 `docs/IMAGE_GENERATION_RULES.md`；素材流程见 `docs/ASSET_PIPELINE.md`。
> 更完整的 Nyra / Veno / Lina Q 上下文见 `docs/NEXT_SESSION_NYRA_VENO_LINA_Q.md`；本文件只聚焦 Veno-Spider 与 Lina Q 的特效改造。

---

## 0. 可直接复制的开场 prompt

```text
先阅读 docs/NEXT_SESSION_VENO_LINA_Q_VFX.md 和 AGENTS.md；如需生成图片，再读 docs/IMAGE_GENERATION_RULES.md。
本轮只改 Veno-Spider 与 Lina Q 的技能视觉特效，默认不改伤害、判定、时序、冷却、AI、默认阵容。
先运行 .venv/Scripts/python.exe main.py --smoke-test，确认基线 exit 0；然后按文档 §4 的 5 个问题逐项向我确认。
确认后按 §5 分阶段实现：先做不需要新素材的程序化层，再决定是否生成 sprite FX。
所有新素材先出 contact sheet，批准后才允许接入游戏。
不要 commit；不要 git reset / git checkout -- . / git stash；不要动 Image/、instruction.docx、UI Resources/。
```

如果用户只说了“改 Veno 和 Lina Q 特效”而没有给具体视觉要求，先按 §3 的推荐方案确认，不要直接猜。

---

## 1. 基线、分支与工作区

- 当前分支：`nyra-veno-sandbox`
- 最近提交：`9c4d39d Add Nyra Steel and Veno-Spider sandbox content`
- 工作区仍有大量未提交改动（Nyra 帧、`nyra_slash_fx`、Q/E 数值、文档等）。**不要清理、revert、stash 或批量覆盖。**
- `Image/` 是 canonical 视觉源，只读。`instruction.docx`、`UI Resources/` 不要动。

### 1.1 基线命令

```bat
.venv/Scripts/python.exe main.py --smoke-test
```

基线应为 **exit 0**，与本任务相关的字段：

```text
q_damage_ok=True q_block_ok=True flame_ok=True
veno_bite_ok=True veno_poison_ok=True veno_poison_stack_ok=True
veno_web_ok=True veno_ai_ascent_ok=True veno_ai_descend_ok=True
veno_win_ok=True roster_ok=True
missing_frames=0 veno_missing_frames=0
```

补充：

- 启动、F5/F9/R 重置后敌人 AI 默认关闭；手动测 Veno 时按 **F8** 开 AI，或用 **V/C/X** 强制技能。
- smoke 只验证逻辑与数值，不验证特效外观；视觉必须手动看或看 contact sheet。
- 若基线不是全绿，先报告，不要叠加特效改动。

---

## 2. 当前实现（事实）

### 2.1 Lina Q

| 项 | 当前值 |
|---|---|
| attack id | `q`（`game/data/attacks.json`） |
| 伤害 | 20（`basic 1.0` + `extra 1.5` × 初始 extra 0）；flame bonus 另乘 |
| duration | 0.35s；hitstun 0.2；hitstop 0.06 |
| 冷却 | 8s；仅地面可放 |
| 弹体事件 | `t=0.26` 生成 `q_wave`；`lane="fist"`；speed 700；range 520；knockback 150 |
| 生成位置 | `attacker.x + facing*50`，y = `lane_y("fist", attacker.y)` = 脚底 - 142 |
| 碰撞 | `QWave.rect` 44×34；visual surface 64×64 |
| 回能 | 普通形态 +20 energy；flame 形态不 grant energy，改为命中挂 burn 5 HP/s × 3s |
| 动画 | `assets/frames/lina/q/q_00..03.png`，4 帧，durations `0.06/0.10/0.10/0.09` |
| flame 动画 | `assets/frames/lina/flame/q/q_00..03.png`，同 4 帧/durations |

当前时序：

```text
0.00–0.06  q_00  无气流
0.06–0.16  q_01  聚气 / 手部漩涡
0.16–0.26  q_02  普通：手前方有一颗小青色光球（已烘进角色帧）
                  flame：拳部有火焰，没有独立的青色球
0.26–0.35  q_03  手部干净 / 收势
t=0.26     生成 QWave（60Hz 下实际约 0.267 生效）
```

`QWave.draw()` 当前是纯程序化：

- 青色 `(120, 230, 255)` 或 flame 橙色 `(255, 150, 90)`；
- 3 个拖尾圆 + 中心大圆 + 白色高光 + 外圈；
- 没有独立 sprite、没有发射/命中专用特效；
- 命中走 `resolve_projectile_hit()` 的通用 hit particles，颜色被**硬编码为青色** `(120, 230, 255)`，flame Q 命中也是青色。

已知行为/风险：

- **普通 Q 的 `q_02` 已经烘了一颗小光球**。如果新弹体外观与它差异很大，会出现“手边旧球 + 前方新球”的割裂；第一轮建议保持角色帧不变，把新 QWave 做成与旧球同量级的升级版。
- **flame Q 的 `q_02` 是拳部火焰，不是独立球**；新 flame 弹体可以在手前方出现，但要避免和拳部火焰重复成大团。
- `QWave.update()` **没有 wall 检查**；block 检查不读取 `stage.blocks_enabled`（与 `SwordWave`、`AimedProjectile` 不一致）。如果本轮只改视觉，先不要顺手改碰撞；若改，必须单独确认并更新 smoke。
- 当前没有 Lina Q 的独立 FX 素材目录。

### 2.2 Veno-Spider

| attack | 伤害 | duration | 投射物/判定 | 状态 |
|---|---:|---:|---|---|
| `veno_bite` | 15 | 0.50 | hitbox `[24,-120,110,90]`，t 0.18–0.30 | 无 |
| `veno_poison` | 8 | 0.60 | `t=0.25` 生成 `venom_glob`；origin_height 100；speed 520；range 800；knockback 40；radius 18 | poison 3.0s，dps = 3% 目标最大生命 |
| `veno_web` | 10 | 0.65 | `t=0.30` 生成 `web_bolt`；origin_height 100；speed 480；range 800；knockback 60；radius 14 | stun 1.0s |

- 两个远程弹道都是**发射瞬间瞄准玩家位置**的直线弹，不追踪；跳跃/位移可以躲。
- 生成位置：`attacker.x + facing*24`，y = `attacker.y - 100`；目标是玩家 hurtbox 中心。
- 角色施法帧：
  - `veno_poison` 3 帧，durations `0.15/0.15/0.30`；frame 01 口部有绿色小光。
  - `veno_web` 3 帧，durations `0.16/0.16/0.33`。
  - **施法帧没有烘弹体**；这是正确的，特效应继续保持独立层。
- 当前弹体外观：
  - 毒：深绿/亮绿叠层圆 + 高光，radius 18，带一点气泡感，但没有年龄/旋转/滴落。
  - 网：淡蓝白圆 + 6 根辐条 + 一条横线，radius 14；更像“圆形网图标”，没有旋转或丝线拖尾。
  - 两者共用 `AimedProjectile.draw()`，没有 `age`/`spin` 字段。
  - 命中都走通用 hit particles，颜色同样是硬编码青色；毒没有绿色飞溅，网没有网状爆裂。
- 状态视觉：
  - poison：目标 hurtbox 上叠一层绿色矩形 pulse + 每 2 tick 的绿色毒粒子。
  - stun：头顶 3 个黄色光点绕圈。
- hover 时场景画一条 2px 灰白蛛丝，从屏幕顶部到蜘蛛上方；蛛丝不在角色帧里。

### 2.3 绘制顺序

`game/scene.py` 的 `ArenaScene.draw()` 顺序：

```text
stage
→ knock-up 效果
→ enemy
→ enemy status FX
→ projectiles
→ particles
→ player
→ slash_effects
→ player status FX
→ marks
→ HUD
```

影响：

- 弹体绘制在敌人之上、玩家之下；大型弹体会遮住敌人但不遮玩家。
- `particles` 在玩家之下；如果命中爆裂很大，可能被玩家身体挡住一部分。
- `slash_effects` 在玩家之上；适合做“命中爆点/网状爆裂”这类需要盖住角色的短特效，但不要长时间遮挡角色。
- 新增 FX 层时，先决定它属于 `projectiles`、`particles` 还是 `slash_effects`，不要默认全塞进 `slash_effects`。

### 2.4 已有但未接入的 Veno 蛛网素材

这些文件已经存在，但**没有接入游戏**：

```text
assets/generated/contact_sheets/veno_web_spit_v2_web_master.png      1147×1182 RGBA
assets/generated/contact_sheets/veno_web_spit_v2_frames/veno_web_spit_web_00..05.png      640×320 RGBA
assets/generated/contact_sheets/veno_web_spit_v2_frames/veno_web_spit_spider_00..05.png   640×320 RGBA
assets/generated/contact_sheets/veno_web_spit_v2_frames/veno_web_spit_combined_00..05.png 640×320 RGBA
assets/generated/contact_sheets/veno_web_spit_v2_manifest.json
tools/generate_veno_web_spit.py
```

要点：

- 预览：`veno_web_spit_v2_web_sheet.png`、`veno_web_spit_v2_web_preview.png`、`veno_web_spit_v2_combined_preview.png`。
- `web_master.png` 是一张干净的、青柠绿/白高光的蛛网图标，适合作为**弹体或命中贴花**的裁切来源。
- `veno_web_spit_v2_frames/veno_web_spit_web_00..05.png` 是 6 帧“施法 + 蛛网飞行”层，画布是 640×320，蛛丝起点按 640×320 里的口部坐标烘死；它不是独立弹体，不能直接塞进 `AimedProjectile`。
- `veno_web_spit_v2_frames/veno_web_spit_combined_00..05.png` 包含蜘蛛本体；**不要**把 combined 帧直接拷进运行时，否则会出现“角色帧里的蜘蛛 + 场景里的 Veno”双本体。
- `veno_web_spit_v2_frames/veno_web_spit_spider_00..05.png` 只是现有 `veno_web_00..02` 三张姿势的重复排列，不是新角色动画。
- 如果复用，只取 `web_master` 的裁切/缩放版本，或把 `veno_web_spit_web_00..05` 当作“施法特效参考”，重新按 Veno 的实际口部坐标和朝向放置。

### 2.5 当前视觉问题 / 可改进点

- Lina Q：弹体小、静态、拖尾弱；flame 命中仍是青色粒子；普通 Q 角色帧里有一颗旧小球，换弹体外观时容易割裂。
- Veno 毒/网：都是简单圆形；没有施法特效、没有命中特效、没有元素色；毒和网在飞行中几乎只靠颜色区分。
- 现有 `veno_web_spit_v2` 的蛛网素材没有被利用。
- poison 状态是整块绿色矩形 overlay；stun 只有黄点，没有“被网住”的视觉联系。
- hover 蛛丝是单一灰线，存在感很弱。
- `resolve_projectile_hit()` 对所有投射物使用同一套青色 hit particles；改特效时不要直接改 `emit_hit()` 的全局颜色，否则拳/腿/斧的命中反馈也会被改掉。
- `AttackRuntime` 的 `fx` 事件目前只会调用 `scene.spawn_slash_effect()`，而 `SlashEffect` 是 Nyra 专用（384×384 / pivot 192,372）。**在给 Lina/Veno 加 `fx` 事件前，必须先泛化 FX 播放器**，否则会加载错误的帧尺寸。

---

## 3. 推荐目标（用户未指定时按此执行）

总原则：

- 只改视觉，不改伤害/判定/时序/冷却/AI。
- 1× 缩放下能看清元素（青/橙/绿/白），不要用大面积半透明遮住角色。
- 施法与命中特效控制在 0.10–0.25s；不要为了特效延长 hitstop 或 attack duration。
- 弹体 visual 可以大于碰撞盒，但碰撞盒保持不变；不要通过放大碰撞盒来“配合”特效。
- 不新增屏幕震动/全屏后处理，除非用户明确要求。

### 3.1 Lina Q：青白气弹 / 橙红火弹

第一轮建议**保留角色 Q 帧**，只升级 `QWave`：

- 普通：青白核心 + 外层光环 + 3–5 个渐隐拖尾点，带轻微脉冲；视觉直径约 48–64px，碰撞仍 44×34。
- flame：橙红核心 + 深红外环 + 小火星拖尾；同样保持 48–64px。
- 发射：在 `t=0.26` 生成弹体时，在手部位置加一个 0.10–0.15s 的小闪光/气环，但不要生成第二颗球。
- 命中：按形态使用不同颜色——普通青白、flame 橙红；加 10–14 个粒子的短爆 + 一圈快速扩散环。flame 可额外留 2–3 个短暂火星。
- 如果用户想要明显更大的新球：必须同时重做普通 `q_02/q_03` 与 flame `q_02/q_03`，否则旧球会和新弹体冲突；flame 帧还要重算 `flame_offsets`。

### 3.2 Veno 毒液：酸绿黏液团

- 弹体：绿色核心 + 外膜 + 3–4 个气泡；随 `age` 轻微摆动/旋转；后方留 3–5 个滴落/飘散的小绿点。视觉直径约 36–48px，碰撞 radius 仍 18。
- 施法：`t=0.25` 口部出现 0.10–0.15s 的绿色小雾/闪光；不要烘进角色帧。
- 命中：绿色飞溅（8–12 个粒子）+ 0.2s 左右的毒雾残留；可与现有 poison 状态粒子衔接。
- 不要把 `emit_hit()` 全局改成绿色；只对 poison projectile 走单独 impact 分支。

### 3.3 Veno 蛛网：淡绿白丝网团

- 弹体：淡绿白核心 + 4–6 根放射丝 + 一条向后拖的丝线；随 `age` 缓慢旋转。视觉直径约 28–40px，碰撞 radius 仍 14。
- 施法：`t=0.30` 口部出现 0.10–0.15s 的丝束/白绿闪光；可参考 `veno_web_spit_v2_frames/veno_web_spit_web_00..05.png` 的节奏，但按 Veno 实际口部坐标重新放置。
- 命中：短促的网状爆裂（可把 `veno_web_spit_v2_web_master.png` 缩到约 80–120px，life 0.15–0.25s）+ 白色闪光 + 2–3 个黄色眩晕火星；不要长时间盖住目标。
- 如果复用 `web_master`：先裁切/缩放成独立 impact sprite，新文件名，不要覆盖原图；contact sheet 通过后再接入。

### 3.4 可选低优先级

- `veno_bite` 命中：口部绿色小弧光/火花，0.1s；不做也可。
- hover 蛛丝：从 2px 灰线升级为细丝 + 轻微弧度 + 上方锚点光点；绘制仍在 `Veno.draw()` 里、蜘蛛身后。不是技能，优先级最低。
- poison 状态 overlay：可改成边缘柔化的绿色轮廓/气泡，而不是整块矩形；但会改变状态视觉，需用户确认。
- stun 状态：保留现有黄点，可加一圈短暂的网纹；不要替换成新的控制逻辑。

### 3.5 建议色板

| 元素 | 核心 | 中层 | 外圈/拖尾 |
|---|---|---|---|
| Lina Q 普通 | `(240,255,255)` | `(120,230,255)` | `(70,170,255)` |
| Lina Q flame | `(255,245,200)` | `(255,170,90)` | `(255,90,40)` |
| Veno 毒 | `(216,255,168)` | `(110,220,100)` | `(45,150,60)` |
| Veno 网 | `(245,255,235)` | `(200,240,170)` | `(140,210,120)` |
| 眩晕火星 | `(255,244,170)` | `(255,224,90)` | — |

保持角色本体配色不变；特效颜色只用于弹体/粒子/爆点。

---

## 4. 开始前必须确认的 5 个问题

> 推荐答案已写在箭头后；如果用户说“按推荐”，直接执行。

**Q1 — 范围**：只改视觉，还是也改弹道/命中/数值？
→ 推荐：只改视觉；`q`、`veno_poison`、`veno_web` 的 damage/duration/speed/range/lane/status/hitbox 全部保持。

**Q2 — Lina Q 素材**：保留现有角色 Q 帧，只升级 QWave；还是重做普通/flame 的 `q_02/q_03`？
→ 推荐：第一轮保留角色帧，新 QWave 与旧小球同量级；只有用户明确要“大球/新形态”时才重做帧并重算火焰 offset。

**Q3 — Veno 蛛网来源**：复用 `veno_web_spit_v2_web_master.png`，还是重新生成一张？
→ 推荐：先复用 web_master 做弹体/命中贴花；风格不匹配再生成新版本。不要直接接入 combined 6 帧。

**Q4 — 特效层**：只改弹体外观，还是同时加施法与命中特效？
→ 推荐：同时加施法（0.10–0.15s）和命中（0.15–0.25s）；先程序化，必要时再 sprite 化。

**Q5 — 可选范围**：是否连带升级 hover 蛛丝、poison 状态 overlay、bite 命中小特效？
→ 推荐：hover 蛛丝可以顺手做；poison overlay 和 bite 命中只有在用户明确要求时再做，避免一次改太多。

---

## 5. 实施顺序

### Phase 0 — 基线

1. `git status --short`，确认没有需要保留的未提交改动被误碰。
2. 跑 smoke，确认 §1 字段全绿。
3. 按 §4 和用户确认范围；确认前不要改代码。

### Phase 1 — 共用投射物视觉管线（不改玩法）

建议先做这一层，Lina Q 和 Veno 都能复用：

- 给 `QWave` / `AimedProjectile` 增加纯视觉字段：
  ```python
  self.age = 0.0
  self.hit_color = (120, 230, 255)
  self.impact_kind = "qi"   # "qi" | "poison" | "web" | "flame"
  ```
  在 `update()` 里 `self.age += dt`。
- 在 `scene.py` 增加：
  - `spawn_projectile_cast_fx(projectile, attacker)`：按 kind/flame 发射口/手部小闪光或粒子；
  - `spawn_projectile_impact(projectile)`：按 kind/flame 选择颜色、粒子和可选的短 sprite。
- 在 `combat.resolve_projectile_hit()` 里：
  - 保留现有伤害/状态/knockback/hitstop 逻辑；
  - 把硬编码的 `emit_hit(..., (120,230,255))` 改成使用 `projectile.hit_color`；
  - 调用 `scene.spawn_projectile_impact(projectile)`。
- 在 `scene.spawn_projectile_from_event()` 创建投射物后调用 `spawn_projectile_cast_fx(...)`。
- 不要改 `ParticleSystem.emit_hit()` 的全局行为；新增 `emit_burst()` / `emit_poison_splash()` / `emit_web_splash()` 之类的独立方法，避免影响拳/腿/斧的命中反馈。
- 这一阶段不改 JSON 数值、不改 smoke 期望。

### Phase 2 — Lina Q

1. 升级 `QWave.draw()`：
   - 双层核心/光环；
   - 用 `age` 做轻微脉冲；
   - 拖尾从 3 个点增加到 4–5 个，按距离渐隐；
   - 普通青白、flame 橙红。
2. `spawn_projectile_cast_fx`：在 `t=0.26` 手部位置发一个短气环/闪光。
3. `spawn_projectile_impact`：
   - 普通：青白爆点 + 快速扩散环；
   - flame：橙红爆点 + 短暂火星。
4. 视需要决定是否重做 `q_02/q_03`；如果重做，走 contact sheet，更新 `flame_offsets`，保持 256×256 / pivot `(128,244)`。
5. 如果要做 sprite 发射/命中特效，先泛化 FX 播放器（见 Phase 4），不要让 `fx` 事件误用 `SlashEffect`。

### Phase 3 — Veno-Spider

1. 毒：
   - `AimedProjectile.draw()` 对 `venom_glob` 画分层黏液 + 气泡 + 滴落拖尾；
   - `spawn_projectile_cast_fx` 在口部加绿雾；
   - `spawn_projectile_impact` 加绿色飞溅 + 0.2s 毒雾。
2. 网：
   - `web_bolt` 画放射丝 + 旋转 + 后拖丝线；
   - 口部加丝束/白绿闪光；
   - 命中加网状爆裂（可复用 `web_master` 的裁切版）+ 黄色眩晕火星。
3. 可选：bite 命中小弧光、hover 蛛丝升级。
4. 不改 `veno_poison` / `veno_web` 的 attack 数据、status 时长、AI 逻辑。

### Phase 4 — 可选 sprite FX 泛化

只有在用户要求“sprite 特效/新素材”时做：

- 方案 A：把 `game/slash_fx.py` 的 `SlashEffect` 抽成通用 `SpriteEffect`（目录、帧名、durations、frame size、pivot 可配置），Nyra 继续用同一套行为。
- 方案 B：新增 `game/sprite_fx.py`，保留 `SlashEffect` 不动，`scene.spawn_fx_effect()` 按 `event["fx"]` 分派。
- 无论哪种，`AttackRuntime` 的 `fx` 分支要从 `spawn_slash_effect` 改为通用分派；Nyra 的 `nyra_slash` 必须保持原行为，smoke 全绿。
- 新增 FX 目录时，仿照 `nyra_slash_fx_missing` 增加 `*_fx_missing` smoke 检查。
- 如果新增 projectile kind，更新 `game/config.py` 的 `PROJECTILE_KINDS` 和 `scene.spawn_projectile_from_event()`。

### Phase 5 — 验证与文档

- 跑 smoke；数值型字段应保持不变。
- 手动看普通/flame Q、毒/网、施法/命中、block/wall/ground 边界。
- 更新 `README.md`、`docs/DEBUG.md`、`docs/DESIGN_DECISIONS.md`、`docs/ASSET_PIPELINE.md`、`docs/NEXT_SESSION_CHARACTERS.md` 中与特效相关的描述。
- 除非用户明确要求，不要 commit。

---

## 6. 素材生成与接入

### 6.1 强制规则

- 生成任何图片前读 `docs/IMAGE_GENERATION_RULES.md`；角色帧仍受 body layering、weapon grip、no interpenetration、size lock 约束。
- `Image/` 只读；不要覆盖 `Image/Character/lina-seabright-v1-256.png` 或 `Image/Enemy/veno-spider-128.png`。
- 所有候选、contact sheet、预览默认放 `assets/generated/contact_sheets/`；只有用户批准后才复制到 `assets/frames/`。
- 不覆盖已有版本；新版本用新文件名/版本号。

### 6.2 命名建议

```text
lina_q_cast_fx_00.png
lina_q_hit_fx_00.png
lina_q_flame_cast_fx_00.png
lina_q_flame_hit_fx_00.png
veno_poison_cast_fx_00.png
veno_poison_hit_fx_00.png
veno_web_cast_fx_00.png
veno_web_hit_fx_00.png
```

contact sheet 用 `lina_q_fx_v1.png`、`veno_web_fx_v1.png` 这类版本名。运行时目录建议：

```text
assets/frames/lina/q_fx/
assets/frames/lina/flame/q_fx/
assets/frames/veno/veno_poison_fx/
assets/frames/veno/veno_web_fx/
```

如果特效是“跟随弹体”的，不要强行用 256×256/320×320 角色画布；用小画布 + 明确的 draw offset，避免 pivot 限制。

### 6.3 画布与锚点

- Lina 角色帧：256×256，pivot `(128,244)`，body ~210；flame 帧有 `flame_offsets`。
- Veno 角色帧：320×320，pivot `(160,308)`，body 150。
- cast-anchored 特效用角色画布/pivot；独立 projectile/impact 用小画布，并在代码里写清 offset。
- **不要把弹体、爆点、蛛网烘进角色施法帧**；Veno 现有帧是干净的，继续保持。
- 普通 Q 的 `q_02` 有一颗已烘的小球；flame Q 的 `q_02` 是拳部火焰。重做这些帧时要保持 handoff 在 `t=0.26`。
- flame Q 的 `q_01/q_02` alpha bbox 已经顶到画布右边（x=256）；重绘时留出余量，并重算 `flame_offsets`。

### 6.4 复用 `veno_web_spit_v2`

- `web_master.png`：可裁切/缩放到约 28–40px 做弹体，或 80–120px 做命中贴花；保留 alpha，不要覆盖原图。
- `veno_web_spit_v2_frames/veno_web_spit_web_00..05.png`：只作为施法节奏/丝线形态参考；它绑定 640×320 的口部坐标，不能直接用于 320×320 的 Veno。
- `combined_*`、`spider_*`：不要接入运行时；会与场景里的 Veno 本体重复。
- 如果最终决定重新生成，按 `docs/ASSET_PIPELINE.md` 的流程走；新素材先 contact sheet。

### 6.5 热重载

- F5 会刷新 JSON 和 PNG（按 mtime），但**不会重新导入 Python 代码**。
- 修改 `QWave`/`AimedProjectile`/新增 FX 类/`FRAME_DURATIONS` 这类 Python 常量后，必须重启进程。
- 新增 sprite FX 时，建议按 `SlashEffect` 的 mtime 缓存方式实现，保证替换 PNG 后 F5 可刷新。

---

## 7. 验证清单

### 7.1 自动

```bat
.venv/Scripts/python.exe main.py --smoke-test
```

要求：

- exit 0；
- `q_damage_ok=True`、`q_block_ok=True`、`flame_ok=True`；
- `veno_bite_ok=True`、`veno_poison_ok=True`、`veno_poison_stack_ok=True`、`veno_web_ok=True`；
- `veno_ai_ascent_ok=True`、`veno_ai_descend_ok=True`、`veno_win_ok=True`；
- `roster_ok=True`、`missing_frames=0`、`veno_missing_frames=0`。

如果只改视觉，以上数值应全部保持不变。若改了 projectile 碰撞盒、速度、生成时刻，必须同步更新 smoke。

### 7.2 手动

- **Lina Q 普通**：地面 Q、站 block Q；看手部小球 → 前方 QWave 的交接；命中 Dummy 的青色爆点；无旧球残留。
- **Lina Q flame**：E 变身后 Q；橙红弹体/拖尾/命中；命中不是青色粒子；火焰 Q 帧没有明显横移。
- **Veno 毒**：地面/悬空各放一次；看口部绿雾、绿色弹体、气泡/滴落、命中绿色飞溅；poison 状态正常。
- **Veno 网**：地面/悬空各放一次；看口部丝束、旋转网团/拖尾、命中网状爆裂 + 黄点；stun 正常。
- **边界**：弹体撞 block、飞出 wall、落到地面、超过 range 后消失；不要出现“命中后特效还跟着飞”。
- **绘制层级**：大弹体不遮玩家；命中爆点不长时间盖住角色；Veno 悬空蛛丝仍在蜘蛛身后。
- **F5/重启**：替换 PNG 后 F5 能看到变化；改 Python 后重启才生效。

### 7.3 可选离屏预览

```python
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
pygame.init()
screen = pygame.display.set_mode((1280, 720))
# 构造 JsonStore / ArenaScene，推进到目标帧后：
scene.draw(screen)
pygame.image.save(screen, "preview.png")
```

必须先 `set_mode` 再绘制。

---

## 8. 不要踩的坑

- 不要改 `q` / `veno_poison` / `veno_web` 的 damage、duration、speed、range、lane、status、hitbox，除非用户明确要求。
- 不要把普通 Q 的 `q_02` 旧球忽略掉；换弹体外观时要么保持同量级，要么重做 `q_02/q_03`。
- 不要忘记 flame Q 的 `flame_offsets` 和右侧裁切风险。
- 不要直接改 `ParticleSystem.emit_hit()` 的颜色/数量；那会影响拳/腿/斧的命中反馈。新增独立 impact 方法。
- 不要直接改 `resolve_projectile_hit()` 的伤害/状态逻辑；只加视觉分派。
- 不要给 Lina/Veno 的 `fx` 事件直接接 `spawn_slash_effect()`；`SlashEffect` 是 Nyra 专用 384×384 / pivot 192,372，必须先泛化。
- 不要把 `veno_web_spit_v2_frames/veno_web_spit_combined_*` 或 `veno_web_spit_spider_*` 直接拷进运行时；会双本体。
- 不要给 Veno 角色帧烘弹体/蛛网；hover 蛛丝由场景绘制。
- 不要把 Veno 的 150×150 hurtbox 缩小；它是故意大于视觉高度的，缩小会让 Lina Q / axe throw 打空。
- 不要为了特效延长 hitstop；hitstop 会冻结整个场景，特效自然暂停。
- 不要默认所有 FX 都画在玩家上面；先看 §2.3 的绘制顺序。
- F5 只刷新 PNG/JSON，不刷新 Python。
- 不要 `git reset` / `git checkout -- .` / `git stash`；不要覆盖未提交的 Nyra 帧和文档。
- 默认阵容保持 **Lina vs Warrior**；不要改 `debug.json` 的默认值。
- 除非用户明确要求，不要 commit。

---

## 9. 文件导航

| 区域 | 文件 |
|---|---|
| Lina Q 启动/命中回能 | `game/lina.py`（`_start_q`、`on_projectile_hit`） |
| Lina Q 数据 | `game/data/attacks.json`（`"q"`） |
| Lina Q 动画/flame offset | `game/data/animations.json`（`clips.q`、`flame_clips.q`、`flame_offsets`） |
| Lina Q 弹体 | `game/projectile.py`（`QWave`） |
| Veno 技能/AI/状态/蛛丝 | `game/veno.py` |
| Veno 数据 | `game/data/attacks.json`（`veno_bite/poison/web`） |
| Veno 动画 | `game/data/animations.json`（`veno_clips`） |
| Veno 弹体 | `game/projectile.py`（`AimedProjectile`） |
| 投射物生成/绘制顺序 | `game/scene.py`（`spawn_projectile_from_event`、`draw`） |
| 命中结算 | `game/combat.py`（`resolve_projectile_hit`） |
| 粒子 | `game/particles.py` |
| sprite FX 参考 | `game/slash_fx.py`（Nyra Q） |
| 校验 | `game/config.py`（`PROJECTILE_KINDS`、required clips） |
| smoke | `main.py`（`q_damage_ok`、`q_block_ok`、`flame_ok`、`veno_*`） |
| Lina 角色帧 | `assets/frames/lina/q/`、`assets/frames/lina/flame/q/` |
| Veno 角色帧 | `assets/frames/veno/` |
| 已有蛛网原型 | `assets/generated/contact_sheets/veno_web_spit_v2_*`、`tools/generate_veno_web_spit.py` |
| 图片门禁 | `docs/IMAGE_GENERATION_RULES.md` |
| 素材流程 | `docs/ASSET_PIPELINE.md` |
| 旧的全量 handoff | `docs/NEXT_SESSION_NYRA_VENO_LINA_Q.md` |

---

## 10. 完成标准

- [ ] 基线 smoke exit 0，改动后仍 exit 0；数值型字段不变。
- [ ] Lina Q 普通/火焰的弹体、拖尾、施法、命中都能在 1× 下区分；flame 命中不再是青色。
- [ ] Veno 毒/网的弹体、施法、命中都能区分；毒是酸绿，网是淡绿白丝网；stun 仍有黄点。
- [ ] 没有旧球/双弹体/双本体；没有把特效烘进角色帧。
- [ ] 弹体撞 block/wall/ground/range 后消失，特效不残留。
- [ ] 大弹体和爆点不长时间遮挡角色；绘制层级符合 §2.3。
- [ ] 替换 PNG 后 F5 生效；改 Python 后重启生效。
- [ ] 所有新素材都有 contact sheet 且已获批准；`Image/`、`instruction.docx`、`UI Resources/` 未动。
- [ ] 文档已同步；未提交 git（除非用户明确要求）。
