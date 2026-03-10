# Zero2x + Alpha Earth Demo（cesium_app_v6, V6.6 / 0.21）

本仓库是 **Zero2x 叙事页 + AI‑Native 工作台壳** 与 **Alpha Earth Demo 场景验证系统** 的同栈融合版本：

- 前端：Vue 3 + Vite + CesiumJS（按路由按需挂载）
- 后端：FastAPI + Google Earth Engine（可 stub；支持瓦片代理/统计/模板+LLM）

核心约束：**不推倒重来**，保留 `/demo` 作为“工具化场景验证系统”；同时将 `/` 升级为 Zero2x Landing（渐进式揭示，不默认加载重 WebGL）。

## 📌 当前状态（2026-03-03）

- 路由分离（渐进式揭示）：
  - `/`：Zero2x Landing（五幕叙事 + Omni‑Bar；默认不初始化 Cesium）
  - `/act2`：第二幕叙事场景（极简 UI + Cesium 镜头编排）
  - `/demo`：Alpha Earth Demo（Missions + AI Console + Cesium 场景验证）
  - `/workbench`：AI‑Native 工作台壳（路由级拆包；Monaco 等重依赖按需加载）
- Dev 研发环境已 Docker 化并固化端口：前端 8404 / 后端 8405（推荐使用 `make docker-dev-up`）。
- Prod（本分支唯一生产方式：Docker Prod）端口：前端 8406 / 后端 8407（推荐使用 `make docker-prod-up`）。
- 一键验收门禁：
  - Dev：`make docker-dev-check`（smoke + pytest + vitest）
  - Prod：`make docker-prod-check`（smoke + nginx 静态资源 + /api 反代）
- 后端提供可观测/排障入口：`/health`、`/api/debug/version`、以及若干瓦片代理诊断接口。
- 前端地图：支持 2D 底图切换（含 Google XYZ 测试模式/Google 官方会话模式）+ Cesium Ion Photorealistic 3D Tiles。
- 视觉一致性：Photorealistic 3D Tiles 支持“按相机高度 LOD 自动显隐”，并支持 AI 图层激活时自动遮挡（hide/dim）。

功能接口：
- `/api/report`：监测简报（模板/LLM）
- `/api/analyze`：智能体分析控制台（模板/LLM）
- 前端调试：地图左下角实时显示“屏幕中心经纬度 CENTER: lat, lon”（用于校准飞行/定位）

- [docs/zero2x/zero2x_v4.md](docs/zero2x/zero2x_v4.md) - Zero2x v4 体验目标与工程落地约束（本分支主规格）
- [docs/zero2x/update_patch_0303.md](docs/zero2x/update_patch_0303.md) - v4 视觉/布局复盘与补丁目标
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 常用命令与端口速查
- [docs/架构升级与敏捷开发.md](docs/架构升级与敏捷开发.md) - 基于仓库真实现状的工程化/Dev Docker/TDD 指南
- [docs/oneearth_v6.6.md](docs/oneearth_v6.6.md) - 最新迭代说明（如与 v6 有差异以该文档为准）
- [docs/deploy_github_actions.md](docs/deploy_github_actions.md) - GitHub Actions 持续集成/发布

> 重要说明（接口/端口口径）：
>
> - 本仓库/本分支的 **Prod 唯一口径是 Docker Prod：8406/8407**。
> - “8506/8507（systemd+nginx）真生产”属于主项目历史部署口径；**本分支不维护也不验收 8506/8507**。
> - 如必须对齐外部访问端口为 8506/8507：请在宿主机层用 nginx / 端口转发把 `8506 -> 8406`、`8507 -> 8407`，而不是在本仓库内维护两套生产体系。

## 🏗️ 技术架构

```text
Frontend (8404/8406)            Backend API (8405/8407)               Google Earth Engine
┌─────────────────────┐         ┌─────────────────────────┐          ┌───────────────────┐

- Runtime deps: `pip install -r backend/requirements.txt`
- Dev/test deps (needed for `make test-fast`): `pip install -r backend/requirements-dev.txt`
│ Vue3 + Vite + CesiumJS│◄──────► │ FastAPI                 │◄────────►│ AEF Dataset        │
│ - Zero2x (/ )         │  JSON    │ - 图层/瓦片 URL 生成     │   ee API  │ - Embeddings       │
│ - Act2 (/act2)        │         │ - reduceRegion 统计      │          │ - Sentinel-2 etc.  │
│ - Demo (/demo)        │         │ - 缓存/预热/导出         │          └───────────────────┘
│ - Workbench (/workbench)       │
└─────────────────────┘         └─────────────────────────┘
```

