# Next Session — 新增 Character 与 Enemy（Handoff）

> **下一轮 handoff（2026-10-23）**：Nyra / Veno 细节调整 + Lina Q 特效改造，直接使用 `docs/NEXT_SESSION_NYRA_VENO_LINA_Q.md`。
>
> **2026-10-22 实施状态（Q 于 2026-10-23 更新）**：Nyra Steel 与 Veno-Spider 已实现并通过 smoke（`exit=0`，`nyra_missing_frames=0`、`veno_missing_frames=0`、`warrior_missing_frames=0`）。
> - 默认仍为 Lina vs Warrior；`[` / `]` 为 Lina ↔ Nyra；F7 为 Warrior → Veno → Dummy。
> - Nyra：384×384 / pivot (192,372) / body 214，25 帧最小集（slash 6、thrust 3、wave 3、dash 3）；LMB 20、RMB 24、Q 30（8s）、E 30（15s）；Q 不再发射弹体，使用 cast-anchored 分段 hitbox：00/01/05 帧（及首尾空白段）用右键 thrust 的 `[28,-165,130,48]`，02–04 帧（t=0.12–0.30）用延长到剑光范围的 `[28,-212,162,123]`（最远 190px）；`game/wave_fx.py` 播放 `assets/frames/nyra/nyra_wave_fx/` 的 6 帧透明剑光贴图（00/01/05 透明，02 出现、03 最盛、04 原位淡出）；仅近战叠印记，第 4 次近战引爆 `1.8×atk + 10% 目标最大生命` 并保留 1 层；E 穿敌不穿地形。
> - Veno：320×320 / pivot (160,308) / body 150，20 帧最小集；HP 50 / ATK 10；咬 15、毒 8 + 3%/s×3s、网 10 + 眩晕 1s；地面撕咬、浮空 140–300px（基准 220）优先毒/网；单只生成。
> - 素材已安装到 `assets/frames/nyra/` 与 `assets/frames/veno/`；原始候选/接触表在 `assets/generated/`。
> - **待办**：Veno 的 `n=3` 多敌人未实现；后续可把最小帧集扩到 Lina/Warrior 标准。`nyra_slash` 已扩为 6 帧（初始前下方 45° → 剑抬到水平下 10–20° 的过渡 → v11 大臂前伸帧（219px、脚底 372）→ 复用 thrust_v5_01 长剑接触 → 两张收势帧）；durations 0.04/0.04/0.05/0.08/0.05/0.05（总 0.31s），LMB hitbox `[34,-170,120,60]`，判定窗口 0.13–0.21。`nyra_wave` 起始剑指前上方 45°，frame 01 平举长剑、肘部微屈，frame 02 收到前下方 45°；剑气不再发射弹体，`wave_fx.py` 播放 6 帧透明剑光贴图，02–04 帧使用延长 hitbox `[28,-212,162,123]`（最远 190px），其他帧使用右键 thrust 的 `[28,-165,130,48]`。
> - 工作区未提交；不要 revert / stash / 覆盖用户现有改动。
>
> 以下为 2026-10-21 的原始 handoff，架构说明仍有效；其中 branch/baseline 头部已过期（当前 `main`，HEAD `26db0cf`，工作区有未提交实现）。

> 写于 2026-10-21，供下一次 session 直接读取。
> 当前分支：`warrior-combat-sandbox-2026-10-21`
> 基线提交：`054702b`，但工作区有未提交改动（roster/技能槽/击飞/输入缓冲/文档）。
> **不要 revert、stash 或覆盖这些未提交改动；先看 `git status`。**

## 启动指令（复制给新 session）

```text
读取 docs/NEXT_SESSION_CHARACTERS.md，按文档添加新的可玩 character 和 enemy。
先读必读文件，检查 instruction.docx 对应角色/敌人的规格，给出计划、数值和素材缺口；
先不要改代码或素材，等我确认计划后再开始。
```

## 0. 一分钟理解当前架构

- 技术栈：Python 3.14 + pygame-ce；`run.bat` 启动；固定 60Hz；`run.bat --smoke-test` 验证。
- 数据：`game/data/` 下五份 JSON —— `stats.json`、`attacks.json`、`animations.json`、`debug.json`、`roster.json`；F5 热重载。
- 构造：`game/roster.py` 读取 `roster.json`，按 `class` 找到 Python 类，再构造 `AnimationPlayer` 和 Fighter。
- 场景：`game/scene.py` 只认 `player` / `enemy` 和 roster 数据，不直接 new Lina/Warrior/Dummy。
- 参考实现：
  - 可玩角色模板：`game/lina.py`
  - 有 AI 的敌人模板：`game/warrior.py`
  - 无 AI 训练目标模板：`game/dummy.py`
