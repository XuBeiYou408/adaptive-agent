# RAG 问答系统 (Enterprise Edition)

基于 LangChain + BGE + FAISS + DeepSeek 的企业级 RAG 问答系统，支持混合检索、查询重写、重排序、流式输出、增量索引更新与全链路评估。

## 项目结构

```
rag-enterprise/
├── run.py                         # 启动入口 (uvicorn)
├── config.py                      # 环境变量与全局配置
├── README.md
│
├── app/                           # FastAPI 应用层
│   ├── __init__.py
│   ├── main.py                    # App 实例、日志系统、路由注册
│   ├── schemas.py                 # Pydantic 请求/响应模型
│   └── routes/
│       ├── __init__.py
│       └── ask.py                 # /health /ask /stream 接口
│
├── rag/                           # RAG 核心逻辑层
│   ├── __init__.py
│   ├── embeddings.py              # BGE Embedding 模型封装
│   ├── vector_store.py            # FAISS 向量库管理、持久化、增量更新、损坏恢复
│   ├── loader.py                  # PDF / Markdown 文档加载
│   ├── splitter.py                # 文档清洗 + 父子块递归切分
│   ├── rewriter.py                # LLM 查询重写（多视角检索）
│   ├── retriever.py               # 混合检索（向量 + BM25）、并行召回
│   ├── reranker.py                # FlagEmbedding 重排序
│   ├── dedup.py                   # 文档去重（来源 + 内容联合键）
│   ├── prompts.py                 # 提示词模板（重写 + 问答）
│   ├── llm.py                     # LLM 实例配置 (DeepSeek-Chat)
│   └── chain.py                   # LangChain 问答链组装 (LCEL)
│
├── evaluator/                     # 全链路评估框架
│   ├── test_dataset.py            # 黄金测试数据集生成器
│   └── evaluator.py               # 三层评估管道（检索/工程/生成质量）
│
└── utils/                         # 通用工具层
    ├── __init__.py
    └── noise_suppressor.py        # 警告/日志屏蔽、离线 HuggingFace 模式
```

## 架构

```
run.py
  │
  └── app/main.py ── app/routes/ask.py ── rag/chain.py
                                              │
              ┌───────────────────────────────┤
              │                               │
         rag/retriever.py              rag/llm.py
              │                               │
    ┌────┬────┼────┬────┐              rag/prompts.py
    │    │    │    │    │
 vector  BM25  rewriter  reranker
 _store 检索     │         │
         查询重写(rag/llm.py)
    │
    ├── rag/embeddings.py ── SentenceTransformer (BGE)
    ├── rag/vector_store.py ── FAISS + manifest.json
    ├── rag/loader.py ── PyMuPDF + TextLoader
    ├── rag/splitter.py ── 父子块切分
    └── rag/dedup.py ── 来源+内容去重
```

## 检索流水线

```
用户问题
  │
  ├─ ① 查询重写 ── DeepSeek LLM 将问题扩展为 3 个视角
  │
  ├─ ② 并行检索 ── 每个视角同时执行向量检索 (FAISS) + 关键词检索 (BM25)
  │
  ├─ ③ 展平合并 ── 多路召回结果合并
  │
  ├─ ④ 去重 ── 按 (来源, 内容) 联合键去重
  │
  ├─ ⑤ 重排序 ── BGE-Reranker 精排，取 Top-5
  │
  ├─ ⑥ 父子块扩展 ── 子块展开回父块获取完整上下文
  │
  ├─ ⑦ 二次去重 ── 扩展后再次去重
  │
  └─ ⑧ LLM 生成 ── DeepSeek-Chat 生成最终答案
```

## 功能模块

