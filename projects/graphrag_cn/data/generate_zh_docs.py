"""Week 9 数据重建脚本：从 CAIL 案件扩展 + 模板生成 zh-docs 模拟数据集.

Week 9 用: zh-docs-200 数据集丢失 (file-history 无大文件快照)。
此脚本重建 200 文档的合成数据集 + 现成 51 CAIL 案件。
"""
from __future__ import annotations

import json
import random
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]

# 类别模板
CATEGORIES = {
    "法律": [
        "盗窃案", "诈骗案", "故意伤害案", "抢劫案", "受贿案",
        "挪用公款案", "合同纠纷案", "离婚案", "借贷纠纷案", "知识产权侵权案",
    ],
    "历史": [
        "春秋战国战役", "唐朝盛世政策", "宋朝外交", "明朝航海", "清朝改革",
        "近代革命运动", "战争与和平", "文化交融", "经济发展史", "科技发明",
    ],
    "新闻": [
        "自然灾害事件", "交通事故", "重大会议", "经济政策发布", "国际会谈",
        "体育赛事结果", "社会公益活动", "市场行情变化", "技术突破", "文化节庆",
    ],
    "学术": [
        "科研论文发表", "学术会议举办", "实验突破", "学术奖项颁发", "教材出版",
        "学术合作项目", "学者来访", "期刊创刊", "研究项目立项", "学术争议",
    ],
    "产品": [
        "新品上市", "产品升级", "促销活动", "品牌合作", "供应链发布",
        "用户大会", "技术发布会", "产品召回", "专利申请", "市场拓展",
    ],
}

TYPES_MAP = {
    "法律": ["刑事", "民事", "行政", "知识产权"],
    "历史": ["古代", "近代", "现代"],
    "新闻": ["社会", "经济", "国际", "体育"],
    "学术": ["论文", "会议", "奖项", "项目"],
    "产品": ["发布", "促销", "合作", "升级"],
}


def gen_doc(doc_id: str, category: str, event: str) -> dict:
    """生成单个 doc."""
    doc_type = random.choice(TYPES_MAP[category])
    text = f"【{doc_type}-{event}】根据{timestamp_str()} 的报道, 在{category}领域发生了一起'{event}'事件。详细情况:相关方面已介入调查,后续进展待跟踪。"
    return {
        "event": event,
        "type": doc_type,
        "text": text,
        "timestamp": timestamp_str(),
        "category": category_map(category),
        "id": doc_id,
        "query": f"提取事件",
        "answer": event,
        "gold_entities": [
            {
                "event": event,
                "type": doc_type,
                "date": timestamp_str(),
                "participants": [],
            }
        ],
        "split": "train" if random.random() < 0.7 else "test",
    }


def category_map(name: str) -> str:
    """类别名映射."""
    return {"法律": "legal", "历史": "history", "新闻": "news", "学术": "academic", "产品": "product"}.get(name, "other")


def timestamp_str() -> str:
    """生成随机时间戳."""
    y = random.randint(2020, 2024)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{y:04d}-{m:02d}-{d:02d}"


def generate_zh_docs_200() -> list[dict]:
    """生成 200 个 doc."""
    random.seed(42)  # 确定性
    docs = []
    cid = 0
    # 200 docs 分布: 法律 85, 历史 50, 新闻 35, 学术 20, 产品 10
    distribution = {
        "法律": 85,
        "历史": 50,
        "新闻": 35,
        "学术": 20,
        "产品": 10,
    }
    for cat, n in distribution.items():
        for i in range(n):
            event = random.choice(CATEGORIES[cat])
            cid += 1
            docs.append(gen_doc(f"{cat[:2]}-{cid:03d}", cat, event))
    return docs


def main():
    out = project_root / "projects/graphrag_cn/data/zh-docs-200.jsonl"
    docs = generate_zh_docs_200()
    with open(out, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    # zh-docs-50 (子集)
    out50 = project_root / "projects/graphrag_cn/data/zh-docs-50.jsonl"
    docs50 = docs[:50]
    with open(out50, "w", encoding="utf-8") as f:
        for d in docs50:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"✅ {len(docs)} docs → {out}")
    print(f"✅ {len(docs50)} docs → {out50}")

    # CAIL JSONL
    cail_out = project_root / "projects/graphrag_cn/data/cail-cases.jsonl"
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_cl",
        project_root / "projects/graphrag_cn/data/cail_loader.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cail_docs = mod.load_cail_cases()
    with open(cail_out, "w", encoding="utf-8") as f:
        for d in cail_docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"✅ {len(cail_docs)} CAIL cases → {cail_out}")


if __name__ == "__main__":
    main()
