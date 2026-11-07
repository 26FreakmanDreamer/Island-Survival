# Shadow Ninja 第二形态（幻影形态）动画设计

> 日期：2026-11-07
> 状态：**设计已确认，实现与素材进行中**。
> 来源：当前采用的实施计划 `C:\Users\litia\.claude\plans\instruction-docx-docs-next-session-shad-purrfect-prism.md` 的 §3「动画总表」。
> **2026-11-07 v2 更新**：idle / walk 采用 v2；`transform` 改为 **11 帧 / 1.36s**；`revert` 改为 **6 帧 / 0.60s**。
> 权威规格：`instruction.docx` 的 Shadow Ninja 段（P294–P319）。本文只记录动画；`instruction.docx` 永远不改。
> 素材状态：no-aura / shadow 侧视 base 已批准；idle / walk / transform / revert v2、P1 影爪 v2、P2 影缚（v1 施法 + v2 缠绕）、P3（attack/vanish v2，其余 v1）均已接入运行时；**所有 62 个角色帧与 FX 已安装，smoke exit 0**。最终以用户批准的独立帧为准，不能用普通形态帧凑。

---

## 1. 动画总表

| 表 | clip | 帧数 | 每帧时长 | 总时长 | 循环 |
|---|---|---|---:|---:|---|
| `shadow_ninja_clips`（normal） | `transform` | 11 | 见 §2 | 1.36s | 否 |
| `shadow_ninja_phantom_clips` | `idle` | 4 | 0.30 | 1.20s | 是 |
| 同上 | `walk` | 6 | 0.10 | 0.60s | 是 |
| 同上 | `shadow_phantom_rend`（P1） | 5 | 0.09 | 0.45s | 否 |
| 同上 | `shadow_phantom_bind`（P2） | 5 | 0.10 | 0.50s | 否 |
| 同上 | `phantom_vanish`（P3 消失） | 5 | 0.06 | 0.30s | 否 |
| 同上 | `phantom_appear`（P3 出现，用两次） | 5 | 0.06 | 0.30s | 否 |
| 同上 | `phantom_flash_attack`（P3 手部+暗影） | 3 | 0.08 | 0.24s | 否 |
| 同上 | `phantom_pause`（P3 停顿/紫眼沉雾） | 3 | 0.10 | 0.30s | 否 |
| 同上 | `phantom_shark_emerge`（P3 鲨鱼破雾） | 3 | 0.07 | 0.21s | 否 |
| 同上 | `phantom_shark_charge`（P3 鲨鱼冲刺） | 3 | 0.104 | 0.312s | 否 |
| 同上 | `phantom_shark_recover`（P3 鲨鱼散雾/回幻影） | 3 | 0.07 | 0.21s | 否 |
| 同上 | `revert`（还原） | 6 | 0.10 | 0.60s | 否 |

**角色帧合计：11 + 4 + 6 + 5 + 5 + 25（P3 去重后）+ 6 = 62 帧。**

P3 的 25 帧 = 消失 5 + 出现 5 + 攻击 3 + 停顿 3 + 鲨鱼破雾 3 + 冲刺 3 + 恢复 3；消失/出现各用两次，图复用，不重复计数。

路径：

```text
assets/frames/shadow_ninja/transform/transform_00..10.png
assets/frames/shadow_ninja/phantom/idle/idle_00..03.png
assets/frames/shadow_ninja/phantom/walk/walk_00..05.png
assets/frames/shadow_ninja/phantom/shadow_phantom_rend/shadow_phantom_rend_00..04.png
assets/frames/shadow_ninja/phantom/shadow_phantom_bind/shadow_phantom_bind_00..04.png
assets/frames/shadow_ninja/phantom/vanish/vanish_00..04.png
assets/frames/shadow_ninja/phantom/appear/appear_00..04.png
assets/frames/shadow_ninja/phantom/flash_attack/flash_attack_00..02.png
assets/frames/shadow_ninja/phantom/pause/pause_00..02.png
assets/frames/shadow_ninja/phantom/shark/emerge_00..02.png
assets/frames/shadow_ninja/phantom/shark/charge_00..02.png
assets/frames/shadow_ninja/phantom/shark/recover_00..02.png
assets/frames/shadow_ninja/phantom/revert/revert_00..05.png
assets/frames/shadow_ninja/phantom/fx/*.png
```

---

## 2. 变身 `transform`（normal 表，11 帧 / 1.36s）

