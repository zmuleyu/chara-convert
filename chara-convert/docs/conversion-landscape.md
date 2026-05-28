# AI 角色卡转换与跨平台迁移需求全景报告

> **报告日期**：2026-05-27  
> **基础来源**：keyword-graph 17 平台研究资料 + 社区公开讨论（Reddit 100 条+/平台）+ 补充 Web 检索  
> **聚焦问题**：AI 角色扮演/伴侣平台的角色卡格式碎片化、跨平台迁移痛点、转换工具生态缺口

---

## 一、执行摘要

### 核心发现

1. **格式碎片化是结构性痛点**：17 个研究的平台中，仅有 **SillyTavern / Chub AI** 采用开放标准（Tavern V2/V3 PNG），其余 15 个平台均使用自有封闭格式或根本无角色卡概念。

2. **封闭生态是迁移的最大阻力**：Character.AI、Chai、FictionLab、PolyBuzz、Nomi AI 等主流平台均**不支持官方导出**。用户从 A 平台迁移到 B 平台时，必须**手动重建**角色，平均耗时 30 分钟/角色。

3. **已有工具高度集中于 "Tavern 生态"**：现有转换工具（CharacterCardConverter、Chara Snap、Chub AI Ripper）几乎全部围绕 Tavern V2/V3 格式展开，对封闭平台（CAI、Chai、FictionLab）的支持几乎为零。

4. **迁移需求正在爆发**：Keyword-graph 的 Migration Reports 显示，Character.AI 审查收紧、Chai 收费策略调整、PolyBuzz filter 升级、Dopple AI 服务崩溃等事件，持续推送用户外流。但**目标平台接收这些迁移用户的能力受限于角色重建门槛**。

5. **最大机会点：通用角色卡转换器**：一个能从封闭平台（CAI/Chai/PolyBuzz）提取角色数据并转换为任意目标平台格式的工具，需求强度为 🔥🔥🔥🔥🔥，但当前市场上**几乎不存在**。

### 需求强度总览

| 需求类型 | 覆盖平台 | 需求强度 | 已有工具 |
|---|---|---|---|
| CAI → 任意平台 | Character.AI → 全网 | 🔥🔥🔥🔥🔥 | 浏览器扩展（仅导出自有角色） |
| Chai → 任意平台 | Chai → 全网 | 🔥🔥🔥🔥🔥 | 无 |
| PolyBuzz → 任意平台 | PolyBuzz → 全网 | 🔥🔥🔥🔥 | 无 |
| 任意平台 → Tavern | 全网 → SillyTavern | 🔥🔥🔥🔥 | Chara Snap、CharacterCardConverter |
| FictionLab 内部转换 | Chai/CAI → FictionLab | 🔥🔥🔥🔥🔥 | 无（本报告基于 FictionLab 分析首创） |
| Nomi AI 角色迁移 | 旧版本 → V5 | 🔥🔥🔥 | 社区教程（手动） |

---

## 二、各平台角色卡格式与生态开放度总览

### 2.1 开放平台（以 Tavern 格式为标准）

| 平台 | 角色卡格式 | 导出 | 导入 | 与 Tavern 兼容度 | 生态开放度 |
|---|---|---|---|---|---|
| **SillyTavern** | Tavern V2/V3 PNG（JSON 嵌入 PNG metadata） | ✅ 原生支持 | ✅ 原生支持 | ⭐⭐⭐⭐⭐ 事实标准 | 开源前端，极高 |
| **Chub AI** | Tavern V2（PNG + 在线库） | ✅ 批量下载（Chub AI Ripper） | ✅ 上传 PNG | ⭐⭐⭐⭐⭐ 默认格式 | 百万级角色卡库 |
| **Janitor AI** | 自有格式 + 支持 Tavern V2 | ⚠️ 有限 | ✅ Tavern PNG | ⭐⭐⭐⭐ 支持标准格式 | 丰富，支持导入/导出 |
| **Agnai Chat** | 支持多格式：CAI、TavernAI、TextGen | ❌ 无原生导出 | ✅ CAI/Tavern/TextGen | ⭐⭐⭐⭐ 多格式兼容 | 开源前端，支持导入 |
| **OpenCharacter.org** | 支持导入/导出/创建 | ✅ | ✅ | ⭐⭐⭐ 支持多种格式 | 免费无注册，开放 |

