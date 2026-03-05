# Endless Sky 数据格式指南

Endless Sky 使用一种自定义的、基于缩进的文本数据格式（类似于 Python）。本指南详细说明了主要的根节点（Root Nodes）、它们常见的子节点（Sub-nodes）以及源代码中负责处理它们的类。

## 加载机制概述

所有数据加载的入口点是 `UniverseObjects::LoadFile` (位于 `source/UniverseObjects.cpp`)。它读取 `.txt` 文件，并根据每一行的第一个标记（Token）将数据路由到相应的对象处理器。

---

## 主要根节点参考

### 1. `ship` (舰船)
定义一艘舰船的属性、外观和装备槽位。
- **处理类**: `Ship` (`source/Ship.cpp`)
- **常见子节点**:
  - `sprite`: 引用的图像资源路径。
  - `attributes`: 基础属性（质量、转向、推力等）。
  - `outfits`: 初始装备。
  - `engine`, `reverse engine`, `steering engine`: 引擎火焰位置。
  - `gun`, `turret`: 武器硬点位置和属性。
  - `bay`: 载机库（战机或无人机）。
  - `description`: 舰船描述。
  - **其他子节点**:
    - `plural`: 名称的复数形式。
    - `leak`, `explode`, `"final explode"`: 定义受损或被摧毁时的视觉效果。
    - `add attributes`: 在变体中用于修改父级舰船的属性。
    - (在 `attributes` 块内部): `licenses` (所需许可证), `automaton` (设为无人机), `hull repair rate` (船体修复率) 等更多详细属性。

### 2. `outfit` (装备)
定义可以安装在舰船上的任何物品。
- **处理类**: `Outfit` (`source/Outfit.cpp`)
- **常见子节点**:
  - `category`: 装备类别（如 "Guns", "Engines"）。
  - `cost`: 购买价格。
  - `thumbnail`: 商店中显示的缩略图。
  - `attributes`: 提供的属性增益。
  - `weapon`: 如果是武器，定义弹药、伤害等。
  - `description`: 装备描述 (显示文本)。
  - **其他子节点**:
    - `display name`: 装备的显示名称 (显示文本)。
    - `series`: 装备的系列或子类别。
    - `index`: 用于排序的索引。
    - `plural`: 装备名称的复数形式 (显示文本)。
    - `mass`: 质量。
    - `unplunderable`: 如果设置，则无法从被瘫痪的舰船上掠夺。
    - `illegal`: 如果设置，携带此装备将可能导致罚款 (相关信息显示文本为 `fineMessage`)。
    - `unique`: 如果设置，一艘船上只能安装一个。
    - `licenses`: 购买此装备所需的执照。
    - **占位与硬点**:
      - `outfit space`, `weapon capacity`, `engine capacity`: 占用的舰船空间。
      - `gun ports`, `turret mounts`: 提供的火炮口或炮塔挂载点。
    - **视觉与音效**:
      - `flare sprite`, `reverse flare sprite`, `steering flare sprite`: 引擎光斑效果。
      - `flare sound`, `reverse flare sound`, `steering flare sound`: 引擎音效。
      - `afterburner effect`: 加力燃烧器效果。
      - `jump effect`: 跳跃效果。
      - `hyperdrive sound`, `jump sound`: 超空间/跳跃驱动音效。
      - `flotsam sprite`: 装备被摧毁后留下的碎片图像。
    - **武器子节点 (`weapon` 块内)**:
      - **弹药**: `ammo` (定义弹药类型和使用量)。
      - **视觉与音效**: `sprite` (弹药图像), `icon` (UI图标), `sound`, `empty sound` (空仓音效)。
      - **效果**: `fire effect`, `live effect`, `hit effect`, `target effect`, `die effect`。
      - **行为**: `stream` (持续射击), `cluster` (集束射击), `safe` (安全范围), `phasing` (相位穿透), `homing` (追踪), `submunition` (子弹药)。
      - **伤害**: `shield damage`, `hull damage` 及各种 `damage` 类型 (如 `ion damage`, `heat damage` 等), `hit force`。
      - **范围与衰减**: `blast radius`, `trigger radius`, `safe range`, `damage dropoff`。
      - **弹道**: `velocity`, `acceleration`, `drag`, `turn`, `lifetime`, `inaccuracy`。
      - **其他**: `penetration count`, `piercing`, `prospecting`。
    - **属性修改**: `attributes` 块可以包含大量属性，如 `cooling` (散热), `shield generation` (护盾生成), `energy generation` (能量生成), `scan power` (扫描能力), `cloaking` (隐形) 等，这些都会直接修改舰船的对应属性。

