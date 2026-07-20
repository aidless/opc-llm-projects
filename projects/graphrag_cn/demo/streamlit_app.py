"""Streamlit Web Demo — Phase 2 Week 9 Day 2 (Cloud-ready).

功能:
1. 选择预设 query (10 个 demo queries per dataset)
2. 显示 Graph Retriever top-K doc
3. 显示 QA Engine 答案 (可选, 无 LLM 时跳过)
4. 显示 Latency / Tokens / Graph 拓扑
5. **Cloud-friendly**: 不依赖 .db 文件; 直接从 JSONL gold_entities 构建图谱
6. **数据集切换**: zh-docs-200 (Phase 1) 或 CAIL 51 (Phase 2 Week 9)
7. **demo mode 默认开**: 无 Ollama 时只显示检索 + 图谱, 不报错
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Set up project path (work in both local dev + Streamlit Cloud)
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st

from projects.graphrag_cn.rag import GraphRetriever
from projects.graphrag_cn.graph import EntityGraph

# QAEngine + OllamaClient 延迟导入 (避免 Cloud 环境加载失败)
try:
    from projects.graphrag_cn.rag import QAEngine  # noqa: F401
    from opc_platform.gateway.ollama import OllamaClient  # noqa: F401
    HAS_LLM = True
except Exception as _e:
    HAS_LLM = False
    _LLM_IMPORT_ERR = str(_e)


# ============== Streamlit Config ==============
st.set_page_config(
    page_title="GraphRAG-CN Web Demo",
    page_icon="🕸️",
    layout="wide",
)


# ============== Data Sources ==============

def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """加载 JSONL."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@st.cache_resource
def load_zh_docs():
    """加载 zh-docs-200."""
    path = project_root / "projects/graphrag_cn/data/zh-docs-200.jsonl"
    return _load_jsonl(path)


