# Crooked Witch 动画方案

日期：2026-11-03。用户已确认动画方案，并授权记录本文档。用户已选定 v4_02 作为后续图像的参考 base，并授权记录；各动作仍按接触表逐组审批，素材尚未接入游戏。

2026-11-04：用户确认继续，并允许将上一批 fly、teleport_out、teleport_in 写入文档。三组人物动作帧已通过当次审批；当时瞬移独立特效仍待绘制。

2026-11-04：用户确认 `crooked_witch_teleport_fx_v1`，授权写入本文档，并明确要求暂不接入游戏。特效素材和预览保存在 `assets/generated/contact_sheets/crooked_witch_teleport_fx/`。

2026-11-04：用户确认 `crooked_witch_ice_spike_v1`、`crooked_witch_ice_warning_v1` 和 `crooked_witch_ice_spike_fx_v1`，授权写入本文档。本批仅保留接触表与预览，暂不接入游戏。

2026-11-04：用户确认 `crooked_witch_walk_v3`、`crooked_witch_hurt_v2`、`crooked_witch_ko_v2` 的接触表，并授权写入本文档。三组均沿用未替换的旧帧，只更新各自修订帧；素材仍未接入游戏。

2026-11-05：用户确认闪电的向前、向上、向下三组人物动作，并允许将本轮结果写入本文档。当前素材分别为 `crooked_witch_lightning_v2`、`crooked_witch_lightning_up_v1`、`crooked_witch_lightning_down_v5`；下射 01 帧随后按用户意见调整了袖口遮挡、向下握杖姿势、法杖直线轮廓和紫色衣料亮度。三组仅制作人物帧、接触表和预览，闪电特效仍按独立特效处理，素材尚未接入游戏。

2026-11-05：用户确认治疗动作的 `crooked_witch_heal_v4_01.png` 单帧姿势，并授权写入本文档。新增过渡帧仍待审批，治疗动作整组尚未通过，素材未接入游戏。

2026-11-05：用户确认 `crooked_witch_fly_v3`，授权写入本文档。01、02 帧的远侧左手改为被裙摆完全遮挡；04 帧的远侧左手改为自然垂在身侧，并参照 05 帧进一步收近身体。其他帧沿用上一版，素材尚未接入游戏。

2026-11-05：用户确认 potion 动作及对应药瓶、碎裂、毒区特效，并授权写入本文档。当前人物动作采用 `crooked_witch_potion_v2`：01、02 帧按 03 帧配色调暗，00、03 帧沿用 v1；特效仍采用各自的 v1。素材和预览已存档，尚未接入游戏。

2026-11-06：用户确认火雨人物动作的最新姿势与配色，并要求写入本文档。当前审批接触表为 `crooked_witch_fire_rain_v6_sheet.png`：00 沿用已通过的飞行姿势，01–04 完成侧身转正面、移杖至身前、双手高举法杖；01–04 的紫色衣料、浅色布料和金色亮度参照 00 调整，人物轮廓及动作未因调色改变。素材尚未接入游戏。

2026-11-06：用户确认火雨的像素施法特效和完整预览，并授权写入本文档。当前施法特效采用 `crooked_witch_fire_rain_v7_pulse`：白色倒三角光区内三道浅黄色光束旋转、淡入蓄亮，达到峰值后光区消失；随后长而粗的黄色光柱用 0.4s 淡入，顶部为长轴水平的椭圆，光柱连接杖顶并固定保持。完整预览串联飞入、正面举杖、施法、10 颗火球、落地爆开和返回原位；人物仍采用 fire_rain v6 与 fly v3，火球及落地效果沿用各自 v1。素材和演出已确认，尚未接入游戏。

2026-11-06：用户确认闪电特效 `crooked_witch_lightning_fx_v2`，并授权写入本文档。向前、向上、向下三组均在原特效前新增 3 张生成的过渡帧，每帧 0.06s，共 0.18s，表现杖尖起电、电弧聚集和压缩放电；以形态变化引入，不做淡入或交叉渐变。原 v1 的杖尖闪光、完整闪电和末尾消散原样保留，接在新增帧后。素材与预览已确认，尚未接入游戏。

## 来源与绘制基准