| 模块 | 功能 | 技术栈 |
|------|------|--------|
| 文档加载 | PDF + Markdown 批量导入 | PyMuPDF + LangChain TextLoader |
| 文档切分 | 中英文感知清洗 + 父子块递归切分并完整保留 `source`/`page` 元数据 | RecursiveCharacterTextSplitter (父块 800, 子块 300) |
| 向量化 | 中文语义向量生成 | BGE-base-zh-v1.5 (本地绝对路径加载) |
| 向量存储 | 持久化 + 增量更新 + 索引损坏自愈 | FAISS (HNSW + Cosine) + manifest.json |
| 查询重写 | 中英双语多视角问题扩展 + 行首序号过滤 | DeepSeek-Chat |
| 混合检索 | 语义 (Top-35) + 关键词 (Top-6) 并行检索 | Vector + BM25 + ThreadPoolExecutor |
| 重排序 | 召回精排 | BGE-Reranker-base (本地加载，限定 Top-45 候选) |
| 流式输出 | SSE (Server-Sent Events) | FastAPI StreamingResponse |
| 全链路评估 | 6维度全息自动化评估 (含检索/工程/生成质量/完整性等) | DeepSeek-Chat (LLM-as-Judge) |

## 关键设计决策

### 父子块切分

子块 (300 tokens, overlap=45) 用于精准向量检索，父块 (800 tokens, overlap=100) 提供完整上下文。检索命中子块后，通过元数据映射自动展开为父块内容，解决块大小困境——小块的精准匹配与大块的完整语义不可兼得。

### 增量索引更新

FAISS 不支持高效的原位删除或更新。系统通过 `manifest.json` 跟踪每个文件的 SHA-256 哈希和修改时间实现增量同步：
- **新增文件** → 增量追加到现有索引
- **修改/删除文件** → 触发 FAISS 索引全量重建

### 混合检索并行化

Embedding 和 Reranker 推理是 CPU/GPU 密集型操作，会阻塞 FastAPI 事件循环。使用 `asyncio.to_thread` + `ThreadPoolExecutor` 将这些任务从主事件循环中剥离，保证 API 响应不阻塞。

### 查询重写后公平排序

各路召回结果先合并再统一重排序，不按来源做硬截断（仅设 45 条安全上限），保证重写后的查询视角获得公平的排序机会。

### 中英多视角检索与查询自动清洗

对于包含英文技术术语、代码概念或可能对应英文技术文档（如LangChain, Matplotlib, JSON, PyTorch等）的查询，查询扩展器会自动生成针对性的英文/代码检索词（如 `langchain.debug = True` 或 `verbose=True`），极大地提升了中英混合技术文档库的检索召回率。同时，在接收端通过正则表达式过滤行首多余的序号标记（如 `1. `、`2) ` 等），避免污染向量空间。

### Windows 运行环境防闪退兼容性设计 (DLL/OpenMP 修复)

在纯离线 Windows 部署环境中，由于 `sentence_transformers` 导入链（包含 `datasets` 与 `pyarrow`）的 C 级扩展加载的 OpenMP 运行时冲突，容易导致 Python 进程无声闪退（exit code 1）。系统在全局防御入口中强制设置 `KMP_DUPLICATE_LIB_OK=TRUE` 并严格按 `numpy` -> `scipy` -> `sklearn` -> `transformers` 顺序初始化预加载依赖库，彻底消除了底城动态库冲突，保证系统自适应高健壮运行。

### LLM-as-Judge 三级 Few-Shot 校准

评估系统使用 LLM 作为裁判对生成质量打分。为消除评分两极化（非 1 即 0），在 judge prompt 中内置高/中/低三级 few-shot 示例，并显式约束评分区间（0.30~0.85 为常见质量区间），使评分具有区分度。temperature=0.0 保证同一数据集多次评估结果完全一致。此外，新增了 `completeness`（答案完整性）维度评估。

## 模块详细逻辑

### `evaluator/test_dataset.py` — 黄金测试数据集生成

从知识库的 `safe_all_wenjian`（已切分文档列表）中随机采样 N 个片段，通过固定种子 `random.seed(42)` 保证每次采样结果一致。过滤掉短于 50 字符的无意义片段（目录页、免责声明等）。对每个采样片段，调用 DeepSeek-Chat 以"出题官"角色反向生成一个问答对（question + ground_truth），并将源文档的父块 ID（`dad_id`）绑定到每个测试用例上，作为检索评估的"正确答案定位锚点"。生成后校验 QA 质量（question > 10 字符、ground_truth > 20 字符），不合格则自动重试最多 3 次。最终输出 `golden_dataset.json` 到 `LOCAL_DB_PATH`。

### `evaluator/evaluator.py` — 三层全链路评估管道

