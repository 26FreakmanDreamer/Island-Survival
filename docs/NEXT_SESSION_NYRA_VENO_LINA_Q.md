# Next Session — Nyra / Veno 细节调整 + Lina Q 特效改造

> 日期：2026-10-23
> 用途：新 session 的 handoff。先读本文件，再按文末 prompt 开始。
> 原则：**先确认用户具体要改什么，再动代码/素材**；不要自行改数值，也不要 revert/stash 现有未提交改动。

---

## 0. 给新 session 的开场 prompt（可直接复制）

```text
先阅读 docs/NEXT_SESSION_NYRA_VENO_LINA_Q.md 和 AGENTS.md。
这一轮我要：
1) 细节调整 Nyra：<在这里补充具体项目>
2) 细节调整 Veno：<在这里补充具体项目>
3) 修改 Lina Q 技能特效：<在这里补充视觉/机制/时长/颜色等要求>

先不要改代码或素材。请先跑一次 smoke 确认基线，然后逐项 grill 我：
- 每项要改的当前值、目标值、判定/时序、是否影响 smoke；
- Lina Q 是只改视觉，还是也要改 projectile/hitbox/命中方式；
- 是否要新素材，若需要则先走 contact sheet 审批。
确认后再实现，最后跑 smoke + 视觉检查并同步文档。
```

如果用户只说了“调整 Nyra/Veno、改 Lina Q 特效”而没有给具体项，**先问清单**（见 §9），不要猜。

---

## 1. 当前工作区与基线（先做，不要跳过）

- 分支：`main`；最后提交：`26db0cf Complete data-driven roster, knock-up FX and sandbox polish`。
- **所有 Nyra/Veno 实现与最近的 Q 改造都还未提交**。工作区有大量 modified 与 untracked 文件。
- 不要执行 `git reset`、`git checkout -- .`、`git stash`、批量覆盖或删除。
- `instruction.docx` 是用户修改过的文件；`UI Resources/`、`assets/generated/*`、`assets/frames/nyra/`、`assets/frames/veno/`、`game/wave_fx.py` 等是未跟踪内容。没有明确要求时不要动 `instruction.docx`、`UI Resources/`。
- `Image/` 是 canonical 视觉源，**只读**，不得覆盖。

### 1.1 基线命令

```bat
run.bat --smoke-test
```

或：

```bat
.venv/Scripts/python.exe main.py --smoke-test
```

当前基线应为 **exit 0**，关键字段：

```text
missing_frames=0
nyra_q_ok=True
nyra_q_range_ok=True
nyra_missing_frames=0
veno_missing_frames=0
warrior_missing_frames=0
roster_ok=True
```

如果基线不是全绿，先报告并修复基线，不要叠加新改动。

### 1.2 默认阵容与操作

- 默认：**Lina vs Warrior**。
- `[` / `]`：Lina ↔ Nyra。
- F7：Warrior → Veno-Spider → Dummy。
- F8：切换敌人 AI（无 AI 的敌人则切 invincible）。
- F9：重置；F5：热重载 JSON；F1：hitbox/hurtbox overlay；F2：debug panel。
- B：开关 blocks；F6：时间倍率；F11：状态演示；F12：扣玩家血。
- Veno 技能槽：V/C/X = bite/poison/web，Z 为空槽 no-op。

---

## 2. Nyra 当前实现（可调整点）

### 2.1 数值（`game/data/stats.json` → `nyra`）

| 项 | 当前值 |
|---|---|
| HP | 100 |
| basic_atk / extra_atk | 20 / 0 |
| stage_body_width | 100 |
| walk / jump_v / gravity | 260 / 760 / 2200 |
| Q / E cooldown | 8.0s / 15.0s，初始就绪 |
| hurtbox standing | 56 × 210 |
| hurtbox crouching | 56 × 130 |
| energy | 无（没有 energy/flame） |

### 2.2 攻击与判定（`game/data/attacks.json`）

