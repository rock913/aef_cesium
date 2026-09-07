# AlphaEarth CH9 古建筑天地一体预防性保护 · 技术报告

> 编制时间：2026-09-07 · 状态：**演示沙箱轨已落地并部署**
> 关联文档：`AlphaEarth_CH9_古建筑天地一体预防性保护_PRD.md`（产品需求）· `ROADMAP.md`（进度）
> 提交：`a6e9c17`（核心叙事+单体档案）→ `a85f5b5`（真实开放数据接入）

---

## 一、概述

CH9（古建筑天地一体预防性保护数字孪生）将同一套「天地一体」链路对准中国 30.8 万处古建筑，回答 CH8 未回答的问题——**把地下形变（InSAR）与地上风载（气象）两条独立物理链锚定到同一栋建筑，得出可下发的处置结论**。

本报告记录当前**已落地**的技术路线、实现细节、数据真实性分级与验证结果。核心设计约束是 **demo 可用性优先 + 诚实边界**：凡无法真实取得的数据一律走「确定性仿真 + 明确标注」，凡真实可用的物料（FEA 云图、病害标注、Wikidata/OSM 开放数据）一律直接接入。

---

## 二、当前实现状态一览

| 模块 | 状态 | 说明 |
|------|:--:|------|
| 配置注册 | ✅ | 3 location / 4 mode / 3 mission / viewport buffer |
| 4 个图层（GEE 实时仿真） | ✅ | deformation / wind_risk / aef_discovery / change |
| 单体五层档案 | ✅ | `/api/heritage/building/{id}`，越城 6 / 卢宅 2 / 平遥 3 |
| 风载研判 | ✅ | `/api/heritage/wind_assessment`（`review.required=true`） |
| 真实开放数据（L1/L2/本地） | ✅ | Wikidata 世界遗产 3643 / 国保 5678 / OSM 本地 33 |
| 前端五层档案面板 | ✅ | `HeritageArchivePanel.vue`（FEA 云图 + 病害 SVG 叠加） |
| 前端点云渲染 | ✅ | `EntityCluster` LOD 聚合，三色分级 |
| 数据物料同源访问 | ✅ | `/api/heritage/assets/{filename}`（中文文件名 URL 编码） |
| 自动化测试 | ✅ | 后端 232 passed / CH9 25 / 前端 missionBrief+missionDeck 19 |

---

## 三、技术架构与数据流

```
┌─────────────────────────────────────────────────────────────────────┐
│  前端 Vue3 + CesiumJS（Demo /app → nginx 7702/8406）                  │
│  App.vue ── mission 卡 → lockMission → flyTo → runAgenticWorkflow     │
│    ├─ loadAILayer(GEE 瓦片)     ← /api/layers (ch9_heritage_*)         │
│    ├─ loadHeritageBuildings     ← /api/heritage/buildings/{loc}        │
│    ├─ loadHeritagePointCloud    ← /api/heritage/points (L1/L2/local)   │
│    ├─ HeritageArchivePanel      ← /api/heritage/building/{id}（点击）  │
│    └─ 🌍 全球遗产 toggle        ← /api/heritage/points?scope=global    │
└─────────────────────────────────────────────────────────────────────┘
                                  │ HTTP REST（同源代理 /api/*）
┌─────────────────────────────────────────────────────────────────────┐
│  后端 FastAPI（8405/8407）                                            │
│  main.py ── 路由层                                                     │
│    ├─ /api/layers         → gee_service.get_layer_logic + smart_load  │
│    ├─ /api/heritage/*     → heritage_catalog（纯 Python，无 GEE）      │
│    └─ /api/heritage/assets→ FileResponse 直连 data/ 物料                │
│  heritage_catalog.py ── 确定性五层档案 + 真实点位加载器                │
│  gee_service.py ── 4 个 CH9 确定性仿真分支（pixelLonLat 高斯场）        │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────────┐
                    ▼             ▼                 ▼
               GEE（瓦片）    data/ 物料          data/ch9_heritage_points.json
              （仿真场经GEE渲染）(FEA云图/病害标注)   （Wikidata+OSM 离线缓存）
```

