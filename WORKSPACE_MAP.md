# WORKSPACE_MAP — AlphaEarth Cesium 项目拓扑

## 项目概述

AlphaEarth Cesium (Zero2x / OneEarth) — 基于 CesiumJS 的 3D 地球空间智能平台，提供 AI 驱动遥感分析、天文可视化、AI-Native 工作台。

## 子项目/模块

| 模块 | 角色 | 路径 |
|------|------|------|
| **frontend** | Vue 3 + Vite + CesiumJS + Three.js 前端 | `frontend/` |
| **backend** | FastAPI + Google Earth Engine + LLM 后端 | `backend/` |
| **tests** | pytest 后端测试套件 | `tests/` |
| **compose** | Docker Compose 编排 (dev/prod/canary) | `compose/` |
| **deploy** | nginx 配置、systemd 服务、部署脚本 | `deploy/` |

## 端口架构

| 模式 | 前端 | 后端 | 技术 |
|------|------|------|------|
| Docker Dev | **8404** | **8405** | Vite dev server + uvicorn --reload |
| Docker Prod | **8406** | **8407** | nginx 静态 + uvicorn |
| Canary | **8508** | **8509** | nginx 静态 + uvicorn |
| Legacy systemd | **8506** | **8507** | nginx + systemd |

## 通信方式

```
Browser → Vite Dev Server (8404) → proxy /api/* → Backend (8405)
Browser → Nginx (8406) → static dist OR proxy /api/* → Backend (8407)
```

前后端通过 HTTP REST API 通信，无跨系统 Python import。

## 关键入口

| 入口 | 文件 |
|------|------|
| 前端路由分发 | `frontend/src/main.js` |
| FastAPI 应用 | `backend/main.py` |
| GEE 服务层 | `backend/gee_service.py` |
| LLM 服务层 | `backend/llm_service.py` |
| 前端配置 | `frontend/vite.config.js` |
| 环境变量 | `.env` (基于 `.env.example`) |

## 依赖隔离

- 前后端通过 HTTP 通信，不存在 Python import 依赖
- 前端测试独立于后端（vitest vs pytest）
- Docker 容器内网络通信通过 Compose DNS

## 环境变量

- `.env` — 运行时密钥和配置（不提交到 Git）
- `.env.example` — 所有变量文档化模板
- `.env.dev` / `.env.prod` / `.env.canary` — 环境特定覆盖（可选）
