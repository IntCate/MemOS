# MemOS Linux 内核架构设计文档

> MemOS · OpenClaw · Hermes Agent 三方对照 & Linux 路线实施方案

---

## 一、设计哲学与定位

| 维度 | **OpenClaw** | **Hermes Agent** | **MemOS** |
|------|-------------|-----------------|-----------|
| **设计隐喻** | 网络路由器 | 自我进化引擎 | **Linux 操作系统** |
| **核心理念** | "AI 模型提供智能，我提供执行环境" | "不是工具，是同事——会成长的智能体" | "像 Linux 管理进程一样管理记忆与能力" |
| **组织中心** | Gateway（控制平面） | Agent Loop（执行循环） | **Kernel（内核调度）+ Bus（子系统总线）** |
| **开源方** | Peter Steinberger → OpenAI Foundation | Nous Research (Paradigm $50M) | — |
| **语言/运行时** | Node.js 22+ 守护进程 | Python + 多后端 | Python / FastAPI |
| **GitHub Stars** | 38 万+ | 14 万+ | — |
| **定位** | 多通道个人 AI 助手平台 | 自进化持久化智能体框架 | 可组合的 AI 记忆操作系统 |

### 核心差异一句话

| 框架 | 一句话 |
|------|--------|
| OpenClaw | **"路由器哲学"** — Gateway 是上帝，一切流经它，适合"部署一个多通道助手" |
| Hermes Agent | **"进化哲学"** — Agent Loop 是核心，能力随使用自动增长，适合"需要一个越用越聪明的数字同事" |
| MemOS | **"内核哲学"** — Kernel 调度子系统，Gateway 处理协议，适合"需要一个可组合、可扩展的 AI 操作系统" |

---

## 二、架构分层对照

```
OpenClaw                          Hermes Agent                        MemOS（方案）
═══════════════════════════════════════════════════════════════════════════════════

Gateway (WebSocket Server)        AIAgent Loop (同步编排引擎)           Gateway（网络通讯网关）
  ├─ Channel Adapters               ├─ Gateway / Scheduler               ├─ HTTPAdapter
  │   WhatsApp/Telegram/Discord     │   多通道接入                        │   ├─ WSAdapter
  │   Slack/Signal/iMessage         │   事件驱动                          │   ├─ WeChatAdapter
  │                                 │                                     │   └─ MessageNormalizer
  ├─ Session Manager                ├─ Cron Engine（定时任务）           │      统一消息格式
  │   会话生命周期 + 安全边界        │   主动心跳                          │
  │                                 │                                     │
  ├─ Auth / ACL                     ├─ ACP Integration                   │
  │   配对 + 访问控制               │   Agent Communication Protocol     │
  │                                 │                                     │
  └─ Heartbeat (30-60min)           └─ Tooling Runtime                   │
       │                                 │                               │
       ▼                                 ▼                               ▼
Agent Runtime (Pi Core)           GEPA Self-Eval Engine               MemOS Kernel（控制中心）
  Receive → Plan →                  Execute → Evaluate →                RequestDispatcher
  Execute → Evaluate →              Abstract → Refine                    ├─ Pipeline Orchestrator
  Report                            (per-task learning loop)             │   ChatPipeline / AgentPipeline
       │                                 │                               │
       ▼                                 ▼                               └─ KernelBus（子系统总线）
Skills (人工编写)                 Skills (Auto-Learn)                    ┌────┼────┬───────┐
  ├─ SKILL.md 文件                  ├─ Level 0 (3K tokens 概要)        Memory  Ctx   AI     Cap
  ├─ 选择性注入                      ├─ Level 1 (完整内容)              Subsys  Sub  Subsys  Subsys
  └─ ClawHub 5000+                  └─ Level 2 (深入参考)                │       │     │       │
                                                                        KB      │   Infer    MCP
                                                                      Subsys    │           Skill
Memory (File-backed)              Memory (Three-Tier)                            │
  ├─ Session JSON                   ├─ Core Memory                               │
  ├─ MEMORY.md                      │   MEMORY.md + USER.md               KernelBus Event System
  └─ Semantic Search                │   ~1.3K tokens 硬上限                ├─ 子系统注册/发现
                                    ├─ Session History                      ├─ 事件发布/订阅
                                    │   SQLite FTS5 + LLM 摘要             └─ 跨子系统通信
                                    └─ Honcho（用户建模）
                                        偏好/推理模式/价值观提取
```

