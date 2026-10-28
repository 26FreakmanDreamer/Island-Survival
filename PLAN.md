# Lina Seabright 战斗沙盒 — 实施计划

> **Nyra / Veno 更新（2026-10-22；Q/LMB 绑定于 2026-10-23 修正）**：新增可玩角色 **Nyra Steel** 与敌人 **Veno-Spider**，默认仍为 Lina vs Warrior。Nyra 使用 384×384 画布、pivot (192,372)、体高 214，最小 29 帧（slash 6、thrust 5、wave 5）；LMB 波 20（5 帧 0.06s，0.30s）、RMB 突刺 24（5 帧 0.08s，0.40s）、Q 剑气斩 30（8s，+1 印记/全程霸体）、E 冲刺突刺 30（15s，0.06–0.36 霸体/约 330px）；LMB 的 cast-anchored 三段为 0–0.06 / 0.06–0.24 / 0.24–0.30，Q 为 0–0.12 / 0.12–0.30 / 0.30–0.40，RMB 单段 0.16–0.24；LMB 额外叠印记且无特效，Q +1 印记并播放 `game/slash_fx.py` 的 `assets/frames/nyra/nyra_slash_fx/` 6 帧透明剑光；LMB/RMB/Q 命中叠印记，第 4 次引爆 `1.8×atk + 10% 目标最大生命` 并保留 1 层；E 冲刺 0.06–0.36s（1100px/s，约 330px），只穿敌人、不穿墙壁/block，结束时把敌人推到外侧。slash 的 6 帧（Q）为「初始前下方 45° → 剑抬到水平下 10–20°、手臂开始前伸的过渡 → v11 大臂前伸帧（219px、脚底 372）→ 复用 thrust_v5_01 的长剑接触 → 两张收势帧」；durations 为 0.05/0.04/0.05/0.14/0.07/0.05，总时长 0.40s。wave 的 5 帧（LMB）为高位起手（约 55–60°上）→ 抬剑（约 30°上）→ 水平 → 下压（约 20°下）→ 收势（约 45°下），durations 0.06/0.06/0.06/0.06/0.06（总 0.30s），剑气不入帧。FX durations 为 0.02/0.02/0.05/0.14/0.07/0.05；事件标记在 t=0.04，60Hz 下实际在 t≈0.05 生成，02–04 帧与角色 02–04 帧对齐。Veno 使用 320×320 画布、pivot (160,308)、体高 150，最小 20 帧，HP 50 / ATK 10；咬 15、毒液 8 + 3%/s×3s（同源延长）、蛛网 10 + 眩晕 1s；地面追击撕咬，浮空 140–300px（基准 220）优先毒/网，单只生成。F7 顺序改为 Warrior → Veno → Dummy；`[` / `]` 为 Lina ↔ Nyra。smoke 全绿（`nyra_missing_frames=0`、`veno_missing_frames=0`、`warrior_missing_frames=0`）。
>
> **实施更新（2026-10-20）**：已追加第二形态（火焰形态）33 帧战斗动作集（含专用 jump 2 帧与 crouch 1 帧），Q 动画改为「无气流 → 积聚 → 球状打出 → 手部干净」，游戏内 Q 弹道在 0.26s 与精灵帧交棒，并使用 478px 的拳高 lane。**2026-10-21 补齐火焰 hurt 2 帧、KO 4 帧与 revert 2 帧，取消普通帧红色 tint 回退**；总帧数为 45 普通 + 41 火焰 = 86。详细规则见 `docs/DESIGN_DECISIONS.md`，素材流程见 `docs/ASSET_PIPELINE.md`。
>
> **输入手感更新（2026-10-20）**：攻击中的按键改为单槽动作队列（最新按键覆盖，攻击结束时执行；E 在恢复段开始时取消后摇），替代原先需要踩 0.15s 连段窗口的做法。暂停恢复、场景重置/F5、窗口重新获得焦点时，会从物理键盘重建移动/下蹲的 held 状态；启动时关闭文本输入，避免中文输入法吞键。
>
> **攻击朝向更新（2026-10-20）**：取消攻击和站立时的自动面向敌人。攻击方向完全由 A/D 决定的当前面向决定（面向左则拳、腿、Q 全部向左），静止时保持最后的面向；同帧按下方向键和攻击也会先转向再出招。
>
> **Q 弹道高度更新（2026-10-20）**：Q 气流不再使用固定世界坐标 y=478，而是从角色脚底向上 142px 生成。平地为 478，站在 60px 箱子上为 418；F1 的弹道参考线也改为相对 Lina 脚底绘制。
>
> **Block 碰撞更新（2026-10-20）**：地面移动和攻击前踏统一走 `Stage.move_x()`，使用 100px 的移动碰撞体（战斗 hurtbox 仍为 56px），撞 block 时停在箱边；空中改用 hurtbox 宽度，避免从箱边落下时被横向弹开。重叠时按较近的一侧推出；跳上箱顶要求脚底中心在箱体边缘 8px 内。
>
> **E 数值调整（2026-10-20）**：E 冷却由 15s 改为 20s，火焰形态持续时间由 5s 改为 10s；Q 刷新、能量消耗和火焰加成规则不变。
>
> **Phase 2 Warrior 更新（2026-10-20）**：Warrior 已完成并接入。默认敌人为 Warrior，F7 可切回训练木桩；完整 1v1（AI 追击/跳跃过 block/斧击、Lina 受伤/KO、胜负与重开）。Warrior 使用 384×384 画布、pivot (192,372)、体高约 230px，共 36 帧（idle 4、walk 6、jump 2、axe_slash 6、axe_throw 7、dash 5、hurt 2、KO 4）。斧击 0.75s，前摇 0.25s / 判定 0.30s / 后摇 0.20s；HP 300、伤害随 atk 计算、击退 380、冷却 0.9s；前摇+判定霸体至 0.55s。详细规则见 `docs/DESIGN_DECISIONS.md`，素材见 `docs/ASSET_PIPELINE.md`，调试键见 `docs/DEBUG.md`。
>
> **Roster / 技能槽更新（2026-10-21）**：新增 `game/data/roster.json` 与 `game/roster.py`，Lina/Warrior/Dummy 由数据构造；F7 切换敌人、`[` / `]` 切换可玩角色（当前仅 Lina），切换时整场重置且 AI 关闭，B 的 block 开关保留。`V/C/X/Z` 改为读取敌人的 4 个 `skill_slots`，未定义槽位安全 no-op，F2 显示槽位与冷却。Warrior 改为 `basic_atk 20` + `1.2/1.5/1.2` 倍率（斧击 24、冲刺 30、投掷 24/段）；Lina 对齐 docx 公式（拳 20、腿 24、Q 20）。dash 击飞补齐空中 jump 帧、原地 KO、霸体不施加 launch/knock_up，hitstop 0.08s。
>
> **攻击锁定更新（2026-10-21）**：鼠标中键切换攻击锁定，默认关闭；开启后 Lina 的拳/腿/Q 在起手时面向存活敌人（8px 死区），攻击/前踏/弹道随面向；待机面向、移动和 Warrior AI 不变。切换 character/enemy 时锁定重置为关闭，F9 保留当前设置，F5/启动为关闭；HUD 与 F2 显示 `LOCK-ON`。
>
> **身位修复（2026-10-21）**：Warrior/Lina/block 距离过近时，分离逻辑不再把 Warrior 翻到 Lina 另一侧（会造成 100–200px 瞬移）；当前侧被 block/墙挡住时改为反推 Lina。分离移动加入 `combat.separation_speed`（600px/s）上限，深度重叠会在数帧内滑开而不是瞬移。新增 smoke `separation_block_ok`。
>
> **击飞漩涡（2026-10-21）**：`knock_up` 期间在被击飞角色脚底绘制程序化青白三臂漩涡 + 椭圆外环；跟随角色整个 1.5s（含空中/落地），大小与透明度随 `remaining / total` 线性收缩淡出，重复击飞重置为满强度。纯绘制，不改角色动画/状态/碰撞/hitstop；参数在 `combat.knock_up_fx`。新增 smoke `knockup_fx_ok`。
>
> **击飞输入修复（2026-10-21）**：击飞/受击硬直/控制锁定期间按下的拳/腿/Q/E/跳现在进入单槽缓冲，控制恢复时立即执行；不再因 120ms 输入缓冲过期而“击飞结束后按了没反应”。新增 smoke `lock_buffer_ok`。
>
> **滞空延长（2026-10-21）**：knock_up 期间用 `combat.knock_up_gravity`（1013.333）代替普通重力，滞空约 1.5s；落地时漩涡结束、控制恢复，排队动作在落地后 1–3 帧内执行（hitstop 会让墙钟时间略长于 1.5s）。`lock_buffer_ok` 现同时断言落地到出拳不超过 3 帧。
>
> **漩涡可见度（2026-10-21）**：漩涡不再线性淡到不可见；大小/透明度只降到 `min_scale 0.75` / `min_alpha 0.55`，全程保持可读，`knock_up` 结束时立即消失。smoke 新增 `fx_end_visible_ok`。