| 帧 | 时长 | 画面 | 游戏逻辑 |
|---|---:|---|---|
| 00 | 0.08 | Gather：普通形态 idle，面向玩家；脚边紫色影雾开始汇聚，轮廓出现很淡紫边；苦无在近侧右手 | **第 0 帧起** `invincible=True`、`phantom_form=True`、清印记/负面/hitstun/KB/flash、`vx=0`、`ignore_terrain=True` |
| 01 | 0.08 | Blade erodes：低头，右肘弯，苦无横在胸前、刀尖朝右；刀尖开始溶解成紫色细丝；马尾开始上扬，影雾到膝盖 | 无 hitbox；不攻击；不要出现第二把苦无 |
| 02 | 0.08 | Shadow climbs：头/肩后仰，兜帽和衣边熔进暗紫剪影；眼睛开始发光；头发变松、向左扫；影雾到腰 | 无 hitbox |
| 03 | 0.08 | Grip clears：只剩苦无柄和半截刀身，仍在近侧右手中，刀身朝右端崩解；身体更接近幻影 | 无 hitbox；苦无仍只有一把 |
| 04 | 0.08 | Unarmed：完全变成 no-aura 幻影剪影；衣服/武器全部消失；双臂自然下垂；无 aura 触须 | 无 hitbox |
| 05 | 0.08 | Phantom：no-aura 幻影更实，长发流动，眼睛亮紫，脚下影雾略高 | 无 hitbox |
| 06 | 0.08 | Idle：no-aura 幻影 idle，贴近 `phantom/idle/idle_00` | 无 hitbox |
| 07 | 0.10 | Aura burst：紫色 aura/触须从腰后、发下爆出，紫边短暂发亮 | 无 hitbox；仍无敌 |
| 08 | 0.50 | Full aura：shadow 版本侧视帧（`shadow-ninja-phantom-shadow-256.png` 的侧视衍生）；触须完全展开，眼睛亮紫，影雾翻涌；**停留 0.5s** | 无 hitbox；不行动；程序化 aura 脉冲增强 |
| 09 | 0.10 | Retract：aura 收回腰后/脚边，触须变细变短，紫边变暗 | 无 hitbox |
| 10 | 0.10 | Idle：no-aura 幻影 idle；动画结束 → `set_variant("flame")`、`set_clip("idle")`、`state=IDLE`、`phantom_phase="phantom"` | 进入 PHANTOM |

补充：04/05/06/10 的头顶/脚底/身体高度必须与 no-aura base 对齐；08 的 shadow 版本只改 aura/触须，不改身体比例；不缩放、不换镜头。00–04 是普通形态 → 幻影的溶解段，05–06 是 no-aura 落定，07–09 是 shadow aura 的过渡段，10 回到 no-aura 标准形态。

---

## 3. 幻影标准动作

### 3.1 `phantom/idle` — 4 帧 × 0.30s，循环

| 帧 | 画面 |
|---|---|
| 00 | no-aura 幻影 idle，脚踩影雾，长发垂落，眼睛微亮；与 `transform_04/08` 对齐 |
| 01 | 呼吸/影雾轻抬，发梢和裙摆微动，眼睛亮度略增 |
| 02 | 长发和影雾向一侧飘，身体轻微前后晃，眼睛最亮 |
| 03 | 回到接近 00 的姿势，影雾回落，完成循环 |

### 3.2 `phantom/walk` — 6 帧 × 0.10s，循环

| 帧 | 画面 |
|---|---|
| 00–05 | 贴地滑行/漂浮，不做踏步；身体略前倾；长发和脚下影雾向后拖；脚离地 0–6px，影雾接地；6 帧做完整的“飘—拖—收”循环 |

### 3.3 `shadow_phantom_rend`（P1 影爪）— 5 帧 × 0.09s / 0.45s（v2）

| 帧 | 画面 | 游戏逻辑 |
|---|---|---|
| 00 | Wind-up 收势：身体重心下沉，右臂后拉，头发向右手聚拢，眼睛微亮 | 无 hitbox |
| 01 | Claw forms 影爪成形：指尖拉长成黑色爪刃，紫雾沿手臂缠绕，爪尖超出正常手长；身体前压 | 无 hitbox |
| 02 | Sweep 横扫：右爪水平向前扫出，身体前倾，头发/衣摆向后拖；角色帧只画挥击，长爪轨迹由独立 FX 播放 | hitbox active **0.18–0.36**；高位 `[20,-195,240,55]`；1.0atk；击退 80；hitstun 0.2；hitstop 0.06 |
| 03 | Dissolve 爪刃消散：爪刃碎成紫雾，手臂回落 | hitbox 持续到 0.36 |
| 04 | Settle 回 idle：右手恢复普通幻影手，头发回落 | 结束 → `skill_gap=0.2` |

