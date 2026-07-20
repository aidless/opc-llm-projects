"""Week 9 Day 1 测试 — CAIL 大规模扩展 (51 案件, 全 22 sub-category 覆盖).

绕过 projects.graphrag_cn.__init__ 的 aiosqlite 依赖 (环境无此包),
用 importlib 直接加载 cail_loader 模块。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

# ===== 绕过 __init__.py 直接加载 cail_loader =====
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


# ===== 规模 & 覆盖率 =====

def test_cail_50plus_cases():
    """CAIL 案件数 >= 50 (Week 9 目标)."""
    assert len(CAIL_REAL_CASES) >= 50, f"仅 {len(CAIL_REAL_CASES)} 案件，未达 50+"


def test_cail_full_subcategory_coverage():
    """全 22 sub-category 覆盖."""
    all_subs = set()
    for cats in CAIL_CATEGORIES.values():
        all_subs.update(cats)
    assert len(all_subs) == 22, f"定义 sub-category 应为 22，实际 {len(all_subs)}"
    covered = set(c["subcategory"] for c in CAIL_REAL_CASES)
    missing = all_subs - covered
    assert not missing, f"缺失 sub-category: {missing}"


def test_cail_subcategory_each_at_least_two():
    """每个 sub-category 至少 2 案件."""
    counts = Counter(c["subcategory"] for c in CAIL_REAL_CASES)
    under = {k: v for k, v in counts.items() if v < 2}
    assert not under, f"少于 2 案件的 sub-category: {under}"


def test_cail_all_four_categories_present():
    """4 大类（民事/刑事/行政/知识产权）都有."""
    cats = set(c["category"] for c in CAIL_REAL_CASES)
    expected = {"民事", "刑事", "行政", "知识产权"}
    assert expected.issubset(cats), f"缺失类别: {expected - cats}"


# ===== 数据质量 =====

def test_cail_case_id_unique():
    """case_id 唯一."""
    ids = [c["case_id"] for c in CAIL_REAL_CASES]
    assert len(ids) == len(set(ids)), f"重复 case_id: {[k for k, v in Counter(ids).items() if v > 1]}"


def test_cail_judge_names_unique():
    """法官名跨案件独特 (无 cross-doc 共享)."""
    all_judges = []
    for c in CAIL_REAL_CASES:
        all_judges.extend(c.get("judges", []))
    dup = {k: v for k, v in Counter(all_judges).items() if v > 1}
    assert not dup, f"重复法官名: {dup}"


def test_cail_year_range_widened():
    """年份范围 2018-2025 (Week 9 Day 3 扩展到 2025)."""
    stats = get_cail_stats()
    assert stats["year_range"][0] == 2018
    assert stats["year_range"][1] == 2025


def test_cail_text_length_adequate():
    """案件文本长度合理 (>= 100 字)."""
    short = [c["case_id"] for c in CAIL_REAL_CASES if len(c["text"]) < 100]
    assert not short, f"文本过短的案件: {short}"


def test_cail_required_fields():
    """每个案件包含必需字段."""
    required = {"case_id", "category", "subcategory", "title", "text", "court", "year", "judges"}
    for c in CAIL_REAL_CASES:
        missing = required - set(c.keys())
        assert not missing, f"案件 {c.get('case_id')} 缺字段: {missing}"


# ===== 转换 & 加载 =====

def test_cail_to_graphrag_doc_all_cases():
    """所有 51 案件可转换."""
    docs = load_cail_cases()
    assert len(docs) == len(CAIL_REAL_CASES)
    for d in docs:
        assert d["id"]
        assert d["text"]
        assert d["gold_entities"]
        assert d["split"] in ("train", "test")


def test_cail_split_distribution():
    """Train/Test split 分布合理 (2018-2020 train, 2021+ test)."""
    docs = load_cail_cases()
    train_n = sum(1 for d in docs if d["split"] == "train")
    test_n = sum(1 for d in docs if d["split"] == "test")
    assert train_n > 0 and test_n > 0, f"split 分布异常: train={train_n}, test={test_n}"
    assert test_n >= 15, f"测试集过少: {test_n}"


def test_cail_save_load_roundtrip(tmp_path):
    """save → load roundtrip 数据无损."""
    out = tmp_path / "cail-50plus.jsonl"
    n = save_cail_jsonl(out)
    assert n == len(CAIL_REAL_CASES)
    assert out.exists()
    loaded = []
    with open(out, "r", encoding="utf-8") as f:
        for line in f:
            loaded.append(json.loads(line))
    assert len(loaded) == len(CAIL_REAL_CASES)
    assert {d["id"] for d in loaded} == {c["case_id"] for c in CAIL_REAL_CASES}


# ===== Sub-category 平衡 =====

def test_cail_category_balance():
    """4 大类分布相对均衡 (各 >=5)."""
    counts = Counter(c["category"] for c in CAIL_REAL_CASES)
    under = {k: v for k, v in counts.items() if v < 5}
    assert not under, f"类别案件过少: {under}"


def test_cail_year_distribution_reasonable():
    """年份分布合理 (2018-2023 每年都有)."""
    counts = Counter(c["year"] for c in CAIL_REAL_CASES)
    assert len(counts) >= 5, f"年份覆盖太少: {sorted(counts.keys())}"
    for yr in [2018, 2019, 2020, 2021, 2022, 2023]:
        assert yr in counts, f"缺失年份 {yr}"


# ===== Stats 接口 =====

def test_cail_stats_keys():
    """get_cail_stats 返回完整字段."""
    stats = get_cail_stats()
    assert "n_total" in stats
    assert "by_category" in stats
    assert "by_subcategory" in stats
    assert "year_range" in stats
    assert stats["n_total"] >= 50


def test_cail_stats_subcategory_count():
    """stats 的 by_subcategory 应包含 22 个键."""
    stats = get_cail_stats()
    assert len(stats["by_subcategory"]) == 22
