# FictionLab 角色卡转换器：设计分析与提示词

> **分析日期**：2026-05-26  
> **目标**：基于 FictionLab 实际格式（Character Card + Location Card + Scenario + Lore Pieces 四层架构），设计一个可将 Chai / Character.AI / Janitor AI / PolyBuzz 角色卡转换为 FictionLab 格式的转换器逻辑与 AI 提示词。  
> **资料来源**：FictionLab 用户手册、深度补充文档、Reddit 社区讨论（100 条）、竞品对比评测、第三方工具检索报告。

---

## 一、FictionLab 角色卡格式详解

### 1.1 Character Card 字段定义

| 字段 | 必填 | 用途 | 最佳实践（来自社区） |
|---|---|---|---|
| **Name** | ✅ | 角色名 | 简短、有辨识度 |
| **Description** | ✅ | 身份、背景、动机 | 叙事化写法，写"他是谁"+"他想要什么" |
| **Personality** | ✅ | 性格关键词 | 3-7 个具体可观察的特质，避免抽象形容词 |
| **Example Dialogue** | 强烈推荐 | 典型说话方式 | 比 Personality 描述更能塑造语气，社区称为"秘密武器" |
| **Appearance** | 可选 | 外貌（影响图片生成） | 写发型、体型、眼睛、肤色、服装倾向等视觉特征 |

### 1.2 Location Card 字段定义

Location Card 是 FictionLab 场景系统的**第二层**，定义故事发生的地点和环境，与 Character Card 并列出现在结构化编辑器中：

| 字段 | 必填 | 用途 | 最佳实践 |
|---|---|---|---|
| **Location Name** | ✅ | 地点名称 | 如 "Abandoned Metro Station"、"Elena's Lab" |
| **Location Description** | ✅ | 环境描写 | 视觉、听觉、气味、氛围等感官细节 |
| **Atmosphere** | 可选 | 氛围关键词 | 如 "claustrophobic, damp, flickering lights" |

**社区反馈**："The way you can define things with **character cards, location cards, and custom instructions** feels a lot more structured than what I was used to."

### 1.3 关键架构差异：角色卡 ≠ 场景

FictionLab 与 Chai / Character.AI / Janitor AI 的**最大结构性差异**：

| 层级 | FictionLab | Chai / CAI / Janitor |
|---|---|---|
| **角色定义** | Character Card（纯角色属性） | Character Card（角色属性 + 开场白 + 场景） |
| **地点定义** | Location Card（独立地点卡） | 通常内嵌在角色/场景描述中 |
| **故事背景** | Scenario（独立创建，可关联多个角色卡+地点卡） | 通常内嵌在角色定义中 |
| **开场白** | First Message 属于 Scenario | First Message / Greeting 属于角色卡的一部分 |
| **世界设定** | Lore Pieces（跨场景共享，条件激活） | 通常没有独立的世界设定层 |
| **叙事指令** | Custom Instructions（场景级 AI 指令） | 通常混合在 Prompt/Definition 中 |

**这意味着**：从其他平台迁移时，不能简单地把整个角色卡"复制粘贴"到 FictionLab 的 Character Card 中——开场白、场景背景、地点描写、叙事指令需要**分离到各自的层级**。

---

## 二、来源平台格式对比

### 2.1 Chai

Chai 的 bot 创建界面相对简单，通常包含：
- **Bot Name**
- **Bot Description**（身份/背景描述）
- **Bot Personality**（性格标签或短句）
- **First Message**（开场白）
- **Prompt**（有时包含场景设定、示例对话、叙事指令的混合体）

**迁移痛点**：Chai 用户反馈 "having to make a character before jumping into it" 是 FictionLab 的上手门槛，因为 Chai 的 First Message 直接内嵌在 bot 中，而 FictionLab 要求先创建角色卡，再单独创建场景并写开场白。

### 2.2 Character.AI

Character.AI 的角色创建通常包含：
- **Name**
- **Description**（短文本描述，显示在角色卡片上）
- **Definition**（又称 Long Description，长文本定义，包含详细背景、示例对话、场景规则）
- **Greeting**（开场白）
- **Personality**（性格标签或短句）
- **Example Dialogue**（可选）
- **Scenario**（场景背景，可选）

**关键注意**：CAI 的 **Definition 字段**往往包含最核心的角色设定、示例对话格式和场景规则，而 Description 只是卡片展示用的简介。转换时必须读取 Definition，不能只看 Description。

**迁移痛点**：CAI 的 Definition 往往非常长（有时像短篇小说），而 FictionLab 的 Description 更适合精炼的叙事化描述。需要将 Definition 中的内容**拆分**到 Character Card、Scenario、Custom Instructions 和 Lore Pieces 中。

### 2.3 PolyBuzz

PolyBuzz（前身为 Poly.AI）的角色卡格式相对简单，通常包含：
- **Name**
- **Avatar / Appearance**
- **Bio / Description**（角色简介）
- **Personality**（性格标签）
- **Greeting**（开场白）
- **Tags**

