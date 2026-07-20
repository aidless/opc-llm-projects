# 公开部署操作指南 (用户视角)

> Phase 2 / Week 9 / Day 2 · 2026-07-20
> **部署状态**: ✅ READY TO DEPLOY (10/10 自动验证通过)

---

## 🎯 一句话总结

项目代码已就绪，可以**立即推送 GitHub + 部署 Streamlit Cloud**，全程 10-15 分钟。

---

## ✅ 自动验证已通过 (10/10)

运行 `python experiments/deploy_readiness_check.py` 已确认：

| ✅ | 项目 | 状态 |
|---|---|---|
| ✅ | Git log (最新 commit `7e64cf8`) | OK |
| ✅ | 7 个部署必需文件 | 全部就绪 |
| ✅ | requirements.txt (streamlit/pydantic/networkx/httpx) | 完整 |
| ✅ | 数据文件 (zh-docs-200 + cail_loader) | OK |
| ✅ | zh-docs-200 (200 docs, 全有 gold_entities) | 完整 |
| ✅ | CAIL 51 案件 | 完整 |
| ✅ | Demo 不依赖 .db | Cloud-ready |
| ✅ | Demo 支持双数据集 + Demo Mode | OK |
| ✅ | .gitignore 排除 .db 但保留 demo JSON | 安全 |
| ✅ | Streamlit main file path 正确 | OK |

---

## 📋 您需要做的 3 件事

### 1️⃣ 推 GitHub（5 分钟）

**方式 A：HTTPS + Personal Access Token (推荐)**

```bash
cd F:/test/2026-07-19-00-02-50/opc-llm-projects

# 1. 在 GitHub 创建空仓库 https://github.com/new
#    Repo name: graphrag-cn (或 opc-graphrag)
#    Private or Public, **不要**初始化 README/LICENSE/.gitignore

# 2. 添加 remote
git remote add origin https://github.com/<your-username>/graphrag-cn.git

# 3. 推送
git push -u origin main
# 首次推送需输入 GitHub username + PAT (Personal Access Token)
```

**方式 B：SSH Key**

```bash
# 1. 生成 SSH key (如有跳过)
ssh-keygen -t ed25519 -C "your-email@example.com"

# 2. 复制公钥到 GitHub Settings → SSH and GPG keys
cat ~/.ssh/id_ed25519.pub

# 3. 推送
git remote add origin git@github.com:<your-username>/graphrag-cn.git
git push -u origin main
```

**故障排查**：详细步骤见 `docs/GIT_PUSH_GUIDE.md` (213 行)。

### 2️⃣ 部署 Streamlit Cloud（5 分钟）

1. 访问 <https://share.streamlit.io>
2. 用 GitHub 账号登录
3. 点击 "New app"
4. 填写：

   | 字段 | 值 |
   |---|---|
   | Repository | `<your-username>/graphrag-cn` |
   | Branch | `main` |
   | Main file path | `projects/graphrag_cn/demo/streamlit_app.py` |
   | App URL | 自定义如 `graphrag-cn` |

5. 点击 "Deploy!"，等待 2-5 分钟

### 3️⃣ 验证 URL（1 分钟）

打开自动生成的 URL（`https://graphrag-cn.streamlit.app`），应该看到：

- 🕸️ **GraphRAG-CN Web Demo** 标题
- 侧边栏数据集切换：`zh-docs-200` / `CAIL 51`
- 侧边栏 10 个 preset query
- "✅ 加载完成: 200 docs / X graph nodes / Y edges"
- 顶部黄色提示 "🔒 Demo Mode"（Cloud 无 Ollama 正常）

---

## 🎁 已就绪的关键特性

### Cloud-friendly Streamlit Demo

| 特性 | 实现 |
|---|---|
| 无 .db 依赖 | 直接从 JSONL 构建图谱 |
| 双数据集 | zh-docs-200 / CAIL 51 一键切换 |
| Demo Mode | 无 Ollama 自动启用，仅显示检索 + 图谱 |
| 鲁棒 import | LLM 相关代码 try/except 包裹 |

### 商业化文档

- `docs/PRICING.md` - 定价方案
- `docs/SLA.md` - 服务等级协议
- `docs/CASES.md` - 客户案例
- `docs/BETA_PROGRAM.md` - Beta 接入流程
- `docs/SUPPORT.md` - 客户支持
- `docs/DEPLOYMENT.md` - 部署方案 (本地/Cloud/Docker/K8s)

### 数据集

- **zh-docs-200**: 200 模拟文档（5 类别）— Phase 1 训练数据
- **CAIL 51**: 51 真实法律案件（4 大类 22 sub-category）— Phase 2 Week 9 接入

---

## 🔧 部署后监控

部署成功后，定期检查：

1. **Streamlit Cloud 控制台**：share.streamlit.io → 你的 App → Logs
2. **Resource Usage**：确认内存 < 1GB（免费版上限）
3. **Uptime**：确保 99%+ 在线

---

## ❌ 故障排查

### ModuleNotFoundError

- 原因：requirements.txt 缺包
- 解决：在仓库编辑 requirements.txt，然后 Streamlit Cloud → Reboot

### Demo 加载失败

- 原因：JSONL 文件缺失
- 解决：确认 `projects/graphrag_cn/data/zh-docs-200.jsonl` 和 `cail_loader.py` 已 push

### Demo 显示 "加载失败"

- 检查 Streamlit Cloud logs
- 常见原因：JSONL 编码问题（确保 UTF-8）

---

## 📞 联系

部署问题：GitHub Issues 或 email `<your-email>`

---

*Phase 2 Week 9 Day 2 · 2026-07-20*
*代码状态: READY TO DEPLOY (10/10 checks pass)*