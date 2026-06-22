# CLAUDE.md — AlphaEarth Cesium 项目开发指引

> Claude Code 项目操作手册。MAP 全局宪法见 `AI_RULES.md`。

## 项目概述

AlphaEarth Cesium (Zero2x / OneEarth) — 基于 CesiumJS 的 3D 地球空间智能平台：
- **前端**: Vue 3 (Composition API, `<script setup>`) + Vite 7 + CesiumJS + Three.js + GSAP
- **后端**: FastAPI ≤0.68.0 + Google Earth Engine + DashScope (Qwen) LLM
- **部署**: Docker Compose (dev/prod/canary) + 原生 Shell 脚本

```
Browser → Vite (8404) → proxy /api/* → FastAPI (8405) → GEE / LLM
Browser → Nginx (8406) → static OR proxy /api/* → FastAPI (8407)
```

## Docker 调用方式

**本机 Docker 需要通过 `sg docker` 调用**（用户 `hyf` 在主 shell 中 docker 组未激活）：

```bash
sg docker -c "<docker command>"
```

### 开发环境

```bash
# 启动（构建 + 运行）
sg docker -c "make -C /NAS_DATA/hyf/aef_cesium docker-dev-up"
# 停止
sg docker -c "make -C /NAS_DATA/hyf/aef_cesium docker-dev-down"
# 查看日志
sg docker -c "make -C /NAS_DATA/hyf/aef_cesium docker-dev-logs"
# 查看容器状态
sg docker -c "make -C /NAS_DATA/hyf/aef_cesium docker-dev-ps"

# 前端容器交互
sg docker -c "docker exec -it oneearth-021-dev-frontend-1 <cmd>"
# 后端容器交互
sg docker -c "docker exec -it oneearth-021-dev-backend-1 <cmd>"
```

## 部署后验证

部署完成后按以下步骤验证：

```bash
# 1. 确认容器 Running
sg docker -c "docker ps --filter name=oneearth-021-dev --format 'table {{.Names}}\t{{.Status}}'"

# 2. 确认端口监听
ss -tlnp | grep -E ':(8404|8405)\s'

# 3. 验证前端页面
curl -s -o /dev/null -w "Frontend: HTTP %{http_code}\n" http://127.0.0.1:8404/

# 4. 验证关键 Vite 依赖（504 即表示缓存过期，需重启前端）
curl -s -o /dev/null -w "Vue: %{http_code}\n" http://127.0.0.1:8404/src/main.js

# 5. 验证后端健康
curl -s http://127.0.0.1:8405/health

# 6. 验证后端 API 代理
curl -s http://127.0.0.1:8404/api/locations

# 7. 全量 Docker 验证（smoke + pytest + vitest）
sg docker -c "make -C /NAS_DATA/hyf/aef_cesium docker-dev-check"
```

## 常见问题速查

### Vite 返回 504 Outdated Optimize Dep → 前端白屏

**根因**：Docker 卷中的 Vite 依赖预构建缓存 (`node_modules/.vite/`) 过期，文件哈希不匹配。

**修复**：
```bash
# 方法 1：删除缓存 + 重启前端
sg docker -c "docker exec oneearth-021-dev-frontend-1 rm -rf /app/node_modules/.vite"
sg docker -c "docker compose -f /NAS_DATA/hyf/aef_cesium/compose/docker-compose.dev.yml --env-file /NAS_DATA/hyf/aef_cesium/.env restart frontend"

# 方法 2：完整重建（清除卷 + --force --build）
sg docker -c "docker compose -f /NAS_DATA/hyf/aef_cesium/compose/docker-compose.dev.yml --env-file /NAS_DATA/hyf/aef_cesium/.env down -v"
sg docker -c "docker compose -f /NAS_DATA/hyf/aef_cesium/compose/docker-compose.dev.yml --env-file /NAS_DATA/hyf/aef_cesium/.env up -d --build"
```

### GEE 端点返回 503

**根因**：容器无法连接 `earthengine.googleapis.com:443`（网络限制）。

```bash
# 诊断
curl -s http://127.0.0.1:8405/api/debug/gee
# 正常应为: {"gee_initialized":false, "last_error": "GEE init timed out after 10.0s", ...}

# 验证 TCP 连通性
sg docker -c "docker exec oneearth-021-dev-backend-1 timeout 5 python3 -c '
import socket; s=socket.socket(); s.settimeout(5)
s.connect((\"earthengine.googleapis.com\", 443)); print(\"OK\")
' 2>&1 || echo 'GEE API unreachable'"
```

### ThreeTwin.vue 编译错误

**文件**：`frontend/src/views/workbench/engines/ThreeTwin.vue`（4200+ 行，大型三引擎）

**已知陷阱**：`<script setup>` 块中有嵌套 `try/catch` / 函数 / ShaderMaterial 内联 GLSL，容易出现括号不平衡。