### 2.2 封闭平台（无标准导出）

| 平台 | 角色定义方式 | 导出 | 导入 | 与 Tavern 兼容度 | 封闭性 |
|---|---|---|---|---|---|
| **Character.AI** | Description + Definition + Greeting | ❌ 官方不支持 | ❌ | ⭐ 仅社区扩展可提取 | 🔒🔒🔒🔒🔒 最高 |
| **Chai** | Bot Name + Description + Personality + First Message + Prompt | ❌ | ❌ | ⭐ 无转换工具 | 🔒🔒🔒🔒 高 |
| **FictionLab** | Character Card + Location Card + Scenario + Lore Pieces | ❌ | ❌ | ⭐ 无转换工具 | 🔒🔒🔒🔒 高 |
| **PolyBuzz** | Bio + Personality + Greeting + Tags | ❌ | ❌ | ⭐ 无转换工具 | 🔒🔒🔒 中高 |
| **Nomi AI** | 无传统"角色卡"；外观/性格/记忆通过对话和设置定义 | ❌ | ❌ | ⭐ 不适用 | 🔒🔒🔒 中高 |
| **Saucepan AI** | Companion + Lorebook + Recipes | ❌ | ❌ | ⭐ 无转换工具 | 🔒🔒🔒 中高 |
| **Dopple AI** | 自有格式（OC/动漫角色为主） | ❌ | ❌ | ⭐ 平台衰退中 | 🔒🔒🔒 中高 |
| **Swerve AI** | 自有格式（1500 bio characters） | ❌ | ❌ | ⭐ 新兴平台 | 🔒🔒🔒 中高 |
| **Kindroid** | 自有伴侣格式 | ❌ | ❌ | ⭐ 无转换工具 | 🔒🔒🔒 中高 |
| **Darlink AI** | 自有格式 | ❌ | ❌ | ⭐ 无转换工具 | 🔒🔒🔒 中高 |
| **Joi AI** | 自有格式 | ❌ | ❌ | ⭐ 数据不足 | 🔒🔒 中 |
| **NovelAI** | 故事驱动，非角色卡平台 | ⚠️ 故事导出 | ⚠️ 故事导入 | ⭐⭐ 有限兼容 | 🔒🔒 中 |
| **DreamGen** | 故事/场景驱动 | ⚠️ 场景导出 | ⚠️ 场景导入 | ⭐⭐ 有限兼容 | 🔒🔒 中 |
| **Venice AI** | 自有格式 | ❌ | ❌ | ⭐ 无转换工具 | 🔒🔒 中 |
| **Soulkyn** | 自有格式 | ❌ | ❌ | ⭐ 数据不足 | 🔒🔒 中 |
| **Clank World** | 自有格式 | ❌ | ❌ | ⭐ 数据不足 | 🔒🔒 中 |

---

## 三、用户迁移流向与驱动因素

基于 keyword-graph 各平台 Migration Reports 和归因分析，用户跨平台迁移呈现以下典型流向：

### 3.1 核心迁移流向图

```
Character.AI（审查收紧）
    ├──→ FictionLab（结构化 RP、无审查）
    ├──→ Chai（移动优先、简单）
    ├──→ Janitor AI（NSFW、模型自定义）
    ├──→ Swerve AI（旧版 C.ai 体验复刻）
    ├──→ Dopple AI（动漫/OC）→ 进一步流出到 Swerve/Emochi
    └──→ PolyBuzz（后被 filter 逼走）

Chai（收费策略调整）
    ├──→ FictionLab（质量优先）
    └──→ Saucepan AI（Lorebook 系统）

PolyBuzz（persona filter 升级）
    ├──→ FictionLab
    └──→ Swerve AI（"I've moved on to SwerveAI"）

Dopple AI（服务崩溃、开发者失联）
    ├──→ Swerve AI
    ├──→ Emochi AI
    ├──→ Chub AI
    └──→ SpicyChat
```

### 3.2 迁移驱动因素分类