---

## 三、子系统深度对比

### 3.1 Gateway / 入口层

| 对比维度 | OpenClaw | Hermes Agent | MemOS（当前） | MemOS（方案） |
|---------|----------|-------------|--------------|--------------|
| 核心协议 | WebSocket (`ws` lib) | 多通道 HTTP + WebSocket | 仅 HTTP REST | HTTP + WebSocket |
| 通道适配 | 内置 7 种（WhatsApp/Telegram/Discord/Slack/Signal/iMessage） | 15+ 种（含飞书/钉钉/企微） | 仅 API | **Adapter 注册机制** |
| 消息标准化 | 适配器各自实现 | 统一接口 | 无 | **独立 MessageNormalizer** |
| 会话模型 | `main` / `dm:<ch>:<id>` / `group:<ch>:<id>` | SQLite 持久化 | InMemoryContextManager | Session Manager |
| 访问控制 | allowFrom + 配对 + DM 策略 | 指令审批 + 危险模式阻挡 | ❌ 缺失 | **需补充** |
| Heartbeat | ✅ 30-60min 主动检查 | ✅ Cron 定时 + HEARTBEAT.md | ❌ | **需补充 Cron Scheduler** |
| 控制接口 | Web UI + CLI + macOS App + 移动端 | CLI + TUI + Web | ❌（仅 Swagger） | 需补充 CLI/Web UI |

### 3.2 记忆系统

| 对比维度 | OpenClaw | Hermes Agent | MemOS（当前） | MemOS（方案） |
|---------|----------|-------------|--------------|--------------|
| **工作记忆** | Session JSON 文件 | Session History (SQLite FTS5) | `MemoryType.WORKING` (YAML) | 同左 |
| **长期记忆** | MEMORY.md + 语义搜索 | Core Memory (MEMORY.md + USER.md) | `MemoryType.EPISODIC` (向量) | 同左 |
| **用户建模** | ❌ 无 | ✅ **Honcho 辩证用户画像**（偏好/推理模式/价值观提取） | ❌ 无 | **值得借鉴 → UserProfile 层** |
| **语义记忆** | 语义搜索注入 Prompt | LLM 摘要 + FTS5 搜索 | `MemoryType.SEMANTIC`（向量） | 同左 |
| **程序记忆** | Skills 文件 | **自动技能抽象**（工作流→技能） | `MemoryType.PROCEDURAL` | 同左 + Skill 自动生成 |
| **遗忘策略** | ❌ 无 | ✅ Core Memory ~1.3K tokens **硬上限**（强制优先级排序） | ❌ 无 | **需补充 TokenBudget** |
| **跨会话持久化** | ✅ JSON 文件 | ✅ SQLite + MEMORY.md 文件 | ✅ YAML 文件 | 同左 |
| **存储后端** | JSON 文件 | SQLite + Markdown 文件 | YAML / LanceDB | **可插拔后端** |

> **关键差异**：Hermes 的 Core Memory 硬上限是三者中唯一的遗忘机制。强制 ~1.3K tokens 限制倒逼系统做优先级排序和定期清理。MemOS 的 MemorySubsystem 协议已预留扩展点，增加 TokenBudget 策略即可。

### 3.3 技能（Capability）系统

| 对比维度 | OpenClaw | Hermes Agent | MemOS（当前） | MemOS（方案） |
|---------|----------|-------------|--------------|--------------|
| **技能来源** | 人工编写 SKILL.md | **自动学习** + 人工 | 人工编写 SKILL.md | 人工 + 自动生成 |
| **自我进化** | ❌ | ✅ **GEPA 引擎**（100-500 次迭代收敛） | ❌ | **需借鉴 → SkillLearner** |
| **进化流程** | — | Execute→Evaluate→Abstract→Refine | — | CapSubsys 增加 AutoSkill |
| **渐进式披露** | 选择性注入相关技能 | Level 0/1/2 三级（避免 Prompt 膨胀） | 全量加载 | 需借鉴 |
| **热加载** | 插件系统扫描 | 即改即生效 | ✅ SkillWatcher（5s 轮询） | 同左 |
| **技能标准** | SKILL.md（自定） | agentskills.io 开放标准 | SKILL.md（自定） | 考虑对齐 agentskills.io |
| **技能市场** | ClawHub 5000+ | 91 内置 + 520+ 社区 | 无 | — |
| **MCP 协议** | ❌ | ✅ v0.6.0 原生支持（stdio + HTTP） | ✅ langchain-mcp-adapters | 同左 |