首先导入 `utils.noise_suppressor` 应用 Windows 环境 DLL 冲突及 OpenMP 防闪退配置。对 `golden_dataset.json` 中的每条测试用例，依次执行三层评估：

- **检索层**：调用生产环境的 `zhaohui_and_rerank()` 获取 Top-45 重排文档，检查目标 `dad_id` 是否在最终返回列表内（Hit Rate）、出现在第几位（MRR）
- **工程层**：在流式生成过程中测量 TTFT（首字延迟）和端到端总延迟
- **生成层**：将「问题 + 检索上下文 + 系统回答 + 参考答案」提交给 LLM 裁判，在 faithfulness（忠实度 / 幻觉控制）、answer_relevance（答案相关性）、completeness（完整性 / vs 参考答案）三个维度打分。temperature=0.0 + 三级 few-shot 校准保证评分稳定

最终输出结构化评估大盘，保存 `evaluation_results.json`（含每个 case 的评分与理由），并基于分数自动生成诊断建议。

### `rag/embeddings.py` — BGE Embedding 模型封装

将 `SentenceTransformer` (BGE-base-zh-v1.5) 包装为 LangChain 兼容的 `Embeddings` 接口。优先从本地绝对路径加载模型，失败时回退到 HuggingFace Hub。自动检测 CUDA 可用性并移动模型到 GPU（CPU 环境则保留在内存）。输出向量经过归一化处理以适配 Cosine 相似度计算。

### `rag/vector_store.py` — FAISS 向量库管理

维护本地 FAISS 索引文件（HNSW + Cosine）和对应的 docstore pickle。启动时通过 `manifest.json` 判断知识库变更：新文件增量追加索引，修改/删除文件触发全量重建。支持索引损坏检测——加载失败时自动清空并重建。导出 `xiangliangshujuku`（FAISS 实例）和 `safe_all_wenjian`（清洗后的 LangChain Document 列表）供检索和评估模块使用。

### `rag/loader.py` — 文档加载

递归遍历 `YUAN_SUCAI_PATH` 目录，使用 `PyMuPDFLoader` 加载 PDF 文件（保留页码元数据），使用 `TextLoader` 加载 Markdown 文件。返回按文件类型分类的文档列表。

### `rag/splitter.py` — 文档清洗与父子块切分

先用正则清洗文档文本（合并中文和英文被不当换行的行）。然后执行两轮 `RecursiveCharacterTextSplitter` 切分：第一轮生成父块（800 tokens, overlap=100/PDF 120/MD），第二轮将每个父块切为子块（300 tokens, overlap=45/PDF 150/MD）。每个子块的元数据中写入 `dad_id` 和 `dad_content`，建立父子关联。最终导出子块列表——检索用子块精确匹配，回答时展开父块获取完整上下文。

### `rag/rewriter.py` — LLM 查询重写

接收用户原始问题，通过 DeepSeek-Chat（temperature=0, max_tokens=150）调用，指示模型将问题从不同角度扩展为 3 个语义等价但措辞不同的表述（如果包含英文技术概念则包含中英双语扩展式），用于多视角检索以提高召回覆盖率。接收端通过正则表达式自动剥离行首多余的序号标记（如 `1. `、`2) ` 等）以防污染检索。API 调用失败时自动降级为只使用原始问题。

### `rag/retriever.py` — 混合检索编排

核心异步函数 `zhaohui_and_rerank()`：先异步并行调用 rewriter 获取多视角问题列表与启动首路原始问题检索，然后对其余视角使用 `ThreadPoolExecutor` (max_workers=5) 并行执行向量检索（FAISS, Top-35）和 BM25 关键词检索（Top-6）。多路结果合并后经过去重、reranker 重排序（Top-45）、父子块展开、二次去重，最终返回组装好的上下文文本。`return_documents=True` 时返回完整 Document 对象（含元数据），供评估系统使用。

### `rag/reranker.py` — BGE-Reranker 重排序

封装 `FlagReranker` (BGE-reranker-base)，以 FP16 精度从本地路径加载。对每个查询-文档对计算相关性分数，按分数定位最相关的 Top-5 并在返回前注入完整父块内容。内置 45 条文档安全重排上限，防止检索召回过多时 OOM。

### `rag/dedup.py` — 文档去重

以 `(source, page_content)` 元组为联合键，使用集合跟踪已出现的文档，移除完全重复的条目。