FX：`phantom/fx/phantom_rend_trail_00..02.png`（3 帧 × 0.06s，**0.18–0.36s**；384×112，pivot `(0,56)`，角色偏移 `(30,-150)`；`behind_character`，可超出 384 角色画布）。

### 3.4 `shadow_phantom_bind`（P2 影缚）— 5 帧 × 0.10s / 0.50s

| 帧 | 画面 | 游戏逻辑 |
|---|---|---|
| 00 | 俯身：双膝下沉，身体前倾，双手向地面伸 | 无 hitbox |
| 01 | 双手触地：掌心贴地，影雾从手边沿地面铺开，眼睛下压 | 无 hitbox |
| 02 | 触手前冲：影雾凝成数条触手沿地面快速前冲；角色帧只画双手触地/身体前压，触手是独立投射物/FX | 投射物生成 **t=0.20** |
| 03 | 收势：手边影雾回收，身体开始抬起 | 投射物已离手 |
| 04 | 回 idle | 结束 → `skill_gap=0.2` |

投射物：`shadow_phantom_bind`，low lane（60），速度 900，射程 700，半径 20；1.2atk + 1s 眩晕；**穿透 barrier/platform**；命中第一个目标后停下；跳跃可躲、蹲下不躲；超霸体只免眩晕、伤害照扣。
FX：`phantom/fx/phantom_bind_tentacle_00..03.png`（4 帧，120×128，pivot `(60,64)`，50ms/帧，loop，投射物 t=0.20 出手）+ v2 缠绕前后景 `phantom_bind_back_00..05.png` / `phantom_bind_front_00..05.png`（各 6 帧，208×232，pivot `(104,224)`，锚点 `target_ground`；时长 70/90/110/510/130/90ms，共 1s；绘制顺序 **back → target → front**）。

---

## 4. 影闪 P3 时间轴（`shadow_phantom_flash`）

| 阶段 | 起止 | 时长 | 动画 | 游戏逻辑 |
|---|---|---:|---|---|
| VANISH | 0.00–0.30 | 0.30 | `phantom_vanish` | 无 hitbox；位置不变；消失动画：头→脚溶解成地上黑影 |
| APPEAR_BEHIND | 0.30–0.60 | 0.30 | `phantom_appear` | 位置 = 玩家背后 90px（`player.x - player.facing*90`，夹到墙内 40px）；面向玩家；背后没空间时 AI 优先不释放，强制则出现在玩家前方 |
| ATTACK | 0.60–0.84 | 0.24 | `phantom_flash_attack` | 帧 01（t=0.68）手部 hitbox + 暗影投射物；高位；0.8atk；手部/暗影只结算一次 |
| FLIGHT | 0.84–1.15 | 0.31 | `phantom_vanish`（复用） | 暗影飞行期间播放消失动画，t=1.14 完全消失；暗影到最远点或撞墙停下 |
| APPEAR_FAR | 1.15–1.45 | 0.30 | `phantom_appear`（复用） | 位置 = 暗影最远点/撞墙点；面向玩家（转身） |
| PAUSE | 1.45–1.75 | 0.30 | `phantom_pause` | 站立 0.3s；紫眼猛地沉进脚下黑雾 |
| EMERGE | 1.75–1.96 | 0.21 | `phantom_shark_emerge` | 尖吻+紫边背鳍破雾而出，贴地 |
| CHARGE | 1.96–2.272 | 0.312 | `phantom_shark_charge` | 鲨鱼贴地冲约 500px（1600px/s）；低判定 0.8atk；跳跃可躲；**穿透 barrier 和玩家**；撞 arena wall 停 |
| RECOVER | 2.272–2.482 | 0.21 | `phantom_shark_recover` | 鲨鱼散成影雾，幻影从雾中升起，回 idle |

总时长 **2.482s**；`attacks.json` 的 `shadow_phantom_flash.duration = 2.482`。
P3 的 `phantom_vanish` 与 `phantom_flash_attack` **采用 v2**（vanish 5×0.06s；flash_attack 3×0.08s），v2 单帧已接入运行时；P3 其余 clip（appear / pause / emerge / charge / recover）用 v1。`phantom_flash_reveal_00` 是补充 FX，不参与核心流程。

