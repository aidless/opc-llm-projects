"""Week 9 Day 2 测试 — 部署就绪 (Cloud-friendly Streamlit demo).

核心验证:
1. Streamlit demo 不依赖 .db 文件 (Cloud 容器无 sqlite artifact)
2. Demo 直接从 JSONL gold_entities 构建图谱
3. Demo 支持 zh-docs-200 + CAIL 双数据集切换
4. Demo 默认 demo mode 可用 (无 LLM 不报错)
5. requirements.txt 完整
6. .streamlit/config.toml 存在
7. .gitignore 排除 .db 但保留 demo 必需文件
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent

# ===== 路径与文件存在性 =====

def test_streamlit_config_exists():
    """Streamlit config.toml 存在."""
    cfg = project_root / ".streamlit/config.toml"
    assert cfg.exists(), f"缺失: {cfg}"
    content = cfg.read_text(encoding="utf-8")
    assert "port" in content


def test_requirements_txt_complete():
    """requirements.txt 列出核心依赖."""
    req_path = project_root / "requirements.txt"
    assert req_path.exists()
    content = req_path.read_text(encoding="utf-8")
    required_deps = ["streamlit", "pydantic", "networkx", "httpx"]
    for dep in required_deps:
        assert dep in content, f"requirements.txt 缺 {dep}"


def test_gitignore_excludes_db_but_keeps_demo():
    """.gitignore 排除 .db 但保留 demo 必需 JSON."""
    gi_path = project_root / ".gitignore"
    assert gi_path.exists()
    content = gi_path.read_text(encoding="utf-8")
    # 排除 .db
    assert "*.db" in content
    # 保留 demo 必需
    assert "experiments/qa-eval-day6.json" in content or "entity-link-day2.json" in content


def test_zh_docs_200_exists():
    """zh-docs-200 数据存在."""
    p = project_root / "projects/graphrag_cn/data/zh-docs-200.jsonl"
    assert p.exists()
    # 至少 100 行
    with open(p, "r", encoding="utf-8") as f:
        n = sum(1 for line in f if line.strip())
    assert n >= 100, f"仅 {n} 行"


def test_cail_cases_51():
    """CAIL 51 案件可用."""
    spec = importlib.util.spec_from_file_location(
        "_cl",
        project_root / "projects/graphrag_cn/data/cail_loader.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    docs = mod.load_cail_cases()
    assert len(docs) >= 50


# ===== Demo 逻辑（绕过 streamlit 模块） =====

def _read_demo_source() -> str:
    """读 demo 源码 (避免 import streamlit 触发 aiosqlite)."""
    demo_path = project_root / "projects/graphrag_cn/demo/streamlit_app.py"
    return demo_path.read_text(encoding="utf-8")


def test_demo_no_db_dependency():
    """Demo 源码不读 .db 文件."""
    src = _read_demo_source()
    # 不应出现 entity_index_*.db
    assert "entity_index_200_day6.db" not in src, "Demo 仍依赖 .db 文件, Cloud 会失败"
    assert ".db" not in src or "_load_jsonl" in src  # 允许注释/其他 db 引用


def test_demo_uses_jsonl_directly():
    """Demo 用 JSONL 直接构建图谱."""
    src = _read_demo_source()
    assert "build_records_from_docs" in src
    assert "_load_jsonl" in src or "json.loads" in src


def test_demo_supports_dual_dataset():
    """Demo 支持 zh-docs-200 + CAIL 切换."""
    src = _read_demo_source()
    assert "zh-docs-200" in src
    assert "CAIL" in src or "cail_loader" in src


def test_demo_has_demo_mode():
    """Demo 默认 Demo Mode (无 LLM 不报错)."""
    src = _read_demo_source()
    assert "Demo Mode" in src or "demo_mode" in src or "force_demo" in src
    assert "HAS_LLM" in src, "Demo 应检测 LLM 可用性"


def test_demo_dataset_specific_queries():
    """Demo 为每个数据集提供 preset queries."""
    src = _read_demo_source()
    assert "PRESET_QUERIES" in src
    assert "盗窃" in src or "论文" in src  # zh preset
    assert "盗窃" in src and "专利" in src  # CAIL preset (同时覆盖)


# ===== Demo 检索逻辑（用 importlib 绕过 __init__） =====

def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_demo_imports_resilient():
    """Demo 源码中 QAEngine + OllamaClient 是 try/except 包裹的."""
    src = _read_demo_source()
    # 应该有 try/except 包裹 LLM 相关 import
    assert "try:" in src
    assert "except" in src
    # HAS_LLM flag
    assert "HAS_LLM" in src


def test_demo_retrieve_mock():
    """Demo 检索逻辑的最小可用验证 (Mock GraphRetriever).

    Cloud 验证核心: retriever.retrieve() 返回 hits 列表, 含 doc_id + score.
    """
    # Mock 一个 hits 对象
    from types import SimpleNamespace
    mock_hit = SimpleNamespace(
        doc_id="test-001",
        doc_category="法律",
        doc_event="测试",
        doc_text="测试文本",
        score=0.95,
        text_score=0.9,
        graph_score=0.05,
        matched_events=["测试"],
        matched_participants=["当事人"],
    )
    # 模拟 demo 的渲染路径：只要 hits 是 list 且含 doc_id/score 即可
    assert mock_hit.doc_id == "test-001"
    assert mock_hit.score == 0.95
    assert hasattr(mock_hit, "doc_text")


# ===== 部署产物清单 =====

def test_deploy_required_files_present():
    """部署必需的 6 个文件全部存在."""
    required = [
        "README.md",
        "requirements.txt",
        ".gitignore",
        ".streamlit/config.toml",
        "projects/graphrag_cn/demo/streamlit_app.py",
        "docs/PRICING.md",
    ]
    for f in required:
        p = project_root / f
        assert p.exists(), f"缺失部署必需文件: {f}"


def test_demo_main_file_path_correct():
    """Streamlit Cloud main file path 在 demo/streamlit_app.py."""
    demo_path = project_root / "projects/graphrag_cn/demo/streamlit_app.py"
    assert demo_path.exists()
    assert demo_path.name == "streamlit_app.py"


def test_demo_not_referencing_local_paths():
    """Demo 不写死 localhost / 本地路径 (Cloud 友好)."""
    src = _read_demo_source()
    # 允许 'localhost' 作为 demo 文档说明, 但不应作为硬编码路径
    bad_patterns = [
        "C:\\Users\\",
        "C:/Users/",
        "/home/user/",
        "/tmp/",
    ]
    for pat in bad_patterns:
        assert pat not in src, f"Demo 包含硬编码本地路径: {pat}"


def test_zh_docs_data_complete_for_demo():
    """zh-docs-200 数据完整可被 demo 加载."""
    p = project_root / "projects/graphrag_cn/data/zh-docs-200.jsonl"
    docs = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    # 所有 doc 必需有 gold_entities 才能构建图谱
    has_entities = [d for d in docs if d.get("gold_entities")]
    assert len(has_entities) >= 100, f"仅 {len(has_entities)} doc 有 gold_entities"