## Context

已阅读 `instruction.docx` 的「四、战斗系统（重点构建）」：这是**实时 2D 横版动作战斗**，不是回合制。Lina Seabright 的技能组完整（左右键交替拳/腿、Q 气流、E 火焰形态、能量获取），但文档没有给伤害数值、能量上限/回复、冷却、敌人血量或 AI 参数；Mech-Crab / Crooked Witch / Veno-Spider 连技能都未写。

工作区目前**没有任何代码**、引擎工程、数据文件或 git 仓库，只有 `Image/` 美术、`assets/` 旧素材、`sketch/` UI 草图和规格文档。因此目标不是“往现有系统加人物”，而是从零做一个**能反复调试单角色战斗手感的沙盒**，作为后续完整游戏的地基。

已确认的关键事实：
- 本机 `python` 别名失效，必须用 `py`；Python 3.14.8。
- `pygame-ce 2.5.8` 有 `cp314-win_amd64` wheel，已验证可解析；当前未安装 pygame。
- Pillow 12.3.0 已装，可用于切帧/接触表。
- `Image/Character/lina-seabright-v1-256.png` 与 `v2-256.png` 都是**正面 3/4 站姿**，不是横版侧视；v2 是红黑配色版，不是真实火焰特效。
- 背景 `assets/backgrounds/island-arena-16x9.png` 为 1664×936 日落沙滩，正好 16:9。