| attack | 伤害 | duration | 判定/事件 | 备注 |
|---|---:|---:|---|---|
| `nyra_slash` | 20（1.0/1.0） | 0.31 | hitbox `[34,-170,120,60]`，t 0.13–0.21，knockback 80；lunge 24 @0.08 | +1 mark；hitstun 0.2，hitstop 0.06 |
| `nyra_thrust` | 24（1.2/1.3） | 0.40 | hitbox `[28,-165,130,48]`，t 0.12–0.22，knockback 220；lunge 30 @0.10 | +1 mark；hitstun 0.25，hitstop 0.07 |
| `nyra_wave`（Q） | 30（1.5/1.5） | 0.40 | **cast-anchored 分段 hitbox**：0–0.12 `[28,-165,130,48]`；0.12–0.30 `[28,-212,162,123]`（reach 190）；0.30–0.40 `[28,-165,130,48]`；fx t=0.04 | 不生成 projectile；不叠/不引 mark；hitstun 0.25，hitstop 0.06 |
| `nyra_dash`（E） | 30（1.5/1.8） | 0.45 | dash 0.06–0.34 speed 900；hitbox `[0,-180,90,180]` 0.06–0.30，knockback 250 | `pass_through_enemy: true`；hitstun 0.3，hitstop 0.08；不叠 mark |

Q 的 0.12–0.30 延长窗口对应 `nyra_wave_fx` 的**特效帧 02–04**。其他时间（含特效帧 00/01/05 的空白段和首尾）使用右键 thrust 的 hitbox。

### 2.3 印记被动（`game/nyra.py`）

- 只有 `nyra_slash` / `nyra_thrust` 的近战命中叠 1 层；最多 3 层；Q/E 不叠也不引爆。
- 第 4 次近战命中引爆：`1.8 × atk + 0.10 × target.max_hp`，先乘目标的 damage reduction。
- 引爆后保留 1 层；目标死亡则清 0。
- 引爆额外 `0.10s` hitstop，粒子 + 敌人头顶扩散环；`mark_burst_time=0.4`。
- F2 显示 `MARKS n/3 BURST ... LAST ...`；头顶画 3 个 pips。
- `reset()` / 敌人死亡会清 marks、burst、detonations。

### 2.4 帧与素材

- 画布 384×384，pivot `(192,372)`，body height 214；只存右向帧，运行时镜像。
- 角色帧 25 张，位于 `assets/frames/nyra/`：
  - idle 2、walk 2、jump 2、crouch 1、hurt 1、KO 2、`nyra_slash` 6、`nyra_thrust` 3、`nyra_wave` 3、`nyra_dash` 3。
- `nyra_slash` 6 帧结构：初始前下方 45° → 过渡（剑水平下 10–20°，手臂开始前伸）→ v11 大臂前伸帧（219px，脚底 372）→ 复用 thrust_v5_01 长剑接触 → 两张收势；durations `0.04/0.04/0.05/0.08/0.05/0.05`。
- `nyra_thrust`：frame 00/02 原版；frame 01 为 v5 长 sword，导入时按 body-height 238 单独处理，得到约 214 身高。
- `nyra_wave` 角色 clip 仍是 3 帧，durations `0.12/0.12/0.16`，总计 0.40；**不要**把剑气烘进角色帧。
- `nyra_crouch` 是 1 帧 163×170（body ~170，导入用 `--body-height 173`）；蹲下 hurtbox 仍是 56×130，其他 clip 用 214。

### 2.5 Q 特效（`game/wave_fx.py` + `assets/frames/nyra/nyra_wave_fx/`）

- 6 张独立的 384×384 透明剑光贴图，pivot `(192,372)`，cast-anchored 绘制。
- durations：`0.04, 0.04, 0.05, 0.08, 0.05, 0.05`（总 0.31）。
- 帧 00/01/05 **完全透明**；02 出现（小 chevron），03 最盛（大 chevron，bbox reach 190），04 原位淡出。
- `fx` 事件在 `nyra_wave` 的 t=0.04 触发；可见效果约在 t=0.12–0.30。
- 帧缓存按文件 mtime 失效，替换 PNG 后 F5 可刷新；`FRAME_DURATIONS` 是 Python 常量，改时长需重启进程。
- 角色帧 `nyra_wave` 仍是 3 帧；Q 特效和角色帧是两个独立层。

### 2.6 主要文件

