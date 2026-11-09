# Codex 项目工作约定

本文件仅适用于 Codex。如果你不是 Codex，可以忽略以下规则。

## 代码改动

- 默认只阅读、检查、分析和提出方案。创建、修改或删除代码前，先列明拟改动的文件、目的和范围，并取得用户的明确批准。
- 这里的代码包括游戏源代码、工具脚本、测试，以及会改变游戏运行行为的配置或数据文件。用户直接提出具体的代码改动要求，即视为批准该次明确范围内的改动，无须重复询问；范围不明确时先列明拟改文件和内容，取得批准后再改，超出已批准范围时也须重新请求批准。
- 创建或调整文档、预览图和美术素材不属于代码改动，但仍须遵守用户对该任务的具体要求。素材接入游戏、修改资源引用或调整技能逻辑属于代码改动，须先取得批准。

## 角色动画素材

- 新绘制角色动画时，为每个动作建立一个 `assets/generated/contact_sheets/<name>_<animation>/` 目录。将该动作的单帧图、特效、接触表、预览和清单都放在此目录，角色名和动作名沿用项目现有写法。
- 制作前查看同动作已有版本。首版文件以 `<name>_<animation>_v1` 开头，后续依次使用 `v2`、`v3` 等。所有版本共用该动作目录，保留旧版本。按需在版本号后追加帧号或用途，例如 `eira_idle_v1_00.png`、`eira_idle_v1_sheet.png`、`eira_idle_v1_preview.gif`。
- 既有素材保留原位置。用户指定其他交付位置时，按该次要求归档。接入游戏时另按用户授权处理运行用帧目录。
- 角色形象来源和绘制约束遵循 `AGENTS.md`；每次生成图像前读取 `docs/IMAGE_GENERATION_RULES.md`。
- Eira Frostveil 已确认侧身 2 和背身 1。普通动作采用 `assets/generated/base/eira_side_base.png`，攀爬采用 `assets/generated/base/eira_back_base.png`。攀爬使用已通过的 4 帧 v3，落地直接衔接待机或行走。制作参数见 [Eira Frostveil 动画方案](docs/EIRA_FROSTVEIL_ANIMATION_DESIGN.md)。
- Crooked Witch 已确认 base 为 `assets/generated/contact_sheets/crooked_witch_base/crooked_witch_base_v4_02.png`；后续图像均以此为主要参考，保持该图眼形及右手近侧持杖关系。Base 各版本统一保存在 `crooked_witch_base/`，只以文件名版本号区分，不新建版本文件夹。完整动画方案见 `docs/CROOKED_WITCH_ANIMATION_DESIGN.md`。

## UI 素材

- 绘制 UI 相关文件时，默认放在项目实际目录 `UI Resources/`，并按现有内容选择合适的子目录，沿用该目录的命名习惯。
- 若用户指定其他位置、文件名或格式，以该次任务的要求为准。