## 已确认决策

| 决策 | 结果 |
|---|---|
| 首版范围 | 单角色战斗沙盒：Lina vs 训练木桩，一个场景；不做日循环/食物/商店/存档/角色选择/音频 |
| 技术栈 | Python 3.14 + pygame-ce 2.5.8；venv + `run.bat` 一键启动 |
| 动画 | 真序列帧；先生成侧视基准，再约 45 帧；256×256 透明 PNG |
| 生成管线 | Seedream 逐帧 image-to-image，透明背景；每动作接触表审批；单帧可重生成 |
| 首个敌人 | 训练木桩；Warrior 放到 Phase 2 |
| 视角/舞台 | 右侧 3/4 侧视，翻转朝左；1280×720，固定单屏，平地 + 侧墙 + 1–2 个 block |
| 战斗手感 | 60Hz 固定 tick、60ms 顿帧、120ms 输入缓冲、200ms 受击硬直、攻击锁移动并前踏、攻击自动面向最近敌人、左键连段窗口 0.15s、E 可取消后摇 |
| 规则补全 | Q 冷却 8s、E 冷却 15s，**开局均不进入冷却**；E 仍消耗 100 能量；其余采用下面「明确假设」 |
| 调试工具 | 可视化叠层、实时数值/帧信息、沙盒控制（木桩、时间缩放/逐帧、JSON 热重载、场景快捷键） |
| 数值策略 | 全部进可热重载 JSON；临时扁平数值 |
| 工作流 | 骨架与素材并行；先验证 idle+punch+kick，再批量生成；结束交付 `run.bat` 和 git 初始化；exe 后置 |
| 明确不做 | 首版不做 pytest/自动测试套件、不做文件日志、不做音频、不做完整 HUD |

## 目标产物 / 完成定义

1. 双击 `run.bat` 能启动 1280×720 英文界面的战斗沙盒。
2. Lina 完整四招：左右键拳/腿（含左右交替）、Q 气流、E 火焰形态；能量、Q/E 冷却、火焰加成、灼烧、击退均可用。
3. 训练木桩有 1000 HP、无敌开关、位置/血量调整、重置。
4. 三类调试工具可用：F1 叠层、F2 数据面板、F3–F12 沙盒控制。
5. 45 张已审批的 Lina 序列帧接入游戏，帧尺寸、锚点、朝向一致。
6. `Image/` 下的 canonical 素材不被覆盖；生成物写入 `assets/frames/` 与 `assets/generated/`。
7. git 仓库已初始化（是否提交由你决定，不自动 commit）。

## 目录结构

```text
d:/Program Game/Island Survival/
  run.bat                     # 首次运行建 venv、装依赖，然后启动
  requirements.txt            # pygame-ce==2.5.8, Pillow>=12
  .gitignore                  # .venv, __pycache__, 生成候选/临时文件
  README.md                   # 启动方式、操作、调试快捷键
  main.py                     # 入口：py game 初始化、主循环、事件泵
  game/
    __init__.py
    config.py                 # JsonStore：加载/校验/热重载四份 JSON
    input.py                  # InputBuffer + 按键状态 + 输入历史
    fighter.py                # Fighter 基类：状态、物理、朝向、hurtbox、HP/受击
    lina.py                   # Lina：四招、能量、冷却、火焰形态、自动面向
    dummy.py                  # 木桩：1000HP、无 AI、可调位置/血量/无敌
    animation.py              # AnimationPlayer：帧时长、循环、翻转、染色、缓存
    combat.py                 # AttackInstance、HitBox、命中结算、顿帧、伤害管线
    status.py                 # 九种状态的数据模型 + 毒伤多实例叠加
    projectile.py             # Q 气流等投射物、弹道高度
    scene.py                  # ArenaScene：tick 顺序、墙/block、重置、场景预设
    stage.py                  # 背景缩放、地面、block、影子
    particles.py              # 火焰/命中/灼烧粒子
    hud.py                    # 极简 HUD：HP、能量、Q/E 冷却、火焰计时
    debug.py                  # DebugOverlay + DebugPanel
    data/
      stats.json              # 角色/木桩数值、移动、能量、冷却
      attacks.json            # 每个攻击的帧事件、hitbox、伤害、击退
      animations.json         # 帧清单、每帧时长、pivot
      debug.json              # 舞台几何、叠层颜色、场景预设
  assets/
    backgrounds/              # 保持现有 island-arena-16x9.png
    frames/lina/<action>/<action>_NN.png
    generated/
      base/                   # 审批通过的侧视基准
      raw/                     # Seedream 原始候选（可 gitignore）
      contact_sheets/          # 每动作审批图
      rejected/                # 被否掉的帧
  tools/
    import_frames.py          # 透明检查、裁边、统一缩放、256 画布、脚底锚点
    contact_sheet.py          # 棋盘格接触表 + 帧号/时长/基线/pivot
  docs/
    DESIGN_DECISIONS.md       # 文档空白的全部规则假设
    ASSET_PIPELINE.md         # 提示词、审批、命名、导入规范
    DEBUG.md                  # 调试快捷键与面板说明
```

> 运行方式：`run.bat` 里 `cd /d "%~dp0"`，用 `py -3.14 -m venv .venv` 建环境，安装 `requirements.txt`，然后 `.venv\Scripts\python.exe main.py`。路径含空格，所有批处理路径必须加引号。

