# Special Skills — 最终实现（1 / 2 / 3 / 4 特殊技能）

> 日期：2026-11-09（最终实现 2026-11-10）
> 状态：**已实现，测试 sandbox 最终版本。** 本文保留为交接/确认记录。
>
> 基线：分支 `witch-eira`，HEAD `7e42390`；最终版本提交在
> `sandbox-final-special-skills`。
>
> 权威规格：`instruction.docx` 的操作设置段（`1 Special Skill` … `4 Special Skill`）和
> **Special Skill** 商品段（Sacred Shield / Purity Seal / Fury Unbound / Vitality Tonic）。
> 本文只摘录，**绝不修改 docx**。
>
> 本轮只做“实现”：四个特殊技能 + 每局各一次的次数限制 + 简单程序化特效。不做商店、
> 金币、购买、存档或等级系统；没有新立绘/图标要求。

---

## 0. 给下一个 session 的开场 prompt（可直接复制）

```text
读取 docs/NEXT_SESSION_SPECIAL_SKILLS.md、instruction.docx 的 Special Skill 段、AGENTS.md、
README.md、docs/DESIGN_DECISIONS.md、docs/DEBUG.md、docs/ASSET_PIPELINE.md；
先运行 .venv/Scripts/python.exe main.py --smoke-test，确认基线 exit 0。

本轮实现玩家侧的 4 个 special skills（键 1/2/3/4），每个一局只能使用一次；
先按 §6 的 Q1–Q10 逐条 grill 我，我确认后回填 §7 再实施。未确认前不要改代码/JSON。
主工作是技能效果与判定，允许用现有 RingBurstFx/粒子做简单特效，不生成新美术。

约束：不修改 instruction.docx、Image/、UI Resources/、sketch/、其他角色/敌人、背景/BGM；
不用 pytest；验证用 --smoke-test、F1/F2/F6/F7/F8/F9 和游戏内预览。
不要 commit/push，除非我明确要求；文档更新等实现和验证完成后再按 AGENTS.md 问一次。
```

---

## 0.1 最终实现（2026-11-10）

- **代码**：`game/special_skills.py`（scene-owned 控制器）、`game/data/special_skills.json`
  （schema 校验）、`game/status.py`（负面清除/免疫、Fury 倍率）、`game/combat.py`（三个伤害
  结算入口）、`game/fighter.py`（`take_hit`/`apply_dot` 兜底、`clear_hurt_visual`）、
  `game/hazards.py`（冰球命中 FX 抑制）、`game/scene.py`（金色格挡环/清空）、
  `game/hud.py`、`game/debug.py`、`game/input.py`，以及 Nyra/Rhea/Eira 的 `take_hit` 守卫。
- **特效**：V5 序列帧（Sacred Shield / Purity Seal 为 v4，Fury Unbound 为 v5，
  Vitality Tonic 为 v3；每技能 6 帧、320×340、脚底锚点 160,278）已复制到
  `assets/frames/special_skills/`。Shield/Purity/Fury 循环并跟随玩家，Tonic 单次播放；
  源帧与生成代码保留在
  `assets/generated/contact_sheets/special_skills_ingame_v5/`。
- **Shield 视觉规则**：被挡命中不播放 hurt 动画、不闪白；hitstun/knockback/HURT/
  攻击取消/hitstop 仍保留；金色格挡环照常播放。
- **验证**：`main.py --smoke-test` exit 0；Phase L 的 `special_fx_missing=0`，
  `special_skills_present`、`special_input_ok`、`special_shield_ok`、`special_purity_ok`、
  `special_fury_ok`、`special_heal_ok`、`special_once_ok`、`special_switch_ok`、
  `special_reset_ok`、`special_ui_ok` 全部 True。
- **最终版本**：本测试 sandbox 到此封版，不再新增角色/敌人；Lina Shadowtide 不实现
  （仅保留 `Image/Enemy/` 海报素材）。

---

## 1. 本轮范围

### 1.1 做