- 切换：`F7` 循环敌人；`[` / `]` 循环可玩角色；切换会整场重置、AI 关闭、攻击锁定关闭，保留 B 的 block 开关。
- 调试：`F1` 判定叠层，`F2` 状态面板，`V/C/X/Z` 触发当前敌人的第 1–4 技能槽，`F8` AI/无敌，`F9` 重置。

## 1. 开工前（先计划，不改代码/素材）

### 1.1 必读

按顺序读：

1. `AGENTS.md`、`README.md`
2. `docs/DESIGN_DECISIONS.md`、`docs/DEBUG.md`、`docs/ASSET_PIPELINE.md`
3. `PLAN.md` 顶部所有「实施更新」
4. `game/roster.py`、`game/config.py`、`game/scene.py`
5. `game/fighter.py`、`game/combat.py`、`game/animation.py`
6. `game/lina.py`、`game/warrior.py`、`game/dummy.py`
7. `game/data/*.json`
8. `instruction.docx` 中对应角色/敌人的章节（用 python-docx 提取文本；工作区版本可能比 HEAD 新）
9. `main.py` 的 `_smoke_test`

### 1.2 必须问用户的设计问题（一次问完）

- **对象**：新 character 和新 enemy 分别是谁？`Image/Character/`、`Image/Enemy/` 中使用哪张 canonical 图？
- **是否已有素材**：复用现有动作帧，还是需要从 canonical 图生成整套帧？
- **技能**：普通攻击、技能 1–4、被动/资源；每个技能的伤害、范围、前摇/判定/后摇、冷却、击退/击飞/状态。
- **角色资源**：是否有能量/形态/冷却？HUD 要显示什么？是否沿用 Lina 的 `energy`/`flame` 结构？
- **敌人 AI**：是否追击、跳跃过 block、远程/近战选择、技能间隔、霸体、KO/胜负规则？
- **画面**：画布、pivot、身体高度、动作列表和帧数（idle/walk/jump/hurt/KO + 攻击）。
- **默认 roster**：是否保持默认 Lina vs Warrior？新角色/敌人是通过 `[` / `]` / F7 切换，还是设为默认？
- **范围**：本轮是否必须完成全部动作帧和 AI，还是先接入占位/基础动作、后续再补？
- **缺失规格**：`instruction.docx` 没写的数值/行为，逐条列出让用户决定；不要自行假设。

### 1.3 计划产出

给用户一份短计划，至少包含：

1. 新角色/敌人的数据 ID、class ID、canonical 素材路径、画布/pivot/帧数。
2. 技能表：attack_id、槽位、伤害公式、命中窗口、冷却、状态。
3. 代码改动清单（数据 + 类 + 注册表 + smoke）。
4. 素材计划（生成/导入/审批；若复用现有帧也要说明）。
5. 验收方式（smoke 字段 + F2 观察点）。

**完成标准**：用户明确确认计划；没有未决的数值/素材/范围问题。

## 2. 新增 playable character（建议顺序）

### 2.1 数据

1. `game/data/stats.json`：增加该角色的 stats key（HP、basic_atk、extra_atk、move、hurtbox、stage_body_width；按需增加资源/冷却）。
2. `game/data/attacks.json`：增加该角色的攻击条目；`attack_id` 必须与动画 clip 名一致。
3. `game/data/animations.json`：增加该角色的 clip 表、`frame_size`、`pivot`（例如 `nyra_clips` / `nyra_frame_size` / `nyra_pivot`）。
4. `game/data/roster.json` 的 `characters` 增加条目（见 §4 模板）。
5. `game/data/debug.json` 的 `stage` 增加出生点 key（必须以 `_spawn` 结尾）；默认值仍指向 Lina/Warrior，除非用户要求改默认。

### 2.2 代码

1. 新建 `game/<character>.py`，参考 `Lina` 的构造函数、`start_attack`、`update`、`reset`。
2. 在 `game/roster.py`：
   - import 新类；
   - `FIGHTER_CLASSES["<class_id>"] = NewCharacter`。