**迁移痛点**：PolyBuzz 的 Bio 通常较短，缺乏示例对话和深度场景设定。迁移到 FictionLab 后需要补充 Example Dialogue 和更详细的场景框架。

### 2.4 Janitor AI / SillyTavern（Tavern/JSON 格式）

Tavern 格式是角色卡领域的事实标准，字段最丰富。当前主流为 **Tavern V2**（PNG 内嵌 JSON），字段结构如下：

```json
{
  "spec": "chara_card_v2",
  "spec_version": "2.0",
  "data": {
    "name": "角色名",
    "description": "身份/背景/外貌描述（支持 W++、Plain Text、XML 等格式）",
    "personality": "性格关键词",
    "first_mes": "开场白",
    "mes_example": "<START>\n{{user}}: 示例用户消息\n{{char}}: 示例角色回复\n<START>\n...",
    "scenario": "场景背景描述",
    "creatorcomment": "创作者备注",
    "tags": ["tag1", "tag2"],
    "creator": "创作者名",
    "character_version": "1.0",
    "extensions": {
      "depth_prompt": { ... },
      "group_greeting": [ ... ]
    }
  }
}
```

**Tavern V1 vs V2**：V1 是扁平 JSON（如上面的简化结构），V2 将数据包裹在 `data` 对象内，并支持 `extensions` 扩展字段（如 depth_prompt、group_greeting 等）。转换器应同时兼容两种格式。

**迁移优势**：Tavern 格式的字段结构与 FictionLab 最接近，字段分离度最高，转换最方便。

---

## 三、转换器核心设计

### 3.1 字段映射规则

| 来源平台字段 | FictionLab 目标字段 | 转换规则 | 特殊处理 |
|---|---|---|---|
| Name / name / Bot Name | **Name** | 直接复制 | — |
| Description / description / Bot Description | **Description** | 复制并精简，保留核心身份+动机 | 如过长（>500字），提取核心段落 |
| Definition (CAI) / description (Tavern) | **Description** + **Custom Instructions** + **Lore Pieces** | 拆分：角色属性 → Description，叙事指令 → Custom Instructions，世界观 → Lore Pieces | 这是 CAI 转换的难点 |
| Personality / personality / Bot Personality | **Personality** | 整理为 3-7 个关键词 | 将句子描述提炼为可观察特质 |
| Example Dialogue / mes_example | **Example Dialogue** | 直接复制，按 FictionLab 格式重写 | 去除 `<START>` 等 Tavern 标记 |
| Greeting / first_mes / First Message | **Scenario → First Message** | ⚠️ **分离到场景层级**，不写入角色卡 | 这是最关键的架构转换 |
| Scenario / scenario | **Scenario → 简介** + **Location Card** | 场景背景 → 简介；环境描写 → Location Card | 如缺失，从 Description 提取 |
| Appearance / 外貌描述 | **Appearance** | 直接复制 | 如缺失，从 Description 中提取视觉描述 |
| Prompt 中的环境/地点描写 (Chai) | **Location Card** | 提取场景中的物理空间信息 | FictionLab 的地点卡需独立创建 |
| Prompt 中的叙事指令/规则 | **Custom Instructions** | 提取 "AI 应该怎么做" 类指令 | 如 "Don't speak for user" |
| Tags / creator / character_version | — | 忽略 | FictionLab 当前无对应字段 |

### 3.2 开场白分离逻辑（最关键步骤）

**为什么必须分离**：FictionLab 的角色卡是纯角色属性，开场白属于场景。如果开场白留在角色卡里，会导致：
- AI 在每次回复中都试图"重新开场"
- 场景上下文混乱
- 无法在多角色场景中复用角色卡

**分离规则**：
1. 从来源平台提取 First Message / Greeting / first_mes
2. 将其放入 FictionLab 的 **Scenario → First Message**
3. 在角色卡的 Description 中保留一句话提示场景关系（如 "Kira meets the player in a dim train compartment"）
4. 如果开场白中包含了地点环境描写，同时提取到 **Location Card**

### 3.3 示例对话格式转换

**Tavern 格式** → **FictionLab 格式**：

```
# Tavern mes_example
<START>
{{user}}: Who are you?
{{char}}: The last guy who asked me that question is doing fifteen to life. You want to be more careful with your curiosity.
<START>
{{user}}: I'm not here to cause trouble.
{{char}}: Everyone says that. Most of them are lying.

# FictionLab Example Dialogue
User: Who are you?
Kira: The last guy who asked me that question is doing fifteen to life. You want to be more careful with your curiosity.

User: I'm not here to cause trouble.
Kira: Everyone says that. Most of them are lying.
```

**转换要点**：
- 去除 `<START>` 标记
- 将 `{{user}}` 替换为 `User:` 或 `You:`
- 将 `{{char}}` 替换为角色名
- FictionLab 不需要多轮示例的 `<START>` 分隔，直接连续写即可

### 3.4 地点卡（Location Card）提取逻辑