- 四个**所有可玩角色共享**的特殊技能，局内用数字键 **1 / 2 / 3 / 4** 触发。
- **次数限制**：每个技能每局只能使用一次。次数在整场 match 内有效；F9 / R / 切换角色 /
  重新开始后恢复。
- 技能效果（按 `instruction.docx` Special Skill 段）：
  1. **Sacred Shield**：2 秒内免疫一切伤害。
  2. **Purity Seal**：解除当前全部负面效果，并在 3 秒内免疫一切负面效果。
  3. **Fury Unbound**：5 秒内造成的伤害翻倍。
  4. **Vitality Tonic**：立即恢复 `level*50 + 35%` 最大生命值。
- 简单的程序化特效（不新增美术）：护盾光环、净化白光、狂暴红橙光、治疗绿光。
- HUD 四个技能格（按键 + 名称 + 已使用状态）；F2 调试行；smoke 测试。

### 1.2 不做

- 商店、金币、购买、Special Item、存档/跨局保留。
- 等级系统。Vitality Tonic 的 `level` 先按 **1** 处理（`50 + 35%`），见 Q3。
- 新立绘、技能图标、音效、动画帧。
- 敌人使用 special skills；AI 不参与。
- 修改 `instruction.docx`、已有角色技能、已有 HUD 布局以外的大改。

---

## 2. 当前代码状态与接入点

| 位置 | 现状 | 需要做什么 |
| --- | --- | --- |
| `game/input.py` | `InputState.KEY_ACTIONS` 只映射 A/D/W/S、Shift、Space、Q、E；数字键 1–4 空闲；`BUFFERED_KEYS = {"jump","q","e"}` | 增加 `K_1..K_4 → special_1..special_4`，加入 `BUFFERED_KEYS` |
| `game/fighter.py` | `Fighter` 有 `statuses`、`hp/max_hp`、`invincible`、`take_hit`、`reset_common` | 玩家侧挂 `SpecialSkillState`；reset 时清空 used/active |
| `game/status.py` | `StatusSet` 支持 control/slow 免疫和 vulnerable、poison；没有“负面效果免疫/清除” | 增加 `NEGATIVE_EFFECTS`、`cleanse_negative()`、`negative_immune()`，在 `add/add_poison/add_slow/add_vulnerable/refresh_poison/extend_poison` 前置检查 |
| `game/combat.py` | `attack_damage`、`resolve_hit`、`resolve_projectile_hit`、`apply_direct_damage` 是全部伤害入口 | 增加攻击方伤害倍率（Fury）与受击方伤害免疫（Sacred Shield）检查 |
| `game/hud.py` | 已有 Q/E 冷却徽章、E 选区提示 | 加四个 special skill 徽章/提示；已使用置灰 |
| `game/debug.py` | F2 已有角色/敌人/冷却行 | 加 `SPECIAL 1..4 READY/USED` 和剩余持续时间 |
| `game/data/*.json` | 五个数据文件；`JsonStore` 载入并校验 | 推荐新增 `special_skills.json`（见 §3.1） |
| `main.py` | 固定步长、事件循环、smoke Phase A–K | 输入事件、HUD/F2 验证、新增 smoke Phase（如 Phase L） |
| 可玩角色 | Lina / Nyra / Rhea / Eira，均继承 `Fighter` | 四个技能共享；不区分角色 |

---

## 3. 设计

### 3.1 数据（推荐新文件）

新增 `game/data/special_skills.json`：

```json
{
  "schema": 1,
  "skills": [
    {
      "id": "sacred_shield",
      "key": 1,
      "name": "Sacred Shield",
      "type": "damage_immunity",
      "duration": 2.0,
      "vfx": "shield"
    },
    {
      "id": "purity_seal",
      "key": 2,
      "name": "Purity Seal",
      "type": "cleanse_immunity",
      "duration": 3.0,
      "vfx": "purity"
    },
    {
      "id": "fury_unbound",
      "key": 3,
      "name": "Fury Unbound",
      "type": "damage_double",
      "duration": 5.0,
      "damage_multiplier": 2.0,
      "vfx": "fury"
    },
    {
      "id": "vitality_tonic",
      "key": 4,
      "name": "Vitality Tonic",
      "type": "heal",
      "heal_flat_per_level": 50.0,
      "heal_max_hp_pct": 0.35,
      "vfx": "heal"
    }
  ]
}
```