| 区域 | 文件 |
|---|---|
| Nyra 类 | `game/nyra.py` |
| 通用攻击 runtime / cast anchor / fx 事件 | `game/combat.py` |
| 场景 FX / marks / dash push | `game/scene.py` |
| Q 特效 | `game/wave_fx.py` |
| 数值 / 攻击 / 动画 | `game/data/stats.json`、`attacks.json`、`animations.json` |
| roster / 类注册 | `game/data/roster.json`、`game/roster.py` |
| 校验 | `game/config.py` |
| smoke | `main.py` Phase C |

### 2.7 调整 Nyra 时必须连带检查

- 改伤害后，更新 `main.py` 里硬编码的 smoke 期望：
  - `nyra_slash_ok`：Dummy 1000 → 980；
  - `nyra_burst_damage_ok`：4 次 LMB 后 784（4×20 + 136）；
  - `nyra_thrust_ok`：976；
  - `nyra_q_ok`：970；
  - `nyra_dash_ok`：970。
- 改 slash/thrust 帧 dur 或 hitbox 窗口，要同步 `nyra_slash` 的 0.13–0.21 / `nyra_thrust` 的 0.12–0.22。
- 改 Q 的延长范围/时序，要同步 `nyra_q_range_ok`（当前 Nyra 100 / Dummy 300，t<0.12 不受伤，t≥0.13 受伤）。
- 改 Veno hover 或 Nyra Q 的 y 范围时，检查交互：Veno base hover 220，Nyra Q 延长 box 顶到 212；低 hover（约 140）可被地面 Q 打到，base 220 不行。**当前 50 HP 的 Veno 在 3 次 LMB 后就死了（3×20=60），印记引爆通常不会发生在 Veno 身上**；若要让 Veno 体验 marks，需要另议 HP 或沙盒倍率。
- 改 hurtbox 时检查 Lina Q（fist lane 142）和 Warrior axe throw 是否还能命中 Veno；Veno 的 150×150 hurtbox 是故意大于视觉高度的。
- 改帧素材必须走 contact sheet；保持 384 canvas / pivot / body 214；蹲下保持 ~170 视觉身高但 hurtbox 130。

---

## 3. Veno-Spider 当前实现（可调整点）

### 3.1 数值（`game/data/stats.json` → `veno`）

| 项 | 当前值 |
|---|---|
| HP | 50 |
| basic_atk / extra_atk | 10 / 0 |
| stage_body_width | 140 |
| walk / jump_v / gravity | 320 / 700 / 2200 |
| cooldowns | bite 1.8s / poison 3.5s / web 5.0s |
| hurtbox standing / crouching | 150 × 150 / 150 × 150 |
| hover base / min / max | 220 / 140 / 300 |
| hover vertical / descend | 170 / 260 |
| hover oscillation / rate | 80 / 1.2 |
| AI bite_range / close_range / ranged_range | 150 / 140 / 700 |
| AI decision_interval / hover_min_time | 0.1 / 0.3 |

### 3.2 技能与弹道（`game/data/attacks.json`）

| attack | 伤害 | duration | 行为 |
|---|---:|---:|---|
| `veno_bite` | 15（1.5/1.5） | 0.50 | hitbox `[24,-120,110,90]`，t 0.18–0.30，knockback 120；hitstun 0.25，hitstop 0.05 |
| `veno_poison` | 8（0.8/0.8） | 0.60 | projectile `venom_glob` t=0.25，origin_height 100，speed 520，range 800，knockback 40；poison 3.0s，`dps = 3% target max_hp`；同源命中延长剩余时间 |
| `veno_web` | 10（1.0/1.0） | 0.65 | projectile `web_bolt` t=0.30，origin_height 100，speed 480，range 800，knockback 60；stun 1.0s |

- 两个远程弹道都是**发射瞬间瞄准玩家位置**的直线弹，不追踪；跳跃/位移可躲。
- `AimedProjectile` 在 `game/projectile.py`；毒/网的状态在 `game/veno.py` 的 `on_projectile_hit` 挂。
- 毒按来源叠加：同源 `veno_poison` 延长，不同来源独立。眩晕由 `StatusSet` 处理。

### 3.3 AI 当前逻辑（`game/veno.py`）

