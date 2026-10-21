# Next Session — Warrior 完整设计与战斗沙盒

> 工作目录：`D:\Program Game\Island Survival`  
> 当前分支：`warrior-combat-sandbox-2026-10-21`  
> 基线提交：`054702b Complete Warrior combat sandbox and Lina form transition fixes`  
> 用途：新 session 直接读本文件，不依赖上一段对话。
>
> **状态（2026-10-21）**：本文件的三项需求已完成。新增 `game/data/roster.json` 与
> `game/roster.py`；F7 切敌人、`[` / `]` 切角色；`V/C/X/Z` 读取敌人 `skill_slots`，Warrior 第 4
> 槽为空；dash 击飞的空中表现/KO/霸体/hitstop 与 smoke 断言已补齐。数值按工作区
> `instruction.docx`：Warrior HP 300 / basic_atk 20 / 1.2-1.5-1.2，Lina 拳 20 / 腿 24 / Q 20。
> 已完成项与调试方式见 `docs/DESIGN_DECISIONS.md`、`docs/DEBUG.md` 和 `README.md`。
>
> 追加：鼠标中键切换攻击锁定（默认关闭；开启后拳/腿/Q 起手面向存活敌人；切换角色/敌人重置为关闭，F9 保留，F5/启动关闭）。
>
> 追加：Warrior/Lina/block 过近时的身位分离修复——不再把 Warrior 翻到 Lina 另一侧；当前侧被挡时反推 Lina；分离速度上限 600px/s（`combat.separation_speed`），避免瞬移。smoke 新增 `separation_block_ok`。
>
> 追加：击飞漩涡特效——`knock_up` 期间脚底青白三臂漩涡 + 外环，跟随角色 1.5s，随剩余时间收缩淡出；纯绘制不改角色动作。参数在 `combat.knock_up_fx`，smoke 新增 `knockup_fx_ok`。
>
> 追加：击飞/受击硬直/控制锁定期间按下的攻击现在会进入单槽缓冲，控制恢复时立即执行；smoke 新增 `lock_buffer_ok`。
>
> 追加：knock_up 期间使用 `combat.knock_up_gravity`（1013.333）延长滞空，落地约在 1.5s 击飞窗口结束处；落地/漩涡结束/控制恢复对齐，排队攻击在落地后 1–3 帧内出拳。
>
> 追加：漩涡在最后阶段仍保留 `min_scale 0.75` / `min_alpha 0.55` 的最低可见度，不再提前淡没；`knock_up` 结束的当帧立即消失。

## 启动指令（可直接复制）

```text
读取 docs/NEXT_SESSION_WARRIOR.md，按其中的要求先给出“Warrior 完整设计完成计划”；先不要改代码或素材，等我确认计划后再开始。计划中如果与 instruction.docx 或现有数值有冲突，请一次性列出来问我，不要自行假设。
```

## 任务

继续开发这个 Python 3.14 + pygame-ce 的 2D 战斗沙盒，修改战斗沙盒，并完成 Warrior 的全部设计。

### 本轮新增/明确的需求

1. **Warrior 增加击飞能力**：以 `instruction.docx` 的 Warrior 技能 2 为准。先核对现有 dash 的 `launch` / `knock_up` 是否完整（当前数值是 30 伤害 + 1.5s 击飞、`launch` 760），在计划中给出最终的击飞参数、表现和边界处理（霸体、KO、hitstop）。
2. **沙盒必须能更换 character 和 enemy**：当前 Lina/Warrior 不能写死在场景里；需要为后续角色和敌人提供可切换的 roster。默认仍保持 Lina vs Warrior，现有 F7/Dummy 行为不能破坏。
3. **对任意 enemy，`V` / `C` / `X` / `Z` 分别触发其第 1 / 2 / 3 / 4 技能**，用于调试。技能槽必须由 enemy 数据定义，不能把 Warrior 的 `attack_id` 硬编码进场景；未定义的槽位按键无效并在 F2 显示为空。当前 Warrior 对应关系：`V=axe_slash`、`C=dash`、`X=axe_throw`，`Z` 为第 4 槽（尚未定义，计划中明确是新增技能还是暂时空置）。

开始前先完整阅读（不要先改代码）：

- `AGENTS.md`
- `instruction.docx` 的 Warrior 部分
- `docs/WARRIOR_HANDOFF.md`
- `docs/DESIGN_DECISIONS.md`
- `docs/ASSET_PIPELINE.md`
- `docs/DEBUG.md`
- `PLAN.md`
- `game/warrior.py`、`game/combat.py`、`game/scene.py`、`game/lina.py`
- `game/animation.py`、`game/fighter.py`、`game/stage.py`、`game/projectile.py`
- `game/data/stats.json`、`attacks.json`、`animations.json`、`debug.json`
- `main.py` 的 smoke test 与 `tools/` 下的素材工具

## 当前状态（2026-10-21）