- 需要扩展 `JsonStore`（载入 + F5 reload + 失败保留 last-good）、`config.py` 校验
  （四个 id、key 1–4、type、duration/heal 字段）。
- 如果不想加第六个文件，可把同样结构放进 `stats.json` 顶层的 `special_skills` 块；
  **默认按新文件实施**，便于以后商店/购买字段扩展。

### 3.2 运行时

新增 `game/special_skills.py`：

- `SpecialSkillState`（挂在玩家 `Fighter` 上，或由 `ArenaScene` 持有并指向 player）：
  - `used: set[str]`
  - `active: dict[str, float]`（剩余时间；也可直接用 status，二选一）
  - `level: int = 1`
  - `reset()`：清空 used/active；由 `Fighter.reset_common` 或各角色的 `reset()` 调用。
- `try_use(slot_index, scene)`：
  1. 玩家存活、非 KO、非 control-locked（是否允许 hitstun/攀爬见 Q1/Q9）；
  2. 该技能 `used` 未使用；
  3. 标记 used，应用效果，播放简单 VFX，写 HUD toast；
  4. 返回是否成功；重复按键/已使用返回 False，不消耗。
- 四个效果的具体落点：

| 技能 | 实现建议 |
| --- | --- |
| Sacred Shield | 加 `sacred_shield` 状态 2.0s；所有伤害入口检查 `target.is_damage_immune()`（含 status 或控制器的 2s 计时），免疫期间不扣血、不触发 hit_fx/hitstop/受击闪烁 |
| Purity Seal | 激活时 `statuses.cleanse_negative()` 清掉 burn/poison/slow/freeze/stun/vulnerable/knock_up 等；加 `purity_seal` 状态 3.0s；`StatusSet` 的所有负面添加接口在状态存在时直接拒绝 |
| Fury Unbound | 加 `fury_unbound` 状态 5.0s；在 `resolve_hit` / `resolve_projectile_hit` / `apply_direct_damage` 计算最终伤害时乘以 2.0（在冻结/毒等加成之后、目标减伤/易伤之前；见 Q4） |
| Vitality Tonic | 立即 `hp = min(max_hp, hp + level*50 + 0.35*max_hp)`，level 暂为 1；不产生持续状态 |

- 次数限制的边界：一局内使用后 `used` 保持，直到 `scene.reset()` / F9 / R / 角色切换；
  切换角色时旧角色的 used 是否保留？建议**整场共享**还是**按角色**见 Q6。
- 技能没有冷却、没有 energy 消耗；唯一的限制是每局一次。
- 不打断当前攻击/移动；若允许在攻击中使用，效果立即生效（见 Q1）。
- KO 后不可使用；玩家死亡时残留的 active 状态随 reset 清除。

### 3.3 伤害与状态接入

- `game/status.py`：
  - 定义 `NEGATIVE_EFFECTS = ("burn","poison","slow","freeze","stun","knock_up","vulnerable")`
    （`knockback` 是即时参数，不是 status）。
  - `cleanse_negative()`：删除上述 statuses 和所有 `poisons`；保留 buff（damage_reduction 等）。
  - `negative_immune()`：`self.has("purity_seal")`。
  - 在 `add`、`add_poison`、`add_slow`、`add_vulnerable`、`extend_poison`、`refresh_poison`
    开头检查；`add` 里的 `super_armor` 逻辑保留。
  - 注意：`cleanse_negative` 不应删除 `sacred_shield`/`fury_unbound`/`purity_seal` 自身。