## 运行时架构

### 主循环
- `pygame` 窗口 1280×720，`clock.tick(60)`，累加器固定步长 1/60s；真实 dt 上限 0.25s，避免断点后追帧爆炸。
- 所有模拟计时（动画、冷却、状态、输入缓冲、顿帧）使用**模拟秒**；渲染不修改状态。
- 暂停时跳过 tick；逐帧模式每次只跑一个 tick。时间缩放 0.25×/0.5×/1×/2× 只影响累加器。

### 状态机与输入
- 状态：`IDLE, WALK, CROUCH, AIR, ATTACK, HURT, TRANSFORM, KO`。
- 空中是一个状态，用 `vy` 正负选 jump 帧；攻击的 startup/active/recovery 由攻击时钟推导，不单独建状态。
- 移动只在 `IDLE/WALK/CROUCH/AIR`；攻击期间锁水平移动，在数据指定的事件时刻施加小前踏（约 18px）。
- 输入缓冲 120ms，只记录按下（不重复触发）；新输入覆盖旧输入；失焦/重置清空。
- 左键触发拳；在拳的最后 0.15s 内再次按左键，接另一只手的拳。左右/左右腿交替在**起手时**决定，挥空也切换。
- 攻击时自动面向最近敌人；无水平输入且未攻击时也自动面向。翻转绘制时 pivot x 修正为 `width - pivot_x`。
- 地面攻击：LMB/RMB/Q 仅地面可用；E 空中可用。这是对文档空白的明确假设。

### 命中与伤害
- 本地 AABB：`[x_forward, y_from_feet, w, h]`，按朝向和脚底位置变换。
- Lina 站立 hurtbox 56×210；下蹲 56×130；木桩 70×190。
- 攻击帧事件定义 `hitbox` 的生效时间窗；同一 `AttackInstance` 对同一目标只结算一次。
- 伤害管线：`damage = base * (1 + flame_bonus) * (1 - damage_reduction)`；命中后施加受击硬直、击退、顿帧、可选状态；攻击者仅在**造成伤害**时获得能量（火焰形态下不获得）。
- 顿帧 60ms（约 4 tick）：冻结双方、攻击、投射物、状态、冷却、动画和输入年龄。
- 受击硬直 200ms；KO 为终止状态，直到重置。
- 击退：右键 300 px/s，Q 150 px/s，0.35s 线性衰减；撞墙 clamp。

### 资源 / 冷却 / 火焰形态
- 初始 HP 100、ATK 20（basic 20 + extra 0）、能量 0/100、无回复。
- 命中回能：拳 +15、腿 +20、Q +20。
- 攻击伤害按 docx 的 basic/extra 拆分：拳 `atk`、腿 `1.2×basic + 0.8×extra`、Q `basic + 1.5×extra`；当前 basic 20 / extra 0 时即 20/24/20。倍率写在 `attacks.json` 的 `basic_mult`/`extra_mult`，后续 extra atk 会自动生效。
- Q 冷却 8s，开局就绪；E 冷却 15s，开局就绪；E 额外消耗 100 能量（释放后能量归 0）。
- E 激活：刷新 Q（Q 冷却归 0）、进入火焰形态 5s、火焰加成计数归 0；形态内命中不回能。
- 火焰形态命中计数从 0 开始；在结算每一次**造成伤害**的命中前先取该次档位：第 1 次 +20%、第 2 次 +40%、第 3 次及以后 +60%；不刷新持续时间；E 结束后加成清除。
- 火焰形态的视觉：v1 帧预生成红黑调色缓存 + 橙色火焰粒子；v2 只作为调色参考/E 变身闪光参考，不生成整套 v2 动作帧。
- 火焰命中给木桩施加强制刷新的灼烧：5 HP/s × 3s。

### 状态效果（九种全部建模）
文档中的九种：`knockback`、`burn`、`poison`、`slow`、`knock_up`、`freeze`、`stun`、`super_armor`、`damage_reduction`。
- `super_armor` 免疫控制效果；`damage_reduction` 按百分比减伤。
- `burn`：5 HP/s × 3s，重复施加刷新持续时间。
- `poison`：2% 最大 HP/s，数据模型支持文档的叠加规则——**同源再次施毒延长持续时间，不同源各自保留独立实例**；首版不自然触发，只由 F11 调试强制。
- `slow`/`freeze` 首版不自然触发，只由 F11 调试强制。
- `knockback` 由腿和 Q 触发（拳不击退）；`knock_up` 由 Warrior dash 自然触发；`stun` 仍由调试场景强制触发。
- 控制效果的“不可移动/不可攻击/不可用技能道具”统一由 `can_act()` 判定；`super_armor` 绕过控制。

### 木桩
- 1000 HP，无 AI，不攻击，不移动（除非调试推动）；可被击退、硬直、灼烧、强制状态。
- 调试可改血量、位置、无敌、重置；顶部显示独立 HP 条。

### 渲染顺序
背景 → block → 影子 → 木桩 → 投射物/粒子 → Lina → HUD → 调试叠层 → 调试面板。

## 数据文件

所有调参值进 JSON，代码里不写死。

