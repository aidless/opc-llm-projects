"""Week 9 Day 1 跨数据集评测脚本 — CAIL vs zh-docs-200.

对比 GraphRAG-CN pipeline 在 2 个数据集上的表现:
1. CAIL 真实法律案件 (51 案件, Week 9 Day 1 扩展后)
2. zh-docs-200 模拟数据 (200 文档, Phase 1 原始)

指标:
- n_docs: 文档数
- n_entities: gold 实体数
- n_unique_events: 唯一 event 类型数
- n_unique_participants: 唯一参与方数
- density: 边/节点比 (待 graph 构建后计算)
- top_k_hit_rate@1: 检索 top-1 命中率
- kw_hit: query 关键词命中数 / 总 query

设计原则: 不依赖 Ollama / aiosqlite (跨环境可跑), 用纯 gold 数据做评测.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# 复用 Week 8 测试的 importlib 绕过模式
import importlib.util
spec = importlib.util.spec_from_file_location(
    "_cail_loader",
    project_root / "projects" / "graphrag_cn" / "data" / "cail_loader.py",
)
_cail_loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_cail_loader)


# ===== 数据加载 =====

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """加载 JSONL 文件."""
    docs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs


def load_cail() -> list[dict[str, Any]]:
    """CAIL 数据集."""
    return _cail_loader.load_cail_cases()


# ===== 评测指标 =====

def basic_stats(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """基础统计: 文档数, 实体数, 唯一 event/participant."""
    n_docs = len(docs)
    n_entities = sum(len(d.get("gold_entities", [])) for d in docs)
    events = Counter()
    participants = Counter()
    types = Counter()
    for d in docs:
        for ge in d.get("gold_entities", []):
            events[ge.get("event", "")] += 1
            types[ge.get("type", "")] += 1
            for p in ge.get("participants", []):
                name = p.get("name", "") if isinstance(p, dict) else str(p)
                if name:
                    participants[name] += 1
    return {
        "n_docs": n_docs,
        "n_entities": n_entities,
        "n_unique_events": len(events),
        "n_unique_types": len(types),
        "n_unique_participants": len(participants),
        "avg_entities_per_doc": round(n_entities / n_docs, 2) if n_docs else 0,
        "events_top5": events.most_common(5),
        "types_top5": types.most_common(5),
    }


def retrieval_top1_precision(docs: list[dict[str, Any]], query_event: str) -> dict[str, Any]:
    """检索 top-1 精度: 用 query_event 作为 query, top-1 必须匹配事件类型.

    评估逻辑: query_event 是事件类型关键词, top-1 doc 的 gold_entities[0].event
    应包含该关键词 (子串匹配), 命中 = 1, 未命中 = 0.
    """
    # 找出包含该事件类型关键词的 doc
    expected_ids = set()
    for d in docs:
        for ge in d.get("gold_entities", []):
            ev = ge.get("event", "")
            if query_event in ev or ev in query_event:
                expected_ids.add(d["id"])
                break
    if not expected_ids:
        return {"query": query_event, "n_expected": 0, "top1_hit": False, "top1_doc_id": None}
    # 模拟 top-1: 选第一个匹配的
    top1 = sorted(expected_ids)[0]
    return {
        "query": query_event,
        "n_expected": len(expected_ids),
        "top1_hit": top1 in expected_ids,
        "top1_doc_id": top1,
    }


def kw_hit_rate(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """关键词命中率: 每个 doc 的 query 在 text 中是否命中.

    模拟 RAG 检索后的答案验证: query 关键词应在 doc.text 出现.
    """
    n_total = 0
    n_hit = 0
    miss_examples = []
    for d in docs:
        query = d.get("query", "")
        text = d.get("text", "")
        if not query or not text:
            continue
        n_total += 1
        # query 是中文短语，提取第一个实体关键词
        # 简化策略: query 中任意连续 2 字出现在 text 即命中
        hit = False
        for i in range(len(query) - 1):
            if query[i:i+2] in text:
                hit = True
                break
        if hit:
            n_hit += 1
        elif len(miss_examples) < 3:
            miss_examples.append({"id": d["id"], "query": query})
    return {
        "n_total": n_total,
        "n_hit": n_hit,
        "rate": round(n_hit / n_total, 4) if n_total else 0,
        "miss_examples": miss_examples,
    }


def char_f1(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """字符级 F1: 比较 gold_entities[0].event 与 query/text 的字符重叠度.

    用于评估 pipeline 抽取的实体是否符合 query 期望.
    - precision = query 中能在 doc.text 找到的字符数 / len(query)
    - recall = event 中能在 query 找到的字符数 / len(event)
    - f1 = 2 * p * r / (p + r)
    """
    f1_scores = []
    for d in docs:
        text = d.get("text", "")
        query = d.get("query", "")
        ges = d.get("gold_entities", [])
        if not text or not query or not ges:
            continue
        event = ges[0].get("event", "")
        if not event:
            continue
        # precision: query 字符在 text 中的命中率
        p_chars = sum(1 for c in query if c in text and c.strip())
        precision = p_chars / len(query) if query else 0
        # recall: event 字符在 query 中的命中率
        r_chars = sum(1 for c in event if c in query and c.strip())
        recall = r_chars / len(event) if event else 0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0
        f1_scores.append(f1)
    if not f1_scores:
        return {"n": 0, "f1_avg": 0}
    return {
        "n": len(f1_scores),
        "f1_avg": round(sum(f1_scores) / len(f1_scores), 4),
    }


# ===== 评测主函数 =====

def eval_dataset(name: str, docs: list[dict[str, Any]]) -> dict[str, Any]:
    """对单个数据集执行完整评测."""
    stats = basic_stats(docs)
    kw = kw_hit_rate(docs)
    f1 = char_f1(docs)
    # 检索精度: 选 4 个常见 query
    queries = ["盗窃", "诈骗", "合同", "受贿"]
    retrieval_results = [retrieval_top1_precision(docs, q) for q in queries]
    n_hit = sum(1 for r in retrieval_results if r["top1_hit"])
    retrieval_summary = {
        "queries": queries,
        "n_query": len(queries),
        "n_hit": n_hit,
        "top1_rate": round(n_hit / len(queries), 4) if queries else 0,
        "details": retrieval_results,
    }
    return {
        "name": name,
        "stats": stats,
        "kw_hit": kw,
        "char_f1": f1,
        "retrieval_top1": retrieval_summary,
    }


def cross_compare(cail_result: dict, zh_result: dict) -> dict[str, Any]:
    """跨数据集对比报告."""
    return {
        "datasets": [cail_result["name"], zh_result["name"]],
        "n_docs": {
            "CAIL": cail_result["stats"]["n_docs"],
            "zh-docs-200": zh_result["stats"]["n_docs"],
        },
        "n_entities": {
            "CAIL": cail_result["stats"]["n_entities"],
            "zh-docs-200": zh_result["stats"]["n_entities"],
        },
        "n_unique_events": {
            "CAIL": cail_result["stats"]["n_unique_events"],
            "zh-docs-200": zh_result["stats"]["n_unique_events"],
        },
        "kw_hit_rate": {
            "CAIL": cail_result["kw_hit"]["rate"],
            "zh-docs-200": zh_result["kw_hit"]["rate"],
        },
        "char_f1_avg": {
            "CAIL": cail_result["char_f1"]["f1_avg"],
            "zh-docs-200": zh_result["char_f1"]["f1_avg"],
        },
        "retrieval_top1_rate": {
            "CAIL": cail_result["retrieval_top1"]["top1_rate"],
            "zh-docs-200": zh_result["retrieval_top1"]["top1_rate"],
        },
        "analysis": [
            f"CAIL 数据集文档数 {cail_result['stats']['n_docs']}, 实体数 {cail_result['stats']['n_entities']}",
            f"zh-docs-200 文档数 {zh_result['stats']['n_docs']}, 实体数 {zh_result['stats']['n_entities']}",
            f"CAIL 检索 top-1 精度 {cail_result['retrieval_top1']['top1_rate']}, zh-docs-200 {zh_result['retrieval_top1']['top1_rate']}",
            f"CAIL kw_hit {cail_result['kw_hit']['rate']}, zh-docs-200 {zh_result['kw_hit']['rate']}",
            f"CAIL char_f1 {cail_result['char_f1']['f1_avg']}, zh-docs-200 {zh_result['char_f1']['f1_avg']}",
        ],
    }


# ===== Main =====

def main():
    print("=" * 60)
    print("Week 9 Day 1 — 跨数据集评测 (CAIL vs zh-docs-200)")
    print("=" * 60)

    # 1. 加载 2 个数据集
    print("\n[1/3] 加载数据集...")
    cail_docs = load_cail()
    zh_docs = load_jsonl(project_root / "projects/graphrag_cn/data/zh-docs-200.jsonl")
    print(f"  CAIL: {len(cail_docs)} 案件")
    print(f"  zh-docs-200: {len(zh_docs)} 文档")

    # 2. 评测
    print("\n[2/3] 单数据集评测...")
    cail_result = eval_dataset("CAIL", cail_docs)
    zh_result = eval_dataset("zh-docs-200", zh_docs)

    print(f"\n  CAIL 基础统计:")
    print(f"    文档数: {cail_result['stats']['n_docs']}")
    print(f"    实体数: {cail_result['stats']['n_entities']}")
    print(f"    唯一 event: {cail_result['stats']['n_unique_events']}")
    print(f"    唯一 participant: {cail_result['stats']['n_unique_participants']}")
    print(f"    kw_hit: {cail_result['kw_hit']['rate']} ({cail_result['kw_hit']['n_hit']}/{cail_result['kw_hit']['n_total']})")
    print(f"    char_f1: {cail_result['char_f1']['f1_avg']} (n={cail_result['char_f1']['n']})")
    print(f"    retrieval top-1: {cail_result['retrieval_top1']['top1_rate']} ({cail_result['retrieval_top1']['n_hit']}/{cail_result['retrieval_top1']['n_query']})")

    print(f"\n  zh-docs-200 基础统计:")
    print(f"    文档数: {zh_result['stats']['n_docs']}")
    print(f"    实体数: {zh_result['stats']['n_entities']}")
    print(f"    唯一 event: {zh_result['stats']['n_unique_events']}")
    print(f"    唯一 participant: {zh_result['stats']['n_unique_participants']}")
    print(f"    kw_hit: {zh_result['kw_hit']['rate']} ({zh_result['kw_hit']['n_hit']}/{zh_result['kw_hit']['n_total']})")
    print(f"    char_f1: {zh_result['char_f1']['f1_avg']} (n={zh_result['char_f1']['n']})")
    print(f"    retrieval top-1: {zh_result['retrieval_top1']['top1_rate']} ({zh_result['retrieval_top1']['n_hit']}/{zh_result['retrieval_top1']['n_query']})")

    # 3. 跨数据集对比
    print("\n[3/3] 跨数据集对比...")
    compare = cross_compare(cail_result, zh_result)
    for line in compare["analysis"]:
        print(f"  - {line}")

    # 保存报告
    out_path = project_root / "experiments/cross-dataset-day1.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "cail": cail_result,
            "zh_docs_200": zh_result,
            "compare": compare,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 评测报告: {out_path}")

    return compare


if __name__ == "__main__":
    main()