- 技能及被动以 `instruction.docx` 的 Enemy / Crooked Witch 为准；动作组织参考 warrior、creepy shooter 已采用的动画。
- 主要形象来源：`Image/Enemy/crooked-witch-256.png`。保留银白卷发、紫金长袍、弯尖宽檐帽及水晶法杖。
- 常规动作采用朝右的 3/4 侧视：右手近侧持杖，左手位于远侧辅助施法，近侧肢体在前。火雨从侧身飞行转为正面施法，正面帧由双手握住同一根法杖。
- 已选定基准：`assets/generated/contact_sheets/crooked_witch_base/crooked_witch_base_v4_02.png`。今后所有 Crooked Witch 动作和形象衍生图以此图作为唯一或主要参考；旧 A–D、v2、v3 以及 v4_01 仅留档，不再作为生成基准。
- 参考图为 1254×1254 透明 PNG。锁定其眼形、镜头、头身比、身体和法杖比例、近远侧关系；不能为适配或居中逐帧缩小、拉伸人物。运行用画布与 pivot 待素材接入时另行确定，不在本轮变更。
- 全身和完整法杖保留，透明背景，无地影、文字、边框或场景。遵守 `docs/IMAGE_GENERATION_RULES.md` 的遮挡、握姿、不穿模和尺寸检查。

## 移动范围

地面移动使用 walk。fly 只用于原文明确提及的半血恢复、火雨：飞往屏幕中央和结束后返回原位。四点换位使用独立瞬移动作；普通移动和换平台不自行增加飞行。暂不增加 jump、crouch、climb。

## 基础动作

下列帧数与演出时长是本次获确认的美术方案，不替代技能逻辑和数值规格。

| 名称 | 帧数与节奏 | 具体动作 |
| --- | --- | --- |
| `crooked_witch_base_v1` | 四张静态候选 A–D | 右向侧身，全身完整，右手近侧持杖。由用户选择后作为后续姿势与尺寸基准。 |
| `crooked_witch_idle_v1` | 4 帧，0.72s 循环 | 右手竖持法杖、左手轻抬；胸肩轻微呼吸，发梢、帽坠和裙摆延迟摆动，双脚站稳。 |
| `crooked_witch_walk_v2` | 沿用已通过的 v1 六张动作帧；每帧 0.16s，0.96s 循环 | 用户已确认动作通过，并要求放慢。v2 只调整播放节奏，保留 v1 原始图片和预览；新预览与节奏记录放在同一 `crooked_witch_walk/` 文件夹。00 右脚前触地；01 重心移至右脚、左脚蹬地；02 左脚经过支撑腿、身体轻抬；03 左脚前触地；04 重心移至左脚、右脚蹬地；05 右脚经过支撑腿、接 00。右手稳定握杖，杖略前倾、杖尾离地；左手小幅平衡，裙摆随步伐开合，头发和帽坠滞后摆动。 |
| `crooked_witch_walk_v3` | 已通过；6 帧，每帧 0.16s，0.96s 循环 | 保留 v1 的 00–04，以 `crooked_witch_walk_v3_05.png` 替换 05；右脚经过支撑腿时，法杖保持在人物前景，右手握姿与相邻帧连续。接触表和预览分别为 `crooked_witch_walk_v3.png`、`crooked_witch_walk_v3_preview.mp4`，旧版保留。 |
| `crooked_witch_fly_v1` | 已通过；6 帧，预览每帧 0.18s；仅 02/03 飞行段循环 | 00 屈膝收杖；01 脚跟离地；02/03 双脚后收、袍摆后飘，循环飞行；04 回程伸腿；05 触地收势。到屏幕中央直接接悬浮施法，04/05 仅用于返回落地。全六帧预览为 1.08s，不能作为普通飞行循环。 |
| `crooked_witch_fly_v3` | 当前已通过人物素材；6 帧，每帧 0.18s；仅 02/03 飞行段循环 | 保留 v2 的 00、01、02、03、05 帧；04 帧远侧左手在裙侧自然下垂，位置比 v2 更靠近身体，参照 05 帧衔接。v2 的 01、02 帧已将远侧左手完全藏在裙摆后，不再从身后露出；其余动作和法杖握姿保持原方案。04/05 仅用于返回落地，六帧预览不作为普通飞行循环。 |
| `crooked_witch_teleport_out_v1` | 人物动作已通过；3 帧，每帧 0.10s，共 0.30s | 法杖收至身前 → 左手在远侧向锁骨附近收拢、肩部内收 → 袍摆合拢。人物保持完整、不缩小，消失交由独立紫色特效处理。02 灰紫背景雾版本标记 rejected，采用重生成的干净透明人物帧。 |
| `crooked_witch_teleport_in_v1` | 人物动作已通过；3 帧，每帧 0.10s，共 0.30s | 完整人物轮廓对应的收拢姿势 → 抬头、远侧左手展开、袍摆散开 → 法杖归位接待机。02 直接沿用已选 v4_02 base，凝聚特效另绘。 |
| `crooked_witch_hurt_v1` | 2 帧，0.20s | 胸肩后顿，帽檐和头发后摆、持杖手不松 → 稳身回待机。 |
| `crooked_witch_hurt_v2` | 已通过；2 帧，每帧 0.10s，共 0.20s | 用 `crooked_witch_hurt_v2_00.png` 表现受击后顿，远侧左手保持自然位置；01 沿用 `crooked_witch_hurt_v1_01.png` 稳身回待机。右手始终握杖。接触表和预览分别为 `crooked_witch_hurt_v2.png`、`crooked_witch_hurt_v2_preview.mp4`。 |
| `crooked_witch_ko_v1` | 4 帧，约 0.75s，末帧保持 | 法光熄灭、身体后仰 → 屈膝撑杖 → 侧倒 → 完全倒地。帽子保留，法杖落同侧，不穿身体或头发。 |
| `crooked_witch_ko_v2` | 已通过；4 帧，0.15/0.20/0.20/0.20s，共 0.75s；末帧保持 | 00–02 沿用 v1 的后仰、屈膝和侧倒动作；03 改用 `crooked_witch_ko_v2_03.png`，闭眼、落地手收拢，帽子保留，法杖落在同侧。接触表和预览分别为 `crooked_witch_ko_v2.png`、`crooked_witch_ko_v2_preview.mp4`。 |