**关键架构决策：**
1. **前后端仅 HTTP REST**（项目宪法），无 Python import。
2. **单体档案/风载/点位走纯 Python**，不依赖 GEE、不依赖现场网络——这是 demo 稳健性的底座。
3. **图层渲染走 GEE 实时仿真**（沿用 CH8 `pixelLonLat` 范式），GEE 若 503 则球面图层降级（L3 降级预案）。

---

## 四、数据真实性分级（诚实边界）

| 模块 | 落地方式 | 真实性 | 角标 |
|------|----------|--------|------|
| 五层档案结构 | 接口契约即海报六行档案 | ✅ 真实 | — |
| FEA 风载荷云图 | `data/FEA云图_*.png`（东南大学预计算） | ✅ 真实物料 | `东南大学 · 风致响应知识库（预计算）` |
| 病害标注 | `data/072500002AAaa.jpg+json`（木构件开裂多边形） | ✅ 真实物料 | `YOLO + 文润VLM` |
| L1 世界遗产 | Wikidata `P1435=Q9259` 3643 处 | ✅ 真实 | `Wikidata` |
| L2 国保 | Wikidata `P1435=Q1188574` 5678 处 | ✅ 真实 | `Wikidata` |
| 本地 OSM | Overpass `historic/heritage/temple` 33 处 | ✅ 真实 | `OSM` |
| InSAR 形变五指标 | 确定性高斯仿真（越城多台门中心，-12~+1.5 mm/yr） | ⚠️ 仿真 | `demo_sandbox` |
| 风载薄弱点/累计概率 | 确定性查表（`heritage_catalog` 内置映射） | ⚠️ 仿真 | `demo_sandbox` |
| AEF 跨省候选 | 确定性「古建概率」簇场 | ⚠️ 仿真 | `demo_sandbox` |
| 球面图层 | GEE `pixelLonLat` 高斯场 | ⚠️ 仿真场 | `LOS 相对形变` |

**统一口径（对齐 PRD §11.1）：** 形变标注 `LOS 向相对形变`；输出为「相对风险排序」而非「结构安全鉴定结论」；所有仿真数据带 `data_track: "demo_sandbox"` 角标。

---

## 五、后端实现细节

### 5.1 配置注册（`backend/config.py`）

| 类型 | 键 | 值 |
|------|-----|-----|
| location | `dongyang_luzhai` | `[29.2832, 120.2410, 16]` |
| location | `shaoxing_yuecheng` | `[30.0023, 120.5810, 14]` |
| location | `shanxi_pingyao` | `[37.2010, 112.1750, 13]` |
| mode | `ch9_heritage_deformation` | 古建单体形变体检 (SBAS-InSAR + 五指标归因) |
| mode | `ch9_heritage_wind_risk` | 古建风载荷风险研判 (工况知识库 + 累计概率) |
| mode | `ch9_heritage_aef_discovery` | 古建聚落语义筛查 (AEF 零微调迁移) |
| mode | `ch9_heritage_change` | 古建周边年际变化检测 (AEF 语义差分) |
| mission | 卢宅风险 / 越城体检 / 跨省发现 | chapter=CH9 |

viewport buffer：deformation 60km / wind_risk 30km / aef_discovery 90km / change 90km。

### 5.2 GEE 仿真分支（`backend/gee_service.py`）

4 个 CH9 分支均置于 CH8 分支**之前**，规避「形变/insar」关键词误命中（`ch9_heritage_deformation` 字符串同时含「形变」与「SBAS-InSAR」）。