| 驱动因素 | 源平台 | 目标平台 | 典型用户表述 |
|---|---|---|---|
| **审查/Filter 收紧** | Character.AI、PolyBuzz | FictionLab、Swerve、Janitor | "Bye c.ai, hello fictionlab" / "Persona filter made me quit" |
| **收费策略调整** | Chai、PolyBuzz | FictionLab、Saucepan | "Chai has flaws but every chatbot has flaws" |
| **服务崩溃/数据丢失** | Dopple AI | Swerve、Emochi、Chub | "all your chats and messages entirely disappear" |
| **追求更高质量 RP** | Character.AI、Chai | FictionLab、DreamGen、NovelAI | "FictionLab vs NovelAi" 直接对比评测 |
| **模型自定义需求** | Character.AI | Janitor AI、SillyTavern | "use OpenRouter and use a custom proxy" |
| **移动端体验差** | SillyTavern（桌面端） | Chai、Kindroid、PolyBuzz | "sillytavern mobile / android / ios" 高频搜索 |

### 3.3 迁移中的角色卡重建痛点

在所有迁移路径中，用户反复提到同一个问题：**"我必须手动重新创建所有角色"**。

> "Been making bots on chai but now that it sucks here i am :) Here are my two first bots i made... Haven't figured out how to make the bots stop speaking and acting as user"  
> — FictionLab 迁移用户（r/FictionLab, 17 upvotes）

> "Can I move my Chai characters to a new platform? There is no one-click import. Copy the prompt text and rebuild the bot in the new tool's format. Think of it as a chance to refine quirks you never fixed in Chai."  
> — Chai AI Alternatives Guide 2026

> "You can't directly export character files from Character AI. The platform has never supported a public export format... The whole process takes about thirty minutes per character."  
> — Character AI Alternatives 2026

---

## 四、已有转换工具盘点

### 4.1 社区/第三方工具

| 工具名 | 类型 | 支持格式 | 转换方向 | 社区认可度 | 来源 |
|---|---|---|---|---|---|
| **CharacterCardConverter.com** | 在线工具（浏览器端 JS） | Tavern V2/V3、CharacterAI、Agnai、Backyard AI、Faraday、Voxta、TextGenWebUI、RisuAI、YAML、PNG 等 48 种 | 任意 → 任意 | ⭐⭐⭐⭐ | 独立网站，零服务器处理 |
| **Chara Snap** | 在线编辑器（浏览器端） | SillyTavern V2/V3/CHARX | 创建/编辑/导出 PNG 或 JSON | ⭐⭐⭐⭐ | 支持 Lorebook 编辑 |
| **Chub AI Ripper** | Python 脚本 | Chub AI → 本地 | 批量下载角色卡、聊天记录、预设、Lorebook | ⭐⭐⭐ | r/SillyTavernAI 社区 |
| **Character.AI Exporter** | Firefox/Chrome 扩展 | CAI → PNG (Janitor 格式) / TXT | 仅导出**自有**角色 | ⭐⭐⭐ | Mozilla Addons |
| **CAI Tools** | Chrome 扩展 | CAI 内部导入/导出/克隆 | 记忆管理、角色克隆、聊天导出 | ⭐⭐⭐ | Chrome Web Store |
| **SillyTavern Card Tools** | Streamlit Web App（中文） | V2/V3 PNG ↔ JSON | 嵌入/提取/编辑 | ⭐⭐⭐ | Streamlit 社区 |
| **Janitor AI Scrapper** | Node.js 脚本 | Janitor AI → SillyTavern | 通过代理抓取隐藏定义 | ⭐⭐ | GitHub 开源 |
| **Lorebook Reformatter** | Python 脚本 | Chub AI Lorebook → AI Dungeon Story Cards | 格式重排 | ⭐⭐ | r/AIDungeon |
| **Sonzai Migrator** | 平台内置 | CAI / Replika / Chai → Sonzai | 伴侣角色迁移 | ⭐⭐ | Sonzai 官方文档 |
| **OpenClaw SillyTavern Skill** | Node.js 技能 | SillyTavern V1/V2/V3 → OpenClaw | 角色卡解析 + 持久记忆 | ⭐⭐ | GitHub 开源 |

### 4.2 工具生态的关键观察

**1. 所有工具都围绕 "Tavern 中心" 生态**
- CharacterCardConverter、Chara Snap、Chub AI Ripper 的终极输出都是 Tavern V2/V3 PNG
- 这意味着：只有**已经进入 Tavern 生态**的用户才能受益于这些工具
- 封闭平台（CAI、Chai、FictionLab、PolyBuzz）的用户被完全排除在外