### 3. `system` (星系)
定义恒星系统及其在地图上的位置。
- **处理类**: `System` (`source/System.cpp`)
- **常见子节点**:
  - `pos <x> <y>`: 地图坐标。
  - `government`: 所属政府。
  - `habitable`: 宜居度。
  - `object <planet_name>`: 包含的行星或空间站。
  - `link <system_name>`: 超空间连接路径。
  - `asteroid <sprite> <count>`: 存在的环境陨石。
  - **其他子节点**:
    - `display name`: 星系的显示名称 (显示文本)。
    - `music`: 在星系中播放的环境音乐。
    - `attributes`: 星系属性的集合，如 "uninhabited", "hidden" 等。
    - `minables`: 可开采资源的定义。
    - `haze`: 背景雾气图像。
    - `starfield density`: 星场密度。
    - `ramscoop`: 冲压式燃料收集器的属性，可包含 `universal`, `addend`, `multiplier`。
    - `trade`: 贸易商品及其价格。
    - `fleet`: 定义可能在该星系中出现的NPC舰队。
    - `hazard`: 定义该星系中的环境危害。
    - `belt`: 小行星带的半径和权重。
    - `hidden`, `shrouded`, `inaccessible`, `no raids`: 控制星系可见性、可达性或禁止袭击的标志。
    - `arrival`, `departure`: 控制超空间/跳跃抵达或离开距离。
    - `invisible fence`: 玩家在该星系中不能超越的半径。
    - `jump range`: 从该星系可以跳跃的距离。
    - **星体对象子节点 (`object` 块内)**:
      - `sprite`: 天体的图像。
      - `distance`: 天体与其父天体的距离。
      - `period`: 轨道周期。
      - `offset`: 轨道相位偏移。
      - `swizzle`: 天体精灵的颜色替换。
      - `visibility`: 控制天体何时可见。
      - `hazard`: 与该特定天体相关的危害。
      - `object`: 递归定义子天体 (例如，行星的卫星)。

### 4. `planet` (行星/空间站)
定义可以着陆的对象。
- **处理类**: `Planet` (`source/Planet.cpp`)
- **常见子节点**:
  - `attributes`: 环境属性。
  - `description`: 描述文本。
  - `spaceport` / `port`: 港口设施。`spaceport` 提供通用服务（如对话），而 `port` 可更精确地定义可用服务。
  - `shipyard`: 出售的舰船列表。
  - `outfitter`: 出售的装备列表。
  - `bribe`: 贿赂所需的条件和成本。

### 5. `mission` (任务)
定义任务的逻辑、对话和奖励。
- **处理类**: `Mission` (`source/Mission.cpp`)
- **常见子节点**:
  - `landing`: 着陆时触发。
  - `deadline`: 截止日期。
  - `source`: 起始星系或行星。
  - `destination`: 目标星系或行星。
  - `on accept`, `on complete`, `on fail`: 不同状态下的动作。
  - `dialog`: 任务对话内容。
  - **任务信息与显示**:
    - `name`: 任务的名称 (显示文本)。
    - `description`: 任务的描述 (显示文本)。
    - `minor`: 标记为次要任务，不阻止其他任务出现。
    - `invisible`: 任务不会显示在任务列表中。
    - `non-blocking`: 任务不会阻止其他次要任务出现。
    - `job`: 标记为可重复的通用任务。
    - `repeat`: 允许任务重复提供。
    - `autosave`: 接受任务时自动保存游戏。
    - `blocked`: 因条件不满足而无法接受任务时显示的文本 (显示文本)。
    - `illegal`: 携带此任务相关货物或乘客可能导致罚款 (相关信息显示文本为 `fineMessage`)。
    - `stealth`: 如果任务要求隐秘，被发现会导致任务失败。
  - **位置与触发**:
    - `waypoint`: 中途需要访问的星系或行星。
    - `stopover`: 需要停留的地点，通常用于货物或乘客的装卸。
    - `job board`: 任务在任务板上提供。
    - `shipyard`, `outfitter`: 任务在船厂或装备店提供。
    - `entering`, `transition`: 进入星系或进行跃迁时触发。
    - `assisting`, `boarding`: 任务涉及协助或登船。
  - **条件与动作**:
    - `to offer`, `to accept`, `to complete`, `to fail`: 定义任务在不同阶段的条件。
    - `on enter <system name>`, `on land <planet name>`: 进入特定星系或降落特定星球时触发动作。
    - `on visit`, `on stopover`, `on waypoint`: 访问或经过指定地点时触发动作。
    - `on abort`, `on defer`, `on daily`, `on disabled`: 任务中止、推迟、每日触发或舰船被瘫痪时触发动作。
    - `npc`: 定义与任务相关的NPC舰船或舰队，可包含 `government`, `personality`, `ship`, `fleet` 等子节点。
    - `timer`: 定义任务计时器。
  - **对话流程 (`conversation` 块内)**:
    - `choice`: 玩家的对话选项 (显示文本)。
    - `label`: 对话中的命名跳转点。
    - `goto`: 跳转到指定 `label`。
    - `accept`, `decline`, `defer`: 在对话中接受、拒绝或推迟任务。
    - `action`: 在对话中执行游戏动作。
    - `branch`: 基于条件进行对话分支。
    - `scene`: 显示对话背景图片。
    - `to display`: 控制对话选项的显示条件。
    - `to activate`: 控制对话选项的激活条件。