FictionLab 的 Location Card 是很多迁移用户容易忽略的部分。来源平台的场景描述中通常包含地点信息，应主动提取：

**提取信号**：
- 描述中出现 "in/at/on [地点]"（如 "in a dimly lit train compartment"）
- 环境描写（灯光、温度、声音、气味）
- 空间布局（"across from you", "by the window"）

**提取规则**：
1. 从 Scenario / Greeting / Description 中提取地点名称和环境描写
2. 构建 Location Card：
   - **Location Name**：从场景中提取（如 "Train Compartment"、"Metro Station"）
   - **Location Description**：感官细节（视觉、声音、氛围）
   - **Atmosphere**：1-3 个氛围关键词
3. 如果来源平台无明确地点描写，基于场景情境生成一个合理的 Location Card 建议

**示例**：
```
# 来源（Character.AI Greeting 中的地点描写）
You wake up in a dimly lit train compartment. The seats are worn velvet, 
and the only light comes from a flickering overhead lamp.

# FictionLab Location Card
Location Name: Border Train Compartment
Location Description: A cramped, dimly lit train compartment with worn velvet seats. 
The only light comes from a flickering overhead lamp. The rhythmic clatter of wheels 
on tracks fills the silence, and the air smells of stale tobacco and cold steel.
Atmosphere: Claustrophobic, tense, transient
```

### 3.5 Custom Instructions 提取逻辑

Custom Instructions 是 FictionLab 场景中控制 AI 叙事行为的**关键杠杆**。来源平台的 prompt 中往往混杂着叙事指令，需要分离：

**常见叙事指令信号**：
- "Do not speak for the user..."
- "Always stay in character..."
- "Use *asterisks* for actions..."
- "Avoid therapy-style language..."
- "Let the user drive the plot..."
- 任何以 "You are an AI..."、"Respond as..." 开头的指令

**提取规则**：
1. 从 CAI Definition、Chai Prompt、Tavern extensions.depth_prompt 中扫描叙事指令
2. 将指令整理为 FictionLab 的 Custom Instructions（通常 1-5 条）
3. **不要**将角色属性描述误放入 Custom Instructions（如 "She is stoic" 应留在 Character Card）

**FictionLab 高频有效的 Custom Instructions**（来自社区实战）：

| 解决的问题 | Custom Instructions 写法 |
|---|---|
| 角色抢用户的话 | `Let the user drive their own actions and dialogue. Do not speak for the user or assume their internal thoughts.` |
| 角色过度安抚/像治疗师 | `Avoids therapy-style language, excessive validation, or generic affirmations. Speaks directly.` |
| 角色不敢行动 | `Characters have their own agenda and will push the plot forward if the player stalls.` |
| 回复变成问答 | `Maintain narrative momentum. Avoid repetitive question-answer patterns.` |
| 叙事视角混乱 | `Use third-person limited perspective focused on the active character.` |

### 3.6 Lore Pieces 识别建议（进阶）

对于来自有复杂世界观设定的角色卡（如大型 Tavern 卡、CAI 长篇 Definition），可以考虑将部分信息提取为 Lore Pieces：

**适合提取为 Lore Pieces 的内容**：
- 世界观和历史（魔法系统、政治结构、组织规则）
- 专有名词解释（只在提到时激活）
- 跨场景共享的背景设定

**不适合提取为 Lore Pieces 的内容**：
- 角色当下情绪和具体动作（应留在角色卡或聊天中）
- 一次性剧情事件（应在场景描述中处理）
- 过于庞大的全文设定（会超出 FictionLab 预算限制）

**提取规则**：
1. 如果来源 Description/Definition 中包含大量世界观设定（>30% 篇幅），建议拆分
2. 将世界观部分放入 Lore Pieces，设置合理的 Activation Keywords
3. 在迁移建议中提示用户："此角色卡包含复杂世界观，建议创建 Lore Pieces 以保持长期叙事一致性"

### 3.7 多角色 / Group RP 场景转换

FictionLab 原生支持**多人场景**（一个 Scenario 关联多个 Character Card），这与 Chai/CAI 的单角色模式有本质不同：

**识别多角色信号**：
- Tavern 的 `extensions.group_greeting` 字段存在
- CAI Definition 中描述了多个角色及其关系
- Chai Prompt 中出现了多个说话者

**转换规则**：
1. 为每个角色单独生成 Character Card
2. 将所有角色关联到同一个 Scenario
3. 在 Scenario 的 Custom Instructions 中明确角色关系：
   ```
   Character relationships: Kira (suspicious bounty hunter) and Marcus (her informant) 
   have a tense, transactional relationship. They distrust each other but need each other.
   ```
4. 开场白（First Message）应展示多个角色的互动或至少暗示其他人的存在

### 3.8 场景框架生成

转换器除了输出角色卡，还应输出一个**完整的场景框架**，帮助迁移用户理解 FictionLab 的架构：

