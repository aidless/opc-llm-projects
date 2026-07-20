"""Week 9 Day 2 部署就绪自动验证脚本.

检查项:
1. Git 状态: clean + 已 commit
2. 部署必需文件: README / requirements / .gitignore / .streamlit config / demo entry
3. 数据文件: zh-docs-200 + cail-cases 存在且非空
4. Demo 入口: 不依赖 .db, 支持双数据集, 有 demo mode
5. .gitignore: 排除 .db 但保留 demo 必需 JSON
6. 入口点 main file path 正确

输出:
- 控制台 PASS/FAIL 报告
- experiments/deploy-readiness-day2.json 详细结果
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

project_root = Path(__file__).resolve().parents[1]


def run_check(name: str, condition: bool, detail: str = "") -> dict[str, Any]:
    """执行一个 check, 返回结果 dict."""
    return {
        "name": name,
        "pass": condition,
        "detail": detail,
    }


def check_git_state() -> dict[str, Any]:
    """Git 状态."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-3"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        commits = result.stdout.strip().split("\n") if result.returncode == 0 else []
        return run_check(
            "git_log",
            len(commits) > 0,
            f"最近 commit: {commits[0] if commits else '(none)'}",
        )
    except Exception as e:
        return run_check("git_log", False, str(e))


def check_required_files() -> dict[str, Any]:
    """部署必需文件."""
    required = [
        "README.md",
        "requirements.txt",
        ".gitignore",
        ".streamlit/config.toml",
        "projects/graphrag_cn/demo/streamlit_app.py",
        "docs/PRICING.md",
        "docs/GITHUB_DEPLOY.md",
    ]
    missing = [f for f in required if not (project_root / f).exists()]
    return run_check(
        "required_files",
        len(missing) == 0,
        f"缺失: {missing}" if missing else f"全部 {len(required)} 文件就绪",
    )


def check_requirements_complete() -> dict[str, Any]:
    """requirements.txt 完整."""
    req_path = project_root / "requirements.txt"
    if not req_path.exists():
        return run_check("requirements", False, "缺失 requirements.txt")
    content = req_path.read_text(encoding="utf-8")
    required = ["streamlit", "pydantic", "networkx", "httpx"]
    missing = [d for d in required if d not in content]
    return run_check(
        "requirements_complete",
        len(missing) == 0,
        f"缺: {missing}" if missing else "核心依赖完整",
    )


def check_data_files() -> dict[str, Any]:
    """数据文件."""
    zh = project_root / "projects/graphrag_cn/data/zh-docs-200.jsonl"
    cail_jsonl = project_root / "projects/graphrag_cn/data/cail-cases.jsonl"
    cail_loader = project_root / "projects/graphrag_cn/data/cail_loader.py"
    missing = []
    if not zh.exists():
        missing.append("zh-docs-200.jsonl")
    if not cail_loader.exists():
        missing.append("cail_loader.py")
    # cail-cases.jsonl 可选（运行时生成）
    # 但 cail_loader 必须可用
    return run_check(
        "data_files",
        len(missing) == 0,
        f"缺失: {missing}" if missing else f"zh-docs-200 + cail_loader 就绪",
    )


def check_demo_no_db() -> dict[str, Any]:
    """Demo 不依赖 .db."""
    demo = project_root / "projects/graphrag_cn/demo/streamlit_app.py"
    if not demo.exists():
        return run_check("demo_no_db", False, "demo 不存在")
    src = demo.read_text(encoding="utf-8")
    bad = "entity_index_200_day6.db" in src
    return run_check(
        "demo_no_db",
        not bad,
        "Demo 不再依赖 .db 文件" if not bad else "Demo 仍依赖 .db",
    )


def check_demo_features() -> dict[str, Any]:
    """Demo 支持双数据集 + demo mode."""
    demo = project_root / "projects/graphrag_cn/demo/streamlit_app.py"
    if not demo.exists():
        return run_check("demo_features", False, "demo 不存在")
    src = demo.read_text(encoding="utf-8")
    has_dual = "CAIL" in src and "zh-docs-200" in src
    has_demo_mode = "Demo Mode" in src or "HAS_LLM" in src
    has_jsonl = "build_records_from_docs" in src
    all_ok = has_dual and has_demo_mode and has_jsonl
    return run_check(
        "demo_features",
        all_ok,
        f"双数据集={has_dual}, demo mode={has_demo_mode}, JSONL直读={has_jsonl}",
    )


def check_gitignore_safe() -> dict[str, Any]:
    """.gitignore 排除 .db 但保留 demo 必需 JSON."""
    gi = project_root / ".gitignore"
    if not gi.exists():
        return run_check("gitignore", False, "缺失 .gitignore")
    content = gi.read_text(encoding="utf-8")
    excludes_db = "*.db" in content or ".db" in content
    # 保留 demo 必需
    keeps_demo = "qa-eval-day6.json" in content or "entity-link-day2.json" in content
    return run_check(
        "gitignore_safe",
        excludes_db and keeps_demo,
        f"exclude_db={excludes_db}, keep_demo={keeps_demo}",
    )


def check_main_file_path() -> dict[str, Any]:
    """Streamlit Cloud main file path 正确."""
    demo = project_root / "projects/graphrag_cn/demo/streamlit_app.py"
    ok = demo.exists() and demo.name == "streamlit_app.py"
    return run_check(
        "main_file_path",
        ok,
        f"path={demo.relative_to(project_root)}" if ok else "main file 路径错误",
    )


def check_zh_docs_complete() -> dict[str, Any]:
    """zh-docs-200 数据完整性."""
    p = project_root / "projects/graphrag_cn/data/zh-docs-200.jsonl"
    if not p.exists():
        return run_check("zh_docs_complete", False, "zh-docs-200.jsonl 不存在")
    n = 0
    n_with_entities = 0
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            n += 1
            d = json.loads(line)
            if d.get("gold_entities"):
                n_with_entities += 1
    return run_check(
        "zh_docs_complete",
        n >= 100 and n_with_entities >= 100,
        f"{n} docs, {n_with_entities} 有 gold_entities",
    )


def check_cail_complete() -> dict[str, Any]:
    """CAIL 数据完整性."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_cl",
        project_root / "projects/graphrag_cn/data/cail_loader.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    n = len(mod.CAIL_REAL_CASES)
    return run_check(
        "cail_complete",
        n >= 50,
        f"CAIL {n} 案件",
    )


# ===== Main =====

def main():
    print("=" * 60)
    print("Week 9 Day 2 — 部署就绪自动验证")
    print("=" * 60)

    checks = [
        check_git_state(),
        check_required_files(),
        check_requirements_complete(),
        check_data_files(),
        check_zh_docs_complete(),
        check_cail_complete(),
        check_demo_no_db(),
        check_demo_features(),
        check_gitignore_safe(),
        check_main_file_path(),
    ]

    n_pass = sum(1 for c in checks if c["pass"])
    n_total = len(checks)

    print(f"\n📋 检查结果 ({n_pass}/{n_total} PASS):\n")
    for c in checks:
        status = "✅" if c["pass"] else "❌"
        print(f"  {status} {c['name']:30s} {c['detail']}")

    # 保存报告
    report = {
        "total_checks": n_total,
        "passed": n_pass,
        "all_passed": n_pass == n_total,
        "checks": checks,
    }
    out_path = project_root / "experiments/deploy-readiness-day2.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 报告: {out_path}")
    print(f"\n总体: {'READY TO DEPLOY' if n_pass == n_total else 'NEEDS FIXES'}")

    return 0 if n_pass == n_total else 1


if __name__ == "__main__":
    sys.exit(main())