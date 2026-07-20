"""CAIL E2E pipeline (with fallback) — Week 8 Day 4.

CAIL 10 真实案件 → 实体 → 图谱 → QA.
支持 3 种 entity source:
1. Ollama 抽取 (如果可用)
2. Gold entities (CAIL 自带)
3. Mock entities (最后 fallback)
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

# Ensure project root on sys.path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from projects.graphrag_cn.data.cail_loader import load_cail_cases
from projects.graphrag_cn.graph import EntityGraph
from projects.graphrag_cn.storage import EntityIndex, EntityRecord


def build_records_from_docs(docs: list[dict]) -> list[EntityRecord]:
    """从 docs (含 gold_entities) 构建 EntityRecord 列表."""
    records = []
    for d in docs:
        for ge in d.get("gold_entities", []):
            rec = EntityRecord(
                entity_id=str(uuid.uuid4()),
                doc_id=d["id"],
                event=ge.get("event", "案件"),
                type=ge.get("type", "法律"),
                date=ge.get("date", "2020-01-01"),
                participants=ge.get("participants", []),
                source="cail_gold",
                confidence=1.0,
            )
            records.append(rec)
    return records


async def run_ollama_extract(docs):
    """尝试用 Ollama 抽取实体 (失败返回 None)."""
    try:
        from opc_platform.gateway.ollama import OllamaClient
        from projects.graphrag_cn.extraction.extractor import EntityExtractor

        llm = OllamaClient(model="qwen2.5:3b-instruct-q4_K_M", timeout=60.0)
        extractor = EntityExtractor(llm, mode="3-shot")
        texts = [d["text"] for d in docs]
        results = await extractor.extract_batch(
            texts=texts,
            sample_ids=[d["id"] for d in docs],
            batch_task_id="cail_day4",
        )
        n_extracted = sum(len(r) for r in results)
        if n_extracted == 0:
            print(f"  [INFO] Ollama 抽取返回 0 实体")
            await llm.close()
            return None

        # Convert to records
        records = []
        for d, entities in zip(docs, results):
            for ent in entities:
                rec = EntityRecord(
                    entity_id=str(uuid.uuid4()),
                    doc_id=d["id"],
                    event=ent.get("event", ""),
                    type=ent.get("type", "法律"),
                    date=ent.get("date", "2020-01-01"),
                    participants=ent.get("participants", []),
                    source="cail_ollama",
                    confidence=1.0,
                )
                records.append(rec)
        await llm.close()
        return records
    except Exception as e:
        print(f"  [WARN] Ollama 不可用: {e}")
        return None


async def main():
    # 1. Load CAIL cases
    docs = load_cail_cases()
    print(f"[1/5] 加载 {len(docs)} CAIL 案件")

    # 2. Extract entities (Ollama first, fallback to gold)
    print(f"\n[2/5] 实体抽取")
    records = await run_ollama_extract(docs)
    if records is None or len(records) == 0:
        print(f"  [FALLBACK] 使用 gold entities")
        records = build_records_from_docs(docs)
    print(f"  实体: {len(records)}")

    # 3. Build EntityIndex
    print(f"\n[3/5] 持久化 (EntityIndex)")
    db_path = project_root / "experiments/entity_index_cail_day4.db"
    if db_path.exists():
        db_path.unlink()
    eidx = EntityIndex(db_path)
    await eidx.init()
    n_upserted = await eidx.upsert_batch(records)
    print(f"  写入 {n_upserted} entities")
    await eidx.close()

    # 4. Linking (if embedder available)
    print(f"\n[4/5] 实体链接")
    try:
        from projects.graphrag_cn.link import EntityEmbedder, EntityLinker
        embedder = EntityEmbedder(model="nomic-embed-text")
        linker = EntityLinker(embedder, similarity_threshold=0.85)
        report = await linker.link(records, progress=False)
        print(f"  簇数: {report.n_clusters} (raw {report.n_input})")
        if report.n_input > 0:
            print(f"  KCR: {1 - report.n_clusters / report.n_input:.4f}")
    except Exception as e:
        print(f"  [WARN] 链接不可用: {e}")
        report = None

    # 5. Build graph
    print(f"\n[5/5] 图谱构建")
    eg = EntityGraph(records=records)
    stats = eg.get_stats()
    print(f"  节点: {stats['n_nodes']} (events={stats['n_events']}, participants={stats['n_participants']})")
    print(f"  边: {stats['n_edges']} ({stats['edges_by_type']})")

    out = project_root / "experiments/graph-cail-day4.json"
    eg.save_json(out)
    print(f"  保存: {out}")

    # 6. Retrieval test
    print(f"\n[6/6] 检索验证")
    from projects.graphrag_cn.rag import GraphRetriever
    gr = GraphRetriever(eg, docs)
    for q in ["盗窃", "诈骗", "合同纠纷", "受贿"]:
        hits = gr.retrieve(q, top_k=2)
        result = [(h.doc_id, round(h.score, 3)) for h in hits]
        print(f"  '{q}': {result}")

    print(f"\n✅ CAIL E2E Pipeline 完成")
    print(f"  实体: {len(records)}")
    print(f"  节点: {stats['n_nodes']}")
    print(f"  边: {stats['n_edges']}")


if __name__ == "__main__":
    asyncio.run(main())