### `stats.json`
```json
{
  "lina": {
    "hp": 100, "basic_atk": 20, "extra_atk": 0,
    "energy": {"max": 100, "start": 0, "regen": 0,
               "gain": {"punch": 15, "kick": 20, "q": 20}},
    "move": {"walk": 260, "jump_v": 760, "gravity": 2200},
    "cooldowns": {"q": 8.0, "e": 15.0},
    "flame": {"duration": 5.0, "bonus_step": 0.2, "bonus_cap": 0.6}
  },
  "dummy": {"hp": 1000, "invincible": false}
}
```

### `attacks.json`
```json
{
  "punch_r": {
    "basic_mult": 1.0, "extra_mult": 1.0, "duration": 0.25, "lunge": 18,
    "energy_gain": 15, "hitstun": 0.2, "hitstop": 0.06,
    "next": "punch_l", "chain_window": 0.15,
    "events": [
      {"t": 0.10, "until": 0.16, "type": "hitbox",
       "box": [30, -165, 66, 48], "knockback": 0}
    ]
  },
  "kick_r": {
    "basic_mult": 1.2, "extra_mult": 0.8, "duration": 0.4, "lunge": 14,
    "energy_gain": 20, "hitstun": 0.2, "hitstop": 0.06,
    "next": "kick_l", "chain_window": 0.15,
    "events": [
      {"t": 0.14, "until": 0.22, "type": "hitbox",
       "box": [30, -120, 78, 64], "knockback": 300}
    ]
  },
  "q": {
    "basic_mult": 1.0, "extra_mult": 1.5, "duration": 0.35, "lunge": 0,
    "energy_gain": 20, "hitstun": 0.2, "hitstop": 0.06,
    "events": [
      {"t": 0.20, "type": "projectile", "id": "q_wave",
       "lane": "mid", "speed": 700, "range": 520, "knockback": 150}
    ]
  }
}
```
（`x` 为朝向正方向，`y` 为从脚底向上为负；box 的最终世界坐标由 `facing` 和脚底位置变换。）

### `animations.json`
```json
{
  "frame_size": [256, 256],
  "pivot": [128, 244],
  "lina": {
    "idle": {"loop": true,
             "frames": ["idle/idle_00.png", "idle/idle_01.png", "idle/idle_02.png", "idle/idle_03.png"],
             "durations": [0.12, 0.12, 0.12, 0.12]},
    "punch_r": {"loop": false,
                "frames": ["punch_r/punch_r_00.png", "punch_r/punch_r_01.png", "punch_r/punch_r_02.png", "punch_r/punch_r_03.png"],
                "durations": [0.05, 0.07, 0.07, 0.06]}
  }
}
```

### `debug.json`
```json
{
  "stage": {
    "ground_y": 620, "walls": [90, 1190],
    "lanes": {"high": 440, "mid": 500, "low": 560},
    "blocks": [[400, 560, 90, 60], [760, 560, 90, 60]],
    "player_spawn": [280, 620], "dummy_spawn": [1000, 620]
  },
  "overlay": {"hit": [255, 70, 70], "hurt": [70, 220, 130], "pivot": true},
  "scenarios": {
    "flame_demo": {"energy": 100, "force_flame": true},
    "low_hp_dummy": {"dummy_hp": 1},
    "status_demo": {"apply_status": "burn"}
  }
}
```
> 舞台坐标已避开出生点：Lina x=280、木桩 x=1000；block 在 400–490 与 760–850，角色和木桩都不会卡进 block。

### 热重载
- F5 重新读取四份 JSON，校验必需字段；失败时保留上一份好数据，并在调试面板显示错误，不写文件日志。
- 成功后重置当前场景（位置/状态/冷却），避免旧 clip/状态引用失效；木桩的调试配置可保留。
- 动画缓存按 `path + mtime` 失效，替换帧文件后 F5 即可生效。

## 动画生成与导入管线

### 帧清单（共 45 帧）
| 动作 | 帧数 | 说明 |
|---|---:|---|
| idle | 4 | 循环呼吸 |
| walk | 6 | 循环 |
| jump | 2 | 上升/下落 |
| crouch | 1 | 静态 |
| punch_l / punch_r | 各 4 | 左右手交替，非朝向 |
| kick_l / kick_r | 各 4 | 左右腿交替 |
| q | 4 | 出拳 + 气流 |
| transform | 6 | E 变身 |
| hurt | 2 | 受击 |
| ko | 4 | 倒地 |

- 每动作独立帧时长；拳总时长 0.25s、腿 0.4s 与文档一致；`import_frames.py` 校验动画总时长与 `attacks.json` 的 `duration` 误差 < 1 tick。
- 256×256 RGBA，脚底中心 pivot `(128, 244)`，底部留 12px 给影子。

### Seedream 流程
1. 先调用 `get_model_info` 确认当前模型的透明背景/尺寸能力。
2. **侧视基准**：以 `Image/Character/lina-seabright-v1-256.png`（RGBA）为唯一输入，用 `image_to_image`，`size: "1K"`、`background: "transparent"`、`output_format: "png"`、`request_count: 2–4`，保存到 `assets/generated/raw/`。可参考海报 `Image/Character/Posters/lina-seabright-v1-poster.png` 核对服装/发型，但透明输出优先单图输入。
3. 你从 2–4 个基准候选里选 1 个，批准后保存为 `assets/generated/base/lina_side_base.png`。
4. **管线验证批**：以批准的基准为参考，生成 idle 4 + 左右拳各 4 + 左右腿各 4 = 20 帧；每动作拼接触表，审批后导入。
5. **剩余批**：walk 6、jump 2、crouch 1、Q 4、transform 6、hurt 2、KO 4 = 25 帧；同样逐动作审批。

