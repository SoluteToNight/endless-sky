# Endless Sky 字体渲染现代化技术路线图 (Unified TTF Roadmap)

本文档概述了将《无尽星空》从“静态 ASCII 纹理条”迁移到“基于 FreeType 的通用 TTF 动态渲染系统”的技术路线。

## 1. 目标 (Goals)
*   **全语言支持**：原生支持 UTF-8，彻底解决中文、日文、韩文无法显示的问题。
*   **统一渲染管线**：移除 PNG 纹理条硬编码逻辑，所有文字（含英文）均通过 TTF 渲染。
*   **高性能表现**：引入动态纹理图集与批处理渲染，确保在高密度文本下不掉帧。
*   **平滑迁移**：保持与现有 `data/` 语法的兼容性(参考'docs/DATA_SYNTAX.md')，支持平滑过渡到汉化文本。

## 2. 核心架构变更 (Architecture Shift)

| 特性 | 旧架构 (Legacy) | 新架构 (Modernized) |
| :--- | :--- | :--- |
| **数据源** | 98 字符水平 PNG 纹理条 | 标准 `.ttf` / `.otf` 矢量字体文件 |
| **字形加载** | 启动时一次性载入 | 运行时按需加载 (On-demand) |
| **纹理管理** | 静态 UV (1/98 步长) | 动态纹理图集 (Dynamic Texture Atlas) |
| **渲染方式** | 逐字符 Draw Call | 顶点缓冲批处理 (Vertex Batching) |
| **排版逻辑** | 仅空格断行 (English-only) | CJK 友好断行算法 (Unicode-aware) |

## 3. 详细实施阶段 (Phases)

### 第一阶段：基础设施与依赖 (Dependencies)
1.  **CMake 更新**：引入 `FreeType` 库。
    *   修改 `CMakeLists.txt` 添加 `find_package(Freetype REQUIRED)`。
    *   在编译选项中链接 `Freetype::Freetype`。
2.  **着色器重写**：修改 `shaders/font.vert`。
    *   **移除**：基于 98 索引的 UV 计算。
    *   **新增**：接收每个字形在图集中的具体 `uv_rect`。

### 第二阶段：动态纹理图集 (Texture Management)
1.  **实现 `TextureAtlas` 类**：
    *   管理一张大的 OpenGL 纹理（建议 1024x1024 或更高）。
    *   实现 **Shelf Packing** 空间分配算法。
    *   支持 `glTexSubImage2D` 动态上传新字符位图。
2.  **实现 `GlyphCache`**：
    *   使用 `std::unordered_map<char32_t, GlyphInfo>` 存储已缓存字符的 UV 信息。

### 第三阶段：渲染类重构 (Font & FontSet)
1.  **重构 `Font` 类**：
    *   初始化时使用 FreeType 加载字体文件而非 PNG。
    *   `Font::Draw`：改用 `Utf8::DecodeCodePoint` 遍历字符串。
    *   **字体栈 (Font Stack)**：支持加载多个 TTF。如果主字体（如 Ubuntu）缺少某个字符（如汉字），自动回退到备选字体（如思源黑体）。
2.  **宽度与字距**：
    *   从 FreeType 接口获取 `advance` 和 `kerning` 数据，废弃原有的“像素扫描”逻辑。

### 第四阶段：UI 与排版增强 (Layout & UI)
1.  **CJK 断行逻辑**：修改 `WrappedText::Wrap`。
    *   增加对多字节字符的判断，允许在汉字之间直接断行。
    *   处理中文标点的“避头尾”逻辑。
2.  **UTF-8 安全化**：
    *   全局搜索并替换 `toupper`, `tolower` 等单字节操作，确保其在处理 UTF-8 字符串时不破坏内存。

### 第五阶段：性能优化 (Optimization)
1.  **顶点批处理 (Batching)**：
    *   在 `Font::Draw` 内部不再直接调用 `glDrawArrays`。
    *   将一段文本的所有顶点存入 VBO，最后一次性绘制，将 Draw Call 降至最低。

## 4. 迁移与兼容性说明

*   **英文渲染**：由于直接使用原版 `Ubuntu.ttf`，英文的字形样式将完美保留，且由于使用了矢量的渲染精度，高分辨率下的清晰度会更高。
*   **Modding 兼容**：现有的 `data/` 文件不需要修改。未翻译的英文文本将自动使用 TTF 里的英文部分，已翻译的中文文本将自动调用中文字库。
*   **字体选择**：建议默认打包一个轻量级的中文字体（如 `SourceHanSans-Subset`）以确保开箱即用。

---
*Created by Gemini CLI - Modernization Project v1.0*
