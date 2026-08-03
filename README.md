# 面向异构技术文档的自适应容灾型问答 Agent 协同系统 (v2.0)

基于 LangChain + DeepSeek + Firecrawl + FAISS + Vue 3 的企业级智能问答 Agent 协同系统。项目旨在解决静态知识库（RAG）检索中**无法处理逻辑算术运算、缺乏互联网时效性扩展、搜索反爬/死循环、以及会话历史在动态环境部署易混淆崩溃**等工程痛点。

---

## 🛠️ 项目技术亮点与核心架构 (v2.0 全景)

本系统由**前端全景大盘 (Vue 3 + Pinia)、前置分类网关 (Router)、ReAct 协同决策环 (Firecrawl/LangChain)、自适应记忆网关 (Session Isolation)** 四大部分组成：

```mermaid
graph TD
    User(["用户 Web UI (Vue 3 / Element Plus)"]) --> Router{"意图分类路由器 (rag/router.py)"}
    Router -- "简单检索 (simple_rag)" --> RAG["RAG 知识库检索直连通道"]
    Router -- "长文总结 (summarize)" --> Summarize["文档摘要直连通道"]
    Router -- "逻辑计算/时效推理 (agent)" --> Agent["ReAct Agent 自主规划环"]
    
    subgraph agent_engine ["Agent 核心引擎 (rag/agent.py)"]
        Agent --> Memory[("独立 Session 记忆网关 (rag/memory.py)")]
        Agent --> Tools{"Toolbox 协同工具箱"}
        Tools -- "Firecrawl 云端搜索/降级" --> FC_Tool["Firecrawl Web Search Tool"]
        Tools -- "向量+BM25混合召回" --> RAG_Tool["FAISS RAG Tool"]
        Tools -- "物理沙箱计算" --> Calc_Tool["Calculator Tool"]
        Tools -- "文档全局摘要" --> Sum_Tool["Summary Tool"]
    end
    
    Memory -. " Session 物理隔离 " .- Storage[("SQLite / LocalStorage Session Store")]
    Agent -. "流式Thought/Content" .- SSE["SSE 协议分发 (app/routes/ask.py)"]
```

---

## 📂 项目目录结构

```
rag-enterprise/
├── run.py                         # FastAPI 服务启动入口 (Uvicorn)
├── config.py                      # 环境变量读取 (Firecrawl / DeepSeek / 路径预检)
├── README.md                      # [UPGRADED] 项目最新架构与使用说明文档
├── requirements.txt               # 第三方依赖库列表 (已包含 firecrawl-py)
├── .env.example                   # 环境变量安全配置范本 (已脱敏)
│
├── app/                           # FastAPI 服务应用层
│   ├── main.py                    # FastAPI 实例配置与前端 dist 静态目录挂载
│   ├── schemas.py                 # Pydantic 接口入参校验模型 (支持 session_id 校验)
│   └── routes/
│       └── ask.py                 # 问答/流式 SSE /评估结果全套路由
│
├── frontend/                      # [NEW] Vue 3 + Pinia + Element Plus 前端生产项目
│   ├── dist/                      # 编译打包构建产物 (开箱即用直接运行)
│   ├── src/
│   │   ├── api/                   # 接口请求封装 (含 SSE 流解析与 session_id 透传)
│   │   ├── stores/                # Pinia 状态中心 (rag_sessions_history 物理隔离)
│   │   ├── views/                 # 页面视图 (ChatView, HistoryView, EvaluationView 评估大盘)
│   │   └── components/            # DeepSeek 思考流卡片、评分卡片、多轮 waterfall
│   ├── package.json
│   └── vite.config.js
│
├── rag/                           # 核心算法与智能体逻辑层
│   ├── agent.py                   # ReAct Agent 装配中心与 Strict Format Protocol 语法防死锁
│   ├── memory.py                  # Session 级别独占记忆管理器
│   ├── router.py                  # 前置轻量级 LLM 意图路由器 (快慢道分离)
│   ├── embeddings.py              # BGE Embedding 惰性延迟加载器
│   ├── vector_store.py            # FAISS 向量库增量构建与损坏自愈
│   ├── retriever.py               # 混合检索 (语义 + BM25 并行重排)
│   └── tools/                     # [UPGRADED] 协同工具箱
│       ├── web_search_tool.py     # Firecrawl 云端主搜 + 本地降级 + 物理熔断器
│       ├── calculator_tool.py     # 沙箱计算器
│       └── summary_tool.py        # 全局摘要生成器
│
└── evaluator/                     # 自动化全链路评测框架
    ├── test_dataset.py            # 黄金测试数据集自动生成器
    └── evaluator.py               # 检索层/工程层/生成质量 3 维评估管道
```