> **关键差异**：Hermes 的 GEPA 是业界首个可工作的 Agent 自我进化引擎。它将"行为记录→效果评估→策略优化→技能沉淀"形成闭环。OpenClaw 和 MemOS 的技能目前都是静态的。MemOS 的 CapabilitySubsystem 架构已预留 Skill 自动学习扩展点。

### 3.4 Agent 执行模型

| 对比维度 | OpenClaw | Hermes Agent | MemOS（当前） | MemOS（方案） |
|---------|----------|-------------|--------------|--------------|
| **循环模型** | Receive→Plan→Execute→Evaluate→Report | Execute→Evaluate→Abstract→Refine | HarnessEngine 线性管线 | **Pipeline 注册机制** |
| **工具调用** | RPC 风格，每轮 1 个工具 | 子代理并行调用 | LangGraph ReAct StateGraph | KernelBus 并行分发 |
| **子代理隔离** | ❌ | ✅ 一个失败不波及 | ❌ | **需借鉴** |
| **流式响应** | ✅ 逐 token | ✅ 流式 + 中断 + 重定向 | ✅ SSE Streaming | 同左 |
| **多轮推理** | 工具结果回注生成 | 多步骤计划执行 | ReAct (reason→act→reflect) | 同左 |
| **Agent 状态** | Session JSON | AgentState (SQLite) | LangGraph AgentState | Session + AgentState |

> **关键差异**：Hermes 的子代理并行是三者中最强并发模型。每个子代理获得 RPC 风格工具调用，彼此隔离，适合大规模任务。MemOS 的 KernelBus 天然支持并行分发，这是 Linux 架构的先天优势。

### 3.5 安全模型

| 对比维度 | OpenClaw | Hermes Agent | MemOS（当前） | MemOS（方案） |
|---------|----------|-------------|--------------|--------------|
| **工具沙盒** | Docker 隔离 | Docker 容器沙箱 | ❌ 无 | **高优先级补充** |
| **用户审批** | 配对机制 | 指令审批 + 危险模式阻挡 | ❌ 无 | Gateway 层添加 |
| **凭证管理** | 文件系统隔离 | 凭证过滤 + 路径遍历防护 + SSRF 缓解 | ❌ 无 | 需补充 |
| **Prompt 注入防护** | ❌ | ✅ 注入安全扫描 | ❌ | 需补充 |
| **会话安全边界** | ✅ 不同会话不同权限 | 会话级别隔离 | ❌ | SessionPolicy |

> **关键差异**：Hermes 的安全体系是目前最完善的——0 CVE 记录、200+ 安全补丁、多层防护。MemOS 目前安全层面完全空白，这是生产化前必须补上的短板。

### 3.6 模型与推理

| 对比维度 | OpenClaw | Hermes Agent | MemOS（当前） | MemOS（方案） |
|---------|----------|-------------|--------------|--------------|
| **模型数量** | Anthropic/OpenAI/Google + 本地 | 200+ (OpenRouter + 本地) | 10 厂商（模板方法） | 同左 |
| **模型热切换** | 配置更换 | `hermes model` 命令 | 需重启 | 需优化 |
| **多 Agent 路由** | ✅ 不同渠道不同 Agent | ❌ | ❌ | Gateway AgentRouter |
| **推理模式** | RPC 同步 | 子代理异步 | ReAct + Regular + Streaming | 同左 |

---

## 四、核心差异总结

