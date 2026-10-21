# Warrior 交接文档（Phase 2）

> 写于 2026-10-20。Lina 战斗沙盒已完成，下一阶段是 Warrior。
> 新 session 没有旧对话上下文，**以本文件和仓库文件为准**。
>
> **实施状态（2026-10-20）**：Phase 2 Warrior 已完成。默认 Warrior，F7 切 Dummy；384×384 / pivot (192,372)；24 帧（idle 4、walk 6、jump 2、axe_slash 6、hurt 2、KO 4）；完整 1v1、AI 跳跃过 block、前摇+判定霸体、胜负/重开、F1/F2 与 `--smoke-test` 均已验证。以下开放问题已定稿于 `docs/DESIGN_DECISIONS.md`。

## 1. 当前状态

Lina Seabright 战斗沙盒已完成并验证：

- 45 张普通动作帧 + 41 张火焰形态帧，共 86 张，全部 256×256、脚底中心 pivot `(128,244)`。
- 拳/腿左右交替、Q 气流、E 火焰形态、能量、冷却、火焰加成、灼烧、击退、受击、KO。
- 输入：攻击中按键进入单槽队列；暂停/失焦/重置后重建 held；攻击方向由 A/D 面向决定。
- Q 气流高度相对 Lina 脚底（平地 y=478，60px 箱子上 y=418）。
- Block 碰撞：地面使用 100px 移动碰撞体；攻击前踏不再绕过 block 碰撞；重叠按较近一侧推出。
- E 冷却 20s，火焰持续 10s。
- 训练木桩 1000 HP、无 AI、可调血量/位置/无敌。
- `run.bat --smoke-test` 当前输出：

```text
SMOKE ticks=60 punch_hp=980.0 punch_energy=15.0 damaged=True gained=True
queued_kick_ok=True block_lunge_ok=True q_block_ok=True flame_ok=True
missing_frames=0
```

### 开始前

- 仓库已初始化，但**写此文档时还没有 commit**，所有文件都是 untracked。建议先做一次 baseline commit（是否提交、提交哪些文件由用户决定）。
- `~$struction.docx` 是 Word 临时文件，不应提交。
- 不要修改 `Image/` 下的 canonical 素材，只读。
- 不要引入 pytest、自动测试套件或文件日志；继续使用 `--smoke-test` + F1/F2 调试工具。

## 2. 必读文件

按顺序读：

1. `AGENTS.md` — 绑定的素材规则（`Image/` 是默认视觉源；保留分类和角色名）。
2. `PLAN.md` — 原计划 + 顶部全部「实施更新」。
3. `README.md` — 运行、控制、调试键、当前范围。
4. `docs/DESIGN_DECISIONS.md` — 所有规则假设和数值。
5. `docs/DEBUG.md` — F1/F2/F3–F12 和调试流程。
6. `docs/ASSET_PIPELINE.md` — Seedream 生成、接触表、导入流程。

再读实现：

- `game/scene.py` — tick 顺序、目标、投射物、调试键。
- `game/lina.py` — Lina 状态机、攻击、火焰、目标。
- `game/dummy.py` — 当前训练木桩。
- `game/fighter.py` — 共享状态、hurtbox、受击、绘制。
- `game/combat.py` — 攻击事件、命中、前踏。
- `game/animation.py` — 帧动画、翻转、染色。
- `game/stage.py` — 地面/墙/block 碰撞。
- `game/data/stats.json`、`attacks.json`、`animations.json`、`debug.json`。

## 3. Warrior 素材

### Canonical 源

- 角色原图：`Image/Enemy/warrior-336.png`（336×336 RGBA，3/4 正面偏右站姿，持巨型新月斧）。
- 设计海报：`Image/Enemy/Posters/warrior-poster-v2.png`（1024×1536 RGB，左向展示姿势，仅作设计参考，不能直接当透明精灵）。
- 海报生成提示词和设计细节：`Image/Enemy/Posters/README.md` 的 `warrior` 一节。

外形要点（来自海报文档）：

- 成年壮硕男性战士，深红色刺发、红色头带（飘带）、红黑无袖战衣、裸露胸腹和手臂。
- 金色肩甲、黑色金钉护腕、红色层叠腰布、金边黑裤、厚重红黑战靴。
- 单把巨大新月刃银斧，深色漩涡纹、金色配件、红色流苏。

### 朝向与画布