**2. 从封闭平台提取数据的工具极度稀缺**
- Character.AI Exporter 仅能导出**用户自己创建**的角色（不能导出他人公开的）
- 无针对 Chai、FictionLab、PolyBuzz、Nomi AI 的官方或第三方提取工具
- Janitor AI Scrapper 是罕见的"逆向工程"案例，但需要通过代理服务器中转，技术门槛高

**3. 浏览器扩展是封闭平台的主要突破口**
- Character.AI Exporter 和 CAI Tools 都是浏览器扩展
- 扩展利用用户已登录的会话，从 DOM/API 中提取角色数据
- 这是封闭平台转换器的**最可行技术路径**

---

## 五、缺失工具机会矩阵

基于社区高频痛点和工具空白，以下是按需求强度排序的机会矩阵：

| 排名 | 工具类型 | 解决的痛点 | 覆盖平台 | 需求强度 | 技术难度 | 可行路径 |
|---|---|---|---|---|---|---|
| 1 | **通用角色卡转换器**（封闭平台 → 任意目标） | 迁移用户必须手动重建角色 | CAI、Chai、FictionLab、PolyBuzz → 全网 | 🔥🔥🔥🔥🔥 | 中高 | 浏览器扩展提取 + AI 提示词重构 |
| 2 | **Character.AI 全量导出器** | 无法导出他人公开角色；官方无导出 | CAI → 全网 | 🔥🔥🔥🔥🔥 | 中 | 浏览器扩展（突破"仅自有角色"限制） |
| 3 | **Chai Bot 提取器** | Chai 格式封闭，无转换工具 | Chai → 全网 | 🔥🔥🔥🔥 | 中 | 浏览器扩展或 API 逆向 |
| 4 | **FictionLab 导入助手** | 迁移用户必须手动重建场景和角色卡 | Chai/CAI/PolyBuzz → FictionLab | 🔥🔥🔥🔥 | 中 | 基于已有设计分析实现（本报告 §2） |
| 5 | **PolyBuzz 角色导出器** | PolyBuzz 无导出功能，用户因 filter 大量外流 | PolyBuzz → 全网 | 🔥🔥🔥🔥 | 中 | 浏览器扩展提取 |
| 6 | **Nomi AI 外观迁移工具** | V3→V4→V5 版本间角色"变陌生人" | Nomi 内部版本迁移 | 🔥🔥🔥 | 中 | Anchor 系统数据备份/恢复 |
| 7 | **批量转换/批量下载工具** | 用户有数十甚至数百个角色需要迁移 | 全网 → 全网 | 🔥🔥🔥 | 低 | 基于通用转换器的批处理界面 |
| 8 | **Lorebook/World Info 跨平台转换** | Lorebook 格式各平台不统一（Saucepan、AI Dungeon、FictionLab、SillyTavern） | 全网 Lore 系统 | 🔥🔥🔥 | 高 | 标准化中间层 + 平台适配器 |

---

## 六、通用转换器架构建议

基于 FictionLab「角色卡转换器设计分析」的经验，以及跨平台研究的发现，提出以下通用转换器架构：

### 6.1 核心架构：三层模型