- 地面：
  - 玩家距离 > `bite_range` 且毒或网就绪 → 上升；
  - 距离 ≤ `bite_range` 且咬就绪 → `veno_bite`；
  - 前方有 block：有远程就绪 → 上升，否则跳跃；
  - 否则以 320px/s 追击。
- `ascend`：升到 `ground_y - hover_base`，然后转 `hover`。
- `hover`：
  - 距离 ≤ `close_range` 且 hover 时间 ≥ `hover_min_time` → 下降；
  - 毒就绪且距离 ≤ `ranged_range` → 毒；
  - 网就绪且距离 ≤ `ranged_range` → 网；
  - 毒/网都冷却且 hover ≥ 0.5s → 下降；
  - 距离 > `ranged_range` 时以 115px/s 靠近。
- `descend`：落地回 ground；距离 > `bite_range` 时向玩家靠。
- 被击中且仍在空中 → 转 `descend`（被打下来）。
- 单只 Veno；`separates=true`、`decides_match=true`。docx 的 `n=3` 多敌人未实现。

### 3.4 帧与素材

- 画布 320×320，pivot `(160,308)`，body height 150；只存右向。
- 20 张角色帧：idle 2、walk 2、hover 2、jump 2、hurt 1、KO 2、bite 3、poison 3、web 3。
- 当前 idle 与 jump 复用同一张共享帧（生成器在尺寸上漂移）；如果本轮要细化 idle/jump，优先重生成并做 size lock。
- bite 当前是退回的 v1 版本；hover 帧不含蛛丝，蛛丝由场景绘制；毒/网帧不烘弹体。
- 视觉锁：巨大黑色甲壳蜘蛛、腹部高耸、青柠绿毒纹、绿眼、獠牙、八条分节腿（绿环、苍白足尖）；头/牙朝右，腹部在左；八条腿都要清晰，不能多腿。
- KO 帧朝右；透明背景。

### 3.5 主要文件

| 区域 | 文件 |
|---|---|
| Veno 类 / AI / hover / 伤害状态 | `game/veno.py` |
| 远程弹道 | `game/projectile.py`（`AimedProjectile`） |
| 场景 spawn / 状态 FX / 蛛丝绘制 | `game/scene.py` |
| 数值 / 攻击 / 动画 | `game/data/stats.json`、`attacks.json`、`animations.json` |
| roster / 校验 | `game/data/roster.json`、`game/config.py` |
| smoke | `main.py` Phase D |

### 3.6 调整 Veno 时必须连带检查

- 改伤害后，smoke 期望会变：
  - `veno_bite_ok`：Lina 100 → 85；
  - `veno_poison_ok`：Lina 100 → 92，poison `dps=3.0`，remaining >2.5；
  - `veno_web_ok`：Lina 100 → 90，`stun` remaining ≤1.0；
  - `veno_win_ok`：Veno HP 20，Lina punch 20 → WIN。
- 改 hover 范围/速度，要同步 `veno_ai_ascent_ok` / `veno_ai_descend_ok` 的位置与 tick 数。
- 改 hurtbox 高度时，检查 Lina Q（142px lane）和 Warrior axe throw 是否还能命中；150×150 是故意放大。
- 改 idle/jump 帧时注意尺寸漂移；必须 contact sheet 检查 body/abdomen/head 大小一致。
- 改 `skill_slots` 或新增技能时，更新 `veno.py` 的 `start_attack`/`skill_remaining`/`force_attack`、`config.py` 的 `REQUIRED_ATTACKS`/`REQUIRED_VENO_CLIPS`、F2 和 smoke 的 slots 检查。

---

## 4. Lina Q 当前实现（改特效的起点）

### 4.1 机制与数值