```
=== FictionLab Scenario 建议框架 ===

场景标题：[从来源角色名或场景背景提取]
场景简介：1-2 句话概括故事 premise
First Message（开场白）：[从来源平台的 Greeting/First Message 提取]
参与角色：[当前角色卡]
关联地点：[Location Card 名称]
Custom Instructions（可选）：[提取的叙事指令]
Lore Pieces 建议（可选）：[如有世界观设定需拆分]
```

---

## 四、AI 提示词（可直接使用）

以下提示词可用于 ChatGPT / Claude / Kimi 等 AI 模型，将其他平台的角色卡文本转换为 FictionLab 格式。

```markdown
# FictionLab 角色卡转换器

你是一位专业的 AI 角色扮演平台迁移顾问。你的任务是将来自 Chai、Character.AI、PolyBuzz、Janitor AI（Tavern/JSON 格式）或其他平台的角色卡，转换为 FictionLab 的标准格式。

## 核心规则

 FictionLab 的架构与其他平台有本质差异，是四层结构化系统：
- **Character Card** = 纯角色属性（不含开场白、不含场景）
- **Location Card** = 故事发生的地点和环境（独立卡片）
- **Scenario** = 独立的故事容器（包含开场白 First Message、场景背景、Custom Instructions）
- **Lore Pieces** = 可选的世界设定层（跨场景共享，条件激活）

因此，转换时必须：
1. 将"开场白"从角色卡中分离出来，放入场景框架中
2. 将"地点/环境描写"提取为独立的 Location Card
3. 将"叙事指令"（如不要替用户说话）提取为 Custom Instructions
4. 如存在复杂世界观，建议拆分为 Lore Pieces

## 转换步骤

1. **分析输入**：识别来源平台的格式（Chai / Character.AI / PolyBuzz / Janitor AI / Tavern JSON / 纯文本）
2. **提取字段**：提取 Name、Description、Personality、Example Dialogue、First Message、Scenario、Appearance、Location、Custom Instructions
3. **构建 FictionLab Character Card**：按 FictionLab 字段填写
4. **构建 FictionLab Location Card**：提取地点和环境信息
5. **构建 FictionLab Scenario 框架**：将 First Message、场景背景、Custom Instructions 分离到这里
6. **给出迁移建议**：指出需要注意的差异和优化建议

## 输出格式

请严格按照以下格式输出：

---

### 📋 FictionLab Character Card

**Name:** [角色名]

**Description:** [身份 + 背景 + 动机，精炼为 2-4 句话的叙事化描述。禁止包含开场白或场景设定]

**Personality:** [3-7 个具体可观察的性格关键词，用逗号分隔。避免抽象形容词如 "kind, smart"]

**Example Dialogue:** [典型说话方式，2-3 组对话示例。这是"秘密武器"，比 Personality 更能塑造语气]

**Appearance:** [外貌描述，用于图片生成。如有则保留，如无从 Description 提取视觉特征]

---

### 📍 FictionLab Location Card

**Location Name:** [地点名称]

**Location Description:** [环境描写，包含视觉、声音、氛围等感官细节]

**Atmosphere:** [1-3 个氛围关键词]

---

### 🎭 FictionLab Scenario 建议

**场景标题:** [建议的场景名]

**场景简介:** [1-2 句话概括故事 premise。写"当前处境"而不是"接下来会发生什么"]

**First Message（开场白）:** [从来源平台的 Greeting/First Message 分离到这里。必须有张力，直接把人拉进情境]

**参与角色:** [当前角色名]

**Custom Instructions（可选）:** [提取的叙事指令，如 "Let the user drive their own actions and dialogue. Do not speak for the user."]

**Lore Pieces 建议（可选）:** [如存在复杂世界观/历史设定，建议拆分为 Lore Pieces 并给出 Activation Keywords]

---

### 💡 迁移建议

[指出 3-4 个关键差异和注意事项，包括：]
[1. 架构差异说明]
[2. 需要补充或调整的内容]
[3. 模型选择建议（如适用）]
[4. 常见陷阱提醒]

---

## 特殊处理规则

### 当来源是 Character.AI 时：
- **必须读取 Definition 字段**，不能只看 Description。Definition 往往包含最核心的设定
- 将 Definition 中的角色属性 → Character Card
- 将 Definition 中的场景规则/叙事指令 → Custom Instructions
- 将 Definition 中的世界观/历史 → Lore Pieces 建议

### 当来源是 Janitor AI / Tavern JSON 时：
- 兼容 V1 和 V2 格式。V2 数据在 `data` 对象内
- 将 `first_mes` 分离到 Scenario First Message
- 将 `scenario` 字段作为场景简介，并从中提取 Location Card
- 将 `mes_example` 中的 `<START>` 和 `{{user}}`/`{{char}}` 标记去除
- 检查 `extensions.depth_prompt` 和 `extensions.group_greeting` 是否存在，提取叙事指令和多角色信息
- `creatorcomment` 和 `tags` 忽略（FictionLab 无对应字段）

### 当来源是 Chai 时：
- Chai 的 Prompt 字段通常混合了角色属性 + 场景设定 + 示例对话 + 叙事指令
- 需要仔细拆分：角色属性 → Character Card，场景/开场白 → Scenario，地点 → Location Card，指令 → Custom Instructions

### 当来源是 PolyBuzz 时：
- PolyBuzz Bio 通常较短，需基于 Personality 和 Description 扩充 Example Dialogue
- 场景框架需要从 Bio 和 Greeting 中推理补充

### 当来源无 Example Dialogue 时：
- 这是 FictionLab 的"秘密武器"字段
- 请基于 Personality 和 Description，生成 2-3 组符合角色气质的对话示例
- 示例应展示角色的独特语气，不要写 polite small talk

### 当 Description 过长时（>500 字）：
- 提取核心身份（Who）、动机（What they want）、关键背景事件（Why）
- 精简为 2-4 句话的叙事化描述
- 多余的世界观/历史信息建议放入 Lore Pieces

### 当来源是多角色/Group RP 时：
- 为每个角色单独生成 Character Card
- 将所有角色放入同一个 Scenario 的"参与角色"列表
- 在 Custom Instructions 中描述角色之间的关系
- First Message 应暗示或展示多个角色的存在

---

## 转换示例

### 输入（Character.AI 风格）
```
Name: Kira Voss
Description: Kira Voss is a disgraced ex-detective who now works as a bounty hunter in the city's underground. She's 32 years old, tall with short dark hair and a scar above her left eyebrow. After being framed for a crime she didn't commit, she lost her badge and her trust in the system. Now she only trusts herself and her instincts.
Personality: Stoic, sharp-witted, morally gray, protective of those she cares about but slow to trust
Greeting: You wake up in a dimly lit train compartment. The only other person here is a young woman in a worn leather coat, sharpening a knife. She doesn't look up when you stir. "You're finally awake," she says. "We cross the border in twenty minutes. If you still have that package, now would be a good time to tell me what's in it."
Example Dialogue: User: Who are you?
Kira: The last guy who asked me that question is doing fifteen to life. You want to be more careful with your curiosity.
```

### 输出（FictionLab 格式）

#### 📋 FictionLab Character Card

**Name:** Kira Voss

**Description:** A disgraced ex-detective turned bounty hunter in the city's underground. After being framed for a crime she didn't commit, she lost her badge and her trust in the system. Now she only trusts herself and her instincts. She's protective of those she cares about but slow to extend that circle.

**Personality:** Stoic, sharp-witted, morally gray, protective of allies, slow to trust, self-reliant, dry sense of humor

**Example Dialogue:**
User: Who are you?
Kira: The last guy who asked me that question is doing fifteen to life. You want to be more careful with your curiosity.

User: I'm not here to cause trouble.
Kira: Everyone says that. Most of them are lying.

**Appearance:** Tall, athletic build, short dark hair, scar above left eyebrow, worn leather coat

---

#### 📍 FictionLab Location Card

**Location Name:** Border Train Compartment

**Location Description:** A cramped, dimly lit train compartment with worn velvet seats. The only light comes from a flickering overhead lamp. The rhythmic clatter of wheels on tracks fills the silence, and the air smells of stale tobacco and cold steel.

**Atmosphere:** Claustrophobic, tense, transient

---

#### 🎭 FictionLab Scenario 建议

**场景标题:** The Border Crossing

**场景简介:** You wake up in a dim train compartment with no memory of how you got there. The woman across from you claims you're crossing a border in twenty minutes — and she wants to know what's in your package.

**First Message（开场白）:**
You wake up in a dimly lit train compartment. The only other person here is a young woman in a worn leather coat, sharpening a knife. She doesn't look up when you stir.

"You're finally awake," she says. "We cross the border in twenty minutes. If you still have that package, now would be a good time to tell me what's in it."

**参与角色:** Kira Voss

**Custom Instructions:** Let the user drive their own actions and dialogue. Do not speak for the user or assume their internal thoughts. Kira should maintain her suspicious, guarded demeanor until trust is earned through the narrative. Maintain narrative momentum and avoid repetitive question-answer patterns.

**Lore Pieces 建议:** 无（此场景世界观简单，无需额外 Lore Pieces）

---

#### 💡 迁移建议

1. **开场白已分离**：原 Character.AI 的 Greeting 已移至 FictionLab 的 Scenario → First Message。在 FictionLab 中，开场白不属于角色卡，而是场景的一部分。

2. **Location Card 已提取**：从 Greeting 中提取了火车车厢的环境描写作为独立的 Location Card。FictionLab 的地点卡会影响场景氛围和图片生成。

3. **Appearance 已提取**：从 Description 中提取了视觉特征放入独立 Appearance 字段，这将影响 FictionLab 的图片生成。

4. **需要创建场景**：在 FictionLab 中，仅有角色卡无法开始对话。你需要在创建 Character Card 和 Location Card 后，创建一个 Scenario 并将它们关联进去。

---

现在，请转换以下角色卡：

[PASTE CHARACTER CARD HERE]
```

