# Alpha Earth Demo 场景验证系统 (V6.6)

Alpha Earth Demo（AEF）场景验证系统：前端 Vue3 + CesiumJS（3D 数字地球），后端 FastAPI + Google Earth Engine（AEF 表征 / 统计 / 瓦片代理）。

本目录为 `cesium_app_v6`，端口与主案例已固化，适合“快速了解现状 → 继续开发”。

## 📌 当前状态（2026-02-27）

- Dev 研发环境已 Docker 化并固化端口：前端 8504 / 后端 8505（推荐使用 `make docker-dev-up`）。
- 一键验收门禁：`make docker-dev-check`（smoke + pytest + vitest + build）。
- 后端提供可观测/排障入口：`/health`、`/api/debug/version`、以及若干瓦片代理诊断接口。
- 前端地图：支持 2D 底图切换（含 Google XYZ 测试模式/Google 官方会话模式）+ Cesium Ion Photorealistic 3D Tiles。
- 视觉一致性：Photorealistic 3D Tiles 支持“按相机高度 LOD 自动显隐”，并支持 AI 图层激活时自动遮挡（hide/dim）。

功能接口：
- `/api/report`：监测简报（模板/LLM）
- `/api/analyze`：智能体分析控制台（模板/LLM）
- 前端调试：地图左下角实时显示“屏幕中心经纬度 CENTER: lat, lon”（用于校准飞行/定位）

- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 常用命令与端口速查
- [docs/架构升级与敏捷开发.md](docs/架构升级与敏捷开发.md) - 基于仓库真实现状的工程化/Dev Docker/TDD 指南
- [docs/oneearth_v6.md](docs/oneearth_v6.md) - V6 规格与叙事目标（实现对齐基准）
- [docs/oneearth_v6.6.md](docs/oneearth_v6.6.md) - 最新迭代说明（如与 v6 有差异以该文档为准）
- [docs/deploy_github_actions.md](docs/deploy_github_actions.md) - GitHub Actions 持续集成/发布 + 8506/8507 生产部署指南

## 🏗️ 技术架构

```text
Frontend (8504)                 Backend API (8505)                    Google Earth Engine
┌─────────────────────┐         ┌─────────────────────────┐          ┌───────────────────┐

- Runtime deps: `pip install -r backend/requirements.txt`
- Dev/test deps (needed for `make test-fast`): `pip install -r backend/requirements-dev.txt`
│ Vue3 + CesiumJS      │◄──────► │ FastAPI                 │◄────────►│ AEF Dataset        │
│ - Missions/叙事      │  JSON    │ - 图层/瓦片 URL 生成     │   ee API  │ - Embeddings       │
│ - AI Console         │         │ - reduceRegion 统计      │          │ - Sentinel-2 etc.  │
│ - Debug HUD (center) │         │ - 缓存/预热/导出         │          └───────────────────┘
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
│   ├── vite.config.js          # dev server 8504 + /api -> 8505 代理
│   ├── package.json            # npm test (vitest)
│   ├── src/
│   │   ├── App.vue             # Missions 大厅 + AI 控制台 + Debug HUD
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

### 推荐：Docker Dev 一键跑通（8504/8505）

适用于“团队多人协作/避免宿主依赖污染/保证可复现”。

```bash
cd cesium_app_v6
cp .env.example .env

make docker-dev-up
make docker-dev-check
```

启动后：

- 前端：`http://127.0.0.1:8504`
- 后端：`http://127.0.0.1:8505`（Swagger：`/docs`）

### 访问密码（前端轻量闸门）

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

### 1) 启动后端（8505）

```bash
cd cesium_app_v6
./run_backend.sh
```

后端：`http://127.0.0.1:8505`（Swagger：`/docs`）

### 2) 启动前端（8504）

```bash
cd cesium_app_v6
./run_frontend.sh
```

前端：`http://127.0.0.1:8504`

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

最后更新：2026-02-22