3. 在 `game/config.py`：
   - `ROSTER_CLASSES` 加 `<class_id>`；
   - `PLAYABLE_CLASSES` 加 `<class_id>`；
   - 如果有序列帧，`ANIMATED_CLASSES` 加 `<class_id>`。
4. 如果角色有新的资源/形态，更新 `game/hud.py` 和 `game/debug.py` 的玩家信息行；现有 HUD 只对 `energy`/`flame_time` 做属性保护。
5. 如果角色需要攻击锁定，在 `start_attack()` 开头调用 `scene.face_target_if_locked(self, target)`（参考 `Lina.start_attack`）。

### 2.3 角色类最小契约

```python
class NewCharacter(Fighter):
    def __init__(self, store, stage, entry, anim):
        cfg = store.stats[entry["stats"]]
        x, y = stage.spawn(entry["spawn"])
        super().__init__(
            x=x, y=y, facing=1, anim=anim,
            hurtbox_config=cfg["hurtbox"], max_hp=cfg["hp"],
            stage=stage, gravity=cfg["move"]["gravity"],
            knockback_decay=store.stats["combat"]["knockback_decay"],
            stage_body_width=cfg.get("stage_body_width"),
            entry=entry,
        )
        self.store = store
        self.cfg = cfg
        self.spawn = (float(x), float(y))
        self.set_attack_stats(cfg)
        self.knock_up_gravity = float(
            store.stats["combat"].get("knock_up_gravity", self.gravity)
        )
        # 资源/冷却初始化
        self.reset()

    def update(self, dt, input_state, target, scene):
        ...  # 必须保持这个签名；scene.tick 固定这样调用 player
    def reset(self):
        self.reset_common(*self.spawn, 1)
        ...  # 资源/冷却/动画复位
    def start_attack(self, attack_id, scene, target):
        scene.face_target_if_locked(self, target)
        self.attack_id = attack_id
        self.state = FighterState.ATTACK
        self.anim.set_clip(attack_id, reset=True)
        self.attack_runtime = AttackRuntime(self, attack_id, self.store.attacks[attack_id], target, scene)
        ...  # 记录 recovery start；参考 Lina
```

**完成标准**：在没有任何新素材时，角色也能用 fallback 图/占位帧构造、reset、切换，并且 `run.bat --smoke-test` 不新增失败。

## 3. 新增 enemy（建议顺序）

### 3.1 数据

1. `stats.json`：HP、basic_atk、extra_atk、move、hurtbox、stage_body_width；如果沿用 Warrior 式 AI，补 `ai` 段（attack_range、skill_gap、dash_range、throw/remote range、cooldowns）。
2. `attacks.json`：每个技能一个 attack_id；`damage_mult` 用 `basic_mult`/`extra_mult`；事件类型 `hitbox` / `dash` / `projectile`。
3. `animations.json`：敌人类 clip 表、canvas、pivot。
4. `roster.json` 的 `enemies`：`skill_slots` 固定 4 项（攻击 id 或 `null`）、`separates`、`decides_match`。
5. `debug.json`：出生点 `<enemy>_spawn`。

### 3.2 代码

1. 新建 `game/<enemy>.py`，参考 `Warrior`：
   - 构造函数；`ai_enabled = True`（或按用户要求）；
   - `update(dt, scene)`：KO/HURT/ATTACK/control lock 分支；AI 追击/跳跃/攻击；
   - `start_attack`、`force_attack(scene, target, attack_id) -> bool`；
   - `skill_remaining(attack_id) -> float`（用于 F2 冷却显示；未知返回 0）；
   - `reset()`：回到出生点、清冷却、`ai_enabled = True`、重置动画；
   - 如需要霸体，override `take_hit`（参考 Warrior 的 `armor_until`）。
2. 注册：
   - `game/roster.py` 的 `FIGHTER_CLASSES`；
   - `game/config.py` 的 `ROSTER_CLASSES` / `ANIMATED_CLASSES`（有帧就加）。
3. `force_skill` 由基类 `Fighter` 提供：它会从 `skill_slots` 取 attack_id 并调用你的 `force_attack`。没有 `force_attack` 的敌人，V/C/X/Z 自动 no-op。
4. 如果敌人没有 AI（训练目标），可以不实现 `ai_enabled`；F8 会退化为无敌开关（参考 Dummy）。
5. 如果新敌人使用新的 projectile 类型，必须：
   - `attacks.json` 的 projectile 事件写 `"projectile": "<kind>"`；
   - `game/config.py` 的 `PROJECTILE_KINDS` 加 kind；
   - `game/scene.py` 的 `spawn_projectile_from_event` 加对应构造分支。
   - 现有 kind 只有 `"q_wave"` 和 `"axe"`。

