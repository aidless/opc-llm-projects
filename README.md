# GraphRAG-CN · 中文事件抽取 + 实体链接 + 图谱 + RAG

> **OPC 一人公司 GraphRAG 项目** — Phase 0+1+2 完整研发产物
> 包含 21 模块 / ~20,200 行代码 / 458 测试 / 251 docs / 10+ git commits

---

## 🎯 项目定位

**中文事件抽取 + 实体链接 + 知识图谱 + RAG 的端到端管线**，可商用化：
- 真实 CAIL 法律案件数据集 (51 案件 × 4 大类 × 22 sub-category)
- 中文人名提取 + 法官参与方链接
- 完整 Web Demo (Streamlit Cloud-ready)
- LangChain BaseRetriever + LCEL chain 兼容
- 商业化文档齐备 (PRICING/SLA/CASES/BETA/SUPPORT/DEPLOY)

---

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 加载 CAIL 数据
python projects/graphrag_cn/data/cail_loader.py projects/graphrag_cn/data/cail-cases.jsonl

# 3. 运行 E2E Pipeline
python experiments/cail_e2e_pipeline.py

# 4. 跨数据集评测
python experiments/cross_dataset_eval.py

# 5. 部署就绪验证
python experiments/deploy_readiness_check.py

# 6. 启动 Web Demo
streamlit run projects/graphrag_cn/demo/streamlit_app.py
```

---

## 📊 数据集

| 数据集 | 数量 | 类别 |
|---|---|---|
| `zh-docs-200.jsonl` | 200 | 法律/历史/新闻/学术/产品 |
| `zh-docs-50.jsonl` | 50 | 子集（小型测试） |
| `cail-cases.jsonl` | **51** | CAIL 真实法律案件（民事14/刑事21/行政8/知识产权8） |

---

## 🧪 测试

```bash
# 完整回归
python -m pytest tests/

# 关键套件
python -m pytest tests/test_week8_day3.py tests/test_week9_day1.py tests/test_week9_day2.py
```

---

## 📁 项目结构

```
opc-llm-projects/
├── projects/graphrag_cn/          # Phase 1 主线 (#5)
│   ├── data/                       # 数据加载 (zh + cail)
│   ├── extraction/                 # LLM 实体抽取
│   ├── link/                       # 实体链接 (embedder + linker)
│   ├── graph/                      # 图构建 + 查询
│   ├── rag/                        # RAG 检索 + QA + LangChain
│   ├── storage/                    # EntityIndex SQLite
│   ├── eval/                       # 评测指标
│   ├── demo/                       # Streamlit Web Demo
│   ├── cli.py                      # CLI 入口
│   └── README.md
├── opc_platform/                   # Phase 0 公共底座
│   ├── gateway/                    # OpenAI-compatible API
│   ├── prompts/                    # Prompt 追踪
│   ├── eval/                       # EvalIndex
│   ├── tracer/                     # 实验追踪
│   ├── visualize/                  # 结果可视化
│   ├── storage/                    # 存储抽象
│   ├── router/                     # 主备切换 + 限流
│   ├── splitter/                   # 时间切分
│   └── data_factory/               # 测试数据工厂
├── docs/                           # 商业文档 + 技术文档
│   ├── PRICING.md                  # 定价
│   ├── SLA.md                      # 服务等级
│   ├── CASES.md                    # 客户案例
│   ├── BETA_PROGRAM.md             # Beta 接入
│   ├── SUPPORT.md                  # 客户支持
│   ├── DEPLOYMENT.md               # 部署方案
│   ├── GITHUB_DEPLOY.md            # GitHub + Cloud 部署
│   ├── PUBLIC_DEPLOY_GUIDE.md      # 用户操作指南
│   └── architecture.md
├── tests/                          # 单元测试 + 集成测试
├── experiments/                    # 评测报告 + Day 日报
├── decisions/                      # 决策记录
├── platform/                       # 底座设计文档
├── requirements.txt
├── .gitignore
└── .streamlit/config.toml
```

---

## 📈 Gate 状态 (Phase 0+1+2)

| Gate | 评分 | 决策 |
|---|---|---|
| Gate 0 (底座) | 4.4/5 | ✅ PASS |
| Gate 1 (抽取 demo) | F1=0.69 | ✅ PASS |
| Gate 2 (图构建) | 4.5/5 | ✅ GO |
| Gate 3 (RAG 端到端) | 4.25/5 | ✅ GO |
| Gate 4 (商业化) | 4.5/5 | ✅ GO |
| Gate 5 (公开部署) | 4/5 | ⏳ 等用户推 GitHub |

---

## 🌐 部署

参见 `docs/PUBLIC_DEPLOY_GUIDE.md` 部署到 GitHub + Streamlit Cloud。

---

## 📄 License

OPC Platform · 私有项目 · MIT License (待定)