---

## ⚡ 核心协同工具箱 (Toolbox v2.0)

1. **`wangye_sousuo_tool` / `bing_web_search_tool` / `baidu_web_search_tool` (Firecrawl 驱动)**：
   * **主搜索引擎**：接入工业级 **Firecrawl 云端 search API** (`https://api.firecrawl.dev/v1/search`)，天然提取高纯度 Markdown 正文，100% 清除 ICP 备案、广告与导航噪声。
   * **后备与熔断器**：当网络波动时无缝降级至通用抽取器，并植入 **单轮调用物理熔断器 (`_check_and_increment_call`)**，同一个会话被调用超 2 次强行熔断并输出 Final Answer 指令，彻底斩断 ReAct 死循环。
2. **`xiangliang_and_bm25_zhaohui` (FAISS RAG Tool)**：
   * 本地 FAISS (稠密向量，Top-35) + BM25 (稀疏关键词，Top-6) 混合召回，经过 BGE-Reranker 重排截取 Top-15。支持父子块扩展机制（300 Tokens 子块检索命中自动扩展为 800 Tokens 父块）。
3. **`jisuanqi_tool` (Physical Sandbox Calculator)**：
   * 限制表达式 100 字符内，去除 `__builtins__` 的物理隔离安全沙箱计算器，解决大模型高维乘法与字节计算幻觉。
4. **`wendang_zhaiyao_tool` (Summary Tool)**：
   * 全局检索特定主题文档并生成结构化大纲与 Markdown 摘要。

---

## 🚀 快速开始

### 1. 配置环境变量
在项目根目录下复制 `.env.example` 为 `.env` 并填入密钥：
```ini
DEEPSEEK_API_KEY='sk-ba81e719...'                  # DeepSeek 密钥
FIRECRAWL_API_KEY='fc-b1659da2...'                 # Firecrawl 密钥
DEEPSEEK_API_URL='https://api.deepseek.com'         # API 基址
HF_HOME='D:/rag/bge_models'                         # 本地模型缓存目录
BGE_MODEL_PATH='D:/rag/bge_models/hub/models...'    # BGE Embedding 模型目录
RERANKER_MODEL_PATH='D:/rag/bge_models/models...'   # BGE Reranker 模型目录
LOCAL_DB_PATH='D:/rag/faiss-db'                     # FAISS 持久化目录
```

### 2. 启动服务 (开箱即用)
```bash
# 启动统一 FastAPI + Vue 3 服务
python run.py
```
启动后访问 `http://localhost:8010` 即可直接体验全套功能（包括 DeepSeek 思考流、多轮 Session 历史与评估大盘看板）。

---

## 📊 评估看板与数据集

项目包含自动化评估管道 `evaluator/evaluator.py`，支持以下三个核心指标评测：
* **检索层**：Hit Rate@5 (目标 > 65%), MRR@5 (目标 > 0.40)
* **工程层**：首 Token 延迟 TTFT (< 5.0s), 整体 Latency (< 6.0s)
* **生成质量**：忠实度 Faithfulness (> 0.75), 答案相关度 Relevance (> 0.80)
评测结果将实时同步呈现于 Vue 3 评估大盘视图 (`/#/evaluation`)。