**完成标准**：F7 能切到新敌人；F8 能开关 AI；V/C/X/Z 按槽位触发/空槽 no-op；F2 显示槽位和冷却；新敌人能伤害 Lina 且能被 Lina 伤害/KO。

## 4. 数据模板

### 4.1 `roster.json` — character

```json
"nyra": {
  "name": "Nyra Steel",
  "class": "nyra",
  "stats": "nyra",
  "spawn": "player_spawn",
  "clips": "nyra_clips",
  "frame_size": "nyra_frame_size",
  "pivot": "nyra_pivot",
  "frames_dir": "nyra",
  "fallback": "Image/Character/nyra-steel-256.png"
}
```

### 4.2 `roster.json` — enemy

```json
"shooter": {
  "name": "Creepy Shooter",
  "class": "shooter",
  "stats": "shooter",
  "spawn": "shooter_spawn",
  "clips": "shooter_clips",
  "frame_size": "shooter_frame_size",
  "pivot": "shooter_pivot",
  "frames_dir": "shooter",
  "fallback": "Image/Enemy/creepy-shooter-256.png",
  "skill_slots": ["shoot_horizontal", "shoot_lockon", "roll_shoot", null],
  "separates": true,
  "decides_match": true
}
```

### 4.3 `stats.json`

```json
"nyra": {
  "hp": 100,
  "basic_atk": 20,
  "extra_atk": 0,
  "stage_body_width": 100,
  "move": {"walk": 260, "jump_v": 760, "gravity": 2200},
  "hurtbox": {"standing": [56, 210], "crouching": [56, 130]}
}
```

敌人若沿用 Warrior 式 AI，再补：

```json
"ai": {
  "attack_range": 160,
  "attack_cooldown": 0.9,
  "skill_gap": 0.9,
  "dash_range": 340,
  "dash_cooldown": 2.5,
  "throw_min_range": 180,
  "throw_range": 420,
  "throw_cooldown": 2.8
}
```

### 4.4 `attacks.json`

```json
"punch_r": {
  "basic_mult": 1.0,
  "extra_mult": 1.0,
  "duration": 0.25,
  "lunge": 18,
  "lunge_time": 0.08,
  "energy_gain": 15,
  "hitstun": 0.2,
  "hitstop": 0.06,
  "events": [
    {"t": 0.10, "until": 0.16, "type": "hitbox",
     "box": [30, -165, 66, 48], "knockback": 0}
  ]
}
```

- 伤害公式：`basic_atk * basic_mult + extra_atk * extra_mult`；事件里的 `"damage"` 会覆盖公式。
- `attack_id` 必须与 `animations.json` 的 clip 名一致（`AnimationPlayer.set_clip(attack_id)`）。
- 击飞：hitbox 事件加 `"launch": 760, "knock_up": 1.5`；霸体加 `"armor_until": 0.55`（需要类里 override `take_hit` 才生效）。

### 4.5 `animations.json`

```json
"nyra_frame_size": [256, 256],
"nyra_pivot": [128, 244],
"nyra_clips": {
  "idle": {
    "loop": true,
    "frames": ["idle/idle_00.png", "idle/idle_01.png"],
    "durations": [0.12, 0.12]
  },
  "hurt": {
    "loop": false,
    "frames": ["hurt/hurt_00.png", "hurt/hurt_01.png"],
    "durations": [0.10, 0.10]
  }
}
```

- 帧路径相对 `frames_dir`；`frames` 与 `durations` 数量必须一致。
- 至少准备：idle、walk、jump、hurt、KO；攻击 clip 按技能。
- 画布/pivot 可沿用 Lina 的 256×256 `(128,244)`，也可参考 Warrior 的 384×384 `(192,372)`；按素材实际身体尺寸决定。

## 5. 素材管线（有新材料时）

- canonical 源：`Image/Character/<name>.png` 或 `Image/Enemy/<name>.png`；**`Image/` 只读，不覆盖**。
- **每次生成图片前必读 `docs/IMAGE_GENERATION_RULES.md`**：检查身体部件前后层、持武器手/握姿、无穿模、角色尺寸不变；生成后按接触表逐项验收。
- 生成/导入流程、提示词、审批规则见 `docs/ASSET_PIPELINE.md`。
- 生成物：`assets/generated/raw/<id>/...`；导入 staged：`assets/generated/staged/<id>/...`；接触表：`assets/generated/contact_sheets/`；批准后才复制到 `assets/frames/<id>/<action>/`。
- 常用命令（参数按新角色画布调整）：