## 被动与技能动作

| 名称 | 帧数与节奏 | 动作及事件 |
| --- | --- | --- |
| `crooked_witch_heal_v1` | 5 帧，维持段 5s | 飞到中央后，00 右手松杖、法杖悬浮在侧前方；01 双臂向两侧张开、掌心朝上；02/03 张臂呼吸循环，绿色粒子每秒脉冲，共 5 次；04 收臂，右手握回原位置，再飞回。法杖悬浮是满足双手张开的表现设计。 |
| `crooked_witch_heal_v4_01` | 单帧姿势已通过；整组待审批 | 作为原 01 帧的修订姿势：画面右端的远侧左手向外伸出、掌心朝上，参照维持帧的同侧手势但伸展幅度较小；近侧右手放在身侧偏后。双臂各自连接对应肩部，不交叉。人物帧不含法杖，法杖作为独立道具悬浮。原 01 的“双臂同时张开”描述不再适用于这张已通过的单帧。 |
| `crooked_witch_lightning_v1` | 4 帧，0.60s | 00 转肩收杖 0.15s；01 抬肘蓄能 0.15s；02 向前指杖 0.10s，进入此帧发射闪电；03 收杖 0.20s。 |
| `crooked_witch_lightning_v2` | 当前人物素材；4 帧，0.15/0.15/0.10/0.20s，共 0.60s | 00、01、03 沿用 v1；02 保持向前指杖动作，将连续杖身放在近侧右袖外侧，袖子被杖身遮挡，右手手指从前方包握杖身。进入 02 时从实际杖尖发射闪电；人物帧不含闪电特效。 |
| `crooked_witch_lightning_up_v1` | 当前人物素材；4 帧，0.15/0.15/0.10/0.20s，共 0.60s | 00、01、03 与向前闪电共用姿势；02 近侧右手和完整法杖一起斜上指向目标，进入此帧释放，身体比例与脚底基线不变。 |
| `crooked_witch_lightning_down_v1` | 沿用闪电节奏 | 持杖手臂与法杖一起斜下指向目标，身体比例不变。 |
| `crooked_witch_lightning_down_v5` | 当前人物素材；4 帧，0.15/0.15/0.10/0.20s，共 0.60s | 00、02、03 沿用 v4；01 单独蓄能，近侧右前臂位于法杖上方，右手从上向下包握杖身、手指朝下。杖身在垂下的袖子外侧，白色袖口在杖身后方，杖轴保持笔直；紫色衣料亮度参照相邻 00、02 帧统一。02 向右下指杖，进入此帧释放闪电；人物帧不含特效。 |
| `crooked_witch_ice_spike_v1` | 已通过；4 帧，0.15/0.15/0.10/0.20s，共 0.60s | 00 右手将杖抬至肩侧；01 杖尖划短弧；02 右腕向前下方一压并释放预警圈；03 收腕立杖，沿用已选 v4_02 base。右手近侧单手持杖，人物尺寸和脚底基线保持一致。预警圈在目标同高度、目标附近且靠 witch 一侧的地面或平台，出现满 1s 后冰锥升起。 |
| `crooked_witch_potion_v1` | 4 帧，0.65s | 杖向侧后蓄势 → 左手张开辅助凝聚 → 向前挑杖，在杖尖前召出并释放药瓶 → 收杖。药瓶不由手投掷。平台版受重力下落，地面版低位水平前进。 |
| `crooked_witch_potion_v2` | 已通过；4 帧，0.15/0.15/0.15/0.20s，共 0.65s | 00 近侧右手持杖蓄势，远侧左手在身侧；01 左手张开、掌心朝上辅助凝聚，右手保持握杖；02 右手向前上方挑杖，进入此帧时在杖尖前召出并释放药瓶，左手保持辅助姿势；03 收杖归位，沿用已选 v4_02 base。药瓶不由手投掷。v2 的 01、02 仅按 03 的紫金配色调暗，动作沿用 v1；00、03 与 v1 原图相同。人物帧不包含药瓶或碎裂特效。 |
| `crooked_witch_fire_rain_v1` | 历史侧身方案；6 帧，维持段 10 轮 | 飞到中央后，00 杖收肩侧；01 沿帽檐外侧上举；02 手臂伸展、水晶举过头顶；03/04 保持举杖，0.8s 一轮，每轮末端杖尖脉冲并生成火球，共 10 轮；05 降杖，再飞回。维持段 8s、首颗在第 1 轮末生成。当前人物姿势以 v6 为准。 |
| `crooked_witch_fire_rain_v6` | 当前已通过人物素材；5 帧，00–04 | 先沿用 fly 飞到施放位置；00 保持右向侧身悬浮；01 转向镜头，02 完全正面并以双手握杖；03 使用用户选定的正面姿势，法杖竖直置于身体正前方；04 双手举过头顶，法杖沿身体中线上抬，水晶杖尖明显高于帽顶，头部及胸口比例参照 03。00 沿用 `crooked_witch_fire_rain_v2_00.png`；01–04 使用 v6 调色帧，紫色、浅色布料和金色亮度参照 00，动作及透明轮廓不变。04 保持高举姿势，叠加独立的 v7 像素施法特效；火球每 0.8s 一颗、共 10 颗。完整预览的收杖段按 03→02→01→00 衔接，再接 fly 返回落地。 |