### 6. `government` (政府/派系)
定义派系属性和外交关系。
- **处理类**: `Government` (`source/Government.cpp`)
- **常见子节点**:
  - `color`: 在地图上显示的颜色。
  - `attitude`: 对不同派系的基础态度。
  - `reputation`: 玩家的初始声望。
  - `raid`: 袭击逻辑（触发条件和舰队）。
  - `atrocities`: 定义拥有特定非法物品（如偷来的装备或舰船）的惩罚。

---

## 辅助与特殊根节点

| 关键字 | 说明 | 处理类 / 逻辑位置 |
| :--- | :--- | :--- |
| `conversation` | 复杂的交互式对话树 | `Conversation` |
| `phrase` | 随机生成的文本短语 | `Phrase` |
| `event` | 改变宇宙状态的脚本事件 | `GameEvent` |
| `fleet` | 预定义的舰船编队 | `Fleet` |
| `interface` | UI 布局定义（标签、按钮、进度条） | `Interface` |
| `galaxy` | 包含多个星系的星系团（用于背景渲染） | `Galaxy` |
| `hazard` | 空间环境伤害（如辐射、酸性云） | `Hazard` |
| `substitutions` | 动态文本替换逻辑 | `TextReplacements` |
| `gamerules` / `gamerules preset` | 游戏全局规则设置 | `Gamerules` |
| `color` | 定义全局颜色常量 | `Color` |
| `swizzle` | 定义颜色转换规则 | `Swizzle` |
| `effect` | 定义视觉特效（爆炸、尾迹等） | `Effect` |
| `formation` | 定义舰队阵型模式 | `FormationPattern` |
| `minable` | 定义可开采资源 | `Minable` |
| `outfitter` | 定义装备商店的库存 | `Shop<Outfit>` |
| `shipyard` | 定义船厂的库存 | `Shop<Ship>` |
| `person` | 定义特定的 NPC | `Person` |
| `start` | 定义玩家的初始状态和可选剧本 | `StartConditions` |
| `trade` | 定义商品交易的供需关系 | `Trade` |
| `news` | 定义新闻条目 | `News` |
| `wormhole` | 定义虫洞 | `Wormhole` |
| `message` / `message category` | 定义游戏内消息系统 | `Message` / `Message::Category` |
| `category` | 定义舰船和装备的分类 | `CategoryList` |
| `landing message` | 定义着陆在特定对象上时显示的消息 | `UniverseObjects::LoadFile` (内部逻辑) |
| `star` | 定义恒星的属性（太阳能、太阳风） | `UniverseObjects::LoadFile` (内部逻辑) |
| `rating` | 定义评级文本 | `UniverseObjects::LoadFile` (内部逻辑) |
| `tip` / `help` | 定义工具提示和帮助信息 | `UniverseObjects::LoadFile` (内部逻辑) |
| `disable` | 禁用某个游戏对象（任务、事件等） | `UniverseObjects::LoadFile` (内部逻辑) |
| `test` / `test-data` | 用于自动化测试的数据 | `Test` / `TestData` |


## 特殊标记

- `overwrite`: 放置在任何根节点之前，指示加载器清除该对象之前的定义，以便完全替换。
- `#`: 行注释起始符。
- `add`: 用于在现有对象属性基础上增加值，而不是覆盖（如 `add attributes`）。
- `remove`: 用于从现有对象的列表中移除项目（如 `remove fleet "..."`）。