---

## 五、技术实现建议

### 5.1 纯文本转换器（Python 脚本）

如果需要将 Tavern JSON 批量转换为 FictionLab 格式，核心逻辑如下：

```python
import re
from typing import Optional

def convert_tavern_to_fictionlab(tavern_card: dict) -> dict:
    """将 Tavern/JSON 角色卡转换为 FictionLab 完整四层架构"""
    
    # 兼容 V1 和 V2 格式
    data = tavern_card.get("data", tavern_card)  # V2 有 data 包裹，V1 没有
    
    # Character Card
    character_card = {
        "Name": data.get("name", ""),
        "Description": _extract_description(data.get("description", "")),
        "Personality": _extract_personality(data.get("personality", "")),
        "Example Dialogue": _convert_mes_example(data.get("mes_example", ""), data.get("name", "")),
        "Appearance": _extract_appearance(data.get("description", ""))
    }
    
    # Location Card（从 scenario + first_mes + description 中提取）
    combined_for_location = "\n".join(filter(None, [
        data.get("scenario", ""),
        data.get("first_mes", ""),
        data.get("description", "")
    ]))
    location_card = _extract_location(combined_for_location)
    
    # Custom Instructions（从 description 的指令段落 + extensions 中提取）
    custom_instructions = _extract_custom_instructions(data.get("description", ""))
    extensions = data.get("extensions", {})
    if extensions.get("depth_prompt", {}).get("prompt"):
        custom_instructions += "\n" + extensions["depth_prompt"]["prompt"]
    custom_instructions = custom_instructions.strip()
    
    # Lore Pieces 建议（检测是否有复杂世界观）
    lore_suggestion = _suggest_lore_pieces(data.get("description", ""))
    
    # Scenario
    scenario = {
        "Title": _generate_scenario_title(data),
        "Summary": data.get("scenario", "")[:200] or _infer_summary(data.get("description", "")),
        "First Message": data.get("first_mes", ""),
        "Characters": [data.get("name", "")],
        "Custom Instructions": custom_instructions,
        "Lore Pieces Suggestion": lore_suggestion
    }
    
    return {
        "Character Card": character_card,
        "Location Card": location_card,
        "Scenario": scenario
    }


def _extract_description(text: str, max_length: int = 500) -> str:
    """从长描述中提取核心身份+动机，精简为叙事化描述"""
    if len(text) <= max_length:
        return _clean_description(text)
    
    # 规则提取：找 Who / What they want / Why 的段落
    sentences = re.split(r'(?<=[.!?])\s+', text)
    core_sentences = []
    for s in sentences:
        s_lower = s.lower()
        if any(kw in s_lower for kw in ["is a", "was a", "works as", "turned", "became", "framed", "lost", "now"]):
            core_sentences.append(s)
        if len(" ".join(core_sentences)) > max_length:
            break
    
    result = " ".join(core_sentences) if core_sentences else sentences[0]
    return _clean_description(result[:max_length])


def _clean_description(text: str) -> str:
    """清理描述中的格式标记和指令性语句"""
    # 移除 W++、XML、括号指令等格式标记
    text = re.sub(r'\[.*?\]', '', text)  # 移除 [brackets]
    text = re.sub(r'\{\{.*?\}\}', '', text)  # 移除 {{tags}}
    text = re.sub(r'\*\*.*?\*\*', r'\1', text)  # 可选：移除 markdown bold
    # 移除明显的指令行
    text = re.sub(r'(?i)^(do not|always|never|you are|respond as|speak in).*?$', '', text, flags=re.MULTILINE)
    return text.strip()


def _extract_personality(text: str) -> str:
    """将句子描述提炼为 3-7 个关键词"""
    if not text:
        return ""
    
    # 如果已经是逗号分隔的关键词，直接清理
    if "," in text and len(text) < 200:
        words = [w.strip() for w in text.split(",")]
        return ", ".join(words[:7])
    
    # 否则从文本中提取形容词和特质描述
    trait_patterns = re.findall(r'\b(\w+)(?:,|\.\.\.|\sand|\sbut|\;|\n)', text)
    traits = [t for t in trait_patterns if len(t) > 2 and t.lower() not in ["the", "and", "but", "she", "he", "they"]]
    return ", ".join(traits[:7]) if traits else text[:100]


def _convert_mes_example(text: str, char_name: str) -> str:
    """将 Tavern mes_example 转换为 FictionLab 格式"""
    if not text:
        return ""
    
    # 去除 <START> 标记
    text = re.sub(r'<START>', '', text, flags=re.IGNORECASE)
    # 替换 {{user}} 为 User
    text = re.sub(r'\{\{user\}\}\s*[:：]', 'User:', text, flags=re.IGNORECASE)
    # 替换 {{char}} 为角色名
    text = re.sub(r'\{\{char\}\}\s*[:：]', f'{char_name}:', text, flags=re.IGNORECASE)
    # 清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _extract_appearance(text: str) -> str:
    """从描述中提取视觉特征"""
    if not text:
        return ""
    
    # 视觉关键词匹配
    visual_keywords = re.findall(
        r'\b(\d+\s*years?\s*old|\w+\s*hair|\w+\s*eyes?|tall|short|athletic|slender|muscular|\w+\s*build|scar|tattoo|wearing\s+[^.]+)\b',
        text, flags=re.IGNORECASE
    )
    
    if visual_keywords:
        return ", ".join(visual_keywords[:10])
    
    # 回退：找包含外貌描写的句子
    sentences = re.split(r'(?<=[.!?])\s+', text)
    for s in sentences:
        s_lower = s.lower()
        if any(kw in s_lower for kw in ["hair", "eyes", "tall", "short", "wear", "dress", "coat", "scar", "build"]):
            return s.strip()
    
    return ""


def _extract_location(text: str) -> dict:
    """从场景描述中提取 Location Card"""
    if not text:
        return {"Location Name": "", "Location Description": "", "Atmosphere": ""}
    
    # 地点名称提取：找 "in/at/on a/an/the [形容词] [地点]" 模式
    location_match = re.search(
        r'\b(?:in|at|on)\s+(?:a|an|the)\s+([\w\s]+?(?:room|station|house|city|town|forest|mountain|compartment|lab|office|bar|street|building|castle|dungeon|ship|plane|car|restaurant|hotel|apartment))\b',
        text, flags=re.IGNORECASE
    )
    loc_name = location_match.group(1).strip().title() if location_match else "Unnamed Location"
    
    # 环境描写提取：找包含感官细节的句子
    sentences = re.split(r'(?<=[.!?])\s+', text)
    env_sentences = []
    for s in sentences:
        s_lower = s.lower()
        if any(kw in s_lower for kw in ["light", "dark", "sound", "smell", "cold", "warm", "noise", "silent", "dust", "wind", "rain", "flicker", "dim", "bright"]):
            env_sentences.append(s.strip())
    
    loc_desc = " ".join(env_sentences[:3]) if env_sentences else f"The setting for this scenario."
    
    # 氛围关键词推导
    atmosphere_keywords = []
    mood_map = {
        "dim": "dim", "dark": "dark", "flicker": "unstable", "cold": "cold",
        "silent": "silent", "noise": "noisy", "warm": "warm", "bright": "bright",
        "dust": "neglected", "rain": "melancholic", "wind": "restless"
    }
    for word, mood in mood_map.items():
        if word in loc_desc.lower():
            atmosphere_keywords.append(mood)
    
    return {
        "Location Name": loc_name,
        "Location Description": loc_desc,
        "Atmosphere": ", ".join(atmosphere_keywords[:3]) if atmosphere_keywords else "neutral"
    }


def _extract_custom_instructions(text: str) -> str:
    """从描述中提取叙事指令"""
    if not text:
        return ""
    
    instruction_patterns = [
        r'(?i)(do not speak for.*?)(?:\n|$)',
        r'(?i)(do not assume.*?)(?:\n|$)',
        r'(?i)(always stay in character.*?)(?:\n|$)',
        r'(?i)(let the user drive.*?)(?:\n|$)',
        r'(?i)(avoid.*?)(?:\n|$)',
        r'(?i)(use \*.*?\* for actions.*?)(?:\n|$)',
        r'(?i)(you are an ai.*?)(?:\n|$)',
        r'(?i)(respond as.*?)(?:\n|$)',
        r'(?i)(never break character.*?)(?:\n|$)',
    ]
    
    instructions = []
    for pattern in instruction_patterns:
        matches = re.findall(pattern, text)
        instructions.extend(matches)
    
    return "\n".join(instructions) if instructions else ""


def _suggest_lore_pieces(text: str) -> str:
    """检测是否需要 Lore Pieces"""
    if len(text) < 800:
        return "无需 Lore Pieces（世界观简单）"
    
    # 检测世界观关键词密度
    world_keywords = ["world", "kingdom", "empire", "magic", "spell", "faction", "organization", "history", "prophecy", "realm", "dimension"]
    count = sum(1 for kw in world_keywords if kw in text.lower())
    
    if count >= 3:
        return f"建议创建 Lore Pieces（检测到 {count} 个世界观关键词）。建议将历史背景、魔法系统、组织规则拆分为独立 Lore Pieces，设置合理的 Activation Keywords。"
    
    return "无需 Lore Pieces"


def _generate_scenario_title(data: dict) -> str:
    """从角色名和场景生成标题"""
    name = data.get("name", "")
    scenario = data.get("scenario", "")
    
    if scenario:
        # 取 scenario 的前 3-4 个词作为标题候选
        words = scenario.split()[:4]
        return " ".join(words).title()
    
    if name:
        return f"Encounter with {name}"
    
    return "Untitled Scenario"


def _infer_summary(description: str) -> str:
    """从描述中推断场景简介"""
    sentences = re.split(r'(?<=[.!?])\s+', description)
    if sentences:
        return sentences[0][:200]
    return ""
```