## 📁 项目结构（实际）

```text
cesium_app_v6/
├── backend/
│   ├── main.py                 # FastAPI 路由：locations/modes/missions/layers/stats/report/analyze
│   ├── config.py               # locations/modes/missions + 端口 + viewport buffer 策略
│   ├── gee_service.py          # GEE 算法与图层生成
│   ├── llm_service.py          # DashScope/Qwen(OpenAI-compatible) + 模板回退
│   └── requirements.txt
├── frontend/
│   ├── vite.config.js          # dev server 8404 + /api -> 8405 代理
│   ├── package.json            # npm test (vitest)
│   ├── src/
│   │   ├── main.js             # 路由级装配：/ /act2 /demo /workbench
│   │   ├── Zero2xApp.vue       # Zero2x Landing（五幕 + Omni‑Bar）
│   │   ├── Act2App.vue         # 第二幕叙事（Cesium 极简编排）
│   │   ├── WorkbenchApp.vue    # 工作台壳（按需加载重依赖）
│   │   ├── App.vue             # /demo：Missions + AI 控制台 + Debug HUD
│   │   ├── components/
│   │   │   ├── CesiumViewer.vue# Cesium viewer、飞行、图层、center 坐标 emit
│   │   │   └── HudPanel.vue
│   │   ├── services/api.js     # 后端 API 封装
│   │   └── utils/coords.js     # formatLatLon
│   └── tests/                  # vitest 单测
├── tests/                      # pytest（API 契约/集成/服务单测）
├── .env / .env.example
├── run_backend.sh / run_frontend.sh / start.sh / setup_env.sh
└── README.md
```

## 🚀 快速开始

### 推荐：Docker Dev 一键跑通（8404/8405）

适用于“团队多人协作/避免宿主依赖污染/保证可复现”。

```bash
cd cesium_app_v6
cp .env.example .env

make docker-dev-up
make docker-dev-check
```

远程访问（公网 IP / 反代）说明

- 默认情况下，compose 会把 8404/8405 绑定到 `127.0.0.1`（仅本机可访问）。如果你需要从其他机器访问（例如 `http://<server-ip>:8404`），请显式开放绑定：

```bash
ONEEARTH_BIND_IP=0.0.0.0 make docker-dev-up
```

- 如果你通过公网 IP / 反向代理访问 Vite Dev Server，HMR websocket 可能不可达；两种处理方式：
  - 最简单：禁用 HMR（适合演示/只读访问）：`VITE_DISABLE_HMR=1 ONEEARTH_BIND_IP=0.0.0.0 make docker-dev-up`
  - 或者指定 HMR host/port（适合需要热更新）：设置 `VITE_HMR_HOST/VITE_HMR_PORT/VITE_HMR_CLIENT_PORT`（见 frontend/vite.config.js）。

常见 502 排障（你浏览器里看到 `/src/App.vue` 或 `/api/tiles/*` 502）

- 先确认 502 是不是来自 Vite：
  - 正常命中 Vite 时，响应头会带 `X-OneEarth-Upstream: vite-dev`。
  - 如果没有该响应头，通常说明你打到的是“外层 nginx/反代/端口占用者”在返回 502，而不是本项目的 Vite。
- 若 `/api/tiles/*` 频繁报错：优先检查 backend 容器是否在运行（`make docker-dev-ps` / `make docker-dev-logs`），以及是否被外层反代正确转发到 8404（让前端通过同源 `/api` 代理到 8405）。

### Docker Prod 一键跑通（8406/8407）

适用于“静态前端 + 同源 /api 反代”的更接近生产的形态。

```bash
make docker-prod-up
make docker-prod-check
```

如果 `8406/8407` 已经在运行并且你想“更新到当前工作区最新源码构建的 dist”，用：

```bash
make docker-prod-update
make docker-prod-check
```

说明（常见误解）：