### 提示词模板（每次固定前缀 + 只改动作句）
```text
Same character as the reference: young woman, long purple hair, star hair clip,
pearl earrings, blue anchor jacket, purple sash, black leggings, blue boots.
Pixel-art game sprite, right-facing 3/4 side view (about 15-20 degrees toward camera),
full body, feet visible, centered with margin, flat transparent background,
no shadow, no text, no border. Keep the exact same outfit, colors, proportions,
camera, scale, position and lighting in every frame. Only change the pose:
<ACTION, FRAME N OF M>.
```
- 每个动作单独一组提示；帧之间只改变动作描述，禁止改变镜头/比例/配色。
- 透明失败时退回纯色 chroma 背景 + Pillow 去背，但优先使用模型透明输出。
- 所有生成物先进 `raw/`，审批通过才进 `assets/frames/lina/`；被否的进 `rejected/`。

### 接触表与审批
- `contact_sheet.py` 把每个动作的帧拼成棋盘格，标注动作名、帧号、每帧时长、脚底基线、pivot 十字。
- 输出 `assets/generated/contact_sheets/<action>_vNN.png`；我会给出路径，你查看后批准或指出要重生成的帧。
- 未审批的动作不进入游戏；单个帧可只重生成那一张。

### 导入规则
- `import_frames.py` 检查 RGBA、alpha 覆盖率、近似空帧；裁掉四周透明边。
- 用审批基准校准一个统一缩放系数，把角色身体高度定到约 210px（落在 200–220 内）；**不逐帧自动缩放**，身高异常帧直接标记为待重生成。
- 去掉边缘色边（despill），把 alpha 底边中心放到 256×256 画布的 `(128, 244)`。
- 命名：`assets/frames/lina/<action>/<action>_NN.png`；L/R 表示手/脚，不表示朝向。
- 朝向：只存右向帧；左向在加载时水平翻转并修正 pivot，不生成左向文件。
- 火焰形态：加载时预生成红黑调色缓存（参考 v2 配色）+ 橙色粒子；不生成 v2 动作帧。

### 校验
- 导入器内置轻量校验：按当前动画清单检查已存在的帧；最终检查 45 个预期文件名、256×256 RGBA、非零 alpha、pivot 元数据、动画总时长与攻击 duration 一致。
- 不做 pytest、不生成日志文件；错误显示在调试面板。

## 调试工具

### 按键
| 键 | 功能 |
|---|---|
| F1 | 叠层开关（hit/hurt box、pivot、朝向、弹道线、墙/block、状态文字） |
| F2 | 调试面板开关 |
| F3 | 暂停/继续 |
| F4 | 逐帧（暂停时只跑 1 tick） |
| F5 | 热重载 JSON + 场景软重置 |
| F6 | 时间缩放 0.25× / 0.5× / 1× / 2× |
| F7 | 木桩无敌开关 |
| F8 | 木桩重置（血量/位置） |
| F9 | 整场重置 |
| F10 | 火焰形态演示（能量拉满 + 强制变身） |
| F11 | 给木桩循环施加强制状态（灼烧/毒/眩晕/冻结/减速等，用于验证状态模型） |
| F12 | 对 Lina 触发受击/KO 演示 |
| 方向键 | 移动木桩 ±20px |
| PgUp/PgDn | 木桩血量 ±100 |
| Esc | 暂停菜单（Resume / Restart / Quit），不直接退出 |

### 叠层
- 生效 hitbox 红色、hurtbox 绿色、pivot 十字与朝向箭头、弹道高度虚线（high/mid/low）、墙与 block 边框、实体状态/攻击阶段/当前帧号文字。
- 全部用 `pygame.draw` 在屏幕空间绘制，缓存等宽字体；不修改游戏状态。

### 面板
- FPS / tick / 模拟时间；HP、能量、火焰加成与剩余时间；Q/E 冷却；九种状态及计时/层数；当前动画、帧号、攻击时钟；最近 12 条输入及年龄；顿帧剩余；木桩 HP/无敌/坐标；时间缩放；最近一次热重载状态或错误。
- 右侧半透明面板，英文；错误只在面板显示。

### 沙盒控制
- 木桩：血量、位置、无敌、重置。
- 时间：暂停、逐帧、0.25×–2×。
- 热重载：四份 JSON 即时生效。
- 场景预设：火焰演示、木桩 1HP、强制状态、Lina 受击/KO。

## 场景与 HUD

> 2026-10-27 更新：场景已扩展为 barrier / platform / ladder。当前坐标与规则以
> `game/data/debug.json` 和 `docs/DESIGN_DECISIONS.md` 的 “Stage props and climbing” 为准；
> 下面 2026-10-24 的 block 记录保留为历史。
>
> 当前第一版：地面 barrier `[400,560,90,60]`、`[700,560,90,60]`；长平台 `[170,220,479,78]`
> （surface 220）；短平台 `[796,268,314,78]`（surface 268）；长梯 `[508,220,64,400]`；
> 中梯 `[921,268,64,352]`；玩家出生 x=280，敌人出生 x=600；默认敌人 Warrior。