```text
py tools/import_frames.py --action idle --src assets/generated/raw/nyra/idle --out assets/generated/staged/nyra/idle --base assets/generated/base/nyra_side_base.png --body-height 210 --canvas 256 --pivot-x 128 --pivot-y 244 --expect 4
py tools/contact_sheet.py --action nyra_idle --frames assets/generated/staged/nyra/idle --out assets/generated/contact_sheets/nyra_idle_v1.png --durations 0.12,0.12,0.12,0.12
```

- 先把每个动作的接触表给用户审批；未批准帧不进入游戏。
- 如果复用现有帧，也要核对画布、pivot、身体高度和 clip 名；不要直接把 Lina/Warrior 的帧目录指给新角色而不做视觉检查。

## 6. 验收与 smoke 影响

### 6.1 现有 smoke 会被 roster 增长影响

`main.py` 的 `_smoke_test` 目前有以下硬编码预期，新增 roster 后必须改：

- `f7_cycle_ok = scene.enemy_id == "dummy"`：新增敌人后，F7 的下一个敌人可能不是 Dummy。
- `previous_character_ok` / `next_character_ok` 都断言 `character_id == "lina"`：新增可玩角色后，`[` / `]` 会真正切换，必须改为按 roster 顺序断言。
- `scene.set_character("lina")` 的 no-op 断言仍然有效。
- Phase A/B 仍以默认 Lina vs Warrior 为基线；新角色/敌人的测试加在 Phase B 之后或单独阶段。
- `warrior_missing_frames` 仍然检查 Warrior；新角色/敌人要增加 missing_frames 检查。

### 6.2 新增断言建议

- 新角色能构造、`F2` 显示正确 name/HP/resource、`[`/`]` 能切到并切回、切换后 AI 关闭/锁定关闭/B 保留。
- 新角色每个攻击的伤害/命中/冷却/动画 clip 与数据一致；lock-on 时起手面向敌人。
- 新敌人 F7 能切到；V/C/X/Z 槽位与 `skill_slots` 一致；未定义槽位 no-op；F2 显示槽位/冷却。
- 新敌人 AI 至少覆盖：接近、攻击、受击/KO、胜负（若 `decides_match`）。
- 新角色/敌人 `anim.missing_paths()` 为 0。

### 6.3 命令与验收

```bat
run.bat --smoke-test
```

- 所有字段 `True`，`missing_frames=0`，`warrior_missing_frames=0`，`exit=0`。
- 手动：F1 看判定，F2 看 roster/槽位/资源；F7、`[`/`]`、F8、F9、B 逐项过。
- 新素材需要接触表审批；未审批不进入游戏。
- `git status` 确认没有意外文件；不提交，除非用户明确要求。

## 7. 已知坑（务必检查）

