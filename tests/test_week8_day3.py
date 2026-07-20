"""Week 8 Day 3 测试 — CAIL 数据接入.

Week 9 Day 1 升级：用 importlib 直接加载 cail_loader 绕过 __init__ 依赖.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

# ===== 绕过 __init__.py 直接加载 cail_loader =====
_LOADER_PATH = Path(__file__).parent.parent / "projects" / "graphrag_cn" / "data" / "cail_loader.py"
_spec = importlib.util.spec_from_file_location("_cail_loader", _LOADER_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

CAIL_REAL_CASES = _mod.CAIL_REAL_CASES
cail_to_graphrag_doc = _mod.cail_to_graphrag_doc
get_cail_stats = _mod.get_cail_stats
load_cail_cases = _mod.load_cail_cases
save_cail_jsonl = _mod.save_cail_jsonl


def test_cail_cases_present():
    """内置 CAIL 真实案件."""
    assert len(CAIL_REAL_CASES) >= 10  # Week 8 初始 10 案件
    for case in CAIL_REAL_CASES:
        assert "case_id" in case
        assert "text" in case
        assert "category" in case
        assert "court" in case


def test_cail_categories_coverage():
    """CAIL 至少 3 类."""
    cats = set(c["category"] for c in CAIL_REAL_CASES)
    assert len(cats) >= 3
    # 包含主要类别
    assert "刑事" in cats
    assert "民事" in cats


def test_cail_to_graphrag_doc_format():
    """CAIL 案件 → GraphRAG-CN 格式."""
    case = CAIL_REAL_CASES[0]
    doc = cail_to_graphrag_doc(case)
    assert doc["id"] == case["case_id"]
    assert doc["category"] in ("legal", case.get("category", "legal"))
    assert "text" in doc
    assert "gold_entities" in doc
    assert len(doc["gold_entities"]) >= 1
    assert doc["gold_entities"][0]["event"]
    assert doc["split"] in ("train", "dev", "test")


def test_load_cail_cases():
    """加载所有 CAIL 案件."""
    docs = load_cail_cases()
    assert len(docs) == len(CAIL_REAL_CASES)
    for d in docs:
        assert "id" in d
        assert "text" in d
        assert "gold_entities" in d


def test_cail_stats():
    """CAIL 统计信息."""
    stats = get_cail_stats()
    assert stats["n_total"] >= 5
    assert "by_category" in stats
    assert "by_subcategory" in stats
    assert "year_range" in stats
    # year_range 应该是 [2018, 2025] (Week 8 + Week 9 Day 1+3 扩展)
    assert stats["year_range"][0] >= 2018
    assert stats["year_range"][1] >= 2023
    assert stats["year_range"][1] <= 2025


def test_save_cail_jsonl(tmp_path):
    """保存为 JSONL."""
    out = tmp_path / "cail.jsonl"
    n = save_cail_jsonl(out)
    assert n == len(CAIL_REAL_CASES)
    # 验证文件
    assert out.exists()
    with open(out, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == len(CAIL_REAL_CASES)
    for line in lines:
        d = json.loads(line)
        assert "id" in d
        assert "text" in d
        assert "gold_entities" in d


def test_cail_year_split_logic():
    """年份 split 逻辑: 2018-2020 train, 2021+ test."""
    for case in CAIL_REAL_CASES:
        doc = cail_to_graphrag_doc(case)
        if case["year"] < 2021:
            assert doc["split"] in ("train", "dev")
        else:
            assert doc["split"] == "test"


def test_cail_participants_extracted():
    """从 judges 提取参与方."""
    case = CAIL_REAL_CASES[0]  # 有 judges
    doc = cail_to_graphrag_doc(case)
    assert len(doc["gold_entities"][0]["participants"]) >= 1
    # 每个 participant 有 name + role
    for p in doc["gold_entities"][0]["participants"]:
        assert "name" in p
        assert "role" in p