- attack id：`"q"`（`game/data/attacks.json`）。
- 伤害：`basic 1.0 + extra 1.5` = **20**（初始 20/0）；flame bonus 另乘。
- duration 0.35s；hitstun 0.2；hitstop 0.06；cooldown 8s；仅地面可放。
- 事件：`t=0.26` 生成 projectile `q_wave`，`lane="fist"`，speed 700，range 520，knockback 150。
- 普通形态命中回能 20；flame 形态不 grant energy（`grant_energy=not flame`），改为挂 burn 5 HP/s × 3s（`Lina.on_projectile_hit`）。
- `PROJECTILE_KINDS` 含 `q_wave`；`config.py` 会校验。
- 弹体从 `attacker.x + facing*50` 生成，y = `stage.lane_y("fist", attacker.y)` = **feet - 142**。
- lane 高度（`debug.json`）：high 180 / fist 142 / mid 120 / low 60，都是相对脚底；所以站在 block 上 Q 的轨迹也会抬高。
- 弹体在撞 block、命中目标或超过 range 520 后消失；命中只结算一次。**当前 `QWave` 没有 wall 检查**，且 block 检查不读取 `blocks_enabled`（与 `SwordWave`/`AimedProjectile` 不一致）；如果本轮改 Q 的弹道/碰撞，先确认这两点是否要顺手修。

### 4.2 角色动画与 projectile 交接

- 普通 Q：`assets/frames/lina/q/q_00..03.png`，4 帧，durations `0.06/0.10/0.10/0.09`，总 0.35。
- 火焰 Q：`assets/frames/lina/flame/q/q_00..03.png`，同样 4 帧/durations。
- 动画语义（现有设计）：
  - frame 0：无气流；
  - frame 1：聚气；
  - frame 2：球状打出（sprite 里有球）；
  - frame 3：手部干净；
  - **projectile 在 t=0.26 生成，正好 frame 2 结束、frame 3 开始**，避免球重复。
- **注意：球是烘在 Lina 角色 Q frame 2 里的。** 如果只改 `QWave` 的弹体外观，frame 2 的旧球仍在；要保持一致，必须同时重做普通/flame Q 的 frame 2（以及 frame 3 的干净手），并保持 t=0.26 交接，否则会出现“旧球 + 新弹体”两种外观。反过来，如果只想改角色帧里的球/手势，也要确认 projectile 的 t=0.26 交接仍然对齐。
- flame 帧有水平 offset（`animations.json` 的 `flame_offsets`）：
  - `flame/q/q_00.png` -43，`q_01` -25，`q_02` -32，`q_03` -42。
  - 如果替换 flame Q 帧，需要重新计算这些 offset，否则 Lina 会横移。
- Lina 画布 256×256，pivot `(128,244)`，body ~210。

### 4.3 当前“特效”实现

- 不是 sprite，而是 `game/projectile.py` 的 `QWave.draw()`：
  - 64×64 临时 surface，44×34 碰撞矩形；
  - 普通青色 `(120,230,255)`，flame 橙色 `(255,150,90)`；
  - 3 个拖尾圆 + 中心大圆 + 白色高光 + 外圈；
  - 没有专用的 impact/hit sprite；命中时走 `resolve_projectile_hit` 的通用 hit particles；
  - 没有环境光/命中爆炸/独立 sprite 帧。
- 生成分支在 `game/scene.py` 的 `spawn_projectile_from_event()` 的 `else`（非 sword_wave/venom/web/axe 即 QWave）。
- 普通/flame 的颜色和形态只由 `QWave.flame` 决定。
- 当前没有 Lina Q 的独立 FX 素材目录；特效完全程序化。
- 弹体生成 x 是 `attacker.x + facing*50`；如果改球/特效，t=0.26 交接帧要核对角色帧里的旧球位置与新弹体位置，避免位置跳变。

### 4.4 改 Lina Q 特效时，先确认这些选择

1. **只改视觉，还是也改机制？**
   - A. 保留 projectile（推荐先问）：只重画/替换 `QWave` 的 orb/trail/impact。
   - B. 改成命中型 hitbox/wave（类似 Nyra Q）：要重新定义命中窗口、block/wall 行为、flame bonus、能量、smoke。
   - C. 保留 projectile，但增加独立 FX 层（发射、飞行、命中）。
2. **普通/火焰形态是否要不同素材/颜色/大小？**
   - 当前只是青色 vs 橙色程序化圆。
3. **时间点与交接**：
   - 是否保持 t=0.26、frame 2→3 的交接？
   - 飞行速度 700 / range 520 / lane 142 是否保持？
   - 是否要 cast-anchored 的发射特效、跟随弹体的拖尾、命中爆炸？