- Warrior Phase 2 已完成并安装；Warrior 是默认敌人，F7 可切回训练 Dummy。
- Warrior 已有：`axe_slash`（6 帧）、`dash`（5 帧）、`axe_throw`（7 帧回旋斧）、AI、前摇+判定霸体、胜负/重开、F1/F2 调试。
- **Roster 已完成**：`game/data/roster.json` + `game/roster.py`；F7 切敌人、`[` / `]` 切角色（当前仅 Lina）。`V/C/X/Z` 读取敌人 `skill_slots`，未定义槽位 no-op。
- 本轮定稿数值：
  - HP 300
  - `basic_atk` 20（按工作区 docx；`1.2/1.5/1.2` 倍率）
  - dash 30 伤害 + 1.5s 击飞
  - axe throw 每段 24（去程+回程共 48）
  - 全局 `skill_gap` 0.9s
  - dash 冷却 2.5s，throw 冷却 2.8s，axe_slash 冷却 0.9s
- `instruction.docx` 工作区版本为 HP 300 / atk 20；`HEAD` 版本为 HP 200 / attack 30。本轮按工作区版本执行，差异已记录在 `docs/DESIGN_DECISIONS.md`。
- Warrior 帧数：36（idle 4、walk 6、jump 2、axe_slash 6、axe_throw 7、dash 5、hurt 2、KO 4）。
- axe_slash 的 01 是按 idle 体型/斧头大小重做的抬斧过渡；斧头为单刃、只保留上方刀锋；03/04 为单手后握；旧 05 已删除，恢复帧为 05，总时长仍 0.75s。
- Lina 帧数：45 普通 + 41 火焰 = 86；火焰 hurt/KO/revert 已补齐。
- 近期已修复且不要回退：
  - 火焰形态不再有普通帧红色 tint 回退。
  - 变身被打断时立即切到 flame 表，避免 Lina 消失。
  - `flame_offsets` 逐帧对齐火焰素材，revert 不再发生位移。
  - 角色间 110px 最小身位；Warrior 优先让位，被 block/墙挡住时选择可站立侧或反推 Lina。
  - Warrior 朝向 8px 死区，避免重叠时来回翻转。
- Smoke 覆盖：Lina 回归、Warrior 伤害/霸体/KO/胜负、AI、dash、throw、投掷轨道、AI 远程、block 开关、技能间隙、身位分离、变身受击可见性、revert、flame_offsets 覆盖。

## 本次需要产出的计划

先给一份“Warrior 完整设计完成计划”，至少覆盖：

1. 对照 `instruction.docx` 的 Warrior 规格，列出已实现、未实现、以及与当前数值的差异；
2. **击飞能力**：说明现有 dash 击飞是否符合文档，给出最终参数、命中反馈、霸体/KO/hitstop 处理与 smoke 断言；
3. **character/enemy 更换架构**：roster/注册表、选择方式与按键、默认组合、切换时的状态清理（projectiles、hitstop、match result、HUD/名字/动画路径），以及不把 Lina/Warrior 写死的实现方案；
4. **通用 enemy 技能调试键**：`V/C/X/Z` → 第 1/2/3/4 槽的数据结构、`force_skill(slot)` 接口、F2 槽位/冷却显示、未定义槽位的 no-op，以及 Dummy/未来敌人的兼容；
5. 还需要补齐的技能、AI 行为、动画、数值、HUD/反馈与文档；
6. 素材缺口和生成方案（严格使用 `Image/` 作为视觉源，保留其分类与命名；`Image/` 只读）；
7. 分阶段实施顺序与验收方式（每步运行 `run.bat --smoke-test`；素材先 staged + contact sheet，经用户审阅后再安装）。

对于 character/enemy 的选择按键、以及 Warrior 第 4 技能是否要新增，请在计划里给出建议方案并让我确认，不要自行定稿。

如果 `instruction.docx` 或其他文档缺少 Warrior 的具体设计，把缺失项一次性列出来问用户，不要自行假设。

## 约束

- 使用项目 venv / `run.bat`；不要用 pytest；不要写日志文件。
- 固定 60Hz；JSON 热重载（F5）；UI 文案英文。
- `V/C/X/Z` 必须通过 enemy 的技能槽数据调用技能，不能继续写死 `axe_slash` / `dash` / `axe_throw`；未定义槽位必须安全 no-op。
- character/enemy 的更换要数据驱动，优先复用现有 Fighter/AnimationPlayer/AttackRuntime，不要复制两套 Lina/Warrior 场景逻辑。
- 保留当前默认组合 Lina vs Warrior，以及 F7/Dummy、B 开关 block、C/X/V 现有调试习惯的兼容性（如有键位冲突，在计划中提出）。
- 不要回退 Lina 的现有战斗手感和近期修复；如需改 Lina 或场景，先在计划里说明理由。
- 不覆盖 `Image/`；不提交 git，除非用户明确要求。
- 素材生成后先进入 `assets/generated/staged/`，生成 contact sheet 给用户审阅；批准后才复制到 `assets/frames/`。
- 新 session 结束时如用户要求提交，先确认分支；默认不要 push/merge。

## 验收

- `run.bat --smoke-test` 全部字段为 `True`，`missing_frames=0`、`warrior_missing_frames=0`。
- 新增 smoke 断言至少覆盖：dash 击飞（launch + `knock_up`）、character/enemy 切换、`V/C/X/Z` 对 Warrior 第 1–3 槽与未定义第 4 槽的行为、Dummy 无技能时按键 no-op。
- 新增/修改玩法要给 F2 调试信息或截图，便于用户观察。
- 文档同步：`README.md`、`docs/DESIGN_DECISIONS.md`、`docs/DEBUG.md`、`docs/ASSET_PIPELINE.md`、`PLAN.md`、`docs/WARRIOR_HANDOFF.md`。