- **deformation**：越城 6 个台门沉降中心高斯叠加（`v = Σ amp·exp(-k·dist)`），`coherence=0.85`，`|v|>3 mm/yr` 掩膜，窄量程 `-20~+6`，色带 `["B03A2E","C85F45","C89A3C","5DAE8B","2E9CB8"]`。
- **wind_risk**：卢宅 3 中心高斯 + 东风方向性分量（`+0.06·Δlon` clamp），`>0.35` 掩膜，色带红橙黄。
- **aef_discovery**：平遥 5 簇「古建概率」场，`>0.72` 掩膜，色带褐→金。
- **change**：越城 3 热点语义差分场，`>0.25` 掩膜，色带青→红。

所有分支 `format:"png"` 保持透明，`get_mode_vis_and_suffix` 同步返回一致 `(vis, suffix)`。

### 5.3 单体目录（`backend/heritage_catalog.py`，纯 Python）

- `BUILDINGS`：越城 6（恒济台门 `1/280` 旗舰 / 鲁迅故里 / 八字桥 / 戒珠寺 / 仓桥直街 / 王阳明故居）、卢宅 2（卢宅建筑群 / 肃雍堂）、平遥 3 候选。
- 每栋含 §8.2 五层档案：`L1_satellite` / `L2_semantic` / `L3_deformation`（五指标）/ `L4_defect` / `L5_structural` + `fusion`（耦合风险 + 证据链 + 建议）。
- `heritage_points(scope, location)`：加载真实点位缓存（路径回退 `/app/data` → `/mnt/...` → `data/`）。
- `wind_assessment(building_ids, typhoon)`：确定性查表（`basic_type_id → weak_components/cumulative_probability/checklist/measures`），`review.required=true` 恒真。

### 5.4 路由（`backend/main.py`）

| 端点 | 方法 | 说明 | GEE |
|------|------|------|:--:|
| `/api/heritage/buildings/{location}` | GET | 单体清单摘要 | 否 |
| `/api/heritage/building/{building_id}` | GET | 五层档案全量 | 否 |
| `/api/heritage/wind_assessment` | POST | 风载研判 | 否 |
| `/api/heritage/assets/{filename}` | GET | 物料直连（防路径穿越） | 否 |
| `/api/heritage/points` | GET | `scope=global\|china\|local` | 否 |
| `/api/layers?mode=ch9_heritage_*` | GET | 图层瓦片（`render_hints.ai_opacity=0.88`） | 是 |

---

## 六、前端实现细节

| 文件 | 改动 |
|------|------|
| `utils/missionBrief.js` | 4 个 CH9 简报分支（operator/brief/mechanism/legends/insights/technical） |
| `utils/missionDeck.js` | 新增 `heritage` 分类（🏯 文保古建） |
| `services/api.js` | `getHeritageBuildings` / `getHeritageBuilding` / `windAssessment` / `getHeritagePoints` |
| `components/HeritageArchivePanel.vue` | 五层档案卡：L1-L5 + fusion 证据链 + SVG 病害多边形叠加 + 数据角标 + 声明 |
| `components/CesiumViewer.vue` | `loadHeritageBuildings`（🏯 语义色标记）、`loadHeritagePointCloud`（EntityCluster LOD） |
| `App.vue` | CH9 mission → 加载单体+点云；点击就近建筑 → 档案面板；🌍 全球遗产 toggle |

**点云 LOD 方案（PRD §9.1 性能红线落地）：**
- 独立 `Cesium.CustomDataSource` + `clustering`（`pixelRange=38`，`minimumClusterSize=3`），万级点位（5678+3643）不卡顿。
- 三色分级：世界遗产=金 / 国保=橙红 / 其他（含 temple/shrine/pagoda）=青。

**交互流：**
1. 锁定 CH9 mission → `flyTo` → `runAgenticWorkflow`（图层）+ `fetchHeritageBuildings`（单体）+ `fetchHeritagePoints('china'|'local')`（点云）。
2. `onMapClick`（CH9）→ 就近单体 → `/api/heritage/building/{id}` → 档案面板。
3. `abortAndOrbit` / 切换 mission → 清理单体实体 + 点云 + 档案。

---

