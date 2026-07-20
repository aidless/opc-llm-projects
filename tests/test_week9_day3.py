"""Week 9 Day 3 测试 — CAIL 100+ 扩展 (100 案件, 22 sub-category 每个 >= 4).

绕过 projects.graphrag_cn.__init__ 的 aiosqlite 依赖 (环境无此包).
"""
from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

# 绕过 __init__.py 直接加载 cail_loader
_LOADER_PATH = Path(__file__).parent.parent / "projects" / "graphrag_cn" / "data" / "cail_loader.py"
_spec = importlib.util.spec_from_file_location("_cail_loader", _LOADER_PATH)
_cail_loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cail_loader)

CAIL_CATEGORIES = _cail_loader.CAIL_CATEGORIES
CAIL_REAL_CASES = _cail_loader.CAIL_REAL_CASES
cail_to_graphrag_doc = _cail_loader.cail_to_graphrag_doc
get_cail_stats = _cail_loader.get_cail_stats
load_cail_cases = _cail_loader.load_cail_cases
save_cail_jsonl = _cail_loader.save_cail_jsonl


# ===== 100+ 规模 & 覆盖率 =====

def test_cail_100plus_cases():
    """CAIL 案件数 >= 100 (Day 3 目标)."""
    assert len(CAIL_REAL_CASES) >= 100, f"仅 {len(CAIL_REAL_CASES)} 案件，未达 100+"


def test_cail_full_subcategory_each_at_least_four():
    """22 sub-category 每个 >= 4 案件 (Day 3 增强)."""
    counts = Counter(c["subcategory"] for c in CAIL_REAL_CASES)
    under4 = {k: v for k, v in counts.items() if v < 4}
    assert not under4, f"少于 4 案件的 sub-category: {under4}"
    # 至少 1 个 >= 5 (验证扩展深度)
    assert any(v >= 5 for v in counts.values()), "无 ≥5 的 sub-category,扩展深度不足"


def test_cail_year_range_extended_to_2025():
    """年份范围扩展到 2018-2025."""
    stats = get_cail_stats()
    assert stats["year_range"][0] == 2018
    assert stats["year_range"][1] == 2025


def test_cail_year_coverage_complete():
    """年份覆盖 2018-2025 全部 8 个年份."""
    counts = Counter(c["year"] for c in CAIL_REAL_CASES)
    for yr in [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]:
        assert yr in counts, f"缺失年份 {yr}"


# ===== 数据质量 =====

def test_cail_case_id_unique():
    """case_id 唯一."""
    ids = [c["case_id"] for c in CAIL_REAL_CASES]
    assert len(ids) == len(set(ids)), f"重复 case_id"


def test_cail_judge_names_unique():
    """法官名跨案件独特."""
    all_judges = []
    for c in CAIL_REAL_CASES:
        all_judges.extend(c.get("judges", []))
    dup = {k: v for k, v in Counter(all_judges).items() if v > 1}
    assert not dup, f"重复法官名: {dup}"


def test_cail_text_length_adequate():
    """案件文本长度合理 (>= 100 字)."""
    short = [c["case_id"] for c in CAIL_REAL_CASES if len(c["text"]) < 100]
    assert not short, f"文本过短的案件: {short[:3]}"


def test_cail_required_fields_complete():
    """每个案件包含必需字段."""
    required = {"case_id", "category", "subcategory", "title", "text", "court", "year", "judges"}
    for c in CAIL_REAL_CASES:
        missing = required - set(c.keys())
        assert not missing, f"案件 {c.get('case_id')} 缺字段: {missing}"


# ===== 转换 & 加载 =====

def test_cail_to_graphrag_doc_all_100_cases():
    """100 案件全部可转换."""
    docs = load_cail_cases()
    assert len(docs) == len(CAIL_REAL_CASES)
    for d in docs:
        assert d["id"]
        assert d["text"]
        assert d["gold_entities"]


def test_cail_split_distribution_with_2024_2025():
    """Train/Test split 含 2024-2025 测试集."""
    docs = load_cail_cases()
    test_2024_2025 = [d for d in docs if d["split"] == "test" and int(d["id"][4:8]) >= 2024]
    assert len(test_2024_2025) >= 15, f"2024+ 测试集过少: {len(test_2024_2025)}"


def test_cail_save_load_roundtrip_100(tmp_path):
    """save → load roundtrip 数据无损 (100 案件)."""
    out = tmp_path / "cail-100.jsonl"
    n = save_cail_jsonl(out)
    assert n == len(CAIL_REAL_CASES) == 100
    loaded = []
    with open(out, "r", encoding="utf-8") as f:
        for line in f:
            loaded.append(json.loads(line))
    assert len(loaded) == 100
    assert {d["id"] for d in loaded} == {c["case_id"] for c in CAIL_REAL_CASES}


# ===== Sub-category 平衡 =====

def test_cail_category_balance_extended():
    """4 大类分布均衡 (各 >= 15)."""
    counts = Counter(c["category"] for c in CAIL_REAL_CASES)
    under = {k: v for k, v in counts.items() if v < 15}
    assert not under, f"类别案件过少: {under}"


def test_cail_22_subcategory_all_have_min_4():
    """22 sub-category 全部覆盖 + 最小 4."""
    counts = Counter(c["subcategory"] for c in CAIL_REAL_CASES)
    all_subs = set()
    for cats in CAIL_CATEGORIES.values():
        all_subs.update(cats)
    assert len(counts) == 22, f"sub-category 数为 {len(counts)}, 期望 22"
    for sub in all_subs:
        assert counts.get(sub, 0) >= 4, f"{sub} 仅 {counts.get(sub, 0)} 案件"


# ===== Stats 接口 =====

def test_cail_stats_with_100_cases():
    """stats 返回完整字段 + 100 案件."""
    stats = get_cail_stats()
    assert stats["n_total"] >= 100
    assert "by_category" in stats
    assert "by_subcategory" in stats
    assert "year_range" in stats


def test_cail_stats_subcategory_count_22():
    """stats 的 by_subcategory 22 个键."""
    stats = get_cail_stats()
    assert len(stats["by_subcategory"]) == 22