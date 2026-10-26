# Bat Side-View Animation Design

> 日期：2026-10-25
> 状态：**动画设计已批准，14 帧已安装到 `assets/frames/bat/`**。2026-10-26 已完成代码/数值接入（`game/bat.py`、`SonicWave`、数据和 smoke；最终沙盒值：atk 10、5 只、飞行 40–420、sonic-only 随机、俯冲高度门槛）；14 帧未改动。
> 范围：只覆盖 Bat 角色动画与素材；不包含 `game/` 代码、`game/data/` 数值、默认阵容或声波弹体实现。
> 下阶段代码/数据 handoff：`docs/NEXT_SESSION_BAT_FULL.md`。

## 1. 最终决策

| 项 | 结论 |
|---|---|
| 基准 | **side-view base C（流线滑翔）**，`assets/generated/base/bat_side_base.png` |
| 朝向 | 右向 3/4 侧视；运行时按 `facing` 翻转，不生成左向帧 |
| 源画布 | **384×384** |
| 运行时画布 | **192×192**（`animations.json` 加载时 384→192） |
| pivot | 源 `(230, 285)`；运行时 `(115, 143)`；镜像 pivot x = `77` |
| hurtbox（建议） | **100×66**，以 `x` 为中心、底边在 `y`；代码阶段最终确认 |
| 唯一帧数 | **14**：wing 4 + dive 3 + sonic 3 + hurt 1 + stun 1 + ko 2 |
| 身体基准 | 采用动作帧的较大身体；base C 作为造型/比例参考，不要求像素尺寸完全一致 |
| 过渡帧 | `wing_00_01` = **v8 B scaled 1.15×**；动作幅度 35–45% 翼尖下压 |
| 翼型规则 | 白骨数量/骨架/白爪布局必须与 `wing_00 B` 一致；禁止新增左下白骨 |
| stun | 空中僵直下垂、不掉落；**v3 A**（自然闭眼、放松表情）；1 帧保持 |
| KO | 空中瘫软 → 落地瘫倒；2 帧，代码落地时保持/切换 |
| 声波锁定 | 只锁 **0.65s 施法动作**；弹体飞行期间 Bat 恢复飞行 |
| 镜像 | 全 14 帧已镜像检查；镜像 pivot 源 `(154,285)` / 运行时 `(77,143)` |

## 2. 几何与坐标

side base C 的源图（1024）经 `tools/import_bat_side_frames.py` 归一化：

```text
base bbox = (40, 70, 862, 665), width 822
scale = 256 / 822 = 0.31144
源帧 384×384；全剪影约 256×185
pivot = (230, 285) 源 / (115, 143) 运行时
镜像 pivot = (154, 285) 源 / (77, 143) 运行时
```

- 运行时 192 画布下，角色翼展约 128px，身体/头部约 60px 高。
- 动作帧允许比 base C 大 10–15%；`wing_00_01` 已做 1.15× 身体归一化，避免过渡帧缩小。
- hurtbox 建议 `100×66`；以 pivot x 为中心，底边在 pivot y。是否收紧到 `92×60` 在代码阶段确认。

## 3. 14 帧集合

| clip | 帧文件 | 时长 | 循环 | 说明 |
|---|---|---:|---|---|
| `idle` | `wing/wing_00.png`, `wing/wing_00_01.png`, `wing/wing_01.png`, `wing/wing_02.png`, `wing/wing_01.png`, `wing/wing_00_01.png` | 0.22×6 | 是 | 乒乓式慢挥翅；复用 4 张共享振翅图 |
| `fly` | `wing/wing_00.png`, `wing/wing_00_01.png`, `wing/wing_01.png`, `wing/wing_02.png` | 0.10×4 | 是 | 快速循环 |
| `bat_dive` | `bat_dive/bat_dive_00..02.png` | 0.12 / 0.22 / 0.41 | 否 | 总 0.75s；命中窗约 t=0.12–0.34 |
| `bat_sonic` | `bat_sonic/bat_sonic_00..02.png` | 0.10 / 0.30 / 0.25 | 否 | 总 0.65s；弹体 t=0.24 从嘴部生成 |
| `hurt` | `hurt/hurt_00.png` | 0.30 | 否 | 炸翅后仰 |
| `stun` | `stun/stun_00.png` | 0.30 | 否 | 单帧保持到 stun 结束 |
| `ko` | `ko/ko_00.png`, `ko/ko_01.png` | 0.35 / 0.35 | 否 | 空中瘫软 → 落地瘫倒；末帧保持 |

### 共享振翅图

| 文件 | 姿势 | 备注 |
|---|---|---|
| `wing_00` | 翅膀高举（上挥顶点），身体略下沉 | 翼型/白骨基准 |
| `wing_00_01` | 翼尖下压 35–45%，水平中段 | v8 B ×1.15；不新增左下白骨 |
| `wing_01` | 翅膀竖直/与身体齐平 | 下压中段 |
| `wing_02` | 翅膀完全下压/收拢 | 下挥底点 |