## 七、真实数据管线（路线一 · 零审批）

`scripts/ch9_fetch_heritage_points.py`（stdlib `urllib`，无第三方依赖）：

```
Wikidata SPARQL ──┬─ 全国重点文保单位 (P1435=Q1188574) → 5678 → china
                  └─ 世界遗产 (P1435=Q9259)              → 3643 → global
OSM Overpass    ─── historic/heritage/temple（3 靶场 bbox）→ 33  → local
                            ↓
              data/ch9_heritage_points.json（离线缓存，1.4MB）
```

- **离线设计**：缓存随代码入库，demo 现场不依赖网络（Wikidata/Overpass 仅脚本重跑时访问）。
- **诚实口径**：开放数据覆盖的是名录内部分，远低于四普 30.8 万总量；这正是「开放数据对政府名录的覆盖率」叙事数字来源。

---

## 八、验证与测试

| 项 | 结果 |
|---|---|
| 后端 pytest | **232 passed** / 36 skipped |
| CH9 后端测试 | `tests/test_ch9_heritage.py` **25 passed**（config 注册 / vis+suffix / 碰撞规避 / /api 契约 / heritage 5 端点 / assets 中文+防穿越 / points 3 scope+非法） |
| 前端 vitest | missionBrief **10** + missionDeck **9** = 19 passed |
| 前端 vite build | ✅ 编译通过（50s） |
| 生产部署 | 7702/8406 前端 + 8405 后端，容器 healthy |

**运行态契约（实测）：**
```
/api/missions                          → 3 张 CH9 卡
/api/heritage/building/SX-YC-ZP-08     → 恒济台门 · 1/280 · unstable · Ⅲ
/api/heritage/wind_assessment          → review.required=true · Ⅲ · 屋脊/檐口/翼角/山墙
/api/heritage/assets/FEA云图_全景.png   → 200 image/png
/api/heritage/points?scope=china       → 5678 · real_open_data
/api/heritage/points?scope=global      → 3643
/api/layers?mode=ch9_heritage_deformation → tile_url + ai_opacity 0.88
```

---

## 九、已知限制与后续路线

### 已落地
- 核心叙事 + 单体五层档案（L4/L5 真物料）+ L1/L2/本地真实点位（Wikidata/OSM）。

### 未落地（明确后置）
| 项 | 依赖 | 优先级 |
|----|------|:--:|
| L3 三体过境卫星轨迹 | TLE + 轨道计算 | P2 |
| 四普/三普政府名录全量 30.8 万点位 | 省文物局正式申请 | P2 |
| 真实绍兴 InSAR（LiCSAR 取数 / HPC） | 数据检索 + 算力 | P3 |
| 风载荷知识库真实接口 | 中试基地 × 东南大学 | P3 |
| CMA 台风预报 / 最佳路径 API | `tcdata.typhoon.org.cn` | P3 |
| 双物理耦合（材料劣化参数注入） | 病害数据反哺 | P4 |

### 方法论风险（已在 PRD §13 列明）
- GRD≠SLC：GEE 快速调用的 GRD 不能做毫米级形变测量（发现层 ≠ 测量层）。
- 单体相干点不足 → 显式 `data_insufficient`，不外推。
- 阈值（0.75 相干 / ±3 mm/yr / 1/300 角变形）为工程经验值，报告需写清。
- 数据空窗（2021-12~2024-12 单星期）导致历史时序不确定度上升。

---

## 十、结论

CH9 以「演示沙箱轨」完成了一个**可现场演示、诚实标注真实/仿真边界**的纵向切片：三张 mission 卡驱动球面图层 + 指挥官简报 + 单体五层档案，真实物料（FEA 云图、病害标注）与真实开放数据（Wikidata 国保 5678 / 世界遗产 3643 / OSM 本地）直接落地，所有无法真实取得的部分以确定性仿真兜底并明确角标。后端 232 测试、前端 19 测试、生产 7702 端口全链路验证通过。
