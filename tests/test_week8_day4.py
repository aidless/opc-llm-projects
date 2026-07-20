"""Week 8 Day 4 测试 — CAIL E2E pipeline."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from projects.graphrag_cn.data.cail_loader import load_cail_cases
from projects.graphrag_cn.graph import EntityGraph
from projects.graphrag_cn.storage import EntityRecord
from experiments.cail_e2e_pipeline import build_records_from_docs


def test_build_records_from_docs():
    """从 docs 构建 EntityRecord."""
    docs = load_cail_cases()
    records = build_records_from_docs(docs)
    assert len(records) == len(docs)
    for rec in records:
        assert rec.event
        assert rec.doc_id
        assert rec.source == "cail_gold"


def test_build_records_with_missing_gold():
    """缺失 gold_entities 时优雅降级."""
    docs = [{"id": "X", "text": "no gold", "category": "test", "timestamp": "2024-01-01"}]
    records = build_records_from_docs(docs)
    # 没 gold → 0 records (合法)
    assert len(records) == 0


def test_cail_pipeline_graph_construction():
    """CAIL 图谱构建 (10 节点 + 50 边)."""
    docs = load_cail_cases()
    records = build_records_from_docs(docs)
    eg = EntityGraph(records=records)
    stats = eg.get_stats()
    assert stats["n_nodes"] == 30
    assert stats["n_events"] == 10
    assert stats["n_participants"] == 20
    assert stats["n_edges"] == 50
    assert stats["edges_by_type"]["event_participates"] == 40
    assert stats["edges_by_type"]["participant_relates"] == 10


def test_cail_pipeline_retrieval_precise():
    """CAIL 检索精确匹配."""
    from projects.graphrag_cn.rag import GraphRetriever
    docs = load_cail_cases()
    records = build_records_from_docs(docs)
    eg = EntityGraph(records=records)
    gr = GraphRetriever(eg, docs)

    test_cases = [
        ("盗窃", "CAIL2019-CRIMINAL-0001"),  # 孙某盗窃案
        ("诈骗", "CAIL2019-CRIMINAL-0002"),  # 周某电信诈骗
        ("合同纠纷", "CAIL2018-CIVIL-0001"),  # 房屋买卖
        ("受贿", "CAIL2021-CRIMINAL-0001"),  # 局长受贿
    ]
    for query, expected_top in test_cases:
        hits = gr.retrieve(query, top_k=1)
        assert hits[0].doc_id == expected_top, f"Query '{query}' expected {expected_top}, got {hits[0].doc_id}"


def test_cail_pipeline_save_load():
    """CAIL 图谱保存 + 加载."""
    docs = load_cail_cases()
    records = build_records_from_docs(docs)
    eg1 = EntityGraph(records=records)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "graph.json"
        eg1.save_json(path)
        assert path.exists()

        eg2 = EntityGraph.load_json(path)
        assert eg2.graph.number_of_nodes() == 30
        assert eg2.graph.number_of_edges() == 50


def test_cail_pipeline_gold_consistency():
    """CAIL gold entities 与 cail_to_graphrag_doc 一致性."""
    from projects.graphrag_cn.data.cail_loader import cail_to_graphrag_doc
    docs = load_cail_cases()
    # 所有 doc 都应有 gold entities
    for d in docs:
        assert len(d["gold_entities"]) >= 1
        gold = d["gold_entities"][0]
        assert gold["event"]
        assert gold["type"]


@pytest.mark.asyncio
async def test_run_ollama_extract_returns_none_when_unavailable():
    """Ollama 不可用时返回 None."""
    from experiments.cail_e2e_pipeline import run_ollama_extract
    docs = load_cail_cases()
    # Patch OllamaClient to fail
    with patch("opc_platform.gateway.ollama.OllamaClient") as mock:
        mock.side_effect = Exception("Ollama unavailable")
        result = await run_ollama_extract(docs)
        assert result is None


def test_cail_query_through_2_hops():
    """CAIL 2-hop 查询 (跨案件连接).

    CAIL 10 案件用了 20 个不同法官 (每人 1 次), 无 cross-doc 共享 participant.
    因此 2-hop BFS 仅返回 1-hop 邻居 (没有 2-hop 跨案件).
    """
    from projects.graphrag_cn.graph import GraphQuery
    from projects.graphrag_cn.rag import GraphRetriever
    docs = load_cail_cases()
    records = build_records_from_docs(docs)
    eg = EntityGraph(records=records)
    gq = GraphQuery(eg)

    # 所有 participants 1 案 1 次 (CAIL 特征)
    participants = gq.list_participants()
    multi = [p for p in participants if p["count"] >= 2]
    # CAIL 法官独特, 无 cross-doc 共享
    assert len(multi) == 0, f"CAIL 法官应独特, 实际有 {len(multi)} 个 2+ 出现"

    # 2-hop BFS 应返回 0 (无 shared participant)
    related = gq.get_related_events("盗窃", max_hops=2)
    assert len(related) == 0, f"无 shared participant, 2-hop 应 0, got {len(related)}"


def test_cail_subcategory_distribution():
    """CAIL sub-category 分布符合预期."""
    docs = load_cail_cases()
    by_sub = {}
    for d in docs:
        for ge in d["gold_entities"]:
            sub = ge["event"]
            by_sub[sub] = by_sub.get(sub, 0) + 1
    # 应该有 10 unique sub-categories (因为我们 10 个不同案件)
    assert len(by_sub) == 10
    # 每个 sub-category 仅 1 doc
    for sub, n in by_sub.items():
        assert n == 1, f"{sub} 应仅 1 doc, got {n}"