4. **block / wall 行为**：
   - 当前 Q projectile 会被 block 挡住并消失（没有 wall 检查）；若改成 hitbox，`AttackRuntime` 的 hitbox 默认不检查 block（Nyra Q 就是穿 block 的命中判定），这是行为差异，必须先确认。
5. **数值是否保持**：
   - 20 伤害、8s CD、+20 energy（普通）、flame +20/40/60% bonus、knockback 150、hitstun 0.2。
6. **素材方式**：
   - 程序化（改 `QWave.draw`）最快，但普通/flame 两套颜色都在代码里；
   - sprite FX（新目录，如 `assets/frames/lina/q_fx/`）便于美术迭代，但要处理 canvas/pivot/偏移、普通/flame 两套、F5 缓存和 contact sheet；
   - 不要把弹体/爆炸烘进 Lina 的 Q 角色帧，除非明确要求。

### 4.5 如果改成 sprite FX，建议的落点

- 新目录：`assets/frames/lina/q_fx/`（普通）与 `assets/frames/lina/flame/q_fx/`（火焰），或一个带 variant 的目录；命名和 `WaveEffect` 类似。
- 画布/pivot：如果特效要相对 Lina 身体锚定，用 256×256 / pivot `(128,244)`；如果特效独立跟随 projectile，可用独立小画布 + 明确 draw offset，避免被 Lina 的 pivot 限制。
- 发射特效：可由 `q` 的 `fx` 事件触发（`AttackRuntime` 已支持 `fx` + `anchor:"cast"`，可参考 Nyra Q）；但当前 `q` 没有 fx 事件。
- 飞行/命中特效：在 `QWave.draw` / `QWave.update` 或 `resolve_projectile_hit` 里加，注意 hitstop 时冻结、普通/flame 颜色、F5。
- 如果新增 projectile kind：同时改 `config.PROJECTILE_KINDS` 和 `scene.spawn_projectile_from_event`（`docs/NEXT_SESSION_CHARACTERS.md` 的旧提醒仍然有效）。

### 4.6 主要文件

| 区域 | 文件 |
|---|---|
| Lina 类 / Q 启动 | `game/lina.py`（`_start_q`） |
| Q 攻击数据 | `game/data/attacks.json`（`"q"`） |
| Q 动画 / flame offsets | `game/data/animations.json` |
| Q 弹体 | `game/projectile.py`（`QWave`） |
| 生成/命中 | `game/scene.py`（`spawn_projectile_from_event`） |
| 命中结算 | `game/combat.py`（`resolve_projectile_hit`） |
| 校验 | `game/config.py`（`PROJECTILE_KINDS`、required attacks/clips） |
| smoke | `main.py`（`q_damage_ok`、`q_block_ok`、`flame_ok`） |

### 4.7 Lina Q 的 smoke 依赖

- `q_block_ok`：Lina 站在 block 上 Q，检查 `scene.projectiles[0].y == lane_y("fist", player.y)`。
- `q_damage_ok`：Q 命中后敌人 HP = max_hp - 20。
- `flame_ok`：E 后 `anim.variant == "flame"` 且 `flame_time > 0`（不直接验证 flame Q 颜色）。
- 如果改 Q 的生成时机/弹体类型/伤害/height，必须同步这些断言，否则 smoke 会假失败或漏测。
- `switch_clears_ok` 也会检查切换时 projectile 清空；如果 Q 不再生成 projectile，要调整相关断言。

---

## 5. 素材与图片生成规则（强制）

- 生成任何图片前，必须先读 `docs/IMAGE_GENERATION_RULES.md`，并应用：
  - body layering（近侧在前、远侧在后）；
  - weapon hand/grip（持武器手、握点、握法一致）；
  - no interpenetration（逐对检查手臂/躯干/武器/头发/服装）；
  - size/proportion lock（同一角色所有帧身体高度、头身比、脚底基线一致）。
- canonical `Image/` 只读；使用 approved base：
  - Lina：`assets/generated/base/lina_side_base.png`（body 210）；
  - Nyra：`assets/generated/base/nyra_side_base.png`（body 214）；
  - Veno：`assets/generated/base/veno_side_base.png`（body 150）；
  - Warrior：`assets/generated/base/warrior_side_base.png`（body ~230）。