暗影投射物：`shadow_phantom_flash`，high lane（180），速度 900，射程 420，半径 18，`penetrates_blocks=True`，**穿透玩家**（不因命中消失，只造成一次伤害）。她从暗影的停止点出现；停止点 = `spawn_x + facing * min(420, distance_to_wall - radius)`。

手部 hitbox：`[20,-195,90,55]`（高位，下沿 140），active 0.68–0.76，`hit_group="flash_hand"`。玩家**蹲下**可同时躲手部与高位暗影；跳跃会被高位判定命中。

鲨鱼 hitbox：`[-20,-85,220,85]`（低位，顶部 85），active 1.96–2.272，`hit_group="shark"`；玩家**跳跃**可躲，蹲下会被命中。手部/暗影（0.8）和鲨鱼（0.8）是两组独立判定，最多 1.6atk。

### 4.1 P3 子动画逐帧

`phantom_vanish`（v2）— 5 帧 × 0.06s：

| 帧 | 画面 |
|---|---|
| 00 | idle，眼睛亮紫 |
| 01 | 头顶/面部开始溶解成紫雾，眼睛仍亮 |
| 02 | 肩/胸溶解，长发散成雾 |
| 03 | 躯干/腿溶解，只剩脚下云和地面黑影 |
| 04 | 地面黑影压平、消失，她完全不见 |

`phantom_appear` — 5 帧 × 0.06s：

| 帧 | 画面 |
|---|---|
| 00 | 地面黑影出现/聚拢，无实体 |
| 01 | 黑影升起，脚/腿先成形 |
| 02 | 躯干/手臂成形 |
| 03 | 头/长发/眼睛成形，眼睛亮起 |
| 04 | no-aura idle，面向目标 |

`phantom_flash_attack`（v2）— 3 帧 × 0.08s：

| 帧 | 画面 | 游戏逻辑 |
|---|---|---|
| 00 | 右手在胸前聚起暗影团，紫雾旋转 | 无判定 |
| 01 | 向前推出/掷出暗影团，手张开 | t=0.68：手部 hitbox + 暗影投射物生成 |
| 02 | 收势，手收回 | 无判定 |

`phantom_pause` — 3 帧 × 0.10s：

| 帧 | 画面 |
|---|---|
| 00 | no-aura idle，眼睛亮紫 |
| 01 | 眼睛猛地下沉/放大，紫光沉向脚下黑雾 |
| 02 | 眼睛沉入黑雾，身体只剩轮廓，黑雾翻涌 |

`phantom_shark_emerge` — 3 帧 × 0.07s：

| 帧 | 画面 |
|---|---|
| 00 | 脚下黑雾鼓起，紫色边缘 |
| 01 | 尖吻破雾而出，紫边背鳍升起 |
| 02 | 鲨鱼轮廓完全成形，低伏 |

`phantom_shark_charge` — 3 帧 × 0.104s：

| 帧 | 画面 |
|---|---|
| 00 | 鲨鱼前冲，身体拉长，黑雾拖尾 |
| 01 | 中段冲刺，背鳍/尖吻前压，紫边发光 |
| 02 | 冲刺末端，鲨鱼开始碎成雾 |

`phantom_shark_recover` — 3 帧 × 0.07s：

| 帧 | 画面 |
|---|---|
| 00 | 鲨鱼散成黑雾 |
| 01 | no-aura 幻影从雾中升起（半身） |
| 02 | 站回 idle |

鲨鱼本体用独立 FX `phantom/fx/phantom_shark_00..02.png`（3 帧）绘制；角色帧在 CHARGE 阶段只保留脚下影雾/紫眼，不烘焙完整鲨鱼。

---

## 5. 还原 `revert`（phantom 表，6 帧 / 0.60s）

| 帧 | 时长 | 画面 | 游戏逻辑 |
|---|---:|---|---|
| 00 | 0.10 | Mist rises：no-aura idle，影雾翻涌上升，紫边发亮 | 仍 `invincible=True`、`phantom_form=True` |
| 01 | 0.10 | Collapse：轮廓塌回影雾，身体压缩，紫边变暗 | `vx=0`；不攻击 |
| 02 | 0.10 | Head clears：普通形态的兜帽/头部/马尾先出现；眼睛变暗 | 仍无敌；不要出现两把苦无 |
| 03 | 0.10 | Torso clears：普通形态的躯干/护甲/衣摆重形；苦无开始在右手凝形 | 仍无敌 |
| 04 | 0.10 | Re-form：普通形态基本完成，苦无成形，残余影雾向下收 | 仍无敌 |
| 05 | 0.10 | Normal：普通形态 idle；动画结束 → `set_variant("normal")`、`invincible=False`、`phantom_form=False`、`ignore_terrain=False`、`transform_cd=15`、`state=IDLE` | 回 NORMAL |

