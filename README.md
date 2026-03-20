[English](README_en.md) | [中文](README_zh.md)

# TokenSpire2 — LLM 驱动的杀戮尖塔 2 自动游玩代理

一个自主运行的杀戮尖塔 2 Mod，使用大语言模型（LLM）进行决策，完成整局游戏。代理能处理所有游戏阶段——战斗、地图导航、事件、商店、奖励和休息点——通过将游戏状态序列化为文本提示，并解析 LLM 的响应为游戏操作。

## 工作原理

1. **游戏状态序列化** — 每个决策点（战斗回合、地图选择、事件、商店等）被转换为结构化的文本描述，包含生命值、能量、手牌、敌人、遗物、药水和可选项。
2. **LLM 决策** — 序列化的状态发送到 OpenRouter 兼容的 API。LLM 以结构化指令响应（`PLAY 3 -> A`、`CHOOSE 2`、`BUY 5` 等）。
3. **动作执行** — 解析响应并执行为游戏操作（打出卡牌、使用药水、选择地图节点、购买物品等）。
4. **持续学习** — 每局结束后，LLM 反思自己的表现并更新记忆文件，该文件在同一会话的多局游戏间持续存在，使其能从错误中学习。

## 功能特性

- **全自动游玩** — 处理每个游戏阶段：战斗、地图、事件、商店、奖励、休息点、卡牌选择、游戏结束
- **自动重开** — 游戏结束后自动从主菜单开始新一局
- **LLM 集成** — OpenRouter API，支持 SSE 流式传输（非阻塞），支持 Claude、GPT o系列、DeepSeek 等模型的推理/思考功能
- **持续学习** — 会话级记忆系统，LLM 在多局游戏间自主维护和更新策略笔记
- **对话历史** — 完整对话日志以 JSON 格式保存，便于分析
- **降级模式** — 无 LLM 配置时使用随机决策
- **双语提示** — 系统提示和游戏状态描述支持中文和英文

## 性能表现

![Floor Reached per Run by Model](docs/performance.png)

### 多模型对比（铁甲战士 A0）

| 模型 | 局数 | 平均层数 | 最高层数 | 通过 Act 1 Boss |
|------|------|----------|----------|-----------------|
| Claude Opus 4.6 | 10 | 17.2 | 23 | 3/10 |
| GPT-5.4 | 4 | 17.0 | 17 | 0/4 |
| Qwen3.5-Plus（思考 1024） | 7 | 13.0 | 17 | 0/7 |
| Kimi K2.5 | 5 | 12.8 | 17 | 0/5 |
| Qwen3.5-Plus（无思考） | 5 | 10.4 | 15 | 0/5 |

- **Claude Opus 4.6** 表现最佳，10 局中有 3 局突破了第一幕 Boss 进入第二幕（最高第 23 层），且后期表现呈上升趋势
- **GPT-5.4** 稳定到达第一幕 Boss（第 17 层），但 4 局均未能击败 Boss
- **Qwen3.5-Plus（思考 1024）** 开启思考后明显提升，7 局中有 4 局到达 Boss，但后期出现波动
- **Kimi K2.5** 表现与 Qwen 思考版相近，有一局到达 Boss
- **Qwen3.5-Plus（无思考）** 平均在第 10 层左右阵亡，思考能力对其表现有显著影响

### Claude Opus 4.6 — 首次会话（4 局，铁甲战士 A0）

模型：`anthropic/claude-opus-4.6`，通过 OpenRouter 调用，启用扩展思考。

| 局数 | 层数 | 结果 | 死因 | 用时 | 牌组大小 |
|------|------|------|------|------|----------|
| 1 | 9 | 失败 | 下水道蛤蜊 | 14:36 | 13 张 |
| 2 | 9 | 失败 | 骇鳗（精英） | 19:14 | 15 张 |
| 3 | 9 | 失败 | 骇鳗（精英） | 21:32 | 15 张 |
| 4 | 17 | 失败 | 瀑布巨人（Boss） | 23:58 | 16 张 |

**观察：**
- 跨局明显进步 — 第 4 局到达了第一幕 Boss（第 17 层），而前三局均在第 9 层阵亡
- LLM 的持续学习记忆正确识别了关键弱点：**缺乏力量成长** — 4 局游戏中没有任何永久力量来源，导致 Boss 战在数学上不可能获胜
- 良好的策略推理：学会了低血量时避开精英、优先移除卡牌、评估卡牌协同
- 识别了敌人行为模式（噬尸蛞蝓连杀机制、骇鳗眩晕阈值、瀑布巨人伤害递增）
- 早期局药水使用存在 Bug（已修复）— 代理在记忆中记录了这一问题并做出了调整
- 随着 LLM 维护更长的对话和更深入的推理，单局用时逐渐增加

**LLM 记忆亮点（4 局之后）：**
- 正确识别力量成长为铁甲战士的第一优先级
- 从实战经验中建立了详细的敌人知识库
- 制定了卡牌分级表（S 级：耸肩回避、连击拳、战斗狂热、旋风斩）
- 学习了路径策略（血量低于 60% 时避开精英、商店→休息→Boss）
- 设定了具体规则（如"事件重置消耗超过 12 点生命后停止"）

## 安装配置

### 前置要求