### `rag/prompts.py` — 提示词模板

定义两个 `ChatPromptTemplate`：
- `rewrite_prompt`：查询重写指令，要求 LLM 从不同角度重新表述问题
- `llm_prompt`：问答系统 prompt，注入检索上下文和用户问题，约束 LLM 仅基于上下文回答

### `rag/llm.py` — LLM 实例配置

创建两个 `ChatOpenAI` 实例，均指向 DeepSeek-Chat API：
- `rewrite_llm`：temperature=0, max_tokens=150, 非流式（用于查询重写）
- `llm`：temperature=0, max_tokens=500, 流式模式（用于生成回答）

### `rag/chain.py` — LCEL 链组装

使用 LangChain Expression Language (LCEL) 组装问答链：
```
{"context": retrieved_docs, "input": user_question}
  → llm_prompt (模板注入)
  → llm (DeepSeek 流式生成)
  → StrOutputParser (提取纯文本)
```
导出 `rag_chain` 对象供 API 路由调用。

### `app/main.py` — FastAPI 应用实例

创建 `FastAPI` 实例，配置日志系统（INFO 级别 + 格式化），通过 `include_router` 注册 `ask.py` 中的路由。

### `app/schemas.py` — 请求/响应模型

定义 `QueryRequest` Pydantic 模型，包含 `question: str` 字段，用于 API 入参校验。

### `app/routes/ask.py` — API 端点

提供三个端点：
- `GET /health`：健康检查，返回 `{"status": "ok"}`
- `POST /ask`：标准问答，同步返回答案 + 耗时
- `POST /stream`：SSE 流式问答，使用 `StreamingResponse` 逐 token 推送

### `utils/noise_suppressor.py` — 噪声抑制与 Windows 兼容性自适应

系统的全局初始化防御塔。首先执行 Windows 兼容性保护——注入环境变量 `KMP_DUPLICATE_LIB_OK=TRUE` 并严格执行 `numpy -> scipy -> sklearn -> transformers` 依赖加载顺序，彻底解决了 Windows 上 MKL/OpenMP 引起的底层 C 级闪退崩溃。同时，强制开启 HuggingFace `HF_HUB_OFFLINE=1` 离线模式，并对 `transformers`、`chromadb`、`httpx` 及 `sentence_transformers` 进行强力静音，保证控制台输出纯净、不刷屏。

## 环境要求

- Python 3.10+
- CUDA (可选，CPU 可运行)

## 环境变量

`.env` 文件需配置以下变量：

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `DEEPSEEK_API_URL` | DeepSeek API 地址 |
| `HF_HOME` | HuggingFace 缓存根目录 |
| `BGE_MODEL_PATH` | BGE 模型本地路径 (snapshot 目录) |
| `RERANKER_MODEL_PATH` | Reranker 模型本地路径 (snapshot 目录) |
| `YUAN_SUCAI_PATH` | 知识库文档目录 (PDF/MD 源文件) |
| `LOCAL_DB_PATH` | FAISS 向量库持久化路径 |

## 依赖

```
langchain-community
langchain-core
langchain-text-splitters
langchain-openai
sentence-transformers
faiss-cpu          # 或 faiss-gpu (CUDA 环境)
FlagEmbedding
rank_bm25
PyMuPDF
fastapi
uvicorn
pydantic
python-dotenv
torch
```

## 启动

```bash
# 1. 安装依赖
pip install langchain-community langchain-core langchain-text-splitters langchain-openai \
  sentence-transformers faiss-cpu FlagEmbedding rank_bm25 PyMuPDF \
  fastapi uvicorn pydantic python-dotenv torch

# 2. 配置 .env（复制模板并按需填写）

# 3. 启动服务
python run.py

# 4. 验证
curl http://localhost:8000/health
```

## API

### `GET /health`

健康检查，返回 `{"status": "ok"}`。

### `POST /ask`

标准问答接口。

**请求：**
```json
{"question": "什么是 RAG？"}
```

**返回：**
```json
{"answer": "...", "cost_time": 1.23}
```

### `POST /stream`

流式问答接口 (SSE)。

**请求：**
```json
{"question": "什么是 RAG？"}
```

**返回：** SSE 事件流 `data: ...\n\n`