## 独立特效

主体、法杖脱手道具、施法闪光、投射物、地面效果分开处理，释放事件与角色释放帧同步。

| 名称 | 表现 |
| --- | --- |
| `crooked_witch_teleport_fx_v1` | 已通过。独立透明紫金法环与碎光，消失和出现各 6 帧、每帧 0.10s。法环与人物帧分层；预览中的人物淡入淡出仅为合成演示。`crooked_witch_teleport_fx_v1_sheet.png` 为审批接触表，`crooked_witch_teleport_fx_v1_preview.gif` 为动态预览。暂不接入游戏。 |
| `crooked_witch_heal_fx_v1` | 绿色粒子向上环绕，每秒恢复脉冲。 |
| `crooked_witch_lightning_fx_v1` | 历史版本保留；杖尖闪光、完整闪电和消散三帧，作为 v2 的 03–05 帧原样沿用。 |
| `crooked_witch_lightning_fx_v2` | 当前已通过；向前、向上、向下各 6 张独立透明帧。00–02 为新生成的杖尖起电、电弧聚集、压缩放电，各 0.06s；03–05 沿用 v1 的闪光、完整闪电、消散，分别为 0.08/0.10/0.10s。单次特效共 0.46s，新增引入段共 0.18s；逐帧直接显示，无淡入或交叉渐变，保留末尾消散。特效从实际杖尖发出，与人物分层。 |
| `crooked_witch_ice_warning_v1` | 已通过；独立透明蓝色预警圈 5 帧、每帧 0.20s，共 1s；在人物 02 释放帧出现，末帧增强亮度，满 1s 后接冰锥。 |
| `crooked_witch_ice_spike_fx_v1` | 已通过；独立透明冰锥 7 帧：破地、小锥升起、继续生长、峰值、峰值闪光、碎裂、消散。合成预览按每帧 0.10s 播放，特效与人物分层。 |
| `crooked_witch_potion_projectile_v1` | 已通过；独立透明药瓶 3 帧，封口的紫金瓶身内有绿色发光液体。预览按 00→01→02→01 轻微摆转；平台施法后受重力前落，地面施法后以低位水平前进。 |
| `crooked_witch_potion_break_v1` | 已通过；独立透明碎裂特效 4 帧：瓶身开裂并漏液 → 瓶身碎开、液体溅出 → 玻璃和毒液飞溅峰值 → 碎片与液滴消散。直击目标或落地、到达路径终点时均可播放碎裂；直击不接毒区。 |
| `crooked_witch_poison_pool_v1` | 已通过；独立透明毒区 4 帧：00 浅绿色液面初生，01/02 在同一落点翻涌冒泡循环，03 变淡退场。仅药瓶未直接命中、落地或到达路径终点后留下；毒区寿命尚未确定，不以预览循环次数作为技能时长。 |
| `crooked_witch_fire_rain_v7_pulse` | 已通过；独立像素特效。倒三角光区上宽下尖，尖端接在杖顶，白光表示区域，内部三道浅黄色光束围绕法杖竖轴轮转；可见图案每 0.48s 循环一次，保持此前加速 3 倍的节奏。00–23 每帧 0.04s，共 0.96s 淡入蓄亮；24 为 0.04s 亮度峰值，之后倒三角光区与三道旋转光束一起消失。25–44 每帧 0.02s，共 0.4s 淡入一根长而粗的竖直黄色光柱，顶部为长轴水平的椭圆；44 作为持续保持帧，位置与形状固定，底部连接杖顶，不向上飞离。召唤火球期间持续显示光柱，收杖时结束。 |
| `crooked_witch_fireball_v1` | 当前已确认完整预览采用的独立火球素材。每次生成时取目标当前 x，随后保持该 x 竖直下落、尾焰上拖，穿过平台继续下落；不追踪目标后续横向移动。 |
| `crooked_witch_fire_impact_v1` | 当前已确认完整预览采用的独立落地效果。命中或到地面后爆开，火星消散；四帧节奏为 0.08/0.10/0.12/0.14s。 |

