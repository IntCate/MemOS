# MemOS - AI对话智能体

MemOS 是一个基于 Vue 3 和 Python FastAPI + PyWebview 开发的跨平台桌面应用，专注于提供强大的 AI 对话智能体功能，集成了 MCP（模型上下文协议）、企业级 RAG（检索增强生成）、Skill 技能系统以及记忆系统，为用户提供高效、智能的对话体验和知识管理解决方案。

## 项目特点

- **现代化技术栈**：Vue 3 + FastAPI + Python，提供流畅的用户体验和高性能后端
- **跨平台支持**：基于 Web 技术，可在多种操作系统上运行
- **分层架构**：清晰的四层后端架构（基础设施层 → 能力层 → AI 工程层 → 业务逻辑层），便于维护和扩展
- **丰富的功能**：集成 AI 对话、模型管理、文档处理、技能系统、记忆系统等多种功能

## 核心功能

### AI对话智能体
- 提供流畅的自然语言对话体验
- 支持多轮对话和上下文理解
- 可定制对话风格和行为
- 支持智能工具调用和 Agent 功能
- 基于 LangGraph 的编排引擎，支持复杂的 Agent 工作流

### MCP（模型上下文协议）
- 集成 Anthropic 模型上下文协议，支持工具调用
- 连接多个 MCP 服务器，加载和管理外部工具
- 将 MCP 工具转换为 LangChain 工具，与智能体集成
- 提供 MCP 工具的上传、管理和配置功能

### Skill 技能系统
- 基于文件系统的热插拔技能加载机制
- 通过 SKILL.md 文件定义技能元数据和行为描述
- 支持技能规格自动导出为 OpenAI Tool 格式，供 Agent 调用
- 后台文件监控，支持运行时动态新增、修改和删除技能
- 支持脚本和引用文件等技能附属资源

### 记忆系统
- 支持对话记忆的持久化存储和检索
- 基于语义相似度的记忆检索器
- 向量记忆存储，支持高效的相似度匹配
- 本地存储与向量存储双模支持

### 企业级RAG（检索增强生成）
- 支持多种文档格式导入（PDF、Word、Markdown等）
- 高效的向量检索和知识库管理
- 可定制的检索策略和阈值调整
- 支持多知识库并行检索
- 企业级数据安全和隐私保护

### 可视化功能
- 知识图谱可视化
- 上下文可视化
- 工具执行状态展示

## 技术栈

### 前端
- **框架**：Vue 3 (Composition API + `<script setup>`)
- **状态管理**：Pinia
- **路由**：Vue Router
- **构建工具**：Vite
- **UI组件**：自定义组件 + Font Awesome 7
- **其他**：Three.js (3D可视化), Monaco Editor (代码编辑), KaTeX (数学公式)

### 后端
- **框架**：FastAPI（RESTful API）
- **数据库/ORM**：SQLAlchemy ORM + LanceDB（向量数据库）
- **AI 编排**：LangChain, LangGraph
- **MCP 集成**：langchain-mcp-adapters
- **Agent 引擎**：推理引擎 + 编排引擎 + 上下文引擎 + 渠道引擎
- **LLM 供应商**：支持 OpenAI、Anthropic、Google、DeepSeek、Ollama、GitHub Models 等多种模型
- **嵌入模型**：OpenAI、Ollama、HuggingFace 多种嵌入模型支持
- **配置管理**：YAML + Pydantic Settings
- **桌面应用**：PyWebView

## 后端架构分层

```
┌─────────────────────────────────────────────────┐
│                 program/（业务逻辑层）              │
│   API 路由 → 服务层 → 数据仓库 → SQLAlchemy ORM    │
├─────────────────────────────────────────────────┤
│              engineering/（AI 工程层）              │
│   推理引擎 | 编排引擎 | 上下文引擎 | 渠道引擎        │
│   Prompt 模板引擎 | LLM 供应商适配 | Agent 管理     │
├─────────────────────────────────────────────────┤
│             capabilities/（能力层）                 │
│      MCP 能力服务 | Skill 技能系统（热插拔）        │
├─────────────────────────────────────────────────┤
│           infrastructure/（基础设施层）              │
│      数据基础设施 | 搜索基础设施 | 知识库 | 记忆系统  │
└─────────────────────────────────────────────────┘
```

## 环境要求

在开始开发前，请确保您的系统已安装以下软件：

