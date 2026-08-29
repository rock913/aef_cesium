# ROADMAP — AlphaEarth Cesium 开发进度

> 最后更新: 2026-08-29

## 已完成 Sprint: CH8 演进深化 —— AEF 语义多模态融合与 3D 建筑单体 InSAR 时序折线图系统 (V3.1 深度融合版) ✅

| 任务 | 状态 | 描述 |
|------|:--:|------|
| 时序位移 API 设计与开发 | ✅ | 新增 `/api/insar/timeseries`，支持查询坐标历史沉降时序 (2020~2024)、速率、形变类型与因果诊断 |
| AEF 语义多模态融合算子 | ✅ | GEE 算子结合 AEF 卫星人造硬化地物特征，剥离非工程变形，计算 Building Risk Index |
| 时序折线图组件开发 | ✅ | 新建 `frontend/src/components/InsarTimeseriesChart.vue`，SVG 矢量渲染 5 年时序沉降曲线与预警红线 |
| Cesium 3D 白模单体点击交互 | ✅ | `CesiumViewer.vue` 增加 `LEFT_CLICK` 实体/网格拾取，提取经纬度并触发时序深度分析 |
| 指挥官面板联动展示 | ✅ | `App.vue` 与 AI 面板集成时序折线图弹窗，展示建筑风险等级 (Safe/Warning/Critical) 与工程建议 |
| 自动化测试套件 (Pytest + Vitest) | ✅ | 后端 `tests/test_insar_timeseries_api.py` (4/4 passed) + 前端 `tests/insarTimeseriesChart.test.js` (7/7 passed) |
| 生产镜像构建与部署验证 | ✅ | Docker 生产热部署成功，203 后端测试与 188 前端测试 100% 通过，7702 端口验证正常 |

### V3.1 验证结果

```
/api/insar/timeseries?lat=22.72&lon=113.53  → HTTP 200 (南沙软土固结沉降, -26.5mm/yr, Critical) ✅
/api/insar/timeseries?lat=23.12&lon=113.32  → HTTP 200 (天河CBD基坑沉降, -21.5mm/yr, Critical) ✅
/api/insar/timeseries?lat=23.45&lon=113.85  → HTTP 200 (地表常规稳定, -0.5mm/yr, Safe) ✅
pytest (203 tests)                         → 203 passed, 36 skipped in 7.29s ✅
vitest (61 test files / 188 tests)         → 188 passed in 2.69s ✅
```

## 已完成 Sprint: 行星级任务包 UI/UX 约束与横向跑道重构 (方案 A) ✅

| 任务 | 状态 | 描述 |
|------|:--:|------|
| 跑道架构重构 | ✅ | 固定限高双行跑道 (`grid-template-rows: repeat(2, minmax(86px, auto))`)，卡片横向平滑滚动 |
| 业务领域分类筛选 | ✅ | 新增主题胶囊标签栏：全部 (10)、🏙️ 城市基建 (3)、🌿 生态环境 (4)、⚠️ 应急防汛 (3) |
| 自然滚轮横滑与微操按键 | ✅ | 滚轮垂直滑动自动映射横向滑轨；新增精致左右导航翻页按键 `[‹] [›]` |
| 跑道呼吸渐变遮罩 | ✅ | 左右边缘动态渐变遮罩 (`mask-left`, `mask-right`)，智能提示可滚动空间 |
| 赛博朋克霓虹细滚动条 | ✅ | 4px 超细青蓝发光滚动条，hover 发光动效 |
| 领域专属色系微观质感 | ✅ | 城市基建 (高亮青蓝 `#00f5ff`)、生态环境 (翡翠苍翠 `#00ff9d`)、应急防汛 (警戒炽橙 `#ff6b4a`) |
| 模块化与自动化测试 | ✅ | 提取 `frontend/src/utils/missionDeck.js`，新增 `tests/missionDeck.test.js` (9/9 通过，全套 181 测试全过) |
| 生产镜像构建与热更新 | ✅ | Vite 静态资源重新打包，Docker 容器热更新完成，7702 端口可实时预览 |