### 逐帧要点

- `wing_00`：上挥顶点；近翼在身体前、远翼在后；耳直立、闭嘴。
- `wing_00_01`：从 00 向 01 的中间帧；白骨/骨架与 00 一致；身体尺寸已归一化。
- `wing_01`：翅膀竖直/齐平；身体回到中性高度。
- `wing_02`：翅膀下压收拢；身体略上浮。
- `bat_dive_00`：蓄力；缩身、翅膀后收、爪收、闭嘴、眼眯。
- `bat_dive_01`：俯冲命中；翅膀后掠、双爪前伸、张嘴露獠牙。
- `bat_dive_02`：制动恢复；翅膀张开刹车、身体拉回、闭嘴。
- `bat_sonic_00`：吸气；胸腹鼓起、嘴闭、耳前倾、眼眯、翅膀展开。
- `bat_sonic_01`：释放；嘴大张、獠牙/口腔清晰、翅膀稳定展开；无烘焙声波环。
- `bat_sonic_02`：收势；闭嘴、脸颊回落、翅膀回收。
- `hurt_00`：受击后仰；翅膀外炸、头上抬、张嘴、眼挤紧；无血/无冲击线。
- `stun_00`：空中僵直下垂；翅膀半收、头前垂、自然闭眼、嘴微张；无烘焙星星。
- `ko_00`：空中瘫软；翅膀收拢、头下垂、身体翻滚、闭眼。
- `ko_01`：落地瘫倒；身体伏地、翅膀平摊、头前垂；全剪影底边贴地。

## 4. 翼型与过渡规则

1. 所有动作帧的**白骨数量、骨架结构、白爪位置**以 `wing_00 B` 为基准；禁止新增/复制/移动白骨。
2. 过渡帧只允许小幅改变翼尖角度；不得为了幅度把翼根/骨架重新设计。
3. v8 B 的原始输出比相邻帧小，已做 **1.15× 身体归一化**（目标宽 294 源 px），这是管线内的比例归一化，不是局部修图。
4. 若后续动作帧出现身体明显偏大/偏小，优先用同一方法做一次性身体归一化，并在 contact sheet 复核。
5. 镜像版本由 `FLIP_LEFT_RIGHT` 生成；镜像 pivot 用 `384 - 230 = 154` 源 / `77` 运行时。

## 5. 素材与管线

### 已批准基准
- `assets/generated/base/bat_side_base.png`（side base C，1024）
- `assets/generated/base/candidates_bat/...`（A/B/C/D 候选，保留版本）
- `assets/generated/staged/bat/reference/side_base_384.png`（384 参考）

### 最终 staged 帧
- `assets/generated/staged/bat/side_final/wing/`
- `assets/generated/staged/bat/side_final/bat_dive/`
- `assets/generated/staged/bat/side_final/bat_sonic/`
- `assets/generated/staged/bat/side_final/hurt/`
- `assets/generated/staged/bat/side_final/stun/`
- `assets/generated/staged/bat/side_final/ko/`
- 镜像：`assets/generated/staged/bat/side_final_mirror/`

### 运行时帧（已安装）
```text
assets/frames/bat/wing/wing_00.png
assets/frames/bat/wing/wing_00_01.png
assets/frames/bat/wing/wing_01.png
assets/frames/bat/wing/wing_02.png
assets/frames/bat/bat_dive/bat_dive_00..02.png
assets/frames/bat/bat_sonic/bat_sonic_00..02.png
assets/frames/bat/hurt/hurt_00.png
assets/frames/bat/stun/stun_00.png
assets/frames/bat/ko/ko_00..01.png
```

### 工具
- `tools/import_bat_side_frames.py`：固定比例 + 脚底/身体前偏移对齐；超出画布标记 `FIT`，不裁翼。
- `tools/contact_sheet_grid.py`：支持多行/多列与逐格 pivot，用于镜像与全量表。
- `tools/preview_bat_side_wing.py`：idle/fly 4 帧循环 GIF（审批用）。
- `tools/preview_bat_side_clips.py`：dive / sonic / hurt-stun-ko GIF（审批用）。
- 这些 GIF 只作审批预览，不进入游戏。

### 审批产物
- `assets/generated/contact_sheets/bat_v1/bat_side_full_v1.png`（14 帧 + 镜像）
- `assets/generated/contact_sheets/bat_v1/bat_side_keyposes_selected_v9.png`
- `assets/generated/contact_sheets/bat_v1/bat_side_keyposes_mirror_v9.png`
- `assets/generated/contact_sheets/bat_v1/bat_side_wing_*_v9.gif`
- `assets/generated/contact_sheets/bat_v1/bat_side_bat_*_v2.gif`
- `assets/generated/contact_sheets/bat_v1/bat_side_hurt_stun_final.png`

