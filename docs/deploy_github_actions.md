# 部署与持续发布（GitHub Actions + 8506/8507 生产副本）

本文档面向团队协作，目标是把“开发环境(8504/8505)”与“生产环境(8506/8507)”彻底隔离，并用 GitHub Actions 实现可追溯、可回滚的持续集成/持续发布（CI/CD）。

> 约定：
> - 开发：前端 8504（Vite dev），后端 8505（FastAPI）
> - 生产：前端 8506（Nginx 静态 dist），后端 8507（FastAPI + systemd）

---

## 1. GitHub Actions 的用途（团队共识）

GitHub Actions = 仓库内置的自动化流水线，典型用途：

- **CI（持续集成）**：每次 Push/PR 自动跑测试（pytest/vitest）、构建产物（`frontend/dist`），确保“能合并的代码一定可运行”。
- **CD（持续部署/发布）**：把某个 commit/tag 自动发布到服务器，包含：打包 → 上传 → 解包 → 切换版本 → 重启服务 → 健康检查 → 失败回滚。
- **审计与可追溯**：每次发布都有日志、对应 commit SHA、产物与部署记录，团队沟通成本低。

本仓库推荐：
- PR 只跑 CI；
- 生产发布用 **手动触发**（`workflow_dispatch`）或 **tag 触发**（如 `v6.6.1`），避免每次 merge 都自动上线。

---

## 2. 代码位置与环境边界（开发 vs 生产）

### 2.1 仓库内重要路径

- 后端：`backend/`（FastAPI，端口由 `API_PORT` 控制）
- 前端：`frontend/`（Vue3 + Cesium，开发用 Vite；生产用 `dist` 静态文件）
- 启动脚本：
  - 开发后端：`run_backend.sh`
  - 开发前端：`run_frontend.sh`
  - 单进程模式（可选）：`run_prod_single.sh`（不推荐用于本次 8506/8507 双端口方案）
- 部署模板：`deploy/systemd/`、`deploy/nginx/`

### 2.2 关键原则

- **开发环境**：允许热更新、允许更宽松的调试配置（Vite dev / CORS 宽松等）。
- **生产环境**：
  - 前端必须使用构建产物 `frontend/dist`，避免 Vite dev 常见 502 / 模块路径问题。
  - 后端用 systemd 常驻守护，服务重启/日志统一管理。
  - 密钥（GEE/LLM）必须在服务器 `.env.prod` 管理，**不进 Git**。

### 2.3 端口与 env 的映射

建议用独立环境文件（示例命名）：

- 开发：`.env.v6`（现状已可用）
- 生产：`.env.prod`（服务器上维护）

生产 `.env.prod` 最少需要：

```bash
# 生产端口
FRONTEND_PORT=8506
API_PORT=8507
API_HOST=127.0.0.1

# GEE / LLM（按需）
GEE_USER_PATH=users/your_username/aef_demo
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=***
LLM_MODEL=qwen-plus
```

> 说明：后端读取 `API_HOST/API_PORT`，前端生产不需要 `FRONTEND_PORT`（Nginx listen 决定），但保留无害。

---

## 3. 生产部署架构（推荐）

### 3.1 生产进程拆分

- **Nginx（8506）**：
  - `root` 指向 `frontend/dist`
  - `/api/` 反代到 `http://127.0.0.1:8507`
- **FastAPI（8507）**：
  - `uvicorn` 由 systemd 管理

### 3.2 为什么不建议生产继续用 `run_frontend.sh`

`run_frontend.sh` 默认走 Vite dev（`FRONTEND_RUN_MODE=dev`），它适合开发，不适合生产：

- dev server 依赖 node 进程常驻，稳定性不如 nginx 静态。
- 生产需要强缓存策略/静态资源可控。
- 一旦 dev server 崩溃，线上表现通常是 502。

---

## 4. 服务器目录规范（可回滚）

推荐使用“版本目录 + current 软链”的发布结构：

```text
/opt/oneearth/cesium_app_v6/
  releases/
    20260223_abcdef12/
      backend/
      frontend/dist/
      deploy/
      ...
    20260220_12345678/
  current -> releases/20260223_abcdef12
```

优点：
- 回滚 = 切回旧的 `current` 并重启服务，耗时秒级。
- 任何线上问题都可定位到发布版本。

---

## 5. systemd 与 nginx 配置建议

### 5.1 systemd（后端 8507）

建议创建一个独立 service，例如：

- `oneearth-v6-backend-8507.service`

关键点：
- `WorkingDirectory` 指向 `/opt/oneearth/cesium_app_v6/current`
- `Environment=ENV_FILE=/opt/oneearth/cesium_app_v6/.env.prod`
- `ExecStart` 仍复用仓库脚本 `run_backend.sh`

### 5.2 nginx（前端 8506 + /api -> 8507）

建议复制现有示例并改端口：

- 从 `deploy/nginx/oneearth_v6_8504.conf` 复制
- `listen 8506;`
- `proxy_pass http://127.0.0.1:8507;`
- `root /opt/oneearth/cesium_app_v6/current/frontend/dist;`

---

## 6. GitHub Actions：CI（持续集成）建议

推荐工作流：

- 触发：
  - `pull_request`：必须跑
  - `push` 到 `main`：跑
- 任务：
  - 后端：`make test-fast`
  - 前端：`npm ci && npm test && npm run build`
- 产物：将 `frontend/dist`（以及可选的完整 release 包）作为 Actions artifact 保存，便于排查与发布复用。

仓库内已提供对应 workflow：

- CI：`.github/workflows/ci.yml`
- 生产部署（手动触发）：`.github/workflows/deploy_prod.yml`

---

## 7. GitHub Actions：CD（生产部署）建议

建议生产部署用手动触发（避免误上线）：

- `workflow_dispatch` 输入：
  - `ref`：要发布的 commit SHA / tag
  - `release_id`：可自动生成（日期 + 短 sha）
- 流程：
  1) 拉取对应 ref
  2) 跑测试（至少快速测试）
  3) 构建前端 dist
  4) 打包 release（tar.gz）
  5) 用 SSH 上传到服务器（例如 `/opt/oneearth/cesium_app_v6/incoming/`）
  6) 远程执行部署脚本：解包到 `releases/<id>`，切换 `current`，重启后端服务，reload nginx
  7) 健康检查失败则回滚

### 7.1 GitHub Secrets（建议）

GitHub 有两套“作用域”可以存放 Secrets/Variables：

1) **Repository（仓库级）**

- 入口：Repository → Settings → Secrets and variables → Actions
- 特点：对所有 workflow/job 生效（只要 workflow 引用 `secrets.NAME` 或 `vars.NAME`）
- 适用：只有一套部署目标（单生产机），或暂时不需要区分 prod/staging

2) **Environment（环境级，例如 production）**

- 入口：Repository → Settings → Environments → `production` → Add secret / Add variable
- 特点：只有当 job 显式声明 `environment: production` 时才会注入；可加“审批/保护规则”
- 适用：强烈推荐用于生产（prod）凭据，方便后续扩展 staging/prod、多套服务器

本仓库的生产部署 workflow 已设置 `environment: production`（见 `.github/workflows/deploy_prod.yml`），因此你可以把生产相关值放在 **Environment: production** 里。

---

建议放在 **Environment: production（Secrets）**：

- `PROD_HOST`：生产服务器 IP / 域名
- `PROD_USER`：SSH 用户
- `PROD_SSH_KEY`：私钥（建议专用 deploy key）
- （可选）`PROD_SSH_KEY_B64`：把私钥内容 base64 后保存（更不容易因为换行/CRLF 导致 `ssh-add` 解析失败；设置了它会优先使用）
- （可选）`PROD_SSH_PASSPHRASE`：如果私钥带 passphrase，需要配置该 secret（否则请使用无口令私钥）
- `PROD_PATH`：`/opt/oneearth/cesium_app_v6`
- （可选）`PROD_SSH_PORT`：SSH 端口（默认 22）

建议补充（可选，但能减少硬编码/便于多机）：

- `PROD_BACKEND_SERVICE`：systemd 服务名（默认 `oneearth-v6-backend-8507`）
- `PROD_HEALTH_URL`：后端健康检查 URL（默认 `http://127.0.0.1:8507/health`）
- `PROD_FRONTEND_URL`：前端健康检查 URL（默认 `http://127.0.0.1:8506/`）
- `PROD_KNOWN_HOSTS`：ssh known_hosts（可选；不填则 workflow 会用 `ssh-keyscan` 自动写入）

建议放在 **Repository（Variables）**（非敏感默认值，团队可见）：

- `PROD_SSH_PORT`（如果你不想把端口当 secret）
- `PROD_BACKEND_SERVICE` / `PROD_HEALTH_URL` / `PROD_FRONTEND_URL`（如果这些不敏感）

> 说明：当前 workflow 读取的是 `secrets.PROD_*`。如果你决定把某些值改为 Variables（`vars.PROD_*`），需要同步调整 `.github/workflows/deploy_prod.yml` 的取值来源。

最佳实践：
- **SSH key 最小权限**（仅允许部署目录 + systemctl/nginx reload 所需权限）
- 部署用户建议是独立用户 `deploy`，sudo 权限只开放必要命令

权限提醒（很关键）：

- 服务器侧 `deploy/scripts/deploy_release.sh` 会执行 `systemctl restart <backend_service>`、`systemctl reload nginx`、`nginx -t`。
- 如果用非 root 用户部署，请给该用户配置对这些命令的免密 sudo（`sudo -n`），否则部署会在重启/重载阶段失败并回滚。

---

## 8. 最佳实践清单（团队维护重点）

- **发布必须可回滚**：保留最近 3~5 个 release；任何发布失败都应自动回滚。
- **配置不入库**：`.env.prod` 与私钥永不提交；用服务器侧配置 + GitHub Secrets 管理。
- **对齐端口与域名**：生产永远只走 8506/8507；开发只走 8504/8505。
- **部署前先测试**：生产部署 workflow 内至少跑 `make test-fast` + 前端 `npm test`。
- **把“部署动作”脚本化**：把复杂命令集中在 `deploy/scripts/deploy_release.sh`，Actions 只负责上传+调用。
- **日志集中**：后端优先看 `journalctl -u oneearth-v6-backend-8507 -f`；nginx 看 access/error log。

---

## 9. 常用排障命令（服务器）

```bash
# 后端服务状态
sudo systemctl status oneearth-v6-backend-8507
sudo journalctl -u oneearth-v6-backend-8507 -f

# nginx 检查与 reload
sudo nginx -t
sudo systemctl reload nginx

# 端口占用
ss -ltnp | egrep ':(8506|8507)'

# 健康检查
curl -fsS http://127.0.0.1:8507/health
curl -fsS http://127.0.0.1:8506/
```

---

## 10. 推荐的发布方式（团队协作）

- 日常开发：PR → CI 全绿 → merge
- 生产发布：
  - 由负责人在 GitHub Actions 手动触发 deploy workflow
  - 指定 `ref`（commit SHA 或 tag）
  - 发布成功后在 Release/变更记录里写清楚：版本、改动、回滚点
