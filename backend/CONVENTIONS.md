# backend/CONVENTIONS.md — 后端地方法规

> 全局宪法见 `AI_RULES.md` 和 `CLAUDE.md`
> 功能规格见 `docs/` 目录

## 技术栈

- Python 3.11+（Docker 镜像使用 python:3.11-slim）
- FastAPI ≤ 0.68.0 + Pydantic < 2.0
- uvicorn ≤ 0.15.0 (dev: --reload, prod: 1 worker)
- earthengine-api (Google Earth Engine)
- httpx (异步 HTTP 客户端)
- DashScope (Qwen) LLM via OpenAI-compatible API

## 架构红线 (Hard Boundaries)

1. **TDD 强制**: 每个 GEE-dependent 的端点必须有对应测试
2. **GEE Stub 纪律**: 单元测试使用 `tests/conftest.py` 的模块级 stubs (`PYTEST_STUB_EE=1`)
3. **GEE Init Guard**: 所有 GEE-dependent 端点通过 `_require_gee()` 守卫，未就绪返回 503 + Retry-After
4. **Tile Proxy 安全**: 所有 tile 端点仅代理白名单上游，避免 SSRF
5. **Pydantic v1 兼容**: 严禁使用 Pydantic v2 语法（`field_validator`, `model_config` 等）

## 模块结构

```
backend/
├── main.py              # FastAPI app, 路由, GEE init guard, tile proxy
├── config.py            # Pydantic Settings: locations, modes, missions
├── gee_service.py       # GEE 初始化, get_tile_url, smart_load, zonal stats
├── llm_service.py       # LLM 客户端: report generation, agent analysis
├── v7_copilot.py        # v7 Copilot tool-calling stub
├── astro_gis_catalog.py # SIMBAD/VizieR astronomy catalog queries
├── Dockerfile.dev       # 开发容器 (bind mount, reload)
└── Dockerfile.prod      # 生产容器 (copy, no reload)
```

## 测试模式

### 单元测试（stub 模式）
```bash
PYTEST_STUB_EE=1 python3 -m pytest tests/ -v
```
- GEE 和 LLM 模块在 import 时被 `tests/conftest.py` stub
- 测试不依赖网络，快速且确定

### 集成测试（真实 GEE）
```bash
RUN_INTEGRATION_TESTS=1 PYTEST_STUB_EE=0 python3 -m pytest tests/test_gee_tile_diagnostics.py -v
```
- 需要有效的 GEE 凭据和网络连接
- 仅在 CI 或手动验证时运行

### 契约测试
```bash
make test-contract  # tests/test_tile_png_contract.py
```

## API 设计约定

- 查询参数使用 Pydantic 模型验证（`mode`, `location`, `z`, `x`, `y` 等）
- 错误响应: `{"error": true, "message": "...", "hint": "..."}`
- 503 响应包含 `Retry-After` 头（GEE 未就绪时）
- Tile 代理响应需重写 URL 为 same-origin

## GEE 初始化流程

1. 读取 `EE_SERVICE_ACCOUNT` + `EE_PRIVATE_KEY_JSON_B64` 环境变量
2. 解码 base64 私钥 → 临时 JSON 文件
3. `ee.ServiceAccountCredentials()` + `ee.Initialize(credentials)`
4. 成功: `_gee_initialized = True`
5. 失败: `_gee_last_error` 记录错误，所有 GEE 端点返回 503

## 命名规范

- 函数: `snake_case`（公开）、`_snake_case`（模块私有）
- Pydantic 模型: `PascalCase`
- API 路径: `kebab-case` 或 `camelCase`
- 环境变量: `UPPER_SNAKE_CASE`

## 禁止行为

- ❌ 在 `main.py` 的 route handler 中写业务逻辑（应委托到 service 层）
- ❌ 硬编码文件路径（使用 `config.py` 的 Settings）
- ❌ 跳过 `_require_gee()` 守卫直接调用 GEE
- ❌ 在 tile proxy 中代理非白名单上游
- ❌ push main 分支（使用 SLAIB: branch → PR → Squash Merge）