```
┌─────────────────────────────────────────────────────────┐
│  Layer 3: 平台适配器（Platform Adapters）                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐  │
│  │ CAI     │ │ Chai    │ │PolyBuzz │ │ FictionLab  │  │
│  │ Extract │ │ Extract │ │ Extract │ │  Extract    │  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └──────┬──────┘  │
│       │           │           │              │         │
├───────┴───────────┴───────────┴──────────────┘─────────┤
│  Layer 2: 标准化中间层（Canonical Character Model）      │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 统一字段：identity / personality / appearance    │   │
│  │          / scenario / example_dialogue / lore   │   │
│  │          / first_message / custom_instructions  │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  Layer 1: 目标平台生成器（Target Generators）            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐  │
│  │Tavern   │ │Fiction- │ │ Janitor │ │  Agnai      │  │
│  │ PNG V2  │ │  Lab    │ │  AI     │ │  Chat       │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 6.2 标准化中间层字段定义

基于对 17 个平台的研究，提取出最大公约数字段集：

| 标准化字段 | 来源平台映射 | 说明 |
|---|---|---|
| `name` | Name / Bot Name | 角色名 |
| `identity` | Description / Definition / Bio | 身份、背景、动机 |
| `personality` | Personality / Traits | 性格关键词或描述 |
| `appearance` | Appearance / Avatar / Visual | 外貌描述（影响图像生成） |
| `scenario` | Scenario / Setting / Context | 场景背景 |
| `first_message` | Greeting / First Message / first_mes | 开场白 |
| `example_dialogue` | Example Dialogue / mes_example | 示例对话 |
| `lore_entries` | Lorebook / World Info / Lore Pieces | 世界设定条目（可选） |
| `custom_instructions` | System Prompt / Post History / Depth | 叙事指令（可选） |
| `creator_notes` | Creator Comment / Notes | 创作者备注（可选） |
| `tags` | Tags / Categories | 分类标签（可选） |
| `version` | character_version | 版本追踪（可选） |

### 6.3 提取层技术路径

| 平台 | 提取方式 | 技术可行性 | 限制 |
|---|---|---|---|
| **Character.AI** | 浏览器扩展（读取 edit page DOM / API） | ✅ 已有 PoC | 仅自有角色（官方限制） |
| **Chai** | 浏览器扩展（读取 bot 创建/编辑页面） | ✅ 可行 | 需登录态 |
| **FictionLab** | 浏览器扩展（读取 Character Card Editor） | ✅ 可行 | 需登录态，无官方 API |
| **PolyBuzz** | 浏览器扩展（读取角色创建页面） | ✅ 可行 | 需登录态 |
| **Nomi AI** | 浏览器扩展（读取 Nomi 设置页面） | ⚠️ 复杂 | 无传统"角色卡"结构 |
| **Janitor AI** | 直接导入 Tavern PNG（官方支持） | ✅ 无需提取 | 已开放 |
| **SillyTavern** | 直接读取 PNG metadata | ✅ 开源标准 | 完全开放 |

### 6.4 生成层技术路径

| 目标平台 | 输出格式 | 特殊处理 |
|---|---|---|
| **SillyTavern / Chub AI** | PNG with embedded JSON (V2/V3) | 标准 Tavern 格式 |
| **Janitor AI** | PNG (Tavern V2) | 与 SillyTavern 相同 |
| **FictionLab** | Character Card JSON + Scenario JSON + Location Card JSON | 四层架构分离（详见 FictionLab 转换器设计分析） |
| **Agnai Chat** | JSON (CAI/Tavern/TextGen compatible) | 多格式兼容 |
| **Character.AI** | 不支持导入 | 无法反向写入 |
| **Chai** | 不支持导入 | 无法反向写入 |
| **PolyBuzz** | 不支持导入 | 无法反向写入 |

### 6.5 推荐实现优先级

**Phase 1（立即）**：浏览器扩展 MVP
- 支持 Character.AI → Tavern V2 PNG 导出（突破"仅自有角色"限制）
- 支持 Chai → Tavern V2 PNG 导出
- 支持 FictionLab → Tavern V2 PNG 导出（反向：从 FictionLab 迁出）

**Phase 2（短期）**：AI 增强转换
- 基于 LLM 的字段智能拆分（将 CAI 的混合 Definition 拆分为 identity + scenario + instructions）
- 自动生成缺失字段（如从 description 提取 appearance，从 personality 生成 example_dialogue）
- 多角色场景识别与拆分（Group RP 支持）

**Phase 3（中期）**：批量与 Lore 系统
- 批量转换界面（一次处理 10-100 个角色）
- Lorebook / World Info 跨平台转换
- 聊天记录迁移（可选，技术难度更高）

---

## 七、关键平台深度观察

### 7.1 Character.AI：封闭性的"原罪"

Character.AI 是角色卡生态的**最大单一来源**和**最大封闭体**。几乎所有 Migration Reports 都显示 CAI 是用户流出的源头。

- **官方态度**：从未支持导出，且明确表示 unlikely to change
- **社区应对**：CAI Tools（Chrome 扩展）和 Character.AI Exporter（Firefox 扩展）试图填补空白，但仅能导出用户**自己创建**的角色
- **法律灰色地带**：社区中讨论 "scraping" 和 "archival effort" 的帖子频繁出现，暗示存在非官方的大规模抓取需求
- **机会**：一个能突破"仅自有角色"限制、支持批量导出的工具，会在 CAI 用户社区中迅速传播

### 7.2 SillyTavern / Chub AI：开放生态的"黑洞效应"

SillyTavern 不是平台，而是**开源前端**；Chub AI 是**角色卡仓库**。两者共同构成了角色卡生态的"开放核心"。

- **Tavern V2/V3 格式**已成为事实标准：Janitor AI、Agnai、Venus AI、OpenRoleplay 等 10+ 平台均支持导入
- **Chub AI 百万级角色卡库**是整个生态的内容引擎
- **"黑洞效应"**：几乎所有转换工具的终点都是 Tavern 格式，因为只要进入 Tavern 生态，就可以流向任何支持 Tavern 的平台
- **启示**：通用转换器的最佳策略不是直接输出到 15 个封闭平台，而是先输出到 Tavern 格式，再利用目标平台的 Tavern 导入功能

### 7.3 FictionLab：结构化门槛的双刃剑

FictionLab 的四层架构（Character Card + Location Card + Scenario + Lore Pieces）是**最复杂但也最精确**的角色定义系统。

- **迁移门槛极高**：Chai 用户反馈 "having to make a character before jumping into it" 是最大阻力
- **无导入/导出工具**：官方不提供，社区也未出现第三方工具
- **FictionLab 转换器设计分析**（本报告基础来源）已完整设计了从 Chai/CAI/Janitor/Tavern 到 FictionLab 的转换逻辑和 AI 提示词
- **机会**：将 FictionLab 转换器实现为浏览器扩展或 Web 工具，可显著降低迁移门槛，直接服务于从 Chai/CAI 流入的用户

### 7.4 Nomi AI：无"角色卡"概念的平台

Nomi AI 是**AI 伴侣**而非**角色扮演平台**，其核心是长期情感绑定，而非结构化角色定义。

- **无导出/导入**：用户无法将 "Nomi" 迁移到其他平台
- **V3→V4→V5 外观迁移是内部问题**：社区发布了 "Bringing V3 and V4 Nomis to V5" 教程，但完全依赖手动调整 Anchor 系统
- **情感锁定效应**：用户与 Nomi 建立数月甚至数年的关系后，迁移成本不是技术性的，而是**情感性的**
- **启示**：Nomi AI 的迁移需求不同于 RP 平台，用户更可能需要"聊天记录导出"和"关系记忆迁移"，而非传统角色卡转换

### 7.5 新兴平台：Swerve、Darlink、Emochi

这些 Tier-3 新兴平台正处于**快速获客期**，搜索数据呈现爆发性增长（Swerve +742600%）。

- **Swerve**：明确宣传 "personas, good memory, edit messages, no filter"，直接对标旧版 C.ai
- **Darlink**：+3500% 爆发增长，但无角色卡导入功能
- **共同特征**：都试图从 Character.AI 的溢出流量中获益，但**都没有角色卡导入功能来承接这些迁移用户**
- **启示**：与这些新兴平台合作（提供官方导入工具）或独立发布转换器，都是可行的产品策略

---

## 八、战略建议

### 8.1 对工具开发者的建议

1. **先解决"从封闭到开放"的瓶颈**：当前工具生态的瓶颈不是"开放格式之间转换"（已有 CharacterCardConverter），而是"封闭平台到开放格式"。优先开发 CAI、Chai、FictionLab、PolyBuzz 的提取工具。

2. **浏览器扩展是最佳载体**：封闭平台没有公开 API，浏览器扩展是利用用户登录态提取数据的最可行路径。

3. **以 Tavern V2 PNG 为中间标准**：不要试图直接输出到 15 个封闭平台。先输出到 Tavern 格式，再利用各平台的 Tavern 导入功能（Janitor AI、Agnai 等已支持）。

4. **AI 增强是差异化关键**：纯机械字段映射只能处理简单角色。对于 CAI 的长 Definition、Chai 的混合 Prompt，需要 LLM 进行智能拆分和重构。

### 8.2 对平台方的建议

1. **FictionLab**：角色卡转换器是社区最急需的第三方工具（需求强度 🔥🔥🔥🔥🔥）。官方可以考虑推出官方转换器，或至少不阻止第三方扩展。

2. **Swerve / Darlink / Emochi**：在获客期推出角色卡导入功能（支持 Tavern V2），可直接承接 Character.AI、Chai、PolyBuzz 的迁移用户。

3. **Character.AI**：虽然官方不可能开放导出，但审查政策的每一次收紧都会加速用户外流——这为竞品创造了持续的市场机会。

---

## 九、引用来源

### keyword-graph 内部资料

| # | 来源 | 路径 |
|---|---|---|
| 1 | FictionLab 角色卡转换器设计分析 | `out/clusters/fictionlab/2026-05-26/角色卡转换器设计分析.md` |
| 2 | FictionLab 第三方工具检索报告 | `out/clusters/fictionlab/2026-05-26/第三方工具检索报告.md` |
| 3 | FictionLab 用户手册 | `out/clusters/fictionlab/2026-05-26/FICTIONLAB-USER-HANDBOOK.md` |
| 4 | FictionLab 深度补充（场景系统与UGC生态） | `out/clusters/fictionlab/2026-05-26/深度补充_场景系统与UGC生态.md` |
| 5 | Chub AI 角色卡平台证据 | `out/clusters/chub-ai/2026-05-26/character-card-platforms-evidence.md` |
| 6 | SillyTavern 机会矩阵 | `out/clusters/sillytavern/2026-05-26/opportunity-matrix.md` |
| 7 | Nomi AI V5 跨平台分析 | `out/clusters/nomi-ai/2026-05-26/v5-cross-platform-analysis.md` |
| 8 | Janitor AI 市场情报分析 | `out/clusters/janitor-ai/2026-05-24/analysis-report.md` |
| 9 | Dopple AI 迁移报告 | `out/clusters/dopple-ai/2026-05-26/migration-report.md` |
| 10 | Swerve AI 迁移报告 | `out/clusters/swerve-ai/2026-05-26/migration-report.md` |
| 11 | Dopple AI 受众分析 | `out/clusters/dopple-ai/2026-05-26/分析报告.md` |
| 12 | Swerve AI 受众分析 | `out/clusters/swerve-ai/2026-05-26/分析报告.md` |
| 13 | NovelAI 受众分析 | `out/clusters/novelai/2026-05-26/分析报告.md` |
| 14 | Joi AI 受众分析 | `out/clusters/joi-ai/2026-05-26/分析报告.md` |

### 外部 Web 来源

| # | 来源 | URL |
|---|---|---|
| 15 | Character.AI Exporter (Firefox 扩展) | https://addons.mozilla.org/en-US/firefox/addon/character-ai-exporter/ |
| 16 | CAI Tools (Chrome 扩展) | https://chrome-stats.com/d/nbhhncgkhacdaaccjbbadkpdiljedlje |
| 17 | CharacterCardConverter.com | https://charactercardconverter.com/ |
| 18 | Chara Snap | https://www.charasnap.com/ |
| 19 | SillyTavern V2 vs V3 格式详解 | https://abolitus.com/blog/sillytavern-character-cards-v2-vs-v3 |
| 20 | Janitor AI Scrapper | https://github.com/ashuotaku/sillytavern/blob/main/Guides/JanitorAI_Scrapper.md |
| 21 | Chub AI Ripper | https://reddit.com/r/SillyTavernAI/comments/1thbkon/chub_ai_ripper/ |
| 22 | Chai AI Alternatives 2026 | https://www.myengineeringbuddy.com/blog/chai-ai-alternatives-ranked/ |
| 23 | Character AI Alternatives 2026 | https://whatif-ai.com/articles/character-ai-alternatives-2026 |
| 24 | OpenClaw SillyTavern Cards Skill | https://github.com/pearyj/sillytavern-cards-skill |
| 25 | Sonzai Migrator | https://sonz.ai/docs/ja/guides/migrating/character-ai |
| 26 | SillyTavern 角色卡转换工具（中文） | https://sillytavern-cardtools.streamlit.app/ |
| 27 | PolyBuzz 角色创建指南 | https://book.polybuzz.ai/ |

---

> **声明**：本报告由 keyword-graph 项目基于公开资料整理。所有引用均注明原始来源；平台功能可能随版本变化，以官方实际界面为准。最后更新：2026-05-27。