- `8406/8407` 的 Docker Prod 是“运行形态接近生产”（nginx 静态 dist + 同源 `/api` 反代），但它**仍然会在启动时从当前工作区源码 build 镜像**。
- 因此如果你在 `8406` 看到“dev 最新 UI/功能”，这不是 Vite dev server，而是 nginx 正在服务**用最新源码构建出来的 dist**（属于预期行为）。
- 如果你希望 `8406` 固定在某个版本，请先 `git checkout <tag|sha>` 再执行 `make docker-prod-up`（或改用真生产 8506/8507 的 release 发布模型）。

补充（避免端口混淆）：

- 本分支的 Prod 验收命令 `make docker-prod-check` 会以 `http://127.0.0.1:8406` 为准。
- 如你的机器/环境里存在 `8506/8507` 的 nginx/systemd 配置文件（例如 deploy 目录下的示例），它们不代表本分支的默认/推荐生产方式。

- Dev 前端：`http://127.0.0.1:8404`
- Dev 后端：`http://127.0.0.1:8405`（Swagger：`/docs`）
- Prod 前端：`http://127.0.0.1:8406`
- Prod 后端：`http://127.0.0.1:8407`（Swagger：`/docs`）

页面入口：

- Zero2x Landing：`/`（默认首页）
- 第二幕叙事：`/act2`
- 工作台：`/workbench`
- AlphaEarth Cesium Demo（验证系统）：`/demo`

### 访问密码（前端轻量闸门，默认仅用于 `/demo`）

为避免公开访问导致大量瓦片/分析请求影响速度，前端增加了一个“简单密码闸门”（UI 级别，并非强安全认证）：

- 当 `VITE_ACCESS_PASSWORD` 为空/未设置时：不启用密码管控（直接放行）
- 当 `VITE_ACCESS_PASSWORD` 为非空字符串时：启用密码管控（输入该密码才进入）
- 通过后会记住本机浏览器状态（localStorage）
- 注意：Vite 的 `VITE_*` 变量在构建时注入；生产环境修改该值需要重新构建前端产物

### 环境要求

- 后端：Python 3.11+（本仓库已在 `.venv` 跑通）
- 前端：Node.js 18+ / npm 9+
- GEE：已授权的 Google Earth Engine 账户（或服务账号）

### 0) 配置环境变量

推荐使用 `.env`：

```bash
cd cesium_app_v6
cp .env.example .env
# 或使用交互脚本
./setup_env.sh
```

### 1) 运行测试（推荐）

本仓库的 pytest 默认走“快速单元测试”路径（会 stub 掉 `ee`/LLM 等重依赖；集成诊断需显式开启）。

```bash
make test-fast         # 快速全量（默认推荐）
make test-contract     # PNG/JPG/HTTP 契约（瓦片透明度/499 等）
make test-integration  # 真实 EE + 本机后端诊断（需已认证/后端可用）
```

最少需要：

```bash
GEE_USER_PATH=users/your_username/aef_demo
```

LLM（可选）：

```bash
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=...
LLM_MODEL=qwen-plus
```

### 2) 启动后端（8405）

```bash
cd cesium_app_v6
./run_backend.sh
```

后端：`http://127.0.0.1:8405`（Swagger：`/docs`）

### 3) 启动前端（8404）

```bash
cd cesium_app_v6
./run_frontend.sh
```

前端：`http://127.0.0.1:8404`

## 🗺️ 地图与底图配置（常用）

### 2D 底图选择

在 `.env` 设置：

- `VITE_BASEMAP=google_xyz`：Google XYZ 卫星底图（测试/对比用途）
- `VITE_BASEMAP=google_official`：Google Map Tiles API（官方 2D，会话模式）
- `VITE_BASEMAP=osm`：OSM 底图（可配合后端同源代理）
- `VITE_BASEMAP=grid`：本地网格底图（兜底）

Google XYZ（测试模式）常用：

- `VITE_GOOGLE_XYZ_ENABLE=1`
- `VITE_GOOGLE_XYZ_LYRS=s`（卫星）

### Photorealistic 3D Tiles（Cesium Ion）

- `VITE_CESIUM_TOKEN=...`
- `VITE_ION_PHOTOREALISTIC_ASSET_ID=2275207`（示例）
- `VITE_ION_PROXY=1`（可选：通过后端同源代理 Ion API/Assets）

为避免“远景外太空视角根瓦片粗糙马赛克”的观感，默认开启相机高度 LOD：

- `VITE_PHOTOREALISTIC_VISIBILITY_THRESHOLD_M=2000000`（默认 2000km；高于阈值自动隐藏 tileset）