- 逻辑分辨率 1280×720；背景从 1664×936 一次性缩放到 1280×720；固定镜头。
- 地面 y=620；不可见侧墙 x=90 / 1190；两个矩形 block：`[400,560,90,60]`、`[760,560,90,60]`（顶面 y=560，可站立/阻挡地面移动；跳跃可越过；投射物按 AABB 碰撞）。
- 出生：Lina x=280，木桩 x=1000；二者都在 block 外。
- 弹道高度固定：high y=440、mid y=500、low y=560（即地面上方 180/120/60px）；Lina Q 使用 mid。
- Lina 身体高约 210px，256 帧 1:1 绘制，脚底对齐地面；椭圆程序化影子。
- HUD 左上：`LINA`、HP 条、青色能量条、Q/E 冷却徽章（就绪/剩余秒数）、火焰剩余时间；木桩头顶独立 HP 条。全英文。
- 不做 Level/exp/gold/fullness/食物/天数等完整 HUD。
- Esc 暂停菜单：Resume / Restart / Quit（英文）。

## 实施阶段

### P0 环境与骨架
- `py -3.14 -m venv .venv`；安装 `pygame-ce==2.5.8` + `Pillow>=12`；写 `run.bat`、`requirements.txt`、`.gitignore`、`README.md`；`git init`（不自动 commit）。
- 写 `main.py` + 空场景：窗口、背景缩放、60 FPS、Esc 暂停菜单。
- **验证**：双击 `run.bat` 能开窗；背景正确；Esc 菜单可退出；`git status` 正常。

### P1 并行：骨架 + 首帧
- A 线：`config.py`、`input.py`、`fighter.py`、`dummy.py`、`animation.py`、`debug.py` 基础；用矩形占位画 Lina/木桩/boxes；A/D、W/Space、S/Shift、墙与 block 生效。
- B 线：生成并审批侧视基准；生成 idle 4 + 左右拳各 4 + 左右腿各 4 = 20 帧；接触表审批；导入。
- **验证**：移动/跳跃/下蹲/撞墙/跳 block 正常；F1 能看到 boxes/pivot；20 帧按动作播放、无错位、脚底不漂。

### P2 战斗核心
- `combat.py`、`projectile.py`：攻击事件、hit/hurt AABB、命中结算、顿帧、受击硬直、击退、伤害、回能；Q 投射物 + 8s 冷却；木桩 HP。
- **验证**：拳命中 20 伤害 +15 能量；腿命中 30 伤害 +20 能量、300 击退；Q 命中 25 伤害 +20 能量、150 击退、8s 冷却；命中顿帧约 60ms；同一攻击不重复命中；木桩 1000→0 后可重置。

### P3 Lina 完整技能组
- `lina.py`、`status.py`、`hud.py`：E 变身（100 能量 + 15s 冷却）、5s 火焰、Q 刷新、火焰 +20/40/60%、灼烧 5 HP/s×3s、形态内不回能；左右交替、连段窗口、E 取消后摇、自动面向；九状态模型与调试强制；HUD。
- **验证**：能量满时 E 可用；释放后能量 0、Q 冷却归 0、E 进入 15s、火焰 5s；连续三次命中加成 20/40/60，变身重置；火焰命中不回能；灼烧持续扣血且可刷新；连段/取消手感符合预期。

### P4 批量帧
- 生成/审批/导入剩余 25 帧（walk 6、jump 2、crouch 1、Q 4、transform 6、hurt 2、KO 4）。
- 按实际帧调整每帧时长、攻击事件时间、pivot/缩放；更新 `animations.json`。
- **验证**：每个状态/动作都有正确 clip；45 帧全部 256×256；左右翻转 pivot 不跳；火焰调色缓存和粒子正确；无缺失/错帧。

### P5 收尾
- 热重载边界（坏 JSON 保留旧数据、面板显示错误）；时间缩放/逐帧；`run.bat` 在干净 shell 下可用；README/DEBUG/ASSET_PIPELINE/DESIGN_DECISIONS 写完。
- **验证**：完整跑一遍下面的验收清单；`Image/` 未被修改；无日志文件；无 pytest 依赖。

## 验收清单

1. 新开一个终端，双击 `run.bat`，无需手动装依赖即可进入沙盒。
2. A/D 移动；远离梯子时 W/Space 跳跃，近梯时 W 上爬、S 下爬、Space 跳离；Shift 只下蹲；撞侧墙停住；能跳上/越过 barrier；platform 顶/侧/底全实体，外侧边缘可走落（无落地伤害）。
3. 左键拳交替、右键腿交替；命中伤害 20/30，回能 15/20；腿击退明显强于拳。
4. Q 发射中弹道气流；命中 25 伤害、+20 能量；冷却 8s，开局就绪。
5. 能量 100 时 E 可用；释放后能量 0、Q 立即刷新、E 冷却 15s（开局就绪）、火焰 5s。
6. 火焰形态下攻击不回能；连续命中伤害加成 20%→40%→60%，第三次及以后封顶；下次 E 重置。
7. 火焰命中使木桩灼烧，5 HP/s × 3s，重复命中刷新时间。
8. 命中顿帧可感知（约 60ms）；受击硬直 200ms；输入缓冲 120ms；左键连段 0.15s；E 可取消后摇。
9. 木桩 1000 HP、无敌开关、移动、改血、重置均可用。
10. F1 叠层、F2 面板、F3–F12 控制全部生效；0.25×/2× 与逐帧下计时不漂移。
11. F5 热重载坏 JSON 时保留旧数据并在面板报错；改好 JSON 后立即生效。
12. `Image/` 下所有 canonical 文件哈希未变；没有生成日志文件；没有 pytest。
13. 45 帧接触表均已审批；游戏内无缺帧、无脚底漂移、无朝向 pivot 偏移。