```
┌──────────────────────────────────────────────────────────────────┐
│                      核心架构差异                                   │
│                                                                  │
│  OpenClaw          Hermes Agent          MemOS                   │
│  ═══════           ════════════          ═════                   │
│                                                                  │
│  Gateway ──→ Agent      Agent Loop ──→ Skills     Gateway ──→ Kernel ──→ Bus ──→ Subsystems
│  (中心化控制)         (自我进化为核心)           (分层解耦)           │
│                                                                  │
│  差异1: 控制模型                                                 │
│  OC: 单一 Gateway 控制一切                                       │
│  HM: Agent Loop 是上帝                                           │
│  MM: Kernel + Bus 分层调度，子系统可插拔                          │
│                                                                  │
│  差异2: 进化能力                                                 │
│  OC: 无，技能全人工                                              │
│  HM: GEPA 自动进化，技能从使用中学习                              │
│  MM: 无（方案预留在 CapSubsys）                                   │
│                                                                  │
│  差异3: 记忆分层                                                 │
│  OC: 2层（Session + MEMORY.md）                                  │
│  HM: 3层（Core + Session + Honcho用户建模）                       │
│  MM: 5层协议（WORKING/EPISODIC/SEMANTIC/PROCEDURAL/LONG_TERM）    │
│                                                                  │
│  差异4: 安全边界                                                 │
│  OC: Docker + 配对                                               │
│  HM: Docker + 审批 + 注入防护 + 凭证管理（0 CVE）                  │
│  MM: 完全空白 ← 最大短板                                         │
│                                                                  │
│  差异5: 通道覆盖                                                 │
│  OC: 7 通道内置                                                  │
│  HM: 15+ 通道                                                    │
│  MM: 仅 API ← 第二短板                                           │
└──────────────────────────────────────────────────────────────────┘
```

---

## 五、Linux 路线实施方案

### 5.1 总体路线图

```
Phase 1        Phase 2          Phase 3         Phase 4         Phase 5
Gateway        Kernel           Subsystems      Safety          Evolution
═══════        ══════           ══════════      ══════          ═════════
[现在] ────→ [第1步] ────→ [第2步] ────→ [第3步] ────→ [第4步]

ChannelEngine   HarnessEngine    MemorySub       Gateway Auth    GEPA-style
    ↓               ↓               ↓               ↓               ↓
  Gateway        MemOSKernel     ContextSub      Sandbox         SkillLearner
  +Adapter       +KernelBus      +AISub          +Approval       +AutoSkill
  +Normalizer    +Pipeline       +CapSub         +Injection      +UserModel
```

### 5.2 Phase 1: Gateway 层（当前可启动）

**目标**：将 `ChannelEngine` 改造为 Linux 网络栈风格的 Gateway

```
backend/app/gateway/                    # 替代 app/engineering/channel/
├── __init__.py
├── gateway.py                          # Gateway 主入口
│   # class Gateway:
│   #   - 注册通道适配器
│   #   - 消息标准化
│   #   - 路由到 Kernel
│
├── normalizer.py                       # MessageNormalizer
│   # 统一内部消息格式：
│   # KernelMessage {
│   #   type: "chat" | "agent" | "search"
│   #   payload: {query, model, params}
│   #   session: {chat_id, user_id}
│   #   channel_meta: {source, client_ip, ...}
│   #   trace_id: uuid
│   # }
│
├── adapters/
│   ├── __init__.py
│   ├── base.py                         # BaseAdapter 抽象基类
│   │   # class BaseAdapter(ABC):
│   │   #     async def parse_inbound(raw) → KernelMessage
│   │   #     async def format_outbound(response) → channel_raw
│   │
│   ├── http_adapter.py                 # HTTP REST 适配器（当前实现）
│   ├── ws_adapter.py                   # WebSocket 适配器（后续）
│   └── wechat_adapter.py              # 微信适配器模板（后续）
│
└── data_structures.py                  # KernelMessage, ChannelMeta
```

**改动文件**：
| 文件 | 操作 |
|------|------|
| `app/engineering/channel/engine.py` | → 迁移至 `app/gateway/gateway.py` |
| `app/engineering/channel/__init__.py` | 保留兼容 re-export |
| `app/engineering/data_structures.py` | 增加 `KernelMessage`、`ChannelMeta` |
| `app/program/services/message/message_service.py` | 调用 `Gateway.process()` 替代 `ChannelEngine.process_message()` |
| `app/__init__.py` | `register_services()` 注册 `gateway` 替代 `channel_engine` |

### 5.3 Phase 2: Kernel 层 + Bus

**目标**：将 `HarnessEngine` 改造为 Linux 内核风格的调度中心