- `game/combat.py`：
  - `damage_taken_immune(target)`：`target.statuses.has("sacred_shield")` 或
    `target.is_damage_immune()`；在 `resolve_hit`/`resolve_projectile_hit`/`apply_direct_damage`
    入口返回 0，不触发后续 FX/hitstop/status。
  - `damage_dealt_multiplier(attacker)`：`2.0` if `attacker.statuses.has("fury_unbound")` else
    `1.0`；在三个伤害入口统一乘算。
  - 顺序：基础/额外 → 冻结/毒等加成 → Fury ×2 → 目标 damage_reduction → 目标 vulnerable。
    （Fury 是否也放大毒/燃烧的持续伤害？建议**只放大直接命中伤害**，见 Q4。）
- `Fighter.take_hit`：可保留原逻辑；免疫最好在三个 resolve 入口提前返回，避免
  `hit_fx`/`hitstop`/受击闪白。若还有直接调用 `take_hit` 的路径，也在 `take_hit` 里加兜底。

### 3.4 输入与 HUD

- `game/input.py`：
  - `KEY_ACTIONS[pygame.K_1] = "special_1"` … `K_4`；
  - `BUFFERED_KEYS` 加入 `special_1..4`（或直接事件触发，二选一；建议 buffer，避免
    按键当 tick 被攻击状态吞掉）。
- 玩家 update / `_handle_control`：每个 tick 消费 `special_1..4`；调用
  `special_skills.try_use()`；成功后播放 FX。不要把它们塞进普通攻击队列（避免被
  punch/kick 队列顶掉）。
- HUD（`game/hud.py`）：
  - 在左上或 Q/E 徽章旁显示四格：`1 Sacred Shield`、`2 Purity Seal`、`3 Fury Unbound`、
    `4 Vitality Tonic`；已使用置灰并画删除线/`USED`；激活中显示剩余秒数。
  - 本次不要求图标；文本徽章即可（Q7）。
- F2（`game/debug.py`）：
  - `SPECIAL 1 SACRED READY/USED 1.2s` … 四行或两行压缩；
  - 显示当前 `used` 列表、`level`、active 剩余。
- 简单提示：技能激活时在玩家上方显示 0.8s 的名称文本；可选。

### 3.5 简单特效（不新增美术）

> **最终实现（2026-11-10）**：本节程序化方案为历史记录。实际使用 V5 序列帧
> （运行时 `assets/frames/special_skills/`，源帧/生成代码在
> `assets/generated/contact_sheets/special_skills_ingame_v5/`）：Shield/Purity/Fury
> 循环跟随玩家，Tonic 单次播放；格挡另有金色环。程序化光环/施放环已移除。

用现有 `RingBurstFx` / `Particles` / 一个跟随玩家的简单 alpha 圆环实现：

- Sacred Shield：金色 RingBurstFx（start 12 → end 60，life 0.25）＋ 玩家身上 2s 的
  半透明金色圆环（跟随，58% alpha 左右）。
- Purity Seal：白/青 RingBurstFx ＋ 向上粒子 8–12 个；3s 内角色边缘淡青色描边可选。
- Fury Unbound：红/橙 RingBurstFx ＋ 火焰色粒子；5s 内脚下红橙光环可选。
- Vitality Tonic：绿色 RingBurstFx ＋ 向上绿色粒子，立即结算。

所有特效只做视觉，不参与判定；不新增 `assets/frames/` 文件。持续光环可以放在
`scene._draw_status_fx`（status 存在时绘制）或 `game/fx.py` 的轻量 `PlayerAuraFx`。

---

## 4. 实施顺序

1. **基线**：`main.py --smoke-test` exit 0；确认工作区干净（只有 tmp/zoom）。
2. **Grill**：按 §6 的 Q1–Q10 逐条确认，回填 §7。
3. **数据层**：`special_skills.json` + `JsonStore`/`config.py` 校验 + F5 reload。
4. **状态/伤害层**：`status.py` 的负面免疫/净化；`combat.py` 的伤害免疫/翻倍；先跑旧 smoke。
5. **控制器**：`special_skills.py` + 玩家挂载 + reset；`input.py` 1–4 映射。
6. **表现层**：HUD 四格、F2 行、四个简单 FX、提示文本。
7. **Smoke**：新增 Phase（建议 Phase L，排在 Eira Phase K 之后），覆盖 §5；加入最终
   conjunction 和输出行。