当 AI 业务图层激活时，默认优先保证业务可读性（遮挡 3D tiles）：

- `VITE_PHOTOREALISTIC_AI_OCCLUSION=hide`（默认）
- `VITE_PHOTOREALISTIC_AI_OCCLUSION=dim`（半透明）
- `VITE_PHOTOREALISTIC_AI_OCCLUSION=none`（从不遮挡）

## 🧪 测试（TDD）

### 后端：pytest

```bash
cd cesium_app_v6
pytest -q
```

### 前端：vitest

```bash
cd cesium_app_v6/frontend
npm test
```

说明：部分 GEE 相关用例在未配置真实凭据时会 skip，这是预期行为。

## ✅ 可验收的“发布门禁”（建议保持不退化）

- Dev 环境验收：`make docker-dev-check`
- Prod 环境验收：`make docker-prod-check`

这两条命令分别覆盖：端口契约、`/health` 可用、同源 `/api` 反代可用、以及 Zero2x 静态资源（海报/素材）在 Vite/nginx 下可被正确返回。

## 🧩 核心能力速览

### 六章主案例（Missions）

在 `backend/config.py` 注册：

- ch1 余杭：`ch1_yuhang_faceid`（欧氏距离）
- ch2 毛乌素：`ch2_maowusu_shield`（余弦相似度）
- ch3 周口：`ch3_zhoukou_pulse`（特定维度反演）
- ch4 亚马逊：`ch4_amazon_zeroshot`（零样本聚类）
- ch5 盐城：`ch5_coastline_audit`（海岸线红线审计 / 半监督聚类）
- ch6 鄱阳湖：`ch6_water_pulse`（水网脉动监测 / 维差分）

### CH5 V8.1 导出（GEE Asset）

CH5 的随机森林分类器由导出脚本提交到 Earth Engine Tasks，然后由后端通过 `ee.Classifier.load(assetId)` 加载。

```bash
# 1) 配置资产路径（二选一）
export CH5_RF_ASSET_ID=users/<your_username>/aef_demo/classifiers/ch5_coastline_rf_v1
# 或者：export GEE_USER_PATH=users/<your_username>/aef_demo

# 2) 检查资产是否存在
python backend/ch5_rf_export.py --check

# 3) 不存在则提交导出任务（不等待完成）
python backend/ch5_rf_export.py --ensure
```

- GEE Tasks 描述名：`Export_Coastline_RF_V8_1`
- 常用可调参数（环境变量）：
  - `CH5_RF_POINTS_PER_CLASS`（默认 3000）
  - `CH5_RF_TREES`（默认 60）
  - `CH5_RF_MIN_LEAF_POP`（默认 10）
  - `CH5_RF_BAG_FRACTION`（默认 0.6）
  - `CH5_RF_SAMPLE_SCALE`（默认 30）
  - `CH5_RF_SEED`（默认 42）


### 智能体输出（LLM 可选）

- `/api/report`：汇报口径简报（模板/LLM，失败回退模板）
- `/api/analyze`：结构化分析控制台（模板/LLM，失败回退模板）

### 性能策略（降低 GEE 延迟）

- 后端按 `mode_id` 使用不同 viewport buffer（`Settings.viewport_buffer_m_by_mode`）
- 前端通过预热（silent prefetch）降低首次点击等待

### 调试辅助：实时中心点坐标

- 前端左下角显示 `CENTER: lat, lon`
- 数值来源：Cesium 屏幕中心点 `camera.pickEllipsoid()`（拖动/缩放实时更新）

## 📖 后端 API（常用）

```text
GET  /health
GET  /api/locations
GET  /api/modes
GET  /api/missions
GET  /api/layers?mode=...&location=...
POST /api/stats
POST /api/report
POST /api/analyze
POST /api/cache/export
```

## 🧭 下一步开发建议（面向迭代）

- 增加前端 E2E：覆盖“点击 Mission → 飞行 → 图层加载 → 控制台输出”
- 将 Debug HUD 扩展为可开关/可复制（显示 zoom/height、当前 mode、缓存命中等）
- 做一个“将当前中心点写回配置”的开发工具（减少手工改经纬度的循环）
- 依赖治理：`npm audit` 当前存在中等风险项，可择机处理

---

项目状态：✅ 可演示 / 可持续迭代（V6.6 主线已对齐，测试体系已接入）

最后更新：2026-03-03