```
backend/app/kernel/                     # 替代 app/engineering/harness/
├── __init__.py
├── kernel.py                           # MemOSKernel 主入口
│   # class MemOSKernel:
│   #     def __init__(self):
│   #         self.bus = KernelBus()
│   #         self.dispatcher = RequestDispatcher()
│   #
│   #     async def process(self, msg: KernelMessage):
│   #         pipeline = self.dispatcher.route(msg.type)
│   #         return await pipeline.execute(msg)
│
├── dispatcher.py                       # RequestDispatcher
│   # class RequestDispatcher:
│   #     def route(self, msg_type) → Pipeline:
│   #         "chat"   → ChatPipeline
│   #         "agent"  → AgentPipeline
│   #         "search" → SearchPipeline
│
├── bus.py                              # KernelBus（子系统总线）
│   # class KernelBus:
│   #     def register_subsystem(name, subsystem)
│   #     def get_subsystem(name) → Subsystem
│   #     async def call(subsystem, method, *args)
│   #     async def publish(event)
│   #     def subscribe(event_type, handler)
│
├── pipelines/
│   ├── __init__.py
│   ├── base.py                         # BasePipeline
│   │   # class BasePipeline(ABC):
│   │   #     async def execute(msg) → KernelResponse
│   │
│   ├── chat_pipeline.py                # ChatPipeline
│   │   # Context.load → Memory.retrieve → AI.assemble → AI.infer
│   │   # → Memory.store
│   │
│   └── agent_pipeline.py              # AgentPipeline
│       # Chat + Capability.resolve + Agent.invoke
│
└── data_structures.py                  # KernelResponse, PipelineResult
```

**核心：ChatPipeline 执行序列**

```python
class ChatPipeline(BasePipeline):
    async def execute(self, msg: KernelMessage) -> KernelResponse:
        # 1. 加载会话上下文
        ctx = await self.bus.call('context', 'load', msg.session)
        
        # 2. 检索工作记忆（对话历史）
        history = await self.bus.call('memory', 'get_chat_history', 
                                       msg.session.chat_id)
        
        # 3. 增强上下文（情景记忆 + RAG + 搜索）
        ctx = await self.bus.call('context', 'enhance', ctx, msg.payload.query)
        
        # 4. 组装 Prompt
        prompt = await self.bus.call('ai', 'assemble_prompt', ctx, history)
        
        # 5. LLM 推理
        result = await self.bus.call('ai', 'infer', prompt, msg.payload.model)
        
        # 6. 持久化记忆
        await self.bus.call('memory', 'store_episodic', msg, result)
        await self.bus.call('memory', 'sync_working', msg.session, result)
        
        return KernelResponse(content=result.content, ...)
```

**Bus 的事件解耦**：

```
Memory Subsystem ──[memory:updated]──→ KernelBus ──→ Context Subsystem (刷新缓存)
                                                     → AI Subsystem (下次自动包含)
                                                     → Logger (审计)
```

**改动文件**：
| 文件 | 操作 |
|------|------|
| `app/engineering/harness/engine.py` | → 迁移至 `app/kernel/kernel.py` |
| `app/engineering/context/engine.py` | → 迁移至 `app/kernel/subsystems/context_subsystem.py` |
| `app/engineering/inference/engine.py` | → 迁移至 `app/kernel/subsystems/ai_subsystem.py` |
| `app/engineering/prompt/engine.py` | → 迁移至 `app/kernel/subsystems/ai_subsystem.py` |

### 5.4 Phase 3: 子系统标准化

**目标**：每个子系统定义统一的 `load/store/search` 协议接口

```
backend/app/kernel/subsystems/
├── __init__.py
├── base.py                             # Subsystem 基类
│   # class Subsystem(ABC):
│   #     name: str
│   #     async def init()
│   #     async def shutdown()
│
├── memory_subsystem.py                 # MemorySubsystem
│   # 封装 MemoryManager
│   # 对外暴露: retrieve_working / search_episodic / store / sync
│
├── context_subsystem.py                # ContextSubsystem  
│   # 封装 ContextEngine
│   # 对外暴露: load / enhance / save / clear
│
├── ai_subsystem.py                     # AISubsystem
│   # 封装 PromptEngine + InferenceEngine
│   # 对外暴露: assemble_prompt / infer / infer_streaming
│
├── knowledge_subsystem.py              # KnowledgeSubsystem
│   # 封装 KnowledgeBaseManager
│   # 对外暴露: search / add_document / delete_document
│
└── capability_subsystem.py             # CapabilitySubsystem
    # 封装 MCPCapability + SkillManager
    # 对外暴露: resolve_tools / execute_tool / list_skills
```