```bash
# 快速检查 brace 平衡
awk 'NR>=30 && NR<=4187 {for(i=1;i<=length($0);i++){c=substr($0,i,1);if(c=="{")d++;if(c=="}")d--}} END{print "brace balance:", d}' /NAS_DATA/hyf/aef_cesium/frontend/src/views/workbench/engines/ThreeTwin.vue
# 应为: brace balance: 0
```

## 测试

### 后端（pytest）
```bash
make test              # 全量（GEE stub 模式）
make test-fast         # 同上，显式 stub
make test-contract     # Tile PNG 契约测试
make test-backend-api  # FastAPI TestClient 测试
make test-integration  # 集成测试（需 GEE 连接，opt-in）
make test-coverage     # 带覆盖率报告
```

### 前端（vitest）
```bash
cd frontend && npm test           # 单次运行
cd frontend && npm run test:watch # 监听模式
cd frontend && npm run test:coverage  # 带覆盖率
```

## TDD 工作流

修改任何 `.py` / `.js` / `.vue` 文件时：

```
1. 先写 failing test → 确认红灯
2. 实现最小改动 → npm test / make test
3. 绿灯 → commit
4. 红灯 → 分析 → 修正 → 回到步骤 2
```

**注意**：纯文档（`.md`）、配置（`.yaml` / `.json`）修改豁免 TDD。

## 关键文件索引

| 文件 | 用途 |
|------|------|
| `frontend/src/main.js` | 路由分发（`/`, `/demo`, `/workbench`, `/act2`） |
| `frontend/src/Zero2xApp.vue` | Zero2x Landing（首页） |
| `frontend/src/App.vue` | Demo 主应用（`/demo`） |
| `frontend/src/WorkbenchApp.vue` | AI-Native 工作台（`/workbench`，lazy-load） |
| `frontend/src/components/CesiumViewer.vue` | CesiumJS 3D 查看器（核心组件） |
| `frontend/src/views/workbench/engines/ThreeTwin.vue` | Three.js 深空引擎（4200+ 行） |
| `frontend/Dockerfile.dev` | 前端 Docker 开发容器 |
| `frontend/vite.config.js` | Vite 配置（proxy, cesium, HMR） |
| `backend/main.py` | FastAPI 应用（~3000 行，全部路由） |
| `backend/config.py` | Settings：6 locations, 6 modes, 6 missions |
| `backend/gee_service.py` | GEE 初始化 + tile/stats/export |
| `backend/llm_service.py` | LLM 客户端（DashScope Qwen） |
| `tests/conftest.py` | pytest 共享 fixtures + GEE stubs |
| `compose/docker-compose.dev.yml` | Docker Dev 编排 |
| `compose/docker-compose.prod.yml` | Docker Prod 编排 |
| `.env` | 运行时密钥（GEE, Cesium Ion, LLM），不入 Git |
| `.env.example` | 环境变量文档化模板 |

## 环境变量关键变量

| 变量 | 用途 |
|------|------|
| `GEE_USER_PATH` | GEE 用户 Assets 路径 |
| `EE_SERVICE_ACCOUNT` | GEE 服务账号 |
| `EE_PRIVATE_KEY_JSON_B64` | GEE 私钥（base64） |
| `VITE_CESIUM_TOKEN` | Cesium Ion Access Token |
| `VITE_BASEMAP` | 底图选择：`google_xyz` / `osm` / `google_official` |
| `VITE_ION_PROXY` | 通过后端代理 Ion 请求 |
| `ONEEARTH_BIND_IP` | Docker 端口绑定 IP（`127.0.0.1` 或 `0.0.0.0`） |
| `GEE_INIT_TIMEOUT_S` | GEE 初始化超时（默认 6s，内部网络建议 10s） |
| `TILE_UPSTREAM_MAX_CONCURRENCY` | 上游 tile 并发数（默认 16） |
| `TILE_LRU_MAX_BYTES` | tile 内存缓存上限（默认 64 MiB） |

## No-Go Zones（禁止修改）

以下文件仅限架构师层修改：

- `CLAUDE.md` — 本文件
- `AI_RULES.md` — Agent 行为宪法
- `WORKSPACE_MAP.md` — 项目拓扑
- `backend/CONVENTIONS.md` — 后端地方法规
- `frontend/CONVENTIONS.md` — 前端地方法规

## 架构约束

- **前后端通信**：仅通过 HTTP REST API，禁止直接 Python import
- **Three.js 对象**：必须用 `markRaw()` 包裹，避免 Vue reactivity 开销
- **Cesium 入口**：`CesiumViewer.vue` 是唯一 Cesium 入口点
- **GEE 守卫**：所有 GEE 端点通过 `_require_gee()` 守卫，未就绪返回 503 + Retry-After
- **Tile 代理安全**：仅代理白名单上游，避免 SSRF

## Agent 人格

| 上下文 | 风格 |
|--------|------|
| 源代码 (`.py`, `.js`, `.vue`) | IEEE 工程师 — 绝对严谨，禁止游戏化 |
| 文档 (`.md`) | 架构师 — 允许隐喻 |
| Git Commit | Conventional Commits — 绝对无菌 |