## 已完成 Sprint: CH8 城市广域 InSAR 沉降数字孪生系统 (V3.0 城市安防版) ✅

| 任务 | 状态 | 描述 |
|------|:--:|------|
| PRD 文档建立 | ✅ | `docs/AlphaEarth_V3_InSAR_Subsidence_PRD.md` |
| 离线资产固化脚本 | ✅ | `scripts/ch8_insar_asset_builder.py` (GCS -> GEE Image Asset 构建) |
| `backend/config.py` 配置注册 | ✅ | guangzhou_nansha, guangzhou_tianhe, ch8_insar_subsidence, viewport 60km, 2 mission cards |
| `backend/gee_service.py` 算子逻辑 | ✅ | 挂载 InSAR 时序 Asset，Coherence > 0.75 质量过滤，\|v\| > 5mm/yr 靶向警报 |
| `backend/main.py` 渲染参数配置 | ✅ | ch8_insar_subsidence opacity=0.88 (PNG 带 Alpha 透明通道) |
| `frontend/missionBrief.js` 指挥官面板 | ✅ | 五色沉降速率图例 (红→橙→黄→绿→蓝) + 毫米级沉降洞察 + AEF 语义融合分析 |
| Frontend 测试 `missionBrief.test.js` | ✅ | 9 tests passed (含 CH8 算子与图例断言) |
| Backend 测试 `test_ch8_insar_subsidence.py` | ✅ | 10 tests passed (mode/location/mission 注册 + viewport + stub + /api/layers 契约) |
| 部署验证 | ✅ | /api/modes, /api/missions, /api/locations, /api/layers 响应全部正常 |

### 验证结果

```
/api/modes             → ch8_insar_subsidence ✅
/api/missions          → 填海区沉降 + 核心区沉降 ✅
/api/locations         → guangzhou_nansha + guangzhou_tianhe ✅
/api/layers (nansha)   → HTTP 200 (含 tile_url 与 render_hints) ✅
pytest (10 tests)      → 10 passed in 0.38s ✅
vitest (9 tests)       → 9 passed in 0.22s ✅
```

### CH8 算法摘要

| 参数 | 值 |
|------|-----|
| 算法架构 | Asset-Driven (离线 HPC 重算 + 云端 GEE 缓存挂载) |
| 干涉与时序引擎 | NASA JPL ISCE2 (SBAS 短基线组网) + MintPy (WLS/L1 时序平差) |
| 大气与误差校正 | PyAPS + ECMWF ERA5 对流层物理建模延迟剥离 + DEM 残余误差线性反演 |
| 质量控制 (QC) | Temporal Coherence > 0.75 (剥离水体/植被去相干噪声，锁定高质量 PS 点) |
| 靶向异常判定 | 显著形变 \|velocity\| > 5 mm/yr (严重沉降速率 < -20 mm/yr) |
| 多模态融合 (AEF) | InSAR 物理沉降量 × GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL 人造物特征交集 |
| 可视化方案 | 5 色渐变热力图 (PNG 透明通道，确保 3D 白模建筑透视可见) |

### 演示入口

浏览器打开 `http://127.0.0.1:8404/demo` → Demo 页面任务栏可见两个新增沉降卡片：

| 卡片 | 地点 | 相机参数 | 核心看点 |
|------|------|----------|----------|
| 南沙填海造陆区固结监测 | 广州·南沙区 | 22.70°N 113.55°E, 高度 8000m, 俯仰 4.5s | 广域基建体检：大面积软土压密固结，沉降速率 < -20mm/yr |
| 天河地下空间形变监测 | 广州·天河核心区 | 23.08°N 113.32°E, 高度 5000m, 俯仰 4.0s | 城市生命线：穿透城市峡谷，靶向锁定深基坑与地铁沿线不均匀沉降 |

## 已完成 Sprint: CH7 山洪与滑坡灾害极速定损 Demo ✅

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
