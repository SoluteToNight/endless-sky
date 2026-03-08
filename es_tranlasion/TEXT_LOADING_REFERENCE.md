# Endless Sky 文本加载参考手册 (Text Loading Reference)

本文档整理了游戏中常见的玩家可见文本标识符（Tags）及其在源代码中的加载位置。这对于后续的国际化（I18N）重构和翻译工作具有重要参考价值。

---

## 文本加载机制概览

游戏通过 `DataFile` 将 `.txt` 文件解析为 `DataNode` 树。代码中使用 `node.Token(index)` 提取字符串。
- **Token(0)**: 属性关键字（如 `description`）。
- **Token(1)**: 属性值（实际文本）。如果是多行文本，通常作为子节点（Children）存在。

---

## 对象标识符映射表

| 对象类型 | 文本标识符 (Tag) | 源代码位置 | 说明 |
| :--- | :--- | :--- | :--- |
| **星球 (Planet)** | `display name` | `source/Planet.cpp` | 星球在地图上显示的名称 |
| | `description` | `source/Planet.cpp` | 星球详情页面的背景描述 |
| | `port` / `spaceport` | `source/Planet.cpp` | 进入港口时显示的欢迎/拒绝词 |
| **任务 (Mission)** | `name` | `source/Mission.cpp` | 任务日志中显示的标题 |
| | `description` | `source/Mission.cpp` | 任务面板中的详细说明 |
| | `blocked` | `source/Mission.cpp` | 条件不满足时的拒绝消息 |
| **对话 (Conversation)** | `label` | `source/Conversation.cpp` | 流程标记（虽然不直接显示，但影响逻辑） |
| | `choice` | `source/Conversation.cpp` | 玩家可选择的回复选项文字 |
| | (无关键字文本) | `source/Conversation.cpp` | NPC 的对话正文（按行累加） |
| **舰船 (Ship)** | `display name` | `source/Ship.cpp` | 船只型号的显示名称 |
| | `plural` | `source/Ship.cpp` | 复数形式 |
| | `noun` | `source/Ship.cpp` | 替代代词 |
| **装备 (Outfit)** | `display name` | `source/Outfit.cpp` | 装备在商店和面板的名称 |
| | `description` | `source/Outfit.cpp` | 装备的属性介绍和背景故事 |
| | `category` / `series`| `source/Outfit.cpp` | 分类标签 |
| **政府 (Government)** | `display name` | `source/Government.cpp`| 势力全称 |
| | `* hail` | `source/Government.cpp`| 各类通讯指令（友好、敌对、受贿等） |
| **短语 (Phrase)** | (无关键字文本) | `source/Phrase.cpp` | 随机生成的语音/通讯短词 |
| **系统消息 (Message)** | `text` / `phrase` | `source/Message.cpp` | 游戏内弹出的提示文本 |

---

## 特殊文本处理建议

1. **属性列表 (Attributes)**: 
   许多对象（如 Ship, Planet）具有 `attributes` 节点。虽然大部分是数值，但某些自定义属性名可能会显示在 UI 中。
2. **文本替换 (TextReplacements)**:
   源代码位于 `source/text/TextReplacements.cpp`。它负责处理诸如 `${firstName}` 之类的动态占位符替换逻辑。
3. **百科/提示 (Tooltips/Help)**:
   位于 `source/GameData.cpp` 中的 `Tooltip()` 和 `HelpMessage()` 方法，负责加载 UI 交互时的额外帮助文本。

---

## 数据文件主要分布 (data/ 目录)

- **剧情/对话**: `data/human/conversations.txt`
- **星球介绍**: `data/map planets.txt`
- **任务定义**: `data/human/*.txt` (大部分是 intro 和 storyline)
- **短语/对白**: `data/dialog phrases.txt`
