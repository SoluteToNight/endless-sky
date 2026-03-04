# Endless Sky 数据文件语法指南 (Data Syntax Guide)

本文档总结了《无尽星空》(Endless Sky) 数据文件（如 `data/map planets.txt`）的通用语法规则。该格式是一种基于缩进的层级化标记语言，旨在平衡人类可读性与解析效率。

## 1. 核心结构 (Core Structure)

数据由**节点 (Node)** 组成，每个节点占据一行。节点之间的父子关系完全由**缩进 (Indentation)** 决定。

### 1.1 缩进规则
*   **必须使用制表符 (Tab)**：所有的缩进必须使用 Tab 字符。解析器会忽略或错误解析使用空格缩进的行。
*   **层级关系**：
    *   **根节点 (Root Node)**：没有缩进的行。定义一个主要对象（如 `planet`, `ship`, `mission`）。
    *   **子节点 (Child Node)**：比父节点多一个 Tab 缩进的行。代表父对象的属性或子组件。
    *   **孙节点及更多层级**：继续增加 Tab 缩进（如 `tribute` 下的 `threshold`）。

### 1.2 注释
*   以 `#` 开头的行或行尾部分为注释，解析器会将其忽略。

```text
# 这是一个注释
planet "Example Planet"  # 定义根对象
	attributes urban     # 缩进一个 Tab 的属性
```

## 2. 词法单元与引用 (Tokens & Quoting)

每一行被拆分为多个 **Token**（词法单元）。Token 的定义取决于其包含的内容：

| Token 类型 | 语法 | 示例 | 适用场景 |
| :--- | :--- | :--- | :--- |
| **普通词 (Simple)** | 无引号 | `attributes`, `4200`, `land/canyon4` | 不含空格的关键字、数值或路径 |
| **短字符串 (Quoted)** | 双引号 `""` | `"Basic Ships"`, `"required reputation"` | 包含空格的名称或短句 |
| **长文本 (Backticked)** | 反引号 `` ` `` | `` description `Welcome to...` `` | 包含换行、双引号或特殊标点的长描述 |

> **注意**：如果 Token 内部包含双引号，必须改用反引号包裹整个 Token。

## 3. 常见对象定义示例 (以 Planet 为例)

参考 `data/map planets.txt`，一个典型的对象定义如下：

```text
planet Ada
	attributes factory mining paradise research
	landscape land/canyon4
	description `Ada is the home planet of Lovelace Labs...`
	shipyard "Basic Ships"
	outfitter "Lovelace Advanced"
	"required reputation" 2
	bribe 0.1
	security 0.9
	tribute 4200
		threshold 8000
		fleet "Large Republic" 16
```

### 3.1 属性列表 (Attribute Lists)
有些行包含多个值，如 `attributes`。解析器会将该行所有 Token 视为一个列表。

### 3.2 嵌套属性 (Nested Attributes)
如 `tribute` 属性，它本身拥有子节点 `threshold` 和 `fleet`。这表示 `tribute` 不仅仅是一个数值，而是一个复杂的配置对象。

## 4. 条件显示逻辑 (Conditional Logic)

游戏支持通过 `to display` 块实现动态文本或属性：

```text
planet "Buccaneer Bay"
	description `Modified description for Syndicate.`
		to display
			has "start: syndicate"
	description `Original description.`
		to display
			not "start: syndicate"
```

*   **to display**：定义一个逻辑块。
*   **逻辑操作符**：支持 `not`, `or`, `and` 及其组合。
*   **变量引用**：支持引用任务变量、游戏日期或起始背景。

## 5. 多行追加 (Multiline Appending)

对于 `description` 或 `spaceport` 等文本类属性，多次出现同名关键字会将文本自动拼接（通常会自动插入换行符）：

```text
planet Earth
	description `Paragraph 1...`
	description `	Paragraph 2 (indented with a tab inside backticks).`
```

## 6. 插件覆盖机制 (Plugin Overrides)

如果两个文件中定义了同名的根节点（如两个文件都有 `planet Ada`）：
1.  **单值属性**：后加载的文件会覆盖先加载的文件（如 `bribe`）。
2.  **列表属性**：后加载的文件会向列表中追加内容（如 `shipyard`, `outfitter`）。
3.  **删除属性**：使用特殊语法（通常是重新定义对象并留空或特定指令，取决于具体对象类型）。

---
*本文档基于 Endless Sky 源代码中 `DataNode` 与 `DataFile` 类的逻辑总结。*