8. **手动验收**：F1/F2/F9、F7 切角色、R 重开；每个技能一次限制与持续时间。
9. **预览**：生成 `assets/generated/contact_sheets/special_skills_ingame_v1/` 截图
   （四个技能各一张 + F2 + used 状态）；用 headless 工具。
10. **报告**：给用户看结果；按 AGENTS.md 再问一次是否写入文档；未明确要求不 commit。

---

## 5. Smoke 检查清单（建议 Phase L）

- **加载**：`special_skills` 四条，key 1–4，type 正确；起始 `used` 全空。
- **Sacred Shield**：使用后 `used` 含 `sacred_shield`；2s 内已知攻击伤害为 0、无受击
  flash/hitstop；2s 后同攻击恢复伤害；再按 1 不重复触发。
- **Purity Seal**：先施加 poison + slow + vulnerable（可加 freeze），使用后全部清除；
  3s 内再次施加全部被拒绝；3s 后恢复；伤害仍可造成。
- **Fury Unbound**：Lina punch 20 → 40（5s 内），过期回 20；投射物与 hazard 的直接伤害
  同样翻倍（按 Q4 的结论）；再按 3 无效。
- **Vitality Tonic**：玩家 HP 设 40；使用后 `min(max, 40 + 50 + 0.35*max)`；满血时不
  overflow；再按 4 无效。
- **次数/重置**：四个都用过后全 used；`scene.reset()` / F9 / R / 切角色后恢复（按 Q6）。
- **HUD/F2**：四格 READY/USED 正确；active 剩余时间显示。
- 旧 Phase A–K 全 flag 保持 true；最终 exit 0；`special_skills` 相关新 flag 全部 true。

建议新 flag：`special_skills_present`、`special_shield_ok`、`special_purity_ok`、
`special_fury_ok`、`special_heal_ok`、`special_once_ok`、`special_reset_ok`（可按实现拆分）。

---

## 6. 待确认问题（★ 必须先确认；○ 无异议按建议值）

- **Q1 ★** 使用时机：空中、攻击中、受击硬直中能否使用？
  - 建议：存活且非 KO、非 control-locked（冻结/眩晕/硬直）即可；不打断攻击/移动；
    使用后没有施法硬直。
- **Q2 ★** Purity Seal 的“负面效果”是否包括 hitstun/knockback？
  - 建议：包括所有 status（poison/burn/slow/freeze/stun/knock_up/vulnerable），
    3s 内也免疫这些；伤害仍照常结算（不等同于 Sacred Shield）。
- **Q3 ★** Vitality Tonic 的 `level`：当前没有等级系统。
  - 建议：先按 `level = 1`，即 `50 + 35% max HP`；以后有等级再从数据读取。
- **Q4 ★** Fury Unbound 的翻倍范围：
  - 建议：只放大**直接命中伤害**（近战、投射物、hazard），在命中结算时判断；
    不放大 poison/burn 的持续伤害。若希望持续伤害也翻倍请说明。
- **Q5 ○** Sacred Shield 只免疫伤害、不免疫负面状态？建议：是。
- **Q6 ★** 次数归属：四个技能是**整场共享**一套（换角色仍已使用），还是**每个角色各一套**？
  - 建议：整场共享一套（更符合“每局一次”的消耗品定位）；切换角色不恢复。
- **Q7 ○** 本次 HUD 用文本徽章，不制作图标？建议：是。
- **Q8 ○** 数据放新文件 `special_skills.json` 还是 `stats.json`？建议：新文件。
- **Q9 ○** 攀爬中能否使用？建议：不能（与攀爬状态互斥）。
- **Q10 ○** 是否允许某个技能存在时重复触发刷新持续时间？建议：不能，每局一次，
  已激活时再按无效、不刷新。

---

## 7. 确认结果（下一个 session 回填）