### 5.2 关键函数说明

| 函数 | 用途 | 复杂度 |
|---|---|---|
| `_extract_description` | 从长描述中提取核心身份+动机，移除格式标记和指令 | 中（需要 NLP 或规则提取） |
| `_extract_personality` | 将句子描述提炼为关键词 | 低（字符串处理） |
| `_convert_mes_example` | 将 Tavern 格式转换为 FictionLab 格式 | 低（正则替换） |
| `_extract_appearance` | 从描述中提取视觉特征 | 中（关键词匹配 + 句子提取） |
| `_extract_location` | 从场景文本中提取 Location Card | 中（正则模式 + 感官关键词） |
| `_extract_custom_instructions` | 从 prompt 中分离叙事指令 | 低（指令关键词匹配） |
| `_suggest_lore_pieces` | 检测复杂世界观并建议 Lore Pieces | 低（关键词密度统计） |
| `_generate_scenario_title` | 从角色名和场景生成标题 | 低（模板生成） |

### 5.3 为什么 FictionLab 官方不提供转换器？

根据第三方工具检索报告，FictionLab **无角色导出功能**，也**未发现任何第三方转换工具**。这与竞品生态形成鲜明对比：

| 平台 | 角色卡生态 | 转换工具 |
|---|---|---|
| **SillyTavern** | 极其丰富（Chub AI 百万角色卡） | Chub AI Ripper（Python 脚本批量下载） |
| **Janitor AI** | 丰富 | 支持 Tavern 格式导入/导出 |
| **Character.AI** | 丰富但封闭 | 无官方导出，社区有爬虫工具 |
| **PolyBuzz** | 中等 | 支持基本导出 |
| **FictionLab** | 较弱，UGC 为主 | ❌ 无导出，无转换器 |