- **杀戮尖塔 2**（v0.98+），通过 Steam 安装
- 在 Steam 中右键杀戮尖塔 2 → 属性 → 启动选项，添加 `--autoslay`, 此步骤可以装完mod再执行
<img width="2150" height="1426" alt="屏幕截图 2026-03-20 052432" src="https://github.com/user-attachments/assets/6cf79c69-196f-4fa7-8066-29c3a2c7d4a4" />

### 方式一：下载发布版（推荐）

1. 从 [Releases](https://github.com/collinzrj/TokenSpire2/releases) 下载最新的 `TokenSpire2-vX.X.X.zip`
2. 将 zip 解压到 Mod 文件夹：
   - **Windows:** `<Steam>/steamapps/common/Slay the Spire 2/mods/`
   - **macOS:** `~/Library/Application Support/Steam/steamapps/common/Slay the Spire 2/mods/`
3. 确保 `mods/` 下有一个 `TokenSpire2/` 文件夹
4. 编辑 `TokenSpire2/` 文件夹中的 `llm_config.json` — 填入你的 API 密钥



### 方式二：从源码编译

需要 **.NET 9 SDK** — https://dotnet.microsoft.com/download/dotnet/9.0

```bash
dotnet build
```

构建会自动将 `TokenSpire2.dll` 复制到 Mod 文件夹：

**Windows:**
```
<Steam>/steamapps/common/Slay the Spire 2/mods/TokenSpire2/
```

**macOS:**
```
~/Library/Application Support/Steam/steamapps/common/Slay the Spire 2/mods/TokenSpire2/
```

macOS 上游戏数据目录（用于 DLL 引用）：
```
~/Library/Application Support/Steam/steamapps/common/Slay the Spire 2/SlayTheSpire2.app/Contents/Resources/data_sts2_macos_arm64/
```

### LLM 配置

编辑 Mod 文件夹中的 `llm_config.json`（`TokenSpire2.dll` 旁边）：

```json
{
  "Url": "https://openrouter.ai/api/v1",
  "Key": "sk-or-v1-你的密钥",
  "Model": "anthropic/claude-opus-4.6",
  "Lang": "zh"
}
```

| 字段 | 说明 |
|------|------|
| `Url` | OpenRouter（或任何 OpenAI 兼容的）API 端点 |
| `Key` | API 密钥 |
| `Model` | 模型标识（如 `anthropic/claude-opus-4.6`、`deepseek/deepseek-r1`、`openai/o3`） |
| `Lang` | 提示语言：`zh`（中文）或 `en`（英文） |

没有此文件时，Mod 将使用随机决策。

### 推理支持

Mod 会根据模型自动配置推理/思考参数：
- **Claude**：`reasoning: { max_tokens: 2048 }` + Anthropic 提供商路由
- **OpenAI o 系列**：`reasoning: { effort: "high" }`
- **DeepSeek/Qwen/GLM/Kimi/MiniMax**：内置思考能力，无需额外参数

## 项目结构

```
sts2_mod/
├── MainFile.cs                 Mod 入口（Harmony 补丁 + AutoSlay 节点）
├── TokenSpire2.csproj              构建配置
├── TokenSpire2.json                Mod 清单
├── src/
│   ├── AutoSlayNode.cs         主游戏循环 — 状态检测、LLM 调度
│   ├── AutoSlayCardSelector.cs 战斗中卡牌选择（ICardSelector）
│   ├── AutoSlayHelpers.cs      场景树遍历工具
│   ├── AutoSlayPatch.cs        Harmony 补丁
│   ├── Handlers/               各界面操作处理器
│   │   ├── CombatHandler.cs    随机战斗降级方案
│   │   ├── PotionHelper.cs     药水目标解析
│   │   ├── MapHandler.cs       地图导航
│   │   ├── GameOverHandler.cs  游戏结束界面自动化
│   │   ├── ShopHandler.cs      商店购买
│   │   └── ...                 （事件、奖励、休息点等）
│   └── Llm/                    LLM 集成层
│       ├── LlmClient.cs        API 客户端（流式传输、记忆、历史）
│       ├── LlmConfig.cs        配置文件加载
│       ├── GameStateSerializer.cs  游戏状态 → 文本提示转换
│       ├── PromptStrings.cs    双语提示模板
│       └── RunSummaryLogger.cs 运行统计跟踪
└── gameplay_log/               保存的游戏日志，用于分析
```

## 输出文件

Mod 在 `TokenSpire2.dll` 旁边写入以下文件（共享相同的会话时间戳）：

| 文件 | 内容 |
|------|------|
| `llm_log_{ts}.txt` | 完整对话日志，包含思考/推理过程 |
| `llm_log_{ts}.json` | 运行统计摘要（JSON 数组，每局一条） |
| `llm_history_{ts}.json` | 完整对话历史（嵌套数组：局 → 消息） |
| `llm_memory_{ts}.md` | LLM 自主维护的记忆/策略笔记 |

## 致谢

- 参考 erasels 的 [STS2 Mod 框架](https://github.com/erasels/Minty-Spire-2) 构建
- 游戏：Mega Crit 开发的[杀戮尖塔 2](https://store.steampowered.com/app/2868840/Slay_the_Spire_2/)