- 帧流程：生成候选 → `tools/collect_frames.py` → `tools/import_frames.py`（指定 canvas/pivot/body-height）→ `tools/contact_sheet.py` 审批 → 复制到 `assets/frames/...` → F5。
- Nyra contact sheet 参数：`--cell 384 --pivot-x 192 --pivot-y 372`；导入 `--body-height 214 --canvas 384 --pivot-x 192 --pivot-y 372`。
- Veno contact sheet：`--cell 320 --pivot-x 160 --pivot-y 308`；导入 `--body-height 150 --canvas 320 --pivot-x 160 --pivot-y 308`。
- Lina contact sheet：`--cell 256 --pivot-x 128 --pivot-y 244`；导入默认 256 / 128,244。
- 只有 contact sheet 通过后才安装；不要用拉伸/镜像/局部擦除掩盖尺寸或穿模问题。
- 左向不生成：只做右向帧，运行时镜像。

---

## 6. 建议的验证清单

### 自动

```bat
run.bat --smoke-test
```

- exit 0；所有 `*_missing_frames=0`；`roster_ok=True`。
- 若改 Nyra 数值/判定：检查 `nyra_slash_ok`、`nyra_burst_ok`、`nyra_burst_damage_ok`、`nyra_thrust_ok`、`nyra_q_ok`、`nyra_q_range_ok`、`nyra_dash_ok`、`nyra_dash_cd_ok`。
- 若改 Veno：`veno_bite_ok`、`veno_bite_cd_ok`、`veno_poison_ok`、`veno_poison_stack_ok`、`veno_web_ok`、`veno_ai_ascent_ok`、`veno_ai_descend_ok`、`veno_win_ok`。
- 若改 Lina Q：`q_damage_ok`、`q_block_ok`、`flame_ok`、`switch_clears_ok`。

### 手动

- F1：Nyra Q 三段 hitbox 切换；Veno hover hurtbox；Lina Q 的生成位置。
- F2：Nyra `Q/E`、`MARKS`；Veno `MODE/HOVER`、slots/冷却；Lina energy。
- `[`/`]`：Lina ↔ Nyra；F7：Warrior → Veno → Dummy。
- Nyra：LMB/RMB 叠印记、4 次引爆、Q 不叠、E 穿敌不穿墙、蹲下 hurtbox、Q 特效 02–04 与延长框对齐。
- Veno：地面咬、升空、悬垂毒/网、被打下来、V/C/X/Z、毒叠加、网眩晕。
- Lina Q：普通/火焰两种形态的发射/飞行/命中；站在 block 上的 lane 高度；撞 block 或达到 range 后消失（当前无 wall 检查）；F5 热重载。
- 若改素材：逐帧 contact sheet 检查尺寸、脚底、握剑/握斧、穿模；替换后 F5 看缓存是否刷新。

### 离屏截图（可选）

如果要无窗口预览某一帧：

```python
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
screen = pygame.display.set_mode((1280, 720))
# ... 构造 JsonStore / ArenaScene，推进 tick ...
scene.draw(screen)
pygame.image.save(screen, "preview.png")
```

必须先 `set_mode` 再绘制，否则 `convert_alpha()` 或字体初始化会失败。

---

## 7. 已知 caveats / 不要踩

- `SwordWave`（`kind="sword_wave"`）仍在 `game/projectile.py` 和 `PROJECTILE_KINDS` 中，但 Nyra Q 已不再使用；没有明确要求不要删除。
- Nyra Q 的 `nyra_wave_fx` 6 帧**不在** `nyra.anim.missing_paths()` 的检查范围内；smoke 只验证 `scene.wave_effects` 出现，不验证 FX 帧加载/绘制。改特效后必须手动/F1 看一次。
- `game/wave_fx.py` 的 `FRAME_DURATIONS` 是代码常量；F5 只刷新 PNG，不重新导入 Python。改时长需重启进程。
- Veno idle 和 jump 当前共用同一张帧；若细化动作，注意 size lock。
- Veno 的 150×150 hurtbox 是故意大于视觉高度；缩小可能让 Lina Q / axe throw 打空。
- Nyra Q 的延长 box 顶到 212；Veno base hover 220 打不到，低 hover 可以；调 Q 或 hover 后重新测。
- 默认阵容必须保持 Lina vs Warrior；新 session 不要改 `debug.json` 默认，除非用户明确要求。
- `instruction.docx`、`UI Resources/`、`Image/`、未提交的 Nyra/Veno 素材都不要擅自覆盖/回滚。
- 没有明确要求不要 commit；没有 pytest/日志文件的约定，验证走 smoke + 手动 + contact sheet。