- 游戏帧只存**右向**，运行时按 `facing` 水平翻转（与 Lina 一致）。
- 但 `warrior-336.png` 是正面偏右，不是严格侧视。必须先以它为唯一输入生成一张**右向 3/4 侧视基准**，审批后再批量做动作。
- `game/animation.py` 目前把 `FRAME_SIZE = (256, 256)` 写死，任何输入图都会被缩放到 256。Warrior 的斧头在攻击帧可能超出 256。
  - 方案 A（先做）：沿用 256×256、`pivot (128,244)`，Warrior 身体高度约 220–230，观察斧头是否被裁切。
  - 方案 B（需要时）：给 `AnimationPlayer` 增加 `frame_size` 参数，Warrior 使用 336×336 或 384×384，pivot 相应调整。
  - **先决定方案，再开始批量生成。**
- `tools/import_frames.py` 已支持 `--body-height`、`--canvas`、`--pivot-x`、`--pivot-y`，但 `AnimationPlayer` 的 256 写死需要同步处理。

### 生成流程

1. 以 `warrior-336.png` 为唯一输入，用 Seedream `image_to_image`，`size: "1K"`、透明背景、PNG，`request_count: 2–4`。
2. 提示词固定前缀包含上述外形要点；只改变姿势句。要求：right-facing 3/4 side view、全身、武器完整、脚底可见、透明背景、无影子/文字/边框、固定镜头比例。
3. 候选保存到 `assets/generated/raw/`，用户审批后基准存入 `assets/generated/base/warrior_side_base.png`。
4. 首批建议：idle 4 + 一次斧击 4–6 + hurt 2 + KO 4，先验证管线。
5. 每动作拼接触表到 `assets/generated/contact_sheets/`，审批后导入 `assets/frames/warrior/<action>/`。
6. 单帧可重生成，未审批帧不进入游戏。

## 4. 代码耦合点（必须处理）

### 目标系统

- `Scene` 目前硬编码 `self.dummy`。
- `Lina.start_attack()` 接收 `target`，`spawn_projectile_from_event()` 直接使用 `self.dummy`。
- `AttackRuntime` 只支持单个 target。
- 建议先抽象成 `scene.enemy` / `scene.targets` 或 `Enemy` 接口，再决定是否保留木桩。第一版 Warrior 可以只支持一个敌人。

### 动画与绘制

- `Dummy` 是 `pygame.draw` 程序化绘制，没有 `AnimationPlayer`。
- Warrior 应该是 `Fighter` 子类，带 `AnimationPlayer`、自己的 clips、hurtbox 和 stage body width。
- 现有动画缓存、翻转 pivot、火焰染色是 Lina 专用的；Warrior 不需要火焰染色，但需要自己的动画表。

### 战斗与状态

- Lina 的 `take_hit()` 已可用，但目前只有 F12 调试能让她受伤。
- Warrior 攻击可直接复用 `AttackRuntime` / `resolve_hit()`，但需要自己的 `attacks.json` 条目、hitbox、伤害、击退、hitstop。
- 木桩默认 `invincible` 可配置；Warrior 不应该是无敌木桩，需要有 HP、hurt/KO。
- 如果 Warrior 也使用状态效果，复用 `StatusSet`；第一版可以不做霸体/减伤。

### 场景与 HUD

- `Scene.tick()` 当前顺序是 `dummy.update` → `lina.update`；加入 AI 后要明确 Warrior/Lina 更新顺序和互相命中。
- HUD 目前显示 Lina + dummy HP；需要改成 Warrior 名称和 HP，或保留训练木桩模式。
- F7–F12 目前全是 dummy 控制；需要重新分配：例如 AI 开关、Warrior 重置、强制攻击/受击等。
- `config.py` 的 `REQUIRED_*` 列表要加入 Warrior 的 clips / attacks 校验。
- `main.py` 的 `--smoke-test` 要扩展 Warrior 检查，保持无 pytest。

### 物理

- `Fighter` 有 `stage_half_width`（Lina 由 `stats.json` 的 `stage_body_width` 设置）。
- Warrior 体型更大，必须设置自己的 `stage_body_width`、hurtbox、移动速度，并验证撞 block/站上 block 的行为。
- 攻击前踏已经走 `Stage.move_x()`；Warrior 的攻击同样应走这条路。

## 5. 必须先确认的设计问题

在写代码/生成素材前，用 grill-me 和用户确认：