**目录结构总览**：

```
backend/app/
├── gateway/          # Phase 1: 网络通讯网关（替代 channel/）
├── kernel/           # Phase 2: 控制中心（替代 harness/）
│   ├── bus.py
│   ├── dispatcher.py
│   ├── pipelines/
│   └── subsystems/   # Phase 3: 子系统驱动
│       ├── memory_subsystem.py
│       ├── context_subsystem.py
│       ├── ai_subsystem.py
│       ├── knowledge_subsystem.py
│       └── capability_subsystem.py
├── memory/           # 保留，协议驱动
├── knowledgebase/    # 保留，协议驱动
├── capabilities/     # 保留
├── program/          # API 层（调用 Gateway 替代 ChannelEngine）
├── core/             # 基础设施层
└── utils/            # 工具层
```

### 5.5 Phase 4: 安全体系

| 功能 | 实现方式 | 参考 |
|------|---------|------|
| **工具沙盒** | Docker SDK for Python 容器隔离 | Hermes Agent / OpenClaw |
| **Gateway 访问控制** | `allowFrom` + Token 认证 + 配对机制 | OpenClaw |
| **指令审批** | 危险操作（shell/文件写）须用户确认 | Hermes Agent |
| **凭证管理** | 环境变量注入 + 自动脱敏日志 | Hermes Agent |
| **Prompt 注入防护** | 输入扫描 + 敏感模式检测 | Hermes Agent |
| **会话安全边界** | `SessionPolicy`: 不同会话不同权限/沙盒 | OpenClaw |

### 5.6 Phase 5: 自我进化

| 功能 | 实现方式 | 参考 |
|------|---------|------|
| **Skill 自动学习** | CapabilitySubsystem 增加 `SkillLearner`：完成复杂任务后分析工作流 → 生成 SKILL.md | Hermes GEPA |
| **用户建模** | MemorySubsystem 增加 `UserProfile`：从对话中提取偏好/习惯 | Hermes Honcho |
| **记忆遗忘** | MemorySubsystem 增加 `TokenBudget`：Core Memory 硬上限 + 优先级排序 | Hermes |
| **子代理并行** | KernelBus 增加 `parallel_dispatch`：多任务隔离并发 | Hermes |

### 5.7 迁移兼容策略

为不破坏现有代码，采用渐进式迁移：

```python
# Phase 1 兼容层
# backend/app/engineering/channel/__init__.py
from app.gateway.gateway import Gateway as ChannelEngine  # 兼容旧引用

# Phase 2 兼容层
# backend/app/engineering/harness/__init__.py
from app.kernel.kernel import MemOSKernel as HarnessEngine  # 兼容旧引用
```

---

## 六、实施优先级矩阵

```
                 紧急度
                  │
         高       │       低
         ─────────┼─────────
                  │
    ┌─────────────┼─────────────┐
    │ Phase 1     │ Phase 3     │
    │ Gateway     │ Subsystem   │
    │ (1-2天)     │ (2-3天)     │
    ├─────────────┼─────────────┤
重  │             │             │
    │ Phase 2     │ Phase 4     │
要  │ Kernel+Bus  │ Safety      │
    │ (3-4天)     │ (2-3天)     │
性  ├─────────────┼─────────────┤
    │             │             │
    │ —           │ Phase 5     │
    │             │ Evolution   │
    │             │ (4-5天)     │
    └─────────────┴─────────────┘
```

**建议启动顺序**：Phase 1 → Phase 2 → Phase 4（安全必须先于进化）→ Phase 3（标准化）→ Phase 5

---

## 七、参考链接

- [OpenClaw 架构详解](https://openclaw.deeptoai.com/zh-CN/docs/openclaw-architecture)
- [Hermes Agent 5-Pillar Architecture](https://www.mindstudio.ai/blog/hermes-agent-5-pillar-architecture-memory-skills-soul-crons)
- [Hermes vs OpenClaw: Local AI Agents Compared](https://www.turingpost.com/p/hermes)
- [Hermes Agent 官方文档](https://hermesagentai.cn/)
- [Linux Kernel Architecture](https://www.kernel.org/doc/html/latest/)