---

## 8. 本轮建议的推进顺序

1. `git status --short` + 跑 smoke，确认基线。
2. 让用户列出 Nyra/Veno 的具体调整项（见 §9）。
3. 对 Lina Q 先做视觉/机制选择（见 §4.4），必要时用 grilling 逐项确认。
4. 先改 JSON（F5 可迭代），再改代码；涉及帧时先 contact sheet。
5. 每完成一项就跑 smoke；最后做 F1/F2 手动检查。
6. 同步 README / DESIGN_DECISIONS / DEBUG / ASSET_PIPELINE / PLAN / NEXT_SESSION。
7. 只有用户明确要求才 commit。

---

## 9. 新 session 必须先问的清单

### Nyra

- 具体要调什么：HP/ATK/cooldowns、slash/thrust/Q/E 的伤害或判定、marks 公式/层数、移动/跳跃/蹲下、hurtbox、Q 特效时长/范围/颜色、动画帧、HUD/F2？
- 是否要重做/新增帧？哪些动作、什么姿势、目标 body height？
- 改 Q 范围/时序后，是否仍要“02–04 帧延长、其他帧 thrust box”的结构？
- 是否要调整默认阵容/按键？默认应保持 Lina vs Warrior。

### Veno

- 具体要调什么：HP/ATK、三个技能的伤害/冷却、毒/网时长、hover 高度/摆动、AI 距离/决策频率、弹速/瞄准、hurtbox、帧/动作、是否多只？
- 是否要重做 idle/jump（当前共用帧）、bite（当前 v1）、hover/毒/网姿势？
- 是否要保持单只 Veno 和 `n=3` 未来待办？
- 调 hover 时是否要重新检查 Nyra Q / Lina Q / Warrior axe 的命中窗口？

### Lina Q 特效

- 只改视觉，还是也改命中方式/弹道？
- 普通与 flame 形态分别要什么颜色/形状/大小/拖尾/命中 FX？
- 保持 t=0.26 交棒、speed 700、range 520、lane 142、20 伤害、+20 energy、8s CD 吗？
- 是否要独立 FX 素材？程序化还是 sprite？若 sprite，画布/pivot/偏移、普通/flame 两套怎么定？
- 是否仍被 block 挡住（当前没有 wall 检查）？若改成 hitbox，是否要穿 block？
- 是否保留“frame 2 有球、frame 3 手干净、t=0.26 弹体接棒”的现有语义？
- 如果只改弹体外观，是否接受 frame 2 角色帧里的旧球？若不能接受，是否重做普通/flame Q 的 frame 2/3？

---

## 10. 相关文件导航

```text
游戏入口 / smoke          main.py
角色类                    game/lina.py, game/nyra.py, game/veno.py, game/warrior.py
战斗/命中                 game/combat.py
场景/FX/绘制顺序          game/scene.py
弹体                      game/projectile.py
Nyra Q 特效               game/wave_fx.py
舞台/碰撞                 game/stage.py
输入/HUD/调试             game/input.py, game/hud.py, game/debug.py
数据                      game/data/{stats,attacks,animations,roster,debug}.json
校验/类注册               game/config.py, game/roster.py
角色帧                    assets/frames/{lina,nyra,veno,warrior}/
Nyra Q 特效帧             assets/frames/nyra/nyra_wave_fx/
生成/导入/接触表          tools/{collect_frames,import_frames,contact_sheet}.py
设计/调试/素材文档        docs/{DESIGN_DECISIONS,DEBUG,ASSET_PIPELINE,IMAGE_GENERATION_RULES}.md
旧 handoff                docs/NEXT_SESSION_CHARACTERS.md
```