@st.cache_resource
def load_cail_docs():
    """加载 CAIL 51 案件 (from cail_loader)."""
    try:
        import importlib.util
        loader_path = project_root / "projects" / "graphrag_cn" / "data" / "cail_loader.py"
        spec = importlib.util.spec_from_file_location("_cail_loader", loader_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.load_cail_cases()
    except Exception as e:
        st.warning(f"CAIL 数据加载失败: {e}")
        return []


def build_records_from_docs(docs: list[dict]) -> list:
    """从 JSONL docs 的 gold_entities 构建 EntityRecord (不依赖 .db).

    这是 Cloud-friendly 的核心: 直接从 JSONL → records, 跳过 SQLite 持久化.
    """
    import uuid
    # 延迟导入 (避免循环 + 兼容 Cloud)
    try:
        from projects.graphrag_cn.storage import EntityRecord
    except Exception:
        # 退化: 用 SimpleNamespace
        from types import SimpleNamespace
        EntityRecord = lambda **kw: SimpleNamespace(**kw)

    records = []
    for d in docs:
        for ge in d.get("gold_entities", []):
            rec = EntityRecord(
                entity_id=str(uuid.uuid4()),
                doc_id=d["id"],
                event=ge.get("event", ""),
                type=ge.get("type", "未知"),
                date=ge.get("date", "2020-01-01"),
                participants=ge.get("participants", []),
                source="gold",
                confidence=1.0,
            )
            records.append(rec)
    return records


@st.cache_resource
def load_graph_for(dataset: str):
    """根据数据集选择加载 docs + 构建图."""
    if dataset == "zh-docs-200":
        docs = load_zh_docs()
    elif dataset == "CAIL 51":
        docs = load_cail_docs()
    else:
        docs = []

    if not docs:
        return [], None

    records = build_records_from_docs(docs)
    eg = EntityGraph(records=records)
    return docs, eg


@st.cache_resource
def build_retriever(dataset: str):
    """构建 retriever."""
    docs, eg = load_graph_for(dataset)
    if eg is None:
        return None, None
    return GraphRetriever(eg, docs), (docs, eg)


# ============== Page ==============

PRESET_QUERIES = {
    "zh-docs-200": [
        "盗窃案", "论文发表", "体育赛事", "新能源项目", "诈骗案",
        "历史事件", "产品发布", "离婚案", "交通肇事", "医疗突破",
    ],
    "CAIL 51": [
        "盗窃", "诈骗", "故意伤害", "受贿", "合同纠纷",
        "专利侵权", "商标侵权", "挪用公款", "行政诉讼", "土地征收",
    ],
}


def main():
    st.title("🕸️ GraphRAG-CN Web Demo")
    st.markdown("""
    **中文事件抽取 + 实体链接 + 图谱 + RAG** 端到端演示。

    - **数据集**：zh-docs-200 (200 模拟) / CAIL 51 (真实法律案件)
    - **LLM (可选)**：Ollama `qwen2.5:3b-instruct-q4_K_M` (本地)
    - **图**：动态构建 (Cloud-friendly, 无 .db 依赖)
    """)

    # Sidebar
    st.sidebar.header("📊 数据集")
    dataset = st.sidebar.radio(
        "选择数据集:",
        ["zh-docs-200", "CAIL 51"],
        help="zh-docs-200 是 Phase 1 模拟数据; CAIL 51 是真实法律案件",
    )

    st.sidebar.header("⚙️ 模式")
    # 自动检测 LLM 可用性 + 用户可强制 demo 模式
    llm_available_env = os.environ.get("OLLAMA_HOST") or os.environ.get("ENABLE_LLM")
    force_demo = st.sidebar.checkbox(
        "Demo Mode (跳过 LLM, 仅检索 + 图谱)",
        value=not (HAS_LLM and llm_available_env),
        help="Cloud 环境无 Ollama 时自动启用",
    )

    # Load
    with st.spinner(f"加载 {dataset} ..."):
        retriever, ctx = build_retriever(dataset)
        if retriever is None:
            st.error(f"❌ {dataset} 加载失败")
            st.stop()
    docs, graph = ctx
    st.success(
        f"✅ {dataset}: {len(docs)} docs / "
        f"{graph.graph.number_of_nodes()} graph nodes / "
        f"{graph.graph.number_of_edges()} edges"
    )

    # Sidebar - preset queries
    st.sidebar.header("📋 Preset Queries")
    preset = PRESET_QUERIES.get(dataset, [])
    if not preset:
        st.sidebar.warning("该数据集无 preset queries")
    selected = st.sidebar.radio("选择 query:", preset or ["(无)"])

    # Custom query
    custom = st.sidebar.text_input("或输入自定义 query:", "")

    query = custom if custom else selected

    # Settings
    st.sidebar.header("⚙️ Settings")
    top_k = st.sidebar.slider("Top-K", 1, 10, 3)

    # Run
    run_clicked = st.sidebar.button("🚀 Run Query", type="primary")
    if run_clicked or custom:
        with st.spinner(f"查询: {query}"):
            try:
                hits = retriever.retrieve(query, top_k=top_k)
            except Exception as e:
                st.error(f"❌ 检索失败: {e}")
                st.stop()

        # Layout: 2 columns
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader(f"📚 Retrieved Top-{len(hits)} Documents")
            if not hits:
                st.info("(无检索结果)")
            for i, hit in enumerate(hits, 1):
                with st.expander(f"[{i}] {hit.doc_id} (score={hit.score:.3f})"):
                    st.markdown(f"**类别**: {hit.doc_category}")
                    st.markdown(f"**事件**: {hit.doc_event}")
                    st.markdown(f"**text_score**: {hit.text_score:.3f}")
                    st.markdown(f"**graph_score**: {hit.graph_score:.3f}")
                    if hit.matched_events:
                        st.markdown(f"**匹配事件**: {', '.join(hit.matched_events)}")
                    if hit.matched_participants:
                        st.markdown(f"**匹配参与方**: {', '.join(hit.matched_participants)}")
                    st.text(f"{hit.doc_text[:300]}")

        with col2:
            st.subheader("💬 QA Answer")
            st.markdown(f"**Q**: {query}")

            if force_demo or not HAS_LLM:
                # Demo mode: 只显示检索, 不调 LLM
                st.info(
                    f"🔒 **Demo Mode**: 仅展示检索结果。"
                    f"{'环境无 Ollama' if not HAS_LLM else '用户启用'}。"
                    "完整 RAG 答案请启用本地 Ollama."
                )
                # 用检索到的 doc text 拼接一个简单答案
                if hits:
                    snippet = " / ".join(h.doc_text[:60] for h in hits[:3])
                    st.markdown(f"**伪答案**: {snippet}...")
                else:
                    st.markdown("(无相关文档)")
                st.markdown(f"**Latency**: ~0 ms (纯检索)")
                st.markdown(f"**Model**: `(none, demo mode)`")
                st.markdown(f"**Retrieved**: {len(hits)} docs")
            else:
                # Real LLM mode
                try:
                    from opc_platform.gateway.ollama import OllamaClient
                    from projects.graphrag_cn.rag import QAEngine
                    llm = OllamaClient(model="qwen2.5:3b-instruct-q4_K_M", timeout=120.0)
                    engine = QAEngine(retriever, llm=llm)
                    result = asyncio.run(engine.answer(query, top_k=top_k, max_tokens=200))
                    st.info(result.answer or "(无答案)")
                    st.markdown("---")
                    st.markdown(f"**Latency**: {result.latency_ms} ms")
                    st.markdown(f"**Tokens**: {result.prompt_tokens} + {result.completion_tokens}")
                    st.markdown(f"**Model**: `{result.model}`")
                    st.markdown(f"**Retrieved**: {len(result.retrieved)} docs")
                except Exception as e:
                    st.error(f"❌ LLM 调用失败: {e}")
                    st.info("💡 建议: 勾选 Demo Mode 仅看检索结果")

        # Graph stats
        st.subheader("🕸️ Graph Snapshot")
        col3, col4, col5 = st.columns(3)
        stats = graph.get_stats()
        with col3:
            st.metric("Nodes", stats["n_nodes"])
        with col4:
            st.metric("Edges", stats["n_edges"])
        with col5:
            st.metric("Events", stats["n_events"])

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"""
    **Phase 2 Week 9 Day 2**

    🕸️ GraphRAG-CN
    📊 当前: {dataset}
    🔒 模式: {'Demo (无 LLM)' if force_demo or not HAS_LLM else 'Full RAG'}

    📖 [GitHub 仓库](#)
    💼 [商业化方案](docs/PRICING.md)
    """)


if __name__ == "__main__":
    main()