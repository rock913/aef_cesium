# Zero2x / AlphaEarth 快速参考（cesium_app_v6）

本卡片只保留“可执行、可验收”的命令与契约，用于团队日常开发与发布。

## 🌐 路由与端口（固定契约）

- Dev（Docker/Vite）：前端 `8404` / 后端 `8405`
- Prod（Docker/nginx + uvicorn）：前端 `8406` / 后端 `8407`

路由语义：

- `/`：Zero2x Landing（默认首页，轻量，不默认初始化 Cesium）
- `/act2`：第二幕叙事（Cesium 极简编排）
- `/workbench`：AI‑Native 工作台壳（路由级拆包）
- `/demo`：Alpha Earth Demo（场景验证系统：Missions + AI Console）

## ✅ 一键验收（TDD 门禁）

```bash
cd cesium_app_v6

make docker-dev-up
make docker-dev-check

make docker-prod-up
make docker-prod-check
```

说明：

- `docker-dev-check`：包含 smoke + pytest + vitest（容器内），并检查关键静态资源存在
- `docker-prod-check`：验证 nginx 静态 + 同源 `/api` 反代 + `/health` 可用

## 🐳 Docker Dev（推荐开发路径）

```bash
make docker-dev-up
make docker-dev-logs
make docker-dev-ps
make docker-dev-down
```

访问：

- 前端：`http://127.0.0.1:8404/`
- 后端：`http://127.0.0.1:8405/health`、`http://127.0.0.1:8405/docs`

默认情况下 Docker Dev 仅绑定到本机（避免开发服务被误当作发布服务暴露）。需要对外联调时：在 `.env` 或 `.env.dev` 设置 `ONEEARTH_BIND_IP=0.0.0.0`。

## 🧱 Docker Prod（推荐发布路径）

```bash
make docker-prod-up
make docker-prod-logs
make docker-prod-ps
make docker-prod-down
```

访问：

- 前端：`http://127.0.0.1:8406/`
- 后端：`http://127.0.0.1:8407/health`、`http://127.0.0.1:8407/docs`

## 🧰 本机脚本（非 Docker，适合快速调试）

```bash
./run_backend.sh
./run_frontend.sh
```

单进程“最稳”部署（FastAPI 同时托管 dist + /api，减少 502 类型问题）：

```bash
./run_prod_single.sh
```

## 🔐 最小环境变量（.env）

```bash
cp .env.example .env

# 最少需要（GEE）：
GEE_USER_PATH=users/your_username/aef_demo

# LLM（可选，用于 /api/report 与 /api/analyze；未配则模板回退）
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=...
LLM_MODEL=qwen-plus
```

注意：Vite 的 `VITE_*` 变量在 **生产构建时注入**；修改后需要重新构建前端产物（Docker Prod 会自动 build）。

## 🧯 排障速查

- 后端是否就绪：`curl -fsS http://127.0.0.1:8405/health`（Dev）或 `http://127.0.0.1:8407/health`（Prod）
- 同源反代是否通：`curl -fsS http://127.0.0.1:8406/api/locations`（Prod）
- 看容器日志：`make docker-prod-logs` / `make docker-dev-logs`

## 🧪 常用测试（非 Docker）

```bash
make test-fast
make test-contract
```

## 🛰️ CH5（盐城）V8.1 分类器导出（GEE Asset）

```bash
export CH5_RF_ASSET_ID=users/<your_username>/aef_demo/classifiers/ch5_coastline_rf_v1
# 或：export GEE_USER_PATH=users/<your_username>/aef_demo

python backend/ch5_rf_export.py --check
python backend/ch5_rf_export.py --ensure
```

---

更新：2026-03-03