- [Node.js](https://nodejs.org/) (v16+) - JavaScript 运行时
- [npm](https://www.npmjs.com/) (v7+) - Node.js 包管理器
- [Python](https://www.python.org/) (v3.8+) - Python 运行时
- [pip](https://pip.pypa.io/en/stable/) - Python 包管理器

## 快速开始

### 安装依赖

```bash
# 安装前端依赖
npm install

# 安装后端Python依赖
pip install -r backend/requirements.txt
```

### 启动开发服务器

#### 前端开发服务器
```bash
npm run dev
```

#### 后端开发服务器
```bash
python backend/main.py
```

#### 启动桌面应用
```bash
python backend/webview_main.py
```

## 项目结构

项目采用前后端分离的架构：

```
├── src/                          # Vue 前端代码
│   ├── assets/                   # 静态资源
│   ├── components/               # Vue 组件
│   ├── composables/              # Vue 组合式函数
│   ├── layout/                   # 布局组件
│   ├── router/                   # 路由配置
│   ├── services/                 # 服务层
│   ├── store/                    # Pinia 状态管理
│   ├── static/                   # 静态资源（CSS、JavaScript、字体等）
│   ├── utils/                    # 工具函数
│   ├── views/                    # 页面组件
│   ├── App.vue                   # 主应用组件
│   └── main.js                   # 应用入口文件
├── backend/                      # Python 后端代码
│   ├── app/                      # Python 应用代码
│   │   ├── __init__.py           # 应用工厂、服务注册
│   │   ├── dependencies.py       # FastAPI 依赖注入
│   │   ├── capabilities/         # 能力层
│   │   │   ├── mcp.py            # MCP 能力服务
│   │   │   └── skill/            # Skill 技能系统
│   │   │       ├── protocol.py   # 技能抽象协议
│   │   │       ├── manager.py    # 技能管理器
│   │   │       ├── file_skill.py # 基于文件的技能加载
│   │   │       ├── skill_loader.py   # 技能文件扫描器
│   │   │       └── skill_watcher.py  # 技能热更新监听器
│   │   ├── core/                 # 核心基础设施
│   │   │   ├── config.py         # 配置管理
│   │   │   ├── database.py       # SQLAlchemy 配置
│   │   │   ├── data_manager.py   # 数据初始化管理
│   │   │   ├── instance_manager.py   # 实例管理器
│   │   │   ├── logger.py         # 日志配置
│   │   │   └── service_container.py  # 服务容器（DI）
│   │   ├── engineering/          # AI 工程层
│   │   │   ├── channel/          # 渠道引擎
│   │   │   ├── context/          # 上下文引擎
│   │   │   ├── harness/          # 编排引擎
│   │   │   ├── inference/        # 推理引擎
│   │   │   ├── llm/              # LLM 供应商 & Agent 管理
│   │   │   └── prompt/           # Prompt 模板引擎
│   │   ├── infrastructure/       # 基础设施层
│   │   │   ├── data.py           # 数据基础设施
│   │   │   └── search.py         # 搜索基础设施
│   │   ├── knowledgebase/        # 知识库服务
│   │   │   ├── manager.py        # 知识库管理器
│   │   │   ├── embeddings/       # 嵌入模型适配器
│   │   │   └── stores/           # 向量存储
│   │   ├── memory/               # 记忆系统
│   │   │   ├── manager.py        # 记忆管理器
│   │   │   ├── retrievers/       # 记忆检索器
│   │   │   └── stores/           # 记忆存储
│   │   ├── models/               # 数据模型层
│   │   │   ├── database/         # SQLAlchemy ORM 模型
│   │   │   └── schemas/          # Pydantic 响应/输入模型
│   │   ├── program/              # 业务逻辑层
│   │   │   ├── api/              # FastAPI 路由
│   │   │   ├── repositories/     # 数据访问层
│   │   │   └── services/         # 业务服务层
│   │   └── utils/                # 工具模块
│   │       ├── error_handler.py
│   │       ├── file_utils.py
│   │       ├── path_manager.py
│   │       ├── validators.py
│   │       ├── message/          # 消息工具
│   │       ├── model/            # 模型工具
│   │       ├── rag/              # RAG 工具（文档加载、文本分割）
│   │       └── stream/           # 流式响应工具
│   ├── data/                     # 运行时数据目录
│   │   ├── config/               # SQLite 数据库
│   │   ├── logs/                 # 运行日志
│   │   ├── prompts/              # 系统提示词模板
│   │   ├── schemas/              # 消息格式定义
│   │   └── skills/               # 技能文件目录（热加载）
│   ├── main.py                   # 后端应用入口
│   ├── webview_main.py           # 桌面应用入口
│   └── requirements.txt          # Python 依赖配置
├── index.html                    # HTML 入口文件
└── package.json                  # npm 项目配置
```

## 开发指南

### Vue 前端开发

- 所有 Vue 组件和前端代码位于 `src/` 目录
- 使用 Vue 3 的 `<script setup>` 语法编写组件
- 状态管理使用 Pinia
- 路由配置位于 `src/router/` 目录

### Python 后端开发

- 后端代码位于 `backend/` 目录
- 使用 FastAPI 框架构建 RESTful API
- 四层架构：基础设施层 → 能力层 → AI 工程层 → 业务逻辑层
- 所有服务通过 `ServiceContainer` 统一管理，支持依赖注入
- 配置文件位于 `backend/app/core/config.py`
- 支持 Skill 技能热插拔，技能文件放置于 `backend/data/skills/` 目录

## 部署指南

### 开发环境

1. 安装依赖（见快速开始部分）
2. 启动前端和后端开发服务器
3. 访问前端开发服务器地址（默认：http://localhost:5173）

### 生产环境

1. 构建前端静态文件：
   ```bash
   npm run build
   ```
2. 部署后端应用（可使用 uvicorn、gunicorn 等）
3. 配置前端静态文件服务

## API 接口

后端提供了丰富的 API 接口，包括：
- 聊天相关：`/api/chats`
- 消息相关：`/api/messages`
- 模型管理：`/api/models`
- 嵌入模型：`/api/embedding-models`
- 文件管理：`/api/files`
- MCP 管理：`/api/mcp`
- 记忆管理：`/api/memory`
- 向量存储：`/api/vector`
- 设置管理：`/api/settings`
- 健康检查：`/api/health`

## 学习资源

- [Vue 3 官方文档](https://v3.vuejs.org/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [LangChain 文档](https://python.langchain.com/) - 用于RAG功能开发
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/) - 用于Agent编排

## 贡献指南

1. Fork 项目仓库
2. 创建功能分支
3. 提交代码变更
4. 发起 Pull Request

## 许可证

MIT License