---

## 6. 独立 FX 清单

| FX | 帧数 | 用途 |
|---|---:|---|
| `phantom/fx/phantom_rend_trail_00..02.png` | 3 | 影爪长爪轨迹，可超出 384 角色画布 |
| `phantom/fx/phantom_bind_tentacle_00..03.png` | 4 | 影缚地面触手（120×128，pivot 60,64，50ms/帧） |
| `phantom/fx/phantom_bind_back_00..05.png` | 6 | 目标身后的缠绕后景（208×232，pivot 104,224，1s） |
| `phantom/fx/phantom_bind_front_00..05.png` | 6 | 目标身前的缠绕前景（1s，back → target → front） |
| `phantom/fx/phantom_flash_orb_00..02.png` | 3 | 影闪高位暗影团 |
| `phantom/fx/phantom_shark_00..02.png` | 3 | 鲨鱼冲刺 sprite（尖吻+紫边背鳍+影雾拖尾） |
| 变身/还原 ring | 程序化 `RingBurstFx` + 紫色粒子 | 变身第 0 帧、shadow 过渡、还原结束 |
| 命中 FX | 程序化 ring + 粒子 | 影爪/影缚/影闪/鲨鱼命中 |

**不烘焙进角色帧**：长爪轨迹、触手、暗影团、鲨鱼、ring、粒子、印记、眩晕星。

---

## 7. 画布与 base

- 运行时画布 **384×384**，pivot **（192,372）**，body **214**；hurtbox 站立 56×210、蹲下 56×130；`stage_body_width 100`。
- 已批准的侧视 base：
  - `assets/generated/base/shadow_ninja_phantom_side_base.png`：no-aura 侧视，右向完全侧视（不是 3/4），长发、发光眼、脚下影雾、无武器。
  - `assets/generated/base/shadow_ninja_phantom_shadow_side_base.png`：在 no-aura 侧视基础上加 aura/触须；身体比例、头身比、脚底基线一致，只改 aura。
- 长发/影雾撑大 alpha bbox 时**不要**缩小人物；固定 body 214，必要时扩留白；384 放不下就停下来问用户。
- 变身/还原/影闪的所有帧共用同一 base、pivot、body；普通形态与幻影形态头顶/脚底对齐。

---

## 8. 当前素材状态（2026-11-07）

| 项目 | 状态 |
|---|---|
| no-aura 侧视 base | 已批准（fit 256 版） |
| shadow 过渡侧视 base | 已批准（候选 2，256 对齐版） |
| idle 4 帧 | v2 已接入运行时：`assets/frames/shadow_ninja/phantom/idle/idle_00..03.png` |
| walk 6 帧（glide） | v2 已接入运行时：`assets/frames/shadow_ninja/phantom/walk/walk_00..05.png` |
| transform 11 帧 / 1.36s | v2 已接入运行时：`assets/frames/shadow_ninja/transform/transform_00..10.png` |
| revert 6 帧 / 0.60s | v2 已接入运行时：`assets/frames/shadow_ninja/phantom/revert/revert_00..05.png` |
| P1 影爪 5 帧 + 轨迹 3 帧 | v2 已接入运行时：`phantom/shadow_phantom_rend/` + `phantom/fx/phantom_rend_trail_00..02.png`；轨迹 0.18–0.36s |
| P2 影缚 5 帧 + 触手 4 帧 + 缠绕前后景 12 帧 | 已接入运行时：v1 施法 5 帧 + `phantom_bind_tentacle_00..03.png` + v2 `phantom_bind_back/front_00..05.png` |
| P3 影闪 25 帧 + 暗影团 3 帧 + 鲨鱼 3 帧 | **attack / vanish 用 v2 已接入**；appear / pause / emerge / charge / recover 用 v1 已接入；orb / shark FX 已接入 |
| 代码/JSON/状态机/smoke Phase I | 已实现；transform/revert 时长同步为 1.36s / 0.60s；**所有 62 个角色帧与 FX 已安装；smoke exit 0，所有 `*_missing_frames` 为 0** |

素材审批顺序：base → idle/walk → transform/revert → P1/P2 → P3 → 游戏内预览 → 安装到 `assets/frames/shadow_ninja/`。每轮用户确认后才进下一步。`instruction.docx` 永远不改。
