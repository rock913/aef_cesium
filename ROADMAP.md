# ROADMAP — AlphaEarth Cesium 开发进度

> 最后更新: 2026-06-21

## 当前 Sprint: CH7 山洪与滑坡灾害极速定损 Demo ✅

| 任务 | 状态 | 描述 |
|------|:--:|------|
| ROADMAP.md 创建 | ✅ | 本文件 |
| `backend/config.py` 添加 locations/modes/missions | ✅ | beijing_2023, guangdong_2024, ch7_disaster_warning, 2 mission cards |
| `backend/gee_service.py` 添加 GEE 算子 | ✅ | AEF Diff × DEM Topology: 欧氏距离 + SRTM 坡度 + 滑坡/山洪诊断 |
| `backend/main.py` 添加 render_hints | ✅ | ch7_disaster_warning opacity=0.88 |
| `frontend/missionBrief.js` 添加指挥官面板 | ✅ | 双色图例 (青蓝=山洪, 鲜红=滑坡) + 技术分析 |
| Backend 测试 `test_ch7_disaster_warning.py` | ✅ | 9 tests: mode/location/mission 注册 + API 端点 + vis/suffix |
| 部署验证 | ✅ | /api/layers 200, /api/missions 含 ch7 卡片, /api/modes 已注册 |

### 验证结果

```
/api/modes             → ch7_disaster_warning ✅
/api/missions          → ch7_beijing + ch7_guangdong ✅
/api/layers (beijing)  → HTTP 200 ✅
/api/layers (guangdong)→ HTTP 200 ✅
pytest (9 tests)       → 9 passed ✅
```

### CH7 算法摘要

| 参数 | 值 |
|------|-----|
| 算法 | AEF Diff × DEM Topology |
| 滑坡检测 | slope > 12° + Euclidean Distance > 0.20 + delta_A01 < -0.15 |
| 山洪检测 | slope ≤ 12° + delta_A02 > 0.12 |
| DEM | USGS SRTMGL1_003 (30m) |
| 数据源 | GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL (2023 vs 2024) |
| 输出 | 青蓝(#00F5FF)=山洪, 鲜红(#FF3300)=滑坡 |

### 已知限制

- 时间窗口使用年复合 (ANNUAL) 而非月度精度，V2.0 的 per-location event windows 待 `get_layer_logic()` 签名升级后启用
- 位置坐标使用通用经纬度，未精确匹配历史灾害中心

### 演示入口

浏览器打开 `http://127.0.0.1:8404/demo` → Demo 页面底部可见两个新增卡片：

| 卡片 | 地点 | 相机 |
|------|------|------|
| 灾害定损 (北方) | 北京·门头沟/房山 | 39.95°N 115.90°E, 30km |
| 灾害定损 (南方) | 广东·梅州/粤北 | 24.30°N 116.10°E, 30km |

---

## 已完成

| 里程碑 | 日期 | 内容 |
|------|------|------|
| CH7 灾害极速定损 Demo | 2026-06-21 | config + GEE 算子 + 前端 + 9 tests, 端到端验证通过 |
| Docker 代理配置 | 2026-06-21 | network_mode: host, 127.0.0.1:7890 代理可达 |
| Vite 缓存修复 | 2026-06-21 | Dockerfile.dev --force 标志, 504 Outdated Optimize Dep |
| GEE 初始化修复 | 2026-06-20 | TimeoutError handler cleanup |
| ThreeTwin.vue 修复 | 2026-06-20 | 缺失 `}` 导致 SFC 编译 500 |
| TDD 基础设施 | 2026-06-20 | vitest, ESLint/Prettier/Ruff, pytest-cov, Makefile lint |
| MAP 规范引导 | 2026-06-20 | AI_RULES.md, CLAUDE.md, WORKSPACE_MAP.md, CONVENTIONS.md |

## 下一步建议

| 任务 | 优先级 | 描述 |
|------|:--:|------|
| Per-location event windows | P1 | 升级 `get_layer_logic()` 签名接收 location 参数，启用 V2.0 事件驱动时间窗口 |
| 更高时间分辨率 | P2 | 使用 MONTHLY 或 DAILY embedding collection 替代 ANNUAL，实现月级灾害检测 |
| DEM 升级 | P2 | 迁移到 Copernicus DEM GLO30（需处理 ImageCollection → Image 转换） |
| 前端交互优化 | P3 | 灾害热力图透明度控制、滑坡/山洪切换开关 |
| 灾害事件扩展 | P3 | 添加 henan_2024、汶川、雅安等更多历史灾害事件 |