## 火雨完整预览（已确认）

当前演出采用 fly v3、fire_rain 人物 v6、施法特效 v7、fireball v1 和 fire_impact v1。完整视频为 15.32s、1600×1000、50fps；GIF 为 960×600、25fps。下表记录该预览的衔接时序，不将总片长解释为技能冷却或新增数值规格。

| 预览时间 | 演出 |
| --- | --- |
| 0.00–1.44s | 起飞并飞到中央；起飞用 fly 00/01，移动只循环 02/03。 |
| 1.44–2.68s | fire_rain 00→01→02→03→04：侧身悬浮、转正面、移杖至身前、双手高举。 |
| 2.68–3.68s | 像素倒三角光区与三道浅黄色光束淡入、旋转蓄亮，最后 0.04s 达到峰值。 |
| 3.68–4.08s | 前段光效消失，顶部为横向椭圆的黄色光柱用 0.4s 淡入；光柱位置固定。 |
| 4.08–12.08s | 保持正面高举姿势与固定光柱；每 0.8s 生成一颗火球，共 10 颗。首颗在 4.88s、第十颗在 12.08s 生成。火球按生成时的目标位置竖直落下、穿过平台并在地面爆开。 |
| 12.08–13.28s | 最后一颗生成后先保持 0.2s，再结束光柱并收杖、转身。已生成的火球继续下落和播放落地效果。 |
| 13.28–14.72s | fly 02/03 飞回原位，随后用 04/05 落地收势。 |
| 14.72–15.32s | 片尾展示返回完成的状态。 |