1. **范围**：Warrior 替换木桩，还是与木桩共存/可切换？第一版是否只做 1v1？
2. **完整 1v1**：Warrior AI 是否会追击、攻击、造成伤害？Lina 会受伤/KO 吗？是否有胜利/失败和重开？
3. **动作集**：第一版 idle/walk/attack/hurt/KO 各多少帧？先做一套横斩还是两套攻击？是否需要起手预警帧？
4. **画布**：256 还是 336/384？斧头是否会超出 256？是否要改 `AnimationPlayer` 的 `frame_size`？
5. **数值**：Warrior HP、攻击伤害、攻击距离、前摇/后摇、攻击冷却、击退、移动速度、是否霸体。
6. **AI**：追踪距离、攻击距离、转向、攻击间隔、是否跳过 block/箱子、是否会被 Lina 击退到墙/block。
7. **调试键**：F7–F12 如何重新分配？是否需要 AI 开关、Warrior 强制攻击、Warrior 重置、胜败演示？
8. **木桩**：保留为训练模式，还是彻底替换？如果保留，如何切换？

## 6. 推荐里程碑

### M0 — 基线

- 用户确认后做一次 baseline commit。
- 确认本文件中的开放问题，写入 `docs/DESIGN_DECISIONS.md`。

### M1 — 目标系统 + 占位 Warrior

- 把 `dummy` 抽象成可替换的 enemy/target。
- 用占位矩形或 Warrior 基准图接入场景，替换木桩。
- Lina 的拳/腿/Q 能命中 Warrior，Warrior 有 HP 条。
- 不做 AI，不做新动作帧。先保证 Lina 现有功能不回归。

### M2 — 素材管线

- 生成并审批 Warrior 右向侧视基准。
- 首批帧：idle 4 + 斧击 4–6 + hurt 2 + KO 4。
- 接触表审批后导入；接通 `animations.json`。
- 验证脚底、pivot、朝向、斧头是否被裁切。

### M3 — AI + 双向战斗

- Warrior 面向 Lina、接近、进入距离、前摇、挥斧、冷却。
- Lina 会被命中、受击硬直、击退、KO。
- 胜负提示和重开；F9 整场重置。
- 调试键和 F1/F2 面板更新。

### M4 — 收尾

- 第二套攻击（如果范围允许）、状态交互、粒子/音效占位（音频仍不在首版范围）。
- 扩展 `--smoke-test`：Warrior 存在、Lina 能伤害 Warrior、Warrior 能伤害 Lina、重置后恢复。
- 更新 README、DESIGN_DECISIONS、DEBUG、ASSET_PIPELINE。
- 确认无 pytest、无文件日志、`Image/` 未修改。

## 7. 新 session 开场 prompt

```text
继续《Island Survival》项目。Lina 战斗沙盒已完成，现在进入 Phase 2 的 Warrior。

先阅读：
- docs/WARRIOR_HANDOFF.md
- AGENTS.md
- README.md
- PLAN.md（包括顶部所有“实施更新”）
- docs/DESIGN_DECISIONS.md
- docs/DEBUG.md
- docs/ASSET_PIPELINE.md
- game/scene.py、game/lina.py、game/dummy.py、game/combat.py、
  game/animation.py、game/stage.py、game/fighter.py
- game/data/*.json

Warrior 的唯一视觉源是 Image/Enemy/warrior-336.png。
Image/Enemy/Posters/warrior-poster-v2.png 只作设计参考，不能修改 Image/ 下的原文件。
沿用 Lina 的侧视 3/4 基准、透明 PNG、接触表审批和 tools/import_frames.py 流程。

在写代码或生成素材前，先用 grill-me 跟我确认 Warrior 的范围，不要直接开工：
1. Warrior 替换木桩还是共存/可切换？
2. 是否启用完整 1v1（AI 追击攻击、Lina 受伤/KO、胜负、重置）？
3. 第一版动作集与帧数？一套还是两套攻击？
4. 画布与 pivot：256 还是 336/384？是否需要给 AnimationPlayer 增加 frame_size？
5. 攻击数值、前摇/后摇、冷却、击退、霸体？
6. 调试键如何重新分配？

先给计划，再按“骨架与素材并行”实施：先用占位图形接入 Warrior 和目标系统，再逐批生成/审批帧。
```

## 8. 第一版 Warrior 完成标准

- Warrior 以真实序列帧显示，idle 会播放，能受伤、进入 hurt/KO。
- Lina 的拳/腿/Q 能命中 Warrior；Warrior 的斧击能命中 Lina。
- Lina 和 Warrior 的 HP 条、名称、重置、胜负流程可用。
- 站上/撞上 block 不穿模；攻击前踏不穿过 block。
- F1 能看到 Warrior 的 hit/hurt box；F2 能看到 Warrior 状态、动画、HP。
- `--smoke-test` 增加 Warrior 检查并全部通过。
- Lina 的输入队列、面向攻击、Q 相对高度、火焰形态和现有数值无回归。
- `Image/` 原文件未被修改；没有新增 pytest 或日志文件。