- **类注册有两处**：`game/roster.py` 的 `FIGHTER_CLASSES` 和 `game/config.py` 的 `ROSTER_CLASSES`；漏一处会 config error 或 KeyError。
- `PLAYABLE_CLASSES` / `ANIMATED_CLASSES` 也要加；`characters` 里只能放 playable class。
- `spawn` key 必须以 `_spawn` 结尾，并存在于 `debug.json` 的 `stage`；否则 config 拒绝。
- `enemies` 的 `skill_slots` 必须正好 4 项；攻击 id 必须存在于 `attacks.json`。
- 有动画的 class 必须有 `clips` + `frame_size` + `pivot` + `frames_dir` + `fallback`；否则 config 拒绝。
- `config.REQUIRED_STATS` / `REQUIRED_ATTACKS` / `REQUIRED_CLIPS` 仍是 Lina/Warrior 的硬校验；新数据不会被这些列表自动要求，但 roster 校验会检查被引用的 stats/attacks/animation keys。新 clip 表的 `frames`/`durations` 数量目前没有通用校验，自己检查或补校验。
- `HUD` 只为 `energy`/`flame_time` 做属性保护；新角色如果使用不同资源，必须自己加 HUD，否则不会显示。
- 新 playable class 必须实现 `update(dt, input_state, target, scene)`；`scene.tick` 固定这样调用。
- 新 playable class 的 `start_attack` 如果想支持中键攻击锁定，要调用 `scene.face_target_if_locked(self, target)`。
- 新 enemy 如果要有霸体，必须在自己的 `take_hit` 里处理 `armor_until`（参考 Warrior）；基类 `Fighter` 不做。
- 新 enemy 如果要 F2 显示冷却，实现 `skill_remaining(attack_id)`；基类返回 0。
- 新 enemy 如果要 F8 切 AI，设置 `ai_enabled`；`set_enemy` 切换后会把它置 False。
- 新 enemy 如果需要身位分离/胜负，roster 里 `separates` / `decides_match` 设为 true；Dummy 两者都是 false。
- 新 projectile kind 必须同时改 `config.PROJECTILE_KINDS` 和 `scene.spawn_projectile_from_event`，否则会被当成 Q 波。
- `knock_up_gravity` 在 Fighter 子类里从 `combat` 读取；新角色/敌人如果会被击飞，记得设置。
- `AnimationPlayer` 帧路径相对 `frames_dir`；Lina 的 flame clip 路径带 `flame/` 前缀，新角色没有 flame 就不要写 `flame_clips`/`flame_offsets`。
- `F7` / `[` `]` 的顺序就是 `roster.json` 的插入顺序；新增条目会改变循环顺序，smoke 和文档要同步。
- `instruction.docx` 工作区版本可能已被修改；以当前工作区为准，并注意它是未提交状态。
- 不要用 pytest、不要写日志文件；验证只用 `run.bat --smoke-test` + F1/F2。

## 8. 文档同步

新增角色/敌人完成后更新：

- `README.md`：角色/敌人列表、操作、当前 scope、smoke 描述。
- `docs/DESIGN_DECISIONS.md`：新角色/敌人的数值、技能、AI、状态、HUD 规则。
- `docs/DEBUG.md`：新调试信息/槽位/资源。
- `docs/ASSET_PIPELINE.md`：如果新增帧目录/画布/pivot/生成流程。
- `PLAN.md`：顶部实施更新。
- `docs/NEXT_SESSION_*.md`：状态和下一步；必要时更新本文件。
- `instruction.docx`：只有用户明确要求时才改；不要自动改。

## 9. Definition of Done

- [ ] 用户确认了设计计划、数值、素材方案。
- [ ] 新 character 可被 `[` / `]` 选中并正常战斗；新 enemy 可被 F7 选中并正常 AI/受击/胜负。
- [ ] `V/C/X/Z` 对新敌人按 roster 的 4 个槽位工作；空槽 no-op；F2 正确显示。
- [ ] 新角色/敌人的动画/durations/pivot/fallback 正常，无缺帧。
- [ ] `run.bat --smoke-test` 全绿，新增断言覆盖新角色/敌人。
- [ ] F1/F2 手动检查通过；切换重置/AI 关闭/锁定关闭/B 保留正确。
- [ ] `Image/` 未被修改；没有 pytest/日志；没有未经要求的 commit。
- [ ] README / DESIGN_DECISIONS / DEBUG / PLAN / ASSET_PIPELINE 已同步。

## 10. 快速文件索引

| 路径 | 用途 |
|---|---|
| `game/data/roster.json` | 角色/敌人注册表；`characters` / `enemies` |
| `game/roster.py` | 类注册 + AnimationPlayer 构造 |
| `game/config.py` | 五份 JSON 加载/校验；class 列表、PROJECTILE_KINDS |
| `game/scene.py` | tick、切换、技能槽、调试键、绘制顺序 |
| `game/fighter.py` | Fighter 基类、状态、伤害反应、`force_skill` |
| `game/combat.py` | AttackRuntime、伤害公式、命中/击飞 |
| `game/animation.py` | 帧动画、翻转、pivot、缓存 |
| `game/lina.py` / `game/warrior.py` / `game/dummy.py` | 三个参考实现 |
| `game/data/stats.json` | HP/ATK/移动/受击盒/AI/combat 参数 |
| `game/data/attacks.json` | 招式、倍率、命中窗口、事件 |
| `game/data/animations.json` | clip 表、帧路径、durations、画布/pivot |
| `game/data/debug.json` | 舞台、出生点、默认 roster |
| `docs/ASSET_PIPELINE.md` | 素材生成/导入/接触表审批 |
| `main.py` | `_smoke_test`；新增 roster 后必须扩展 |