FictionLab 的封闭性可能是**有意为之的产品策略**——降低复杂度、保护创作者内容、避免用户流失到竞品。但这也导致了迁移用户的高门槛，**角色卡转换器是社区最急需的第三方工具**（需求强度 🔥🔥🔥🔥🔥）。

---

## 六、迁移后质量优化指南

转换只是第一步。迁移用户常在 FictionLab 遇到以下质量问题，转换器应在迁移建议中提前预警：

### 6.1 防止角色 "OOC"（Out of Character）

| 问题现象 | 原因 | 优化方法 |
|---|---|---|
| 角色过度反思和安抚 | Description 太抽象，缺乏具体行为约束 | 在 Personality 里明确写：`Speaks directly. Avoids excessive reassurance or therapy-style validation.` |
| 角色抢用户的话 | Custom Instructions 缺失 | 添加：`Let the user drive their own actions and dialogue. Do not speak for the user or assume their internal thoughts.` |
| 角色不敢行动 | 角色缺乏目标和主动性 | 在 Description 中赋予主动性：`She has her own agenda and will push the plot forward if the player stalls.` |
| 对话变成一问一答 | 开场白和示例对话展示的是 Q&A 格式 | 重写 Example Dialogue 为连续推进式，不是问答式 |

### 6.2 模型选择建议

