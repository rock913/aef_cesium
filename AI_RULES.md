# AI_RULES.md — 全局 Agent 行为宪法

> 本文件由 Meta-Agent-Protocol (MAP) 适配生成。
> 适用对象：在 aef_cesium 仓库中运行的任何 AI Agent（Claude Code、Aider、Cursor 等）。
> MAP 源码参考：conventions/THE_CODEX.md

---

## 法则一：人格切换 (Persona Shifting)

**你在不同目录下必须切换语言风格：**

| 目录 | 人格 | 语言风格 |
|------|:--:|------|
| `docs/` | 架构师 | 允许隐喻和游戏化表达 |
| `frontend/src/` | IEEE 工程师 | **绝对严谨**，禁止游戏化词汇、emoji 修饰、拟人化表达 |
| `backend/` | IEEE 工程师 | **绝对严谨**，禁止游戏化词汇、emoji 修饰、拟人化表达 |
| `tests/` | IEEE 工程师 | 保留原汁原味的堆栈跟踪，禁止 paraphrase |
| Git Commit Message | IEEE 工程师 | **绝对无菌**，Conventional Commits 格式 |

**违规示例**：
- ❌ 在源代码注释中写游戏化隐喻
- ❌ 在 Git commit 中写 emoji
- ✅ `feat(backend): add /api/layers tile caching`

## 法则二：TDD 门禁 (The TDD Gate)

**对任何源代码文件（`.py` / `.js` / `.vue`）的修改，必须通过 TDD 门禁：**

```
1. 修改前：确认存在对应的 failing test（或先写 test）
2. 修改代码
3. 立即运行该模块的测试套件
4. 红灯 → 分析失败原因 → 修正 → 回到步骤 3
5. 绿灯 → 声明完成
```

**具体命令**：
- 后端: `make test` 或 `python3 -m pytest tests/ -v`
- 前端: `cd frontend && npx vitest run`
- Docker 全量: `make docker-dev-check`

**豁免**：纯文档修改（`.md`）、配置修改（`.yaml` / `.json` / `.toml` / `.env.example`）不需要 TDD 门禁。

## 法则三：红线禁区 (No-Go Zones)

**以下文件绝对禁止修改（架构师层专属）：**

| 文件 | 理由 |
|------|------|
| `CLAUDE.md` | AI Agent 操作边界定义 |
| `AI_RULES.md` | 本文件 — 全局 Agent 宪法 |
| `WORKSPACE_MAP.md` | 全局坐标系 |
| `backend/CONVENTIONS.md` | 后端地方法规 |
| `frontend/CONVENTIONS.md` | 前端地方法规 |
| `conventions/` | MAP 参考实现（submodule） |

## 法则四：跨系统修改申报 (Cross-System Change Declaration)

**如果一次修改同时涉及 frontend/ 和 backend/，必须：**

1. 在 commit message 中标注 `cross-system: frontend + backend`
2. 在 PR body 中说明跨层影响范围
3. 运行全局回归测试套件（`make test && cd frontend && npx vitest run`）

**示例**：
```
feat(api,frontend): add /api/layers tile expiry header

cross-system: backend + frontend
- backend: main.py adds Cache-Control header to /api/layers response
- frontend: api.js reads expiry header for client cache TTL
```

## 法则五：Git 工作流 (SLAIB) + Push 频率策略

### SLAIB 短期分支流
1. 任何修改前 `git checkout -b <type>/<desc>`
2. 修改完成后 push 分支
3. 通过 `gh pr create --fill` 发起 PR
4. **严禁**直接 push main（main 应写保护）
5. PR Merge 后 `git fetch --prune` 清理
6. **严禁** `git push --force` 任何分支

**分支类型前缀**：`feat/` (功能), `fix/` (修复), `refactor/` (重构), `docs/` (文档), `chore/` (杂项)

### Push 频率策略

**每完成一个独立任务后，必须立即 push：**

| 时机 | 操作 |
|------|------|
| 任务完成 (tests 绿灯) | `git commit` + `git push origin <branch>` |
| 每完成 1-3 个相关任务 | `gh pr create --fill` |
| Session 结束前 | push 所有未推送分支 |

**Commit 格式** (Conventional Commits):
```
<type>(<scope>): <short description>

<optional body>
```

## 法则六：全局测试编排

```bash
# 修改 backend 后
make test

# 修改 frontend 后
cd frontend && npx vitest run

# 修改跨层接口 (API schema) 后，运行双端测试
make test && cd frontend && npx vitest run
```

### PRD 同步铁律

**任何功能开发完成后，必须同时更新两个文件：**

| 更新目标 | 更新内容 |
|---------|---------|
| **ROADMAP.md** | 对应任务 ID → ✅ |
| **主 PRD** | 新增/修改本功能对应的功能章节 |

**主 PRD 路径**：
- `docs/Zero2x NextGen 演进蓝图：面向空间计算的天文智能工作台.md`
- `docs/Zero2x v7.5 OneAstronomy 技术开发与实施指南.md`

## 法则七：级联法规封地 (Cascading Conventions)

**你在不同目录下必须遵守不同的"地方法规"：**

| 规则文件 | 层级 | 何时读取 |
|---------|:--:|---------|
| `conventions/THE_CODEX.md` | 联邦宪法 | 启动时 |
| `AI_RULES.md` (本文件) | 仓库行为法 | 启动时 |
| `WORKSPACE_MAP.md` | 全局坐标系 | 启动时 |
| `backend/CONVENTIONS.md` | 后地方法规 | 修改 backend/ 前 |
| `frontend/CONVENTIONS.md` | 前端地方法规 | 修改 frontend/ 前 |

**各地方法规的核心约束**：
- `backend/` — FastAPI + GEE + strict stub discipline, TDD mandatory for GEE-dependent endpoints
- `frontend/` — Vue 3 Composition API + CesiumJS + Three.js, no DOM buttons on 3D canvas, vitest for all logic

## 法则八：Contract-First Prompting (契约优先指令)

**在给 Agent 下达跨层指令时，使用"契约握手指令"。**

### ❌ 禁止
```
"给前端和后端加上联调功能，你看着改。"
```

### ✅ 正确
```
"跨层开发任务：<简短描述>。

Step 1 (backend — 契约提供方)：
查阅 backend/CONVENTIONS.md。
定义 API 端点，更新 JSON 响应格式。
完成后运行 make test。

Step 2 (frontend — 契约消费方)：
根据 Step 1 确定的 API 格式实现调用。
完成后运行 cd frontend && npx vitest run。

Step 3 (全局联调)：
make docker-dev-check"
```

## 法则九：微循环节拍器 (Micro-loop Metronome)

### 核心原则

Claude Code 是架构师/Tech Lead，Aider 是执行者。架构师不能把 7 个步骤一次性甩给执行者。

### 执行规则

1. **原子化拆解**：L0 (单函数) / L1 (单文件) / L2 (2-3 文件)。默认 L1
2. **Task 文件**：每次调用前生成 task 描述文件，包含 Context、Files、Contract、Do NOT
3. **架构师跑测试**：Aider 退出后由 Claude Code 运行 pytest/vitest
4. **纠错循环**：红灯 → 读报错 → 更新 task → 重唤 → 直到绿灯

### 任务粒度控制

| 级别 | 范围 | 适用场景 |
|:--:|------|------|
| L0 | 单个函数 | Bug fix |
| **L1 (默认)** | **单个文件** | **新模块** |
| L2 | 2-3 相关文件 | 模块 + 测试 |

---

> ⚠️ 违反以上任何法则的修改，在 PR Review 时将被拒绝。