## 6. 审批记录

| 日期 | 决策 |
|---|---|
| 2026-10-25 | 先做角色动画，动画批准后再做代码/数值 |
| 2026-10-25 | 改为 side-view base，4 候选（A/B/C/D）；选定 **C 流线滑翔** |
| 2026-10-25 | 选中 `wing_00 B`、`wing_01 B`、`wing_02 A`、`dive_01 B`、`sonic_01 A` |
| 2026-10-25 | 接受动作帧较大身体；镜像通过 |
| 2026-10-25 | wing 00→01 过渡：v6 太接近 00；v8 B（35–45% 下压）×1.15 身体归一化通过 |
| 2026-10-25 | 放弃双半帧 t01 设计；最终回到单过渡帧 |
| 2026-10-25 | stun v1 太警觉、v2 眼型奇怪；**v3 A 自然闭眼**通过 |
| 2026-10-25 | 14 帧最终通过，安装到 `assets/frames/bat/` |

## 7. 被取代 / 保留的版本

以下版本保留在 `assets/generated/` 以便追溯，但**不进入运行时**：
- 正面/微侧 128 方案、正面 key poses 与 dive 对比（已被 side-view 方案取代）。
- `wing_00_01` 的 v3/v4/v5/v6 过渡候选；v6 太接近 00；v3/v4/v5 翼型/白骨不合格。
- 双半帧 t01 A/B（水平滑翔感，未采用）。
- stun v1（警觉、FIT）与 v2（眼型奇怪）；最终用 v3 A。

## 8. 后续代码/数值工作（2026-10-26 已接入）

已完成：

- `game/bat.py`：自由飞行、standoff AI、俯冲、0.65s 声波施法锁定、2s/10s 每实例冷却、hurt/stun 空中保持、KO 落地帧切换、reset/facing。
- `game/projectile.py::SonicWave`：去程/回程、左右墙/顶部/地面/真实 block 矩形反弹、命中一次、穿过玩家、追踪 owner 当前位置、owner 死亡 0.5s、超时/泄漏上限。
- `game/data/stats.json`、`attacks.json`、`animations.json`、`roster.json`、`debug.json` 的 bat 条目；默认对局 **5 Bats**（`count: 5`，`spawn_offsets` + `spawn_heights`）。
- `game/config.py`、`game/roster.py`、`game/scene.py`（飞行生成/高度、sonic 分支、cast/impact/dive-hit FX）、`main.py` smoke。
- 声波程序化 **Wi-Fi 三层弧 + 发射点 + 拖尾**；前向圆 hitbox（+8px / r24）；俯冲命中 FX。
- 5 只编组：独立冷却、`bat_group_*` smoke、sonic-only 随机错峰、俯冲高度门槛。
- `README.md`、`docs/DESIGN_DECISIONS.md`、`docs/DEBUG.md`、`docs/ASSET_PIPELINE.md` 的代码相关更新。

仍待：

- 5 只 Bat 的实际平衡/手感（atk 10、冷却、巡航高度、sonic 随机概率仍可调）。
- Bat Cave 背景（默认不接入）。

## 9. 验证

- 安装后 `assets/frames/bat/` 共 **14** 个 PNG。
- `.venv/Scripts/python.exe main.py --smoke-test` → **exit 0**；Bat 与现有 flags 全部通过。
- 游戏默认对局生成 **5 只 Bat**，出生高度/巡航高度为 180/320/240/380/280px。
- 5 只 AI 实测：sonic 随机+群体错峰，俯冲只在 hitbox 能触及玩家时释放；无同技能 0.55s 内重叠。
- 未 commit；未动 `Image/`、`instruction.docx`、`UI Resources/`、其他敌人。

## 10. 风险 / 待确认

- hurtbox `100×66` 是否偏大/偏小，需 F1/F2 调试框确认。
- 运行时画布 192、pivot `(115,143)` 与 source 384 的 downscale 由 `animations.json` 统一；不要在代码里另做缩放。
- 5 只 Bat 的声波压力已用 sonic-only 随机、0.55s 群体错峰和俯冲高度门槛缓解，但仍需实测平衡。
- 巡航高度 180–380 时 Lina 的地面拳/踢大多够不到；需要跳跃或趁俯冲时攻击。若手感不对，优先调 `spawn_heights`/`flight.preferred_height`，不改帧。
- 声波弹体、VFX 与施法/命中帧的 handoff 已按 t=0.24 对齐；hitbox 为前向圆 +8/r24。
- 若后续动作帧身体大小漂移，沿用 v8 B 的一次性归一化方法，不要逐帧修图。