## 明确假设（写入 `docs/DESIGN_DECISIONS.md`）

- Q 冷却 8s、E 冷却 15s，**开局均就绪**；两者只在释放时开始计时。E 仍消耗 100 能量。
- E 刷新 Q；E 无额外冷却以外限制；E 可空中释放；E 可取消攻击后摇。
- 火焰加成按 Lina 的**造成伤害命中**计数，第 1/2/3+ 次分别 +20/40/60%，变身时归零；不刷新持续时间；对 Q/腿/拳都生效，但不作用于灼烧 DoT。
- 灼烧 5 HP/s × 3s，可刷新；毒伤 2% 最大 HP/s，首版只建模/调试演示。
- 同源毒伤再次施加延长时间；不同源各自独立实例、分别扣血。
- 右键击退 300 px/s，Q 150 px/s，0.35s 线性衰减；受击硬直 200ms。
- 高/中/低弹道固定为地面上方 180/120/60px；Q 为中弹道；数值可在 `debug.json` 调整。
- 攻击伤害按 docx 的 basic/extra 拆分（拳 `atk` / 腿 `1.2×basic + 0.8×extra` / Q `basic + 1.5×extra`）；当前 basic 20 / extra 0 → 20/24/20。
- LMB/RMB/Q 仅地面可用；E 空中可用；没有空中普攻。
- 攻击自动面向最近敌人；攻击期间锁水平移动，事件时刻小幅前踏。
- 木桩 1000 HP、无 AI、不攻击；Lina 的 HP/受击/KO 只由调试场景触发。
- block 是类别：barrier 为实体障碍；platform 为可站立的全 AABB 实体（顶/侧/底）；ladder 默认无体积，只做攀爬触发。
- 首版不做音频；所有 UI 文本英文；不做完整 HUD。

## 风险与缓解

- **侧视转换偏离**：正面参考可能仍生成正面/半正面。明确 right-facing 3/4 提示；一次生成 2–4 个基准候选；你审批；拒绝正面帧；接受一致的近侧 3/4。
- **帧间一致性漂移**：固定基准 + 固定前缀提示 + 每动作接触表 + 单帧重生成；导入器检查身高/脚底/pivot，异常帧直接重生成，不做静默拉伸。
- **透明边/色边**：RGBA/alpha 检查、despill；透明输出失败时退回 chroma + Pillow 去背。
- **pygame-ce 与 Python 3.14**：已验证 cp314 wheel；若运行期出现 DLL 问题，退回 Python 3.13 venv（代码不变）。
- **输入/计时漂移**：60Hz 固定步长；输入缓冲/冷却/状态全部用模拟秒；失焦清空输入；0.25×/2×/逐帧验收。
- **动画与攻击窗口不匹配**：导入器校验 clip 总时长 vs `attacks.json` duration；F2 面板显示当前帧/攻击时钟，便于现场调。
- **路径含空格/中文**：`run.bat` 使用 `cd /d "%~dp0"` 和引号；Python 用 `pathlib.Path`。
- **block 与出生点重叠**：舞台坐标集中在 `debug.json`，F1 叠层可见；reset/B 开启时自动解嵌；出生点已检查。
- **canonical 素材被覆盖**：所有生成物只写 `assets/frames/`、`assets/generated/`；`Image/` 只读。
- **没有自动测试**：按约定不做 pytest；用 F1/F2 + 场景预设 + 验收清单替代；每次改规则后手动回归关键路径。
- **生成耗时/成本**：先 20 帧验证管线，审批后再批量 25 帧；不一次性生成全部候选。

## 不在范围内 / Phase 2

- 不在首版：日循环、phase、食物/饱食度、商店/金币、存档/Continue、主菜单、角色选择、音频、完整 HUD、其他角色、其他敌人、Warrior、exe 打包、pytest、文件日志、毒/冻结/减速/霸体/免伤的**自然触发**（仍可由调试快捷键强制施加）。
- Phase 2：Warrior（`Image/Enemy/warrior-336.png`）AI 与动作、真实状态触发、多敌人目标选择、音频、打包。

## 关键文件（实现时优先）

- `game/combat.py` — 命中/伤害/顿帧管线
- `game/lina.py` — 四招、能量、冷却、火焰形态
- `game/animation.py` — 帧动画、翻转 pivot、调色缓存
- `game/data/attacks.json` — 帧事件与 hitbox
- `game/data/animations.json` — 帧时长与清单
- `tools/import_frames.py` — 透明/缩放/锚点/校验
- `tools/contact_sheet.py` — 审批接触表
- `main.py` / `run.bat` — 启动与一键运行
