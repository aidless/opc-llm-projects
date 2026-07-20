# GitHub 推送 + Streamlit Cloud 部署指南

> Phase 2 / Week 8 / Day 2 · 2026-07-20

## 当前 Git 状态

```
$ git log --oneline
72f068b docs: Week 8 Day 1 验收报告（Git 仓库初始化）
72d9728 chore: 排除 data/*.db 大文件
f6c9735 Phase 2 Week 7 收官: Web Demo + LangChain + 商业文档 + Beta 计划
```

**175 文件已 commit，main 分支就绪，等待推 GitHub。**

---

## Step 1: 创建 GitHub 仓库

1. 访问 <https://github.com/new>
2. Repository name: `graphrag-cn`
3. Owner: `<your-org>` (例如 opc-platform)
4. Description: "中文事件抽取 + 实体链接 + 知识图谱 + RAG 端到端解决方案"
5. Visibility:
   - **Public**（推荐，便于 Streamlit Cloud 公开访问）
   - Private（需要 Streamlit Cloud Pro）
6. ⚠️ **不勾选** "Initialize with README"（本地已有）
7. 点击 "Create repository"

---

## Step 2: 推送本地仓库

### 方式 A: HTTPS + Personal Access Token（推荐）

```bash
cd F:/test/2026-07-19-00-02-50/opc-llm-projects

# 1. 创建 PAT
# GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
# Generate new token, 选 'repo' scope, 复制 token

# 2. 添加 remote
git remote add origin https://github.com/<your-org>/graphrag-cn.git

# 3. 推送（首次需要凭据）
git push -u origin main
# Username: <your-github-username>
# Password: <paste-PAT-here>
```

### 方式 B: SSH（更安全）

```bash
cd F:/test/2026-07-19-00-02-50/opc-llm-projects

# 1. 生成 SSH key
ssh-keygen -t ed25519 -C "opc-platform@example.com"
# 默认保存到 ~/.ssh/id_ed25519

# 2. 显示公钥
cat ~/.ssh/id_ed25519.pub
# 复制整个输出

# 3. 添加到 GitHub
# GitHub → Settings → SSH and GPG keys → New SSH key
# Title: "OPC Platform Mac"
# Key: <paste-public-key>

# 4. 测试连接
ssh -T git@github.com
# 输出: Hi <username>! You've successfully authenticated...

# 5. 推送
git remote add origin git@github.com:<your-org>/graphrag-cn.git
git push -u origin main
```

---

## Step 3: 验证推送成功

1. 访问 `https://github.com/<your-org>/graphrag-cn`
2. 应看到所有 175 个文件
3. README.md 应显示项目主页
4. 关键文件验证：
   - `projects/graphrag_cn/demo/streamlit_app.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
   - `docs/PRICING.md`

---

## Step 4: Streamlit Cloud 部署

### 4.1 注册

1. 访问 <https://share.streamlit.io>
2. 点击 "Sign in with GitHub"
3. 授权 access to your repos

### 4.2 创建 App

| 字段 | 值 |
|---|---|
| Repository | `<your-org>/graphrag-cn` |
| Branch | `main` |
| Main file path | `projects/graphrag_cn/demo/streamlit_app.py` |
| App URL | （自动生成 `https://<custom>.streamlit.app`） |

### 4.3 Advanced settings

```toml
# Python version
3.11

# Secrets (无 Ollama 配置即可, 因 Cloud 无 Ollama)
# (空)
```

### 4.4 Deploy

1. 点击 "Deploy!"
2. 等待 2-5 分钟（Python 依赖安装）
3. 看到 "Your app is now deployed!" 提示

### 4.5 验证

打开生成的 URL:
- ✅ 应看到 "🕸️ GraphRAG-CN Web Demo" 标题
- ✅ 应看到 200 docs / 160 graph nodes 提示
- ⚠️ 检索/图谱正常，但 LLM 调用会失败（Cloud 无 Ollama）

---

## Step 5: 公开 URL

部署后 URL 类似：
- `https://graphrag-cn.streamlit.app`
- `https://opc-graphrag-cn.streamlit.app`

**更新 README.md**:
```markdown
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://graphrag-cn.streamlit.app/)
```

---

## 故障排查

### 推送失败

```bash
# 错误: Permission denied
# 解决: 检查 PAT / SSH key

# 错误: Repository not found
# 解决: 检查 remote URL (大小写)
git remote -v
git remote set-url origin https://github.com/<correct-org>/graphrag-cn.git
```

### Streamlit Cloud 部署失败

```bash
# ModuleNotFoundError: No module named 'opc_platform'
# 解决: sys.path.append 在 streamlit_app.py 已设置
# 但可加 PYTHONPATH=.  在 Streamlit Secrets
```

```python
# Error: experiments/entity_index_200_day6.db not found
# 解决: 确认 .gitignore 没排除重要文件
!experiments/qa-eval-day6.json
!experiments/entity-link-day2.json
!experiments/eval-link-200-day6.json
# 必须在 git 中
```

### 公开 URL 慢

```
Cloud 容器冷启动 1-2 分钟是正常的
数据 200 docs + 160 nodes 加载耗时
Streamlit 免费版自动 sleep
```

---

## 验证 Checklist

```
□ GitHub 仓库已创建
□ 175 文件已推送
□ 推送成功 (git status clean)
□ share.streamlit.io 注册
□ New app 配置正确
□ Deploy 成功
□ 公开 URL 可访问
□ README URL 链接已更新
□ 域名监控: uptimerobot.com
```

---

## 联系

部署问题：<github-issues-url>
Email: opc-platform@example.com

---

*Phase 2 Week 8 Day 2 · 2026-07-20 · 草稿*