完整预览中的平台线、地面线、移动目标标记、阶段说明和计数用于审阅；角色原始动作帧、配色和比例未修改。单独施法特效 GIF 的片尾停留仅供查看光柱淡入结果，持续施法时长以完整演出与每 0.8s 一颗、共 10 颗的事件规格为准。

## 原始规格边界

- 半血恢复与火雨期间，按原文免伤、免控、无 hitbox；不因动画设计给其他动作额外增加这些效果。
- 恢复：首次低于 50% 血触发一次，每秒恢复 6%，持续 5s；百分比基准尚需在实现时核实。
- 闪电：1.2atk，易伤 20，最多三层；跨高度与 block 限制按原文。
- 冰锥：atk，冻结 1.5s。
- 药瓶：直击 0.8atk，毒伤 3% 最大生命持续 3s、减速 30%，不留毒区；未命中碎裂留绿色毒区，进入后毒伤 2% 最大生命持续 3s、减速 20%。毒区寿命与毒伤结算频率未定。
- 火雨：每 0.8s 一颗，共 10 次；生成时取目标当前 x，随后竖直下落，无视 block，伤害 1.2atk 并附灼烧；灼烧数值和时长未定。
- 原文技能标题括号的 2s/5s/8s/15s 没有明写 CD，不把它们当作动画时长，也不在本文新增已确认冷却解释。

## 保存、命名与审批