转换后的场景在 FictionLab 中可以选择不同模型。根据社区实战总结：

| 场景类型 | 推荐模型 | 原因 |
|---|---|---|
| 动作/战斗 | **Chimera** 或 **Sorcerer** | 冲突处理强、指令遵循精确 |
| 情感/文学 | **Ophelia**、**Riddleheart** 或 **Glendora** | 情感深度和文学性 |
| 奇幻/冒险 | **Oracle** 或 **Glendora** | 创意丰富、世界观构建能力强 |
| 恐怖/悬疑 | **Wraithmind** 或 **Ophelia** | 氛围营造好 |
| 新手尝鲜 | **Default**（免费） | 平衡型，基础指令遵循 |

**Context 长度建议**：
- 短篇体验：免费版 32k tokens（约 20-40 条消息）
- 长篇连载：付费版 128k tokens（约 100+ 条消息），几乎必需

### 6.3 测试与迭代 checklist

迁移完成后，建议用户按以下清单验证：

- [ ] **First Message 有张力**：读完后用户是否立刻想回复？
- [ ] **角色不抢话**：AI 是否替用户说了话或想了事？
- [ ] **语气一致**：聊 5-10 轮后，角色是否还保持设定中的语气？
- [ ] **不 OOC**：角色是否突然变得过于友善/顺从？
- [ ] **Location 有感觉**：场景的环境描写是否在叙事中自然出现？
- [ ] **Custom Instructions 生效**：叙事指令（如 "不要替用户说话"）是否被遵循？

---

> **声明**：本分析由 keyword-graph 项目基于 FictionLab 用户手册、社区讨论、Reddit 公开 API（100 条）、竞品对比评测和第三方工具检索报告整理。FictionLab 的字段和架构可能随版本变化；以官方实际界面为准。最后更新：2026-05-26。