| 问题 | 用户答案 |
| --- | --- |
| Q1 | 任意存活状态（HP>0）可用：空中、攻击中、受击硬直/冻结/眩晕中、Eira E 施法中、攀爬中（不脱梯）；KO 或 match_over 时不可用。 |
| Q2 | 只清除/免疫 status（burn/poison/slow/freeze/stun/knock_up/vulnerable）；伤害与 hitstun/knockback 照常；buff（super_armor/damage_reduction 及三个 special status）保留。 |
| Q3 | level=1，即 50 + 35% max HP。 |
| Q4 | 只翻倍直接命中（近战/投射物/直接接触 hazard）；在 freeze/poison 加成之后、目标减伤/易伤之前结算；不翻倍 DoT，也不翻倍 mark 引爆。 |
| Q5 | 免疫一切 HP 伤害；被挡的命中仍完整硬直（hitstun/knockback/HURT/攻击取消/hitstop），on-hit status 仍生效；DoT 被挡；hazard 的 status 仍生效。玩家自身 super armor 仍抑制硬直。**Shield 期间不播放 hurt 动画、不闪白**；金色格挡环替代普通红色命中特效。 |
| Q6 | 整场共享一套；切换角色不恢复；F9/R 与 F5 rebuild 恢复。切换角色时 active 效果随旧身体丢弃，used 保留。 |
| Q7 | 文本徽章：左面板下方一行四格；F2 显示全名。 |
| Q8 | 新文件 `game/data/special_skills.json`。 |
| Q9 | 攀爬中可用，且不脱梯。 |
| Q10 | 每局一次；重复按键无效、不刷新。 |

补充确认：

- Vitality Tonic 满血时：**不消耗**次数，玩家头顶显示约 1.5s 的
  `You are at full HP. You do not need to heal.`。
- Sacred Shield 与玩家自身 super armor 同时存在时，armor 仍抑制硬直；Shield 只清零
  HP 损失并播放金色格挡。
- 被格挡的命中仍会触发 on-hit status（burn/poison/stun/marks），但不播放 hurt 动画、
  不闪白；普通红色命中特效替换为金色格挡环，hitstop 仍生效。
- 切换角色时 active 效果随旧角色丢弃，`used` 保留。

---

## 8. 文件与代码导航

- 输入：`game/input.py`（`InputState.KEY_ACTIONS`、`BUFFERED_KEYS`）
- 玩家：`game/fighter.py`（`Fighter`、`take_hit`、`reset_common`）；各角色 `game/lina.py`、
  `nyra.py`、`rhea.py`、`eira.py`
- 状态：`game/status.py`（`StatusSet`、`IMMUNE_EFFECTS`、`add_poison`、`add_slow`、
  `add_vulnerable`）
- 伤害：`game/combat.py`（`attack_damage`、`resolve_hit`、`resolve_projectile_hit`、
  `apply_direct_damage`）
- HUD/调试：`game/hud.py`、`game/debug.py`
- 数据：`game/data/` + `game/config.py` 的 `JsonStore` 校验；`main.py` 的 `--smoke-test`
- 现成特效：`game/fx.py`（`RingBurstFx`、`SpriteStripFx`）、`scene.particles`
- 现有预览工具可仿照：`tools/preview_witch_eira.py`

---

## 9. 验收清单

- [ ] 1 / 2 / 3 / 4 在局内触发对应技能，每个一局一次，重复按键无效。
- [ ] Sacred Shield：2s 伤害免疫，免疫期间无扣血/受击反馈。
- [ ] Purity Seal：立即清除全部负面，3s 内免疫新的负面；伤害仍生效。
- [ ] Fury Unbound：5s 内直接伤害 ×2，过期恢复。
- [ ] Vitality Tonic：恢复 `level*50 + 35% max HP`，满血不溢出。
- [ ] HUD 四格与 F2 状态正确；已使用可见。
- [ ] 简单特效正常、不参与判定。
- [ ] F9 / R / 切换角色后次数和 active 状态正确重置。
- [ ] 旧 smoke Phase A–K 全 true；新增 Phase L exit 0。
- [ ] 未修改 instruction.docx；未新增美术；未 commit（除非用户要求）。