- Base 统一保存在 `assets/generated/contact_sheets/crooked_witch_base/`，不按版本新建文件夹；文件名用 v1、v2、v3 等递增表示版本，保留旧版。
- 原 v1、v2、v3 目录中的素材已归档到上述统一目录。
- 首轮候选：`crooked_witch_base_v1_A.png`、`crooked_witch_base_v1_B.png`、`crooked_witch_base_v1_C.png`、`crooked_witch_base_v1_D.png`。A–D 为同版候选后缀。
- 动作主名遵循 `name_action_v1`；单帧附帧号、预览附用途后缀；后续版本递增，不覆盖旧版。
- 闪电三组人物素材分别保存在 `assets/generated/contact_sheets/crooked_witch_lightning/`、`crooked_witch_lightning_up/`、`crooked_witch_lightning_down/`。当前版本为 v2、v1、v5；每组保留 4 张透明人物帧、`*_sheet.png` 接触表和 `*_preview.gif` 预览。工作画布为 1536×1254，仅平移对齐脚部，未缩放人物或法杖；1254×1254 原始生成帧以 `*_source.png` 保留。旧版及未采用的重生图保留作对照，运行用画布和 pivot 仍待接入时确定。
- 飞行动作当前版本为 `assets/generated/contact_sheets/crooked_witch_fly/crooked_witch_fly_v3`，同目录保留 6 张 1254×1254 透明人物帧、`crooked_witch_fly_v3.png` 全尺寸帧表、`crooked_witch_fly_v3_sheet.png` 审批接触表、`crooked_witch_fly_v3.gif` 动态预览和 `crooked_witch_fly_v3_sheet.json` 帧记录。v3 仅重绘 04 帧；00–03、05 与 v2 逐字节相同，v1、v2 保留作对照。
- 闪电特效保存在 `assets/generated/contact_sheets/crooked_witch_lightning_fx/`，当前采用 `crooked_witch_lightning_fx_v2_{forward/up/down}_00.png` 至 `_05.png`，共 18 张 1400×1400 透明 PNG；共用特效连接点 `(300,700)`，三个方向分别为 0°、向上 35°、向下 35°。连接点仅用于当前素材合成对齐，不代表已确定运行用画布与 pivot。审批接触表为 [v2 帧表](../assets/generated/contact_sheets/crooked_witch_lightning_fx/crooked_witch_lightning_fx_v2_sheet.png)，新增过渡与原闪光的对照为 [杖尖特写](../assets/generated/contact_sheets/crooked_witch_lightning_fx/crooked_witch_lightning_fx_v2_intro_sheet.png)，动态预览为 [正常速度](../assets/generated/contact_sheets/crooked_witch_lightning_fx/crooked_witch_lightning_fx_v2_preview.gif) 和 [3 倍时长慢速](../assets/generated/contact_sheets/crooked_witch_lightning_fx/crooked_witch_lightning_fx_v2_slow_preview.gif)。正常预览在特效前后另有 0.30/0.40s 的人物静止停顿，仅用于审阅，不计入 0.46s 特效时长。同目录保留 3 张 `crooked_witch_lightning_fx_v2_intro_00_source.png` 至 `_02_source.png` 原始生成帧、`crooked_witch_lightning_fx_v2_prompts.json` 生成记录和 `crooked_witch_lightning_fx_v2_sheet.json` 帧序记录；v1 全部原文件保留，v2 的 03–05 与相应 v1 的 00–02 逐字节相同。此次只确认素材演出，不修改人物动作节奏、技能逻辑或数值，尚未接入游戏。
- 冰锥人物帧、预警圈和冰锥特效分别保存在 `assets/generated/contact_sheets/crooked_witch_ice_spike/`、`crooked_witch_ice_warning/`、`crooked_witch_ice_spike_fx/`；各目录的 `*_sheet.png` 是审批接触表，`crooked_witch_ice_spike_v1_preview.gif` 展示施法、1s 预警和冰锥破地碎裂的合成顺序。
- 药瓶人物动作保存在 `assets/generated/contact_sheets/crooked_witch_potion/`，当前采用 `crooked_witch_potion_v2_00.png` 至 `_03.png`；`crooked_witch_potion_v2_sheet.png` 和 `crooked_witch_potion_v2_preview.gif` 分别是审批接触表与动态预览。药瓶飞行、碎裂、毒区的透明单帧和各自 `*_sheet.png`、`*_preview.gif` 分别保存在 `crooked_witch_potion_projectile/`、`crooked_witch_potion_break/`、`crooked_witch_poison_pool/`。同目录保留 v1 人物帧及三种命中分支的演示预览，分支预览中的人物颜色为旧版，仅用于说明事件顺序；当前人物配色以 v2 为准。演示中的平台线、地面线和目标占位轮廓不是游戏素材，全部素材尚未接入游戏。
- 火雨人物素材保存在 `assets/generated/contact_sheets/crooked_witch_fire_rain/`。当前 00 帧为 `crooked_witch_fire_rain_v2_00.png`，01–04 帧为 `crooked_witch_fire_rain_v6_01.png` 至 `_04.png`，审批接触表为 `crooked_witch_fire_rain_v6_sheet.png`。01、02 帧画布为 1536×1536，03、04 帧为保留高举法杖而扩至 1536×1792；接触表仅为排版给 00–02 增加透明上边距，人物和法杖均未缩放。运行用统一画布与 pivot 待接入时确定。v1–v5 保留作修订记录；人物素材尚未接入游戏。
- 火雨施法特效与完整预览同样保存在 `assets/generated/contact_sheets/crooked_witch_fire_rain/`。当前独立特效为 `crooked_witch_fire_rain_v7_pulse_00.png` 至 `_44.png`，共 45 张 512×1280 透明 PNG；像素网格为 8px，杖顶连接点为特效画布 `(256,1216)`。该点仅用于当前素材合成对齐，运行用画布与 pivot 仍待接入时确定。透明帧表为 [v7 pulse sheet](../assets/generated/contact_sheets/crooked_witch_fire_rain/crooked_witch_fire_rain_v7_pulse_sheet.png)，特写为 [v7 pulse preview](../assets/generated/contact_sheets/crooked_witch_fire_rain/crooked_witch_fire_rain_v7_pulse_preview.gif)。特效 v1–v6 保留作修订记录。
- 当前已确认的火雨完整演出：[MP4](../assets/generated/contact_sheets/crooked_witch_fire_rain/crooked_witch_fire_rain_v7_complete_preview.mp4)、[GIF](../assets/generated/contact_sheets/crooked_witch_fire_rain/crooked_witch_fire_rain_v7_complete_preview.gif)、[关键帧对照](../assets/generated/contact_sheets/crooked_witch_fire_rain/crooked_witch_fire_rain_v7_complete_storyboard.png)。完整预览沿用 `crooked_witch_fireball/crooked_witch_fireball_v1_00.png` 和 `crooked_witch_fire_impact/crooked_witch_fire_impact_v1_00.png` 至 `_03.png`。本次只记录已确认的素材与演出，尚未接入游戏或修改技能逻辑。
- 用户先选 base，再绘制并审批各动作接触表；只在用户明确要求接入游戏时处理运行用素材和资源引用。
