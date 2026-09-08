# AlphaEarth 核心场景 CH9：古建筑天地一体预防性保护数字孪生系统

**产品需求文档 (PRD) · V1.0**

| 项 | 内容 |
|---|---|
| 场景代码 | `CH9` |
| 场景名称 | 古建筑天地一体预防性保护数字孪生 (Heritage Guardian) |
| 编制时间 | 2026-09-07 |
| 架构基线 | 继承 CH8 Asset-Driven 架构与双轨真实性机制 |
| 技术底座 | ESA Sentinel-1 + NASA ISCE2 + Miami MintPy + ECMWF ERA5 + Copernicus GLO-30 + Google AEF + 三体计算星座 0.3m + CMA 智能网格预报 + GEE 瓦片流水线 + Cesium 3D 孪生 |
| 配套物料 | 《三体计算星座 × 古建筑保护 · 数贸会展台海报 v3》三页 |
| 前置依赖 | CH8 已跑通的 SLC→ISCE2→MintPy→GEE Asset→Cesium 全链路 |

---

## 0. 一句话读懂 CH9

CH8 回答的是「**城市在沉降，沉的是哪栋楼**」。
CH9 把同一套天地一体链路，对准中国 **30.8 万处古建筑**——它们绝大多数没有监测设备、没有专职看护、甚至没有精确坐标。

但古建的灾害机理与城市楼宇**不同**，且是**两条互相独立的物理链**：

```
地下的水土  →  软土差异沉降 / 地下水位波动 / 周边施工扰动
              年际尺度 · mm/yr · 由 InSAR 观测          →  基础不均匀沉降 → 木构架变形、墙体开裂

地上的风雨  →  台风风致响应 / 强对流 / 暴雨
              小时尺度 · 48–72h 预警窗 · 由气象预报驱动  →  屋面掀揭、翼角断裂、瓦件坠落
```

CH9 的技术命题就是：**把这两条物理链，锚定到同一栋建筑上，得出一个可下发的处置结论。**

---

## 0.1 本次 Demo 实现口径（2026-09-07 落地 · 演示沙箱轨）

> 本节记录**实际落地**与上文示意代码的差异。§6/§7 中的 `get_layer_logic` 分支与 config 注册为「示意性」写法，引用了尚不存在的 GEE 资产（如 `ch9_heritage_insar_shaoxing_v1`、`ch9_heritage_points_zj_positive`）。Demo 实现改为**「无资产即确定性物理仿真」**，严格对齐 PRD §10 双轨真实性机制。

### 真实 vs 仿真（诚实边界）

| 模块 | 落地方式 | 真实性 |
|---|---|---|
| 五层单体档案结构（§8.2） | 已落地为 `/api/heritage/building/{id}` | ✅ 结构真实，接口契约即海报六行档案 |
| 病害标注物料 | `data/072500002AAaa.jpg + json`（木构件开裂多边形） | ✅ 真实物料，前端 SVG 叠加 |
| 风载荷云图 | `data/FEA云图_全景.png` / `FEA云图_薄弱点标注.png` | ✅ 真实物料（东南大学预计算知识库成果） |
| InSAR 形变五指标 | 确定性高斯仿真场（越城多台门沉降中心，LOS 向，-12~+1.5 mm/yr） | ⚠️ 演示仿真，标注 `data_track: demo_sandbox` |
| 风载薄弱点 / 累计概率 | 确定性查表（`heritage_catalog.py` 内置基本型→薄弱点映射） | ⚠️ 演示仿真（知识库真实、查表键为演示值） |
| AEF 跨省筛查 | 确定性「古建概率」簇场（平遥多簇候选） | ⚠️ 演示仿真（AEF 底座真实、候选概率为演示值） |
| 图层渲染 | GEE 实时仿真（`pixelLonLat` 高斯场 → 透明 PNG 瓦片） | ⚠️ 仿真场，经 GEE 出瓦片 |

### 实际落地的接口

- `GET /api/heritage/buildings/{location}` → 单体清单摘要（id/name/centroid/risk_level）
- `GET /api/heritage/building/{building_id}` → 五层档案全量（含 `disclaimer` 与 `data_track`）
- `POST /api/heritage/wind_assessment` → 风载研判（`review.required=true` 恒为真）
- `GET /api/heritage/assets/{filename}` → 同源提供 `data/` 真实物料（FEA云图/病害照片等）
- `GET /api/layers?mode=ch9_heritage_*` → 四个 CH9 图层（deformation/wind_risk/aef_discovery/change）

### 真实开放数据已接入（路线一 · 零审批）

- **L1 全球分布**：Wikidata 联合国教科文组织世界遗产 **3643 处**（含中文标签与国别）→ `/api/heritage/points?scope=global`
- **L2 中国全景**：Wikidata 全国重点文物保护单位 **5678 处**（`wdt:P1435 wd:Q1188574`）→ `/api/heritage/points?scope=china`
- **本地靶场**：OSM `historic=*` / `heritage=*` / `building=temple|shrine|pagoda`（越城 30 / 东阳 3 / 平遥 0）→ `/api/heritage/points?scope=local&location=...`
- 数据管线：`scripts/ch9_fetch_heritage_points.py`（Wikidata SPARQL + Overpass），产出 `data/ch9_heritage_points.json`（离线缓存，demo 现场零网络依赖）
- 前端：`CesiumViewer.loadHeritagePointCloud`（独立 CustomDataSource + EntityCluster LOD 聚合，万级点位不卡顿；三色分级：世界遗产=金 / 国保=橙红 / 其他=青）

> 诚实口径：开放数据（Wikidata 国保 5678 + OSM）覆盖的是**名录内**部分，远低于四普口径 30.8 万古建总量；这正是「开放数据对政府名录的覆盖率」叙事数字的来源。

### 本次仍未落地（明确后置）

- L3 三体过境卫星轨迹（依赖 TLE + 轨道计算）
- 四普/三普政府名录全量 30.8 万点位（需省文物局正式申请，审批周期不可控）
- 真实风载荷知识库接口、CMA 台风预报 API

### 真实绍兴 InSAR：已获取（2026-09-08 更新）

- **已实测确认**：COMET LiCSAR 公共归档（JASMIN）**不含浙江帧**（track 40/84/170/143 帧 bbox 均覆盖中南美洲与日本）；绍兴真实 Sentinel-1 SLC 由 **升轨 relativeOrbit 171**（ASCENDING, frame 96）覆盖。
- **数据已获取**：ASF HyP3 OAuth2 鉴权通过，提交 21 个 `INSAR_GAMMA` 干涉对（~24 天基线，2023-01~2024-05）全部 SUCCEEDED，下载 ~3GB 成果（`los_disp.tif`/`corr.tif`/`vert_disp.tif`，地理编码 GeoTIFF）。
- **速度场合成**：`scripts/ch9_convert_insar_shaoxing.py`（重投影 EPSG:4326 + 相干性加权平均 + 平滑 + 限幅）→ `data/insar_hyp3/sx_*`。
- **后端就绪**：`heritage_catalog` 的 `sample_sx_raster` / `real_insar_available` 已就绪，**相干性门限 γ>0.5** 时以真实值覆盖五指标（`data_track: real_insar`），否则回退 `demo_sandbox`。
- **诚实口径**：原始单对干涉相干性偏低（均值 0.20），未经 SBAS/PS + ERA5 大气校正的速率噪声较大，demo 以确定性仿真为主；完整毫米级速率需后续接入 MintPy SBAS + 大气校正。

### 三合一沉浸式重构（2026-09-08 更新）

- **卡片归一**：原 3 张 mission 卡（卢宅/越城/平遥）合并为 1 张「古建大盘」，`api_mode: ch9_heritage_master`、`location: china_center`，宏观俯瞰全国。
- **一镜到底**：单一场景内通过 `HeritageEvidenceBoard` 靶向导航器 + `CesiumViewer.performDive` 依次下潜绍兴/东阳/平遥，避免反复进出地球。
- **视觉证据板**：废弃大段原理说明，右侧面板升级为多媒体画廊，直接消耗 `data/` 真实物料——`072500002AAaa.jpg`+json（YOLO SVG 扫描）、`微信视频2026-08-21_153842_980.mp4`（CFD 视频）、`FEA云图_薄弱点标注.png`（FEA 定损）。
- **渲染降载**：重度 CFD/病害定位放在 2D DOM 侧边栏，不占 WebGL 算力，Cesium 保持高帧率。

所有对外口径以 §11.1 为准：形变标注 `LOS 向相对形变`、输出为「相对风险排序」而非「结构安全鉴定结论」。

---

## 一、业务洞察与场景演进逻辑

### 1.1 为什么 CH8 不能直接套用

| 维度 | CH8 城市沉降 | CH9 古建保护 | 必须新增的能力 |
|---|---|---|---|
| 观测对象 | 城市网格 / 基坑 / 地铁线 | **文物建筑单体**（往往 < 30m 见方） | 单体轮廓提取 + 缓冲区归因 |
| 物理驱动 | 单一（岩土固结 / 开挖扰动） | **双驱动**（地下形变 + 地上风载） | 双链路耦合与互校正 |
| 判定依据 | 有现成工程规范（−20 mm/yr、−30 mm 累积） | **国内外均无古建专用遥感形变标准** | 相对风险排序 + 五指标体系 |
| 受体敏感性 | 钢混结构，容差明确 | 木构 / 砖石，**容差机理完全不同**，且历经数百年老化 | 材料劣化参数从病害数据反哺 |
| 空间分布 | 集中于城市建成区 | **散布全国，跨气候带、跨形制** | AEF 少样本跨省泛化 |
| 数据完备度 | 城市有完整地籍与管网 | **99% 无档案**，部分名录仅精确到村级 | 多源点位融合 + 开放数据补全 |

### 1.2 政策牵引（对外叙事的第一锚点）

《国家文物事业发展"十五五"规划》主要指标表 **指标 4**：

> **省级以上文物保护单位遥感执法监测覆盖率：2025 年基期值 40% → 2030 年目标值 100%**

同一规划提出建设**国家文物资源大数据库（中国文物云）**。
《国家文物局应对自然灾害应急预案》(2025) 要求编发自然灾害**每日预警预报制度**。
《全国重点文物保护单位文物建筑预防性保护技术导则（试行）》(2025) 确立**日常巡查 / 定期诊断 / 专项诊断**三级体系。

> **CH9 的产品定位**：向"中国文物云"供给天地一体时空底座与遥感监测能力，而非再造一个平行平台。

### 1.3 三体 / AEF / One Earth 的分工（与展台海报严格对齐）

| 角色 | 在 CH9 中承担什么 | 不可替代性 |
|---|---|---|
| **三体计算星座** | 0.3m 定制过境 + 星上在轨计算，覆盖人到不了的 30 万处；灾后 40 分钟估损 | 覆盖 + 时效 |
| **地球科学基础模型 (AEF)** | 64 维语义嵌入：点位对齐去重、跨省零微调筛查、年际变化检测 | 泛化 + 关联 |
| **One Earth 时空底座** | 让影像 / 嵌入 / 形变 / 台账 / 仿真五层异构数据归到同一个建筑 ID | 对齐 |
| （伙伴）文旅中试基地 | 20 类病害体系、48 条判定规则、3000+ 风载荷工况、40+ 基本型 | 认知 + 精算 |

---

## 二、双靶场力学对偶选址论证

沿用 CH8「地貌反差 · 力学对偶 · 受众差异」的选址方法论，CH9 选定**一主二辅**三个靶场。

```
┌──────────────────────────────────────────────┬──────────────────────────────────────────────┐
│  CH9-A  金华东阳 · 卢宅建筑群                 │  CH9-B  绍兴越城 · 历史城区                   │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│  微观单体形变（单栋 ~ 建筑群尺度）            │  宏观广域面状（十至数十平方公里）             │
│  大气驱动：台风风致响应、风吸风压             │  岩土驱动：宁绍平原软土 + 河网水位 + 施工扰动 │
│  突发性、小时级、有明确预警窗（48–72h）       │  缓变性、年际、长期蠕变与差异沉降             │
│  痛点：屋面掀揭、翼角断裂、瓦件坠落伤人       │  痛点：基础不均匀沉降 → 木构歪闪、墙体开裂    │
│  受众：应急管理、文物局、基层巡检员           │  受众：文物局、住建、街道、修缮设计单位       │
│  主算法：风载荷工况库查表 + 累计概率          │  主算法：SBAS-InSAR + 单体五指标归因          │
│  数据现成度：★★★★★（东南大学仿真库已建）    │  数据现成度：★★★★☆（56 处实采 / 600+ 试点）  │
└──────────────────────────────────────────────┴──────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────────────┐
│  CH9-C  山西 / 徽州  ·  跨省零微调泛化验证靶场                                             │
│  用途：不产出业务结论，只验证「浙江样本训练的模型能否直接迁移」——AEF 价值的唯一硬证据      │
│  产出：候选古建聚落点位 + 抽样人工核验准确率（诚实报数，定位为线索而非认定）                │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 CH9-A 东阳卢宅 —— 典型江南木构建筑群风致响应

- **建筑本体**：明清木构建筑群，抬梁式与穿斗式混合，硬山与歇山屋面并存，翼角起翘显著。屋面为小青瓦，自重轻、瓦件间靠叠压与灰浆约束，**抗风吸能力是全结构最薄弱环节**。
- **地质条件**：位于金衢盆地，基底以红层与残积土为主，天然沉降量小 —— **这正是把它设为"纯风载靶场"的原因**：排除了地基因素干扰，风的因果链条更干净。
- **灾害机理**：台风过境时，屋脊、檐口、翼角处形成局部强负压区（风吸），瓦件与望板被整片掀揭；山墙迎风面承受正压，木构榫卯节点承受反复交变荷载。
- **业务窗口**：气象部门可提前 48–72h 给出台风路径与风力预报 → 这是 CH9-A 唯一有意义的时间窗。
- **数据优势**：文旅中试基地已与东南大学共建 **3000+ 风载荷工况**（40+ 基本型 × 70+ 工况维度 × 9–13 级风 × 30° 间隔全风向），**全部预计算完成**，现场为毫秒级查表。

### 2.2 CH9-B 绍兴越城 —— 宁绍平原软土区古建群差异沉降

- **建筑本体**：940+ 处古建筑，含大运河遗产点、鲁迅故里、多处台门建筑（如恒济台门）。台门为绍兴特有形制，砖木混合、多进院落、共用山墙。
- **地质条件**：宁绍平原为典型第四纪滨海—湖沼相沉积区，浅部广泛分布淤泥质粉质黏土，含水量高、压缩性大。老城区河网密布，地下水位季节波动明显。
  > ⚠️ 具体土层厚度、含水量、压缩模量等参数**需向绍兴市自然资源与规划局或地质勘查院索取实测钻孔资料**，本 PRD 不预设数值。
- **灾害机理**：三源叠加 ——（1）软土自重固结的长期蠕变；（2）地下水位季节升降引起的弹性浮沉；（3）周边新建工程降水与开挖引起的局部扰动漏斗。三者共同导致**同一进院落内的差异沉降**，进而引发木构架歪闪、墙体竖向开裂、地面铺装破损。
- **业务窗口**：年际尺度。产出为**年度体检报告 + 相对风险排序**，服务于修缮排期而非应急。
- **数据优势**：已签合作协议，实地病害采集 **56 处**、试点应用覆盖 **600+ 处**，具备完整的"一房一况"台账（编号 / 名称 / 拍摄时间 / 部位 / 说明）。

### 2.3 为什么这个对偶比 CH8 的更有说服力

CH8 的南沙 vs 天河，两者都是**沉降**，只是尺度与诱因不同。
CH9 的东阳 vs 越城，是**两种完全不同的物理场**（大气 vs 岩土）、**两种时间尺度**（小时 vs 年）、**两套观测手段**（气象预报+光学 vs 雷达干涉），却收敛到**同一个数据结构、同一个建筑 ID、同一份报告模板**。

> 这恰好证明了 One Earth 时空底座的价值：**不是把两件事做了两遍，是让两件事对上了。**

---

## 三、科学与算法基座

### 3.1 数据源全清单

#### A 类 · 天基观测

| 数据 | 规格 | 来源 | 用途 | 状态 |
|---|---|---|---|---|
| Sentinel-1 SLC | IW 模式 · VV 极化 · 5×20 m · **6 天重访（S1C+S1D，2025 后）/ 12 天（历史）** | Copernicus Data Space Ecosystem（免费）/ ASF DAAC | InSAR 时序形变反演 | ✅ 公开 |
| 精密轨道星历 POEORB | 重访后 21 天发布，基线误差 < 5 cm | ESA | 轨道相位校正 | ✅ 公开 |
| Copernicus DEM GLO-30 | 30 m · 全球绝对高程精度 < 4 m | Copernicus | 地形相位剥离 + 地理编码 | ✅ 公开 |
| ECMWF ERA5 | 逐小时 · 0.25° · 37 气压层 | Copernicus CDS (API) | PyAPS 对流层延迟校正；历史风向玫瑰图统计 | ✅ 公开 |
| Sentinel-2 L2A | 10 m · 5 天重访 | Copernicus / GEE | 变化检测辅助、灾后估损备份 | ✅ 公开 |
| **AEF Satellite Embedding V1** | **64 维 · 10 m · 年度 · 2017–2024 · 单位球面** | GEE: `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` | 点位语义对齐 / 跨省筛查 / 年际变化检测 | ✅ 公开免费 |
| **三体计算星座 0.3 m 光学** | 定制过境成像；星上在轨推理 | 三体星座 | 单体轮廓提取、灾后估损、高分底图 | ⚠️ 需任务规划；测绘资质约束见 §11.3 |

> **⚠️ 必须更新的口径**：CH8 文档中的「Sentinel-1 A/B、12 天重访」已过时。
> S1B 于 2021-12 失效退役，**S1A 于 2026-06-29 退役**，S1C（2024-12 发射）+ S1D（2025-11 发射，2026-04-17 开放用户数据）构成当前星座，2026-06-24 完成轨道重构，**标称重访 6 天**。
> 2021-12 ~ 2024-12 为单星期，重访退化至 12 天，历史时序在该区间变稀，反演不确定度上升，**报告中必须标注**。
> 浙江区域的 **Track / Frame 编号需在 ASF Vertex 或 COMET LiCSAR 平台实际检索确认**，本 PRD 不预填。

#### B 类 · 气象驱动

| 数据 | 规格 | 来源 | 用途 |
|---|---|---|---|
| CMA 智能网格预报 | 空间 5 km（部分 1 km）· 逐小时 · 临近至中期无缝 | 中国气象数据网 / 省气象局共享 | 48–72h 风速风向驱动场（CH9-A 核心输入） |
| CMA 热带气旋最佳路径 | 逐 6 小时定位与强度 | `tcdata.typhoon.org.cn`（**公开免费**） | 历史台风复现、路径动画 |
| 中央气象台实时台风 | 实时路径与预报圈 | `typhoon.nmc.cn` | 演示素材 |
| ECMWF Open Data | 全球中期集合预报，开放许可 | ECMWF | 交叉验证备份 |

#### C 类 · 地面业务（合作方提供 / 开放数据）

| 数据 | 规格 | 来源 | 状态 |
|---|---|---|---|
| 全国重点文保单位空间分布 | 八批 5058 处（口径以 5053 为准，见 §11.1）· 含批次/年代/类型 | 国家地球系统科学数据中心 | ✅ 注册申请，科研免费 |
| 省级文保单位 | 26992 处 | 省文物局 | ⚠️ 需申请 |
| 四普 / 三普点位 | 不可移动文物 89 万处；其中古建筑约 30.8 万处 | 省文物局正式申请 | ⚠️ 审批周期不可控 |
| OSM `historic=*` / `building=temple` | 数万级，无审批 | Overpass API | ✅ 立即可用 |
| Wikidata 文保类目 | 数千级，结构化 + 多语言 | SPARQL | ✅ 立即可用，利于全球叙事 |
| **古建病害视觉语义数据集** | **5 万+ 张 · 500+ 栋 · 20 类病害 · 48 条判定规则** | 文旅中试基地 | ✅ 已有 |
| **风载荷结构响应知识库** | **3000+ 工况 · 40+ 基本型 · 70+ 工况维度 · 9–13 级风 · 30° 全风向** | 中试基地 × 东南大学 | ✅ 已有（CH9-A 唯一支撑，无替代） |
| 一房一况台账 | 编号 / 名称 / 拍摄时间 / 部位 / 说明 + 修缮措施 | 中试基地（越城 56 处实采） | ✅ 已有 |
| 建筑基本型 3D 模型 | 3D Max 资产，按地区分类（杭州 / 温州 / 金华…） | 中试基地 | ✅ 已有 |

#### D 类 · 待补（中期）

- 绍兴老城区地质钻孔剖面与地下水位监测序列（自然资源局 / 地勘院）
- 越城区近 10 年施工许可与降水记录（住建局）——用于形变归因
- 古建修缮工程档案（省古建院）——用于验证形变与病害的因果关系

---

### 3.2 算法链路 A：地下 · InSAR 形变与**单体归因**（CH9 核心增量）

前 8 步完全继承 CH8 的 ISCE2 + MintPy 标准链，此处不再重复。**CH9 的新增是第 9 步。**

```
[继承 CH8]
S1 SLC 栈 → ISCE2 topsStack（SBAS 组网, B⊥<150m, Δt<60d）
          → SNAPHU 3D 解缠
          → MintPy: modify_network → reference_point → invert_network(WLS)
                    → correct_troposphere(PyAPS+ERA5) → correct_topography → deramp
                    → velocity → geocode
          → velocity.tif (mm/yr) + temporalCoherence.tif

[CH9 新增 · 第 9 步：文物建筑单体归因]
① 建筑轮廓提取
   三体 0.3 m 影像 / 无人机正射 → 深度学习实例分割 → 建筑单体多边形
   （备选：直接使用文旅方已有的建筑档案矢量）
② 缓冲区采点
   对每栋建筑轮廓做 3 m 缓冲区（对标剑川古镇研究方法）
   采集落入缓冲区的全部高相干点（γ > 0.75）
③ 五指标计算
   · 最大沉降速率        v_max          (mm/yr)
   · 沉降速率差          Δv = v_max − v_min   (mm/yr)
   · 角变形              β = Δs / L      (无量纲)
   · 倾斜度              skew
   · 时序形变模式         K-means 聚类分型（线性 / 加速 / 收敛 / 季节主导）
④ 五指标打分 → 相对风险分级
   稳定 5–9 分 / 中等 10–14 分 / 不稳定 15–20 分
```

**为什么是 3 m 缓冲区**：古建单体尺度小（常 < 30 m），Sentinel-1 地面分辨率数十米量级，直接取建筑内像元往往采不到足够相干点。3 m 缓冲区在"采到点"与"不串到邻栋"之间取平衡，该做法有同行评议成果支撑（见 §15 文献 1）。

**输出增补字段**（相对 CH8）：
```
building_id, footprint_wkt, ps_count, coherence_mean,
v_max_mm_yr, v_diff_mm_yr, angular_distortion, skew,
temporal_cluster, risk_score, risk_level
```

---

### 3.3 算法链路 B：地上 · 风载荷结构响应（查表 + 累计概率）

**全链路零实时重计算**，现场毫秒级响应。这是 CH9-A 最稳的工程设计。

```
输入：CMA 智能网格预报（T-72h ~ T-0，逐小时风速 v、风向 θ）
     + 台风路径 / 风圈
     + 当地历史风向玫瑰图（ERA5 长序列统计）
   │
   ├─ ① 建筑基本型匹配（离线预完成，T-14 前绑定）
   │     0.3 m 俯视影像 / 航拍 → 图搜图 → 基本型 ID + 变体 ID
   │     （AEF 嵌入可作为图搜图的特征增强，见 3.4）
   │
   ├─ ② 工况知识库查表
   │     key   = (basic_type_id, variant_id, wind_level, wind_direction)
   │     value = { 正压场, 负压场, 薄弱点排序[] }
   │     3000+ 组合已全部离线算完，纯 O(1) 查表
   │
   ├─ ③ 累计风险概率
   │     对过境窗口内每个时刻 t_i：
   │       取 (v_i, θ_i) 对应受力场 F_i
   │       按持续时长与风速加权：  R = Σ w(v_i, Δt_i) · F_i
   │     → 各构件部位的累计受力概率分布
   │
   └─ ④ 输出
         高危部位排序（屋脊 / 檐口 / 翼角 / 山墙…）
         触发等级 + 灾前专项巡检要点 + 处置建议
```

**诚实边界**：基本型匹配是**统计意义上的群体风险筛查**，不是单体结构鉴定。
- 普通民居 → "基本型 + 巡检数据修正"的低成本模式
- 国宝级建筑（如卢宅）→ 单独采集、单独仿真的精细化模式

这个"双轨"本身就是方案成熟度的体现，对外应主动说明。

---

### 3.4 算法链路 C：AEF 语义（三个用法，按 ROI 排序）

| 用法 | 做法 | 成本 | 价值 |
|---|---|---|---|
| **① 点位融合去重** | 三级级联匹配：空间距离约束（<200 m）+ 中文名称相似度（含拼音 / 字 n-gram）+ **AEF 向量点积**（取点位周边 3×3 像元均值，单位化后点积）。加权得分 > θ 则合并 | 低 | 解决"卢宅 / 肃雍堂 / 卢宅建筑群"这类同实体异名问题；产出**开放数据对政府名录的覆盖率**这一核心叙事数字 |
| **② 跨省零微调筛查** | 浙江已知国保/省保古建 ~400 个作正样本，随机采样 ~2000 个非古建作负样本；**直接对 64 维嵌入拟合 logistic regression / k-NN，不微调 AEF 底座**；在山西/徽州 10 m 网格全域推理 → 连通域聚合 → 剔除已知名录 → 候选线索 | **约 2 人日**（GEE 直接调，无需下载、无需训练） | 基础模型泛化价值的**唯一硬证据**；抽样人工核验后诚实报准确率 |
| **③ 年际变化检测** | 相邻两年 AEF 向量点积落差 → 探测古建周边地表突变（新开工、拆改、植被侵占）→ 与 InSAR 沉降速率图做**空间交集** | 中 | InSAR 回答 where/how much，AEF 回答 what/why → 产出**有因果的预警**，而非孤立的形变数字 |

**AEF 的诚实边界**：10 m 分辨率能识别**聚落形态、屋顶材质、街巷肌理**，**不能**识别构件级病害。粗筛靠 AEF，厘米级病害靠无人机 4K 与巡检照片。

---

### 3.5 算法链路 D：病害视觉识别（复用中试基地能力）

```
巡检员手机拍照
  → 图像质量门控（过暗/模糊 → 提示重拍）
  → YOLO 目标定位与检测
  → 文润 VLM 兜底理解与语义分析
  → 20 类病害体系（木构架 6 / 墙体·地面·场地 5 / 屋面·其他 9）
  → 48 条判定规则 → 危害等级 Ⅰ/Ⅱ/Ⅲ + 处置紧急性
  → 自动生成巡检报告
```

已达指标：**识别准确率 ≥87%、检出完整度 ≥82%、平均推理时延 <2s、可解释置信度输出**。
时延 <2s 意味着**现场实时演示完全可行**，是 CH9 中风险最低的一环。

---

### 3.6 双物理耦合：CH9 相对 CH8 最本质的技术创新

CH8 只有一个物理量（形变）。CH9 有三个数据源，且它们**互为输入**：

```
                  ┌─────────────────────────────────┐
                  │        建筑单体 building_id      │
                  └────────────────┬────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
  ┌───────────┐            ┌───────────┐            ┌───────────┐
  │ A · 形变  │            │ B · 风载  │            │ D · 病害  │
  │ InSAR     │            │ 工况查表  │            │ YOLO+VLM  │
  └─────┬─────┘            └─────┬─────┘            └─────┬─────┘
        │                        │                        │
        │  ①基础状态输入          │                        │
        └───────────────────────►│◄───────────────────────┘
                                 │   ②材料劣化参数修正
                                 │
        ③变形—病害因果验证        │
        ◄────────────────────────┴────────────────────────►
```

**耦合关系一（D → B）材料劣化参数修正**
巡检积累的病害数据（木构件糟朽、墙体开裂、榫卯脱拔）反映真实的材料退化状态。将其作为修正系数注入风载荷模型的构件强度参数，把"标准基本型"的通用受力分析，修正为**"一房一况"的个体化风险评估**。
> 这正是中试基地 PPT 中"基本型底库 → 参数代入 → 薄弱点重算"的能力，CH9 把它接入天基数据。

**耦合关系二（A → B）基础状态输入**
角变形超限的建筑，其上部结构已处于非设计受力状态，抗风能力下降。InSAR 五指标应作为风险等级的**放大系数**，而非独立维度。
> 判据示例：角变形 > 1/300 的建筑，在同等风载工况下风险等级上调一级。

**耦合关系三（A ↔ D）因果互证**
InSAR 探测到某处基础差异沉降，若该建筑的病害台账中同期出现"墙体竖向开裂 / 木构架歪闪"，则两者**互为验证**，置信度显著提升；若形变显著而无病害记录，则触发**优先现场核查**——这正是"天上定宏观、地下做微观，两边对得上结论才敢报"的工程含义。

**耦合关系四（AEF → 归因）**
AEF 年际变化检测发现的"周边新开工"图斑，与 InSAR 沉降漏斗做空间交集，可直接给出**沉降诱因假设**（施工降水扰动 vs 自然固结），把预警从"哪里在沉"升级为"为什么沉"。

---

## 四、阈值与判定标准（诚实口径）

### 4.1 核心事实：没有现成标准

| 标准 | 覆盖范围 | 对 CH9 的可用性 |
|---|---|---|
| **GB/T 50165-2020**《古建筑木结构维护与加固技术标准》 | 木结构承载力、构件残损点 | 提供构件级残损判定依据，**无基于遥感形变的整体判定** |
| **DB11/T**《古建筑结构安全性鉴定技术规范 第1部分：木结构》（北京地标） | 木结构整体与构件安全性鉴定分级 | 可借用鉴定分级框架 |
| **《文物建筑健康监测技术规范》**（中国文物保护技术协会团标） | 监测项、测点布设、预警 | **最贴近**，作为"监测→预警"合规性引用 |
| 上海市《历史建筑安全监测技术标准》 | 历史建筑沉降、倾斜、裂缝限值 | 提供沉降差 / 倾斜限值的地方标准依据 |

> **结论（必须写进对外口径）**：国内外**均缺乏针对古建筑（尤其木结构、砖石结构）的、基于星载形变数据的统一风险判定标准**。现代建筑规范阈值不能直接套用——古建的容忍变形能力与破坏机理与钢混完全不同。

### 4.2 CH9 的临时判定口径

在标准缺位的前提下，系统**只输出相对风险排序，不输出结构安全鉴定结论**。UI 上必须明确标注这一点。

借用剑川古镇研究的五指标体系 + 地方标准的倾斜/沉降差限值：

| 指标 | 参考阈值 | 来源 | 说明 |
|---|---|---|---|
| 角变形 β | **1/300 稳定线 · 1/150 关注线** | 建筑地基变形规范体系；剑川 InSAR 研究采用 | 对古建为借用，非专用 |
| 相干性 γ | > 0.75 保留 | 工程经验值 | 可 0.60–0.85 区间调参，报告须写清所用阈值 |
| 显著形变 | \|v\| > 5 mm/yr | 工程经验值 | 同上 |
| 风速工况 | 9–13 级 | 东南大学仿真库覆盖范围 | 超出范围不外推 |
| 综合风险 | 5–9 稳定 / 10–14 中等 / 15–20 不稳定 | 五指标打分 | **相对排序，非绝对判定** |

### 4.3 继承 CH8 的双标尺教训（CH9 的对应版本）

CH8 踩过的坑是「速率 mm/yr 与累积量 mm 量纲错配」。CH9 有**三个同类陷阱**，必须提前规避：

| 陷阱 | 表现 | 规避设计 |
|---|---|---|
| **① LOS 向 ≠ 垂直沉降** | 把 InSAR 视线向相对形变当成绝对垂直沉降报出去 | 所有形变值标注 `LOS`；需三维分解须升降轨联合观测，未做则明确说明 |
| **② 分辨率 ≠ 测量精度** | 被质疑"Sentinel-1 几十米分辨率怎么测单栋建筑" | 统一话术：分辨率是成像单元尺度，形变精度来自相位测量（λ=5.55 cm）。口径为**"毫米级年速率、厘米级单期位移"**，绝不说"绝对毫米级" |
| **③ 相对风险 ≠ 安全鉴定** | 输出被当成结构安全结论引用 | 报告首页固定声明；风险等级用"关注 / 建议核查 / 优先处置"而非"安全 / 危险" |

---

## 五、离线管线与 GEE 资产化

### 5.1 资产命名规范

```
projects/aef-project-487710/assets/
  ├── ch9_heritage_insar_shaoxing_v1      # 越城区 velocity + coherence 双波段
  ├── ch9_heritage_footprint_shaoxing_v1  # 建筑单体轮廓（FeatureCollection）
  ├── ch9_heritage_metrics_shaoxing_v1    # 单体五指标表（FeatureCollection）
  └── ch9_heritage_points_cn_v1           # 全国古建融合点位（FeatureCollection）
```

### 5.2 资产构建脚本 `scripts/ch9_heritage_asset_builder.py`

```python
"""
CH9 古建筑保护场景 · GEE 资产构建器
沿用 CH8 的 manifest 上传范式，新增建筑单体矢量与五指标表的资产化。
"""
import ee
import os
import json
import subprocess

GCS_BUCKET = os.getenv("CH9_GCS_BUCKET", "gs://your-sros-bucket/ch9_heritage/")


def upload_insar_raster(velocity_tif, coherence_tif, asset_id):
    """栅格：形变速率 + 相干性（继承 CH8 双波段范式）"""
    ee.Initialize()
    print(f"🚀 构建 CH9 InSAR 栅格资产: {asset_id}")

    subprocess.run(f"gsutil cp {velocity_tif} {GCS_BUCKET}velocity.tif", shell=True, check=True)
    subprocess.run(f"gsutil cp {coherence_tif} {GCS_BUCKET}coherence.tif", shell=True, check=True)

    manifest = {
        "name": asset_id,
        "tilesets": [
            {"id": "velocity_tiles", "sources": [{"uris": [f"{GCS_BUCKET}velocity.tif"]}]},
            {"id": "coherence_tiles", "sources": [{"uris": [f"{GCS_BUCKET}coherence.tif"]}]},
        ],
        "bands": [
            {"id": "velocity",  "tilesetId": "velocity_tiles",  "missingData": {"values": [0]},
             "pyramidingPolicy": "MEAN"},
            {"id": "coherence", "tilesetId": "coherence_tiles", "missingData": {"values": [0]},
             "pyramidingPolicy": "MEAN"},
        ],
        # CH9 新增：把处理参数写进资产属性，报告可回溯
        "properties": {
            "scene": "CH9",
            "aoi": "shaoxing_yuecheng",
            "sensor": "Sentinel-1 IW VV",
            "revisit_days": 6,               # S1C+S1D；历史段为 12，见 properties.note
            "stack_start": "2023-01",
            "stack_end": "2026-08",
            "n_slc": 0,                       # 实跑后回填
            "processor": "ISCE2 topsStack + MintPy smallbaselineApp",
            "atmos_correction": "PyAPS + ERA5",
            "dem": "Copernicus GLO-30",
            "reference_point": "TBD - 绍兴老城稳定硬地",
            "coherence_threshold": 0.75,
            "note": "LOS 向相对形变；2021-12~2024-12 为 S1A 单星期，重访退化至 12 天",
        },
    }

    with open("manifest_ch9_raster.json", "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    subprocess.run("earthengine upload image --manifest manifest_ch9_raster.json", shell=True)
    print("✅ 栅格资产任务已提交")


def upload_building_metrics(geojson_path, asset_id):
    """
    矢量：建筑单体轮廓 + 五指标归因结果
    每个 Feature 的 properties 必须包含 §3.2 定义的全部字段
    """
    ee.Initialize()
    print(f"🚀 构建 CH9 单体指标资产: {asset_id}")
    subprocess.run(f"gsutil cp {geojson_path} {GCS_BUCKET}metrics.geojson", shell=True, check=True)
    subprocess.run(
        f"earthengine upload table --asset_id={asset_id} {GCS_BUCKET}metrics.geojson",
        shell=True,
    )
    print("✅ 矢量资产任务已提交")


def upload_heritage_points(geojson_path, asset_id):
    """全国古建融合点位（多源匹配去重后的成果）"""
    ee.Initialize()
    subprocess.run(f"gsutil cp {geojson_path} {GCS_BUCKET}points.geojson", shell=True, check=True)
    subprocess.run(
        f"earthengine upload table --asset_id={asset_id} {GCS_BUCKET}points.geojson",
        shell=True,
    )
    print("✅ 点位资产任务已提交")


if __name__ == "__main__":
    PROJ = "projects/aef-project-487710/assets"
    upload_insar_raster("./data/sx_vel.tif", "./data/sx_coh.tif",
                        f"{PROJ}/ch9_heritage_insar_shaoxing_v1")
    upload_building_metrics("./data/sx_building_metrics.geojson",
                            f"{PROJ}/ch9_heritage_metrics_shaoxing_v1")
    upload_heritage_points("./data/cn_heritage_points.geojson",
                           f"{PROJ}/ch9_heritage_points_cn_v1")
```

### 5.3 单体归因离线脚本 `scripts/ch9_building_attribution.py`（核心增量）

```python
"""
CH9 核心增量：把 InSAR 像元级形变场，归因到文物建筑单体。
对标方法：剑川古镇 SBAS-InSAR 建筑稳定性评估（npj Heritage Science, 2024）
"""
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from sklearn.cluster import KMeans

BUFFER_M = 3.0          # 缓冲区半径（对标剑川方法）
COH_THRESHOLD = 0.75    # 相干性门限
MIN_PS = 5              # 单体最少相干点数，低于此判为"数据不足"


def attribute_to_buildings(footprint_shp, velocity_tif, coherence_tif, ts_h5=None):
    gdf = gpd.read_file(footprint_shp).to_crs(epsg=32651)   # UTM 51N（浙江）
    vel_src = rasterio.open(velocity_tif)
    coh_src = rasterio.open(coherence_tif)

    records = []
    for _, row in gdf.iterrows():
        buf = row.geometry.buffer(BUFFER_M)
        try:
            v, _ = mask(vel_src, [buf], crop=True, filled=False)
            c, _ = mask(coh_src, [buf], crop=True, filled=False)
        except ValueError:
            continue

        v, c = v[0].compressed(), c[0].compressed()
        n = min(len(v), len(c))
        if n == 0:
            continue
        v, c = v[:n], c[:n]

        keep = c > COH_THRESHOLD
        if keep.sum() < MIN_PS:
            records.append({**row.drop("geometry").to_dict(),
                            "ps_count": int(keep.sum()),
                            "risk_level": "data_insufficient"})
            continue

        vk = v[keep]
        v_max = float(np.nanmin(vk))            # 沉降为负，最大沉降取 min
        v_min = float(np.nanmax(vk))
        v_diff = float(v_min - v_max)

        # 角变形 β = 沉降差 / 特征长度
        L = float(np.sqrt(row.geometry.area)) or 1.0
        beta = abs(v_diff) / 1000.0 / L          # mm → m

        rec = {
            **row.drop("geometry").to_dict(),
            "ps_count": int(keep.sum()),
            "coherence_mean": float(np.nanmean(c[keep])),
            "v_max_mm_yr": round(v_max, 2),
            "v_diff_mm_yr": round(v_diff, 2),
            "angular_distortion": round(beta, 6),
            "beta_ratio": f"1/{int(1/beta)}" if beta > 1e-9 else "1/inf",
        }
        rec["risk_score"] = score_five_indicators(rec)
        rec["risk_level"] = grade(rec["risk_score"])
        records.append(rec)

    return gpd.GeoDataFrame(records, geometry=gdf.geometry, crs=gdf.crs)


def score_five_indicators(r):
    """五指标各计 1–4 分，合计 5–20 分。阈值为工程经验值，需随实测标定。"""
    s = 0
    s += bin_score(abs(r["v_max_mm_yr"]),      [3, 6, 12])     # 最大沉降速率
    s += bin_score(abs(r["v_diff_mm_yr"]),     [2, 4, 8])      # 沉降速率差
    s += bin_score(r["angular_distortion"],    [1/500, 1/300, 1/150])  # 角变形
    s += bin_score(r.get("skew", 0.0),         [0.001, 0.002, 0.004])  # 倾斜度
    s += r.get("temporal_cluster_score", 2)    # 时序模式分型得分
    return s


def bin_score(x, thr):
    return 1 if x < thr[0] else 2 if x < thr[1] else 3 if x < thr[2] else 4


def grade(score):
    if score <= 9:  return "stable"        # 稳定
    if score <= 14: return "moderate"      # 中等关注
    return "unstable"                      # 优先核查
```

---

## 六、后端遥感引擎层实现 `backend/gee_service.py`

沿用 CH8 的 `get_layer_logic` 分支范式，新增 CH9 三个 mode。

```python
    # ══════════════════════════════════════════════════════════════
    # CH9-B 古建广域形变体检（绍兴越城）
    # ══════════════════════════════════════════════════════════════
    elif ("ch9_heritage_deformation" in mode_s) or ("古建形变" in mode_s):
        ASSET_ID = os.getenv(
            "CH9_HERITAGE_INSAR_ASSET_ID",
            "projects/aef-project-487710/assets/ch9_heritage_insar_shaoxing_v1",
        )
        try:
            insar_img = ee.Image(ASSET_ID)
        except Exception:
            # 双轨回退：与 CH8 一致，返回常量图，由物理仿真引擎接管
            insar_img = (ee.Image.constant(0).rename("velocity")
                         .addBands(ee.Image.constant(1).rename("coherence")))

        velocity  = insar_img.select("velocity")     # LOS 向速率 (mm/yr)
        coherence = insar_img.select("coherence")

        # 1) 科学级质量控制
        coh_thresh = float(params.get("coh_thresh", 0.75))
        hq_mask = coherence.gt(coh_thresh)

        # 2) 业务靶向：古建阈值比城市更敏感（木构对差异沉降容忍度低）
        defo_thresh = float(params.get("defo_thresh", 3.0))   # CH8 为 5.0
        significant = velocity.lt(-defo_thresh).Or(velocity.gt(defo_thresh))

        img = velocity.updateMask(hq_mask.And(significant))

        # 3) 可视化：古建量程比城市窄（-20 ~ +6），避免小形变被色带压平
        vis = {
            "min": -20,
            "max": 6,
            "palette": ["B03A2E", "C85F45", "C89A3C", "5DAE8B", "2E9CB8"],
            "format": "png",   # 关键：透明，勿遮挡下方 3D 白模与古建单体模型
        }
        return img, vis, "ch9_heritage_deformation"

    # ══════════════════════════════════════════════════════════════
    # CH9-C AEF 语义 · 古建聚落跨省零微调筛查
    # ══════════════════════════════════════════════════════════════
    elif ("ch9_heritage_aef_discovery" in mode_s) or ("古建发现" in mode_s):
        year = int(params.get("year", 2024))
        aef = (ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
               .filterDate(f"{year}-01-01", f"{year}-12-31")
               .first())

        # 训练样本：浙江已知国保/省保古建点位（正）+ 随机非古建（负）
        pos = ee.FeatureCollection(
            "projects/aef-project-487710/assets/ch9_heritage_points_zj_positive")
        neg = ee.FeatureCollection(
            "projects/aef-project-487710/assets/ch9_heritage_points_zj_negative")
        samples = pos.merge(neg)

        bands = [f"A{i:02d}" for i in range(64)]
        training = aef.select(bands).sampleRegions(
            collection=samples, properties=["is_heritage"], scale=10, tileScale=4)

        # 关键：不微调 AEF 底座，仅在 64 维嵌入上拟合轻量分类器
        clf = (ee.Classifier.libsvm(kernelType="LINEAR")
               .setOutputMode("PROBABILITY")
               .train(training, "is_heritage", bands))

        prob = aef.select(bands).classify(clf).rename("heritage_prob")
        img = prob.updateMask(prob.gt(float(params.get("prob_thresh", 0.72))))

        vis = {
            "min": 0.7, "max": 1.0,
            "palette": ["3A3416", "8A6B1F", "C89A3C", "F0C468"],
            "format": "png",
        }
        return img, vis, "ch9_heritage_aef_discovery"

    # ══════════════════════════════════════════════════════════════
    # CH9-D AEF 年际变化检测（古建周边扰动）
    # ══════════════════════════════════════════════════════════════
    elif ("ch9_heritage_change" in mode_s) or ("古建变化" in mode_s):
        y0 = int(params.get("year_from", 2022))
        y1 = int(params.get("year_to", 2024))
        col = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
        bands = [f"A{i:02d}" for i in range(64)]

        a = col.filterDate(f"{y0}-01-01", f"{y0}-12-31").first().select(bands)
        b = col.filterDate(f"{y1}-01-01", f"{y1}-12-31").first().select(bands)

        # AEF 向量为单位长度 → 点积即余弦相似度；1-dot 即语义变化幅度
        dot = a.multiply(b).reduce(ee.Reducer.sum()).rename("similarity")
        change = ee.Image(1).subtract(dot).rename("semantic_change")

        img = change.updateMask(change.gt(float(params.get("change_thresh", 0.25))))
        vis = {
            "min": 0.2, "max": 0.8,
            "palette": ["2E9CB8", "C89A3C", "C85F45", "B03A2E"],
            "format": "png",
        }
        return img, vis, "ch9_heritage_change"
```

---

## 七、后端配置层注入 `backend/config.py`

```python
locations = {
    # ... 原有 locations ...
    "dongyang_luzhai": {
        "coords": [29.2832, 120.2410, 16],
        "name": "金华东阳 · 卢宅建筑群",
        "code": "dongyang_luzhai",
    },
    "shaoxing_yuecheng": {
        "coords": [30.0023, 120.5810, 14],
        "name": "绍兴 · 越城历史城区",
        "code": "shaoxing_yuecheng",
    },
    "shanxi_pingyao": {
        "coords": [37.2010, 112.1750, 13],
        "name": "山西 · 平遥古城（泛化验证）",
        "code": "shanxi_pingyao",
    },
}
# ⚠️ 上述坐标为区域中心近似值，实际单体锚点以文物局点位数据为准

modes = {
    # ... 原有 modes ...
    "ch9_heritage_deformation":   "古建单体形变体检 (SBAS-InSAR + 五指标归因)",
    "ch9_heritage_wind_risk":     "古建风载荷风险研判 (工况知识库 + 累计概率)",
    "ch9_heritage_aef_discovery": "古建聚落语义筛查 (AEF 零微调迁移)",
    "ch9_heritage_change":        "古建周边年际变化检测 (AEF 语义差分)",
}

missions = [
    # ... 原有 missions ...
    {
        "id": "卢宅风险",
        "chapter": "CH9",
        "name": "东阳卢宅台风风险研判",
        "title": "48 小时窗口：从气象网格到构件级薄弱点。",
        "location": "dongyang_luzhai",
        "api_mode": "ch9_heritage_wind_risk",
        "formula": "CMA 智能网格预报 × 风载荷工况知识库 (3000+) × 累计概率",
        "narrative": (
            "台风逼近前 48 小时，One Earth 接入中国气象局 5 公里智能网格预报，"
            "逐小时提取卢宅所在格点的风速与风向序列。系统通过图搜图将建筑群匹配到"
            "其所属地区性基本型与变体，直接检索与东南大学共建的风载荷结构响应知识库"
            "——40 余种基本型、70 余个工况维度、9 至 13 级风全风向共 3000 余种组合，"
            "全部离线预计算完成，现场为毫秒级查表。结合当地历史风向玫瑰图计算过境窗口内"
            "各风向受力的累计概率分布，在 0.3 米过境影像上直接标定屋脊、檐口、翼角等"
            "构件级薄弱点，输出灾前专项巡检要点。"
        ),
        "camera": {"lat": 29.2790, "lon": 120.2410, "height": 900, "duration_s": 4.5},
    },
    {
        "id": "越城体检",
        "chapter": "CH9",
        "name": "绍兴越城古建群形变体检",
        "title": "宁绍软土之上：940 处古建的年度差异沉降排序。",
        "location": "shaoxing_yuecheng",
        "api_mode": "ch9_heritage_deformation",
        "formula": "NASA ISCE2 + MintPy (Sentinel-1) + 单体 3m 缓冲区五指标归因",
        "narrative": (
            "视角落到宁绍平原上的绍兴古城。系统载入基于 ISCE2 框架解算、经 ERA5 大气"
            "校正的 Sentinel-1 时序形变场，滤除相干性低于 0.75 的噪点。与城市场景不同，"
            "古建单体尺度常小于 30 米，系统对每栋建筑轮廓做 3 米缓冲区采集相干点，"
            "计算最大沉降速率、沉降速率差、角变形、倾斜度与时序形变模式五项指标并打分，"
            "输出建筑单体的相对风险排序。角变形超过 1/300 的台门建筑被优先标出，"
            "与地面巡检台账中的墙体开裂记录相互印证——天上定宏观、地下做微观，"
            "两边对得上，结论才敢报。"
        ),
        "camera": {"lat": 29.9950, "lon": 120.5810, "height": 3200, "duration_s": 4.0},
    },
    {
        "id": "跨省发现",
        "chapter": "CH9",
        "name": "古建聚落跨省零微调筛查",
        "title": "浙江样本训练的模型，直接认出山西的古建。",
        "location": "shanxi_pingyao",
        "api_mode": "ch9_heritage_aef_discovery",
        "formula": "AEF Satellite Embedding V1 (64 维 · 10m) + 线性分类器",
        "narrative": (
            "以浙江省内约 400 处已知国保与省保古建作为正样本、随机采样的非古建区域"
            "作为负样本，直接在 AlphaEarth 64 维语义嵌入空间拟合一个轻量线性分类器"
            "——不对基础模型做任何微调。将该分类器搬到一千公里外的山西盆地全域推理，"
            "系统在名录之外浮现出大片高相似度的古建聚落候选。这些是需要文物部门实地"
            "核实的线索，不是认定结论；但它证明了一件事：知识可以迁移，"
            "不必每到一个新省份就从零重来。"
        ),
        "camera": {"lat": 37.1900, "lon": 112.1750, "height": 6000, "duration_s": 4.0},
    },
]
```

---

## 八、接口契约

### 8.1 图层瓦片接口（复用现有）

```
GET /api/layer
    ?mode=ch9_heritage_deformation
    &location=shaoxing_yuecheng
    &coh_thresh=0.75
    &defo_thresh=3.0
    &epoch=2026
→ {
    "tileUrl": "https://earthengine.googleapis.com/v1/.../tiles/{z}/{x}/{y}",
    "legend":  {"min": -20, "max": 6, "unit": "mm/yr", "direction": "LOS"},
    "stats":   {"building_count": 0, "unstable_count": 0, "ps_total": 0,
                "coherence_mean": 0.0},
    "disclaimer": "LOS 向相对形变；输出为相对风险排序，非结构安全鉴定结论"
  }
```

### 8.2 建筑单体档案接口（CH9 新增 · 五层数据对齐的落地）

```
GET /api/heritage/building/{building_id}
→ {
    "building_id": "SX-YC-ZP-08",
    "name": "恒济台门",
    "admin": {"province": "浙江", "city": "绍兴", "district": "越城区"},
    "protection_level": "TBD",
    "era": "TBD",
    "structure": "砖木混合",
    "centroid": [120.5810, 30.0023],
    "footprint": "POLYGON((...))",

    "layers": {
      "L1_satellite": {
        "source": "三体计算星座",
        "resolution_m": 0.3,
        "acquired": "2026-09-XX",
        "tile_url": "..."
      },
      "L2_semantic": {
        "source": "AEF Satellite Embedding V1",
        "dim": 64, "year": 2024,
        "label": "明清木构聚落",
        "confidence": 0.0
      },
      "L3_deformation": {
        "source": "Sentinel-1 SBAS-InSAR",
        "stack": "2023-01 ~ 2026-08",
        "ps_count": 0,
        "coherence_mean": 0.0,
        "v_max_mm_yr": 0.0,
        "v_diff_mm_yr": 0.0,
        "angular_distortion": 0.0,
        "beta_ratio": "1/XXX",
        "temporal_cluster": "linear|accelerating|converging|seasonal",
        "risk_score": 0,
        "risk_level": "stable|moderate|unstable|data_insufficient",
        "direction": "LOS",
        "note": "相对参考点；非绝对垂直沉降"
      },
      "L4_defect": {
        "source": "古建病害视觉语义数据集",
        "ledger_id": "ZP-08",
        "surveys": [
          {"date": "2019-11", "part": "东立面一", "photo_url": "...",
           "defects": [{"type": "墙体开裂", "level": "Ⅱ", "confidence": 0.0}]}
        ],
        "model": {"name": "YOLO + 文润VLM", "accuracy": 0.87, "latency_s": 2.0}
      },
      "L5_structural": {
        "source": "风载荷结构响应知识库",
        "basic_type_id": "TBD",
        "variant_id": "TBD",
        "wind_levels": [9, 13],
        "weak_points": [
          {"part": "屋脊", "rank": 1, "level": "severe"},
          {"part": "檐口", "rank": 2, "level": "moderate"},
          {"part": "翼角", "rank": 3, "level": "moderate"}
        ],
        "material_correction": {
          "applied": true,
          "source": "L4_defect",
          "note": "依据实测病害等级下调构件强度参数"
        }
      }
    },

    "fusion": {
      "coupled_risk_level": "TBD",
      "evidence_chain": [
        "L3 角变形 1/XXX 超过 1/300 关注线",
        "L4 同期记录墙体竖向开裂 Ⅱ 级 → 与形变互证",
        "L5 风载工况下屋脊为一级薄弱点 → 风险等级上调"
      ],
      "recommendation": "优先安排现场核查"
    }
  }
```

### 8.3 风险研判接口（CH9-A）

```
POST /api/heritage/wind_assessment
{
  "building_ids": ["JH-DY-LZ-001"],
  "typhoon": {"name": "示例", "track_source": "CMA-BST", "forecast_hours": 72},
  "grid_forecast": {"source": "CMA", "resolution_km": 5}
}
→ {
  "assessment_id": "...",
  "window": {"start": "...", "end": "..."},
  "dominant_direction_deg": 120,
  "max_wind_level": 12,
  "buildings": [{
      "building_id": "JH-DY-LZ-001",
      "risk_level": "Ⅲ",
      "weak_components": [...],
      "cumulative_probability": {...},
      "pre_disaster_checklist": [...],
      "measures": [...]
  }],
  "report_url": "/api/heritage/report/...",
  "review": {"required": true, "reviewer_role": "古建院专家"}
}
```

> **关键设计**：`review.required = true` 恒为真。文物本体的事，**不做无审核的端到端自动决策**。

---

## 九、前端三维孪生与交互

### 9.1 图层体系（对应展台海报的"球上五层"）

| 图层 | 内容 | 可见层级 | 数据源 |
|---|---|---|---|
| **L1 全球分布** | 世界遗产 + 全球古建光点（呼吸动画） | 全球视角 | Wikidata / UNESCO |
| **L2 中国全景** | 30.8 万处古建点位，三色分级（国保 / 省保 / 未定级） | 国家视角 | 融合点位资产 |
| **L3 三体过境** | 12 颗在轨卫星实时轨迹 + 过境足迹带 + 下次过境倒计时 | 全程可开关 | TLE 计算 |
| **L4 区域影像与形变** | 0.3 m 影像贴片 + InSAR 形变热力（PNG 透明） | 市县视角 | 三体 + GEE 瓦片 |
| **L5 单体三维** | 建筑 3D 模型 + 风压云图 + 构件级薄弱点标记 | 单体视角 | 基本型库 + 工况库 |

**性能红线**：30.8 万点**必须** LOD 聚合（四叉树 / `EntityCluster`）。全球视角只渲染省级聚合圆，省级视角渲染市级，市级以下才渲单点。全量直渲必卡死。目标 ≥30 fps。

### 9.2 三维锚标（继承 CH8，古建特化）

- 点击建筑 → 生成视准脉冲激光柱 + 发光地面雷达锚点
- HUD 标签格式：`🏯 绍兴越城·恒济台门 | 角变形 1/280 | 优先核查`
- **色彩语义与 CH8 区分**：CH8 用蓝-白-红发散表示沉降/抬升；CH9 增加**病害等级三色**（红=严重薄弱 / 橙=次级 / 蓝=一般关注），与中试基地既有成品云图配色保持一致，避免观众认知冲突
- 退出任务时释放实体，杜绝 WebGL 显存泄漏

### 9.3 交互方式：指令式，不用鼠标

领导巡馆时鼠标点击繁琐、易误操作。设计输入框 + 四条预置指令按钮，后台路由到**确定性动作序列**（对外称"智能体编排"，内部是固定路由——这是演示场景的正确工程选择）。

```
[点亮中国的古建筑]  [预测台风对东阳卢宅的影响]  [给越城古建做体检]  [生成研判报告]
```

保留自由输入框作为彩蛋，不进主流程。

### 9.4 三级降级预案

| 级别 | 触发 | 表现 |
|---|---|---|
| L1 正常 | 全链路在线 | 实时调用推理服务与 GEE 瓦片 |
| L2 降级 | 服务/网络异常 | 自动切预录结果，UI 无差别 |
| L3 兜底 | 主视觉异常 | 切 4K 全程录屏（带解说字幕） |

---

## 十、数据真实性双轨机制（继承 CH8 并强化）

| 评估维度 | 生产交付轨 | 演示沙箱回退轨 |
|---|---|---|
| **激活条件** | 配置 `CH9_HERITAGE_INSAR_ASSET_ID` 等环境变量 | 未配置（默认） |
| **形变数据** | GEE 私有资产中的真实 MintPy 输出 | 基于宁绍软土固结参数 + 剑川论文标定值的物理仿真 |
| **风载数据** | 东南大学工况知识库真实查表 | 同一知识库（**本身即真实预计算结果，无需回退**） |
| **病害数据** | 中试基地推理服务实时调用 | 预录推理结果回放（UI 无差别） |
| **点位数据** | 政府名录 + 开放数据融合 | **纯开放数据即可支撑**（OSM/Wikidata/国保数据集，无审批风险） |
| **空间坐标** | 真实文物点位 | 同一坐标 |
| **前后端契约** | 完全一致，零代码热插拔 | 完全一致 |

### 10.1 CH9 相对 CH8 的真实性优势

CH8 的演示轨必须整体回退到物理仿真。**CH9 有三条链路天然是真实的**：

1. **风载荷知识库**本身就是东南大学真实跑完的有限元结果，不存在"仿真回退"问题——它就是真数据
2. **病害识别模型**推理时延 <2s，可现场真实推理
3. **点位融合**纯开放数据即可跑通，无审批依赖

> 因此 CH9 的演示可信度基线**高于** CH8。唯一需要回退的是 InSAR 形变一环。

### 10.2 UI 数据来源角标（强烈建议）

在每个图层上打**明确的来源角标**，反而更显专业：

| 内容 | 角标 |
|---|---|
| 古建点位 | `四普/三普 + 开放数据` |
| 卫星影像 | `三体计算星座 · 0.3m · 2026-09-XX 过境` |
| 台风路径 | `复现：CMA 最佳路径数据集` |
| 风压结果 | `东南大学 · 风致响应知识库（预计算）` |
| 病害识别 | `YOLO + 文润VLM · 20 类病害体系` |
| InSAR 形变 | `Sentinel-1 SBAS-InSAR · 2023–2026 · LOS 向` |

**明确标注"预计算知识库"是加分项**，它说明真的算过、算了几千种工况，不是现场糊弄。解说词可直接说：
> 「这不是现在算的，是我们和东南大学把 40 多种基本型、几千种工况**提前算完存进知识库**的结果——所以台风来的时候，48 小时预警能在**秒级**给出。」

这句话比"实时计算"更有说服力。

---

## 十一、数据获取策略

### 11.1 口径统一表（务必全员对齐）

| 数字 | 统一口径 | 备注 |
|---|---|---|
| 不可移动文物 | **89 万处**（四普口径，中试基地材料） | 国家文物局另有"76.7 万处已完成普查"表述，统计口径不同 |
| **古建筑** | **30.8 万处** | **建议全场主用此数，比 89 万更对题、更少歧义** |
| 国保单位 | **5053 处** | 与"八批 5058 处"公开数据集略有出入，以中试基地口径为准并注明年份 |
| 省保单位 | 26992 处 | |
| 病害照片 | 5 万+ 张 · 500+ 栋 | |
| 越城试点 / 实采 | 600+ 处 / 56 处 | 区别于"越城区古建总数 940+" |
| 病害类别 / 判定规则 | 20 类 / 48 条 | 木构架 6 · 墙体地面场地 5 · 屋面其他 9 |
| 识别指标 | 准确率 ≥87% · 完整度 ≥82% · 时延 <2s | |
| 风载工况 | 3000+ 组合 · 40+ 基本型 · 70+ 工况维度 | 9–13 级风 · 30° 间隔全风向 |
| Sentinel-1 重访 | **6 天（2025 后）/ 12 天（历史）** | S1A 已于 2026-06-29 退役 |
| AEF 规格 | 64 维 · 10 m · 年度 · 2017–2024 | |
| 遥感监测覆盖率 | 40%(2025) → 100%(2030) | "十五五"规划指标 4 |

### 11.2 三条并行获取路线（防止单点阻塞）

```
路线一（可控 · 必走）：开放数据管线
  OSM Overpass + Wikidata SPARQL + 国保空间数据集 + POI API
  → 零审批，可立即启动
  → 这条路线单独就能撑起 L1/L2 图层，是整个场景的安全底座
  → 产出核心叙事数字：开放数据对政府名录的覆盖率

路线二（不可控 · 争取）：政府数据申请
  浙江省文物局 四普/三普点位（含经纬度）
  → 到位则"政府数据 vs 开放数据"对比论证成立（加分）
  → 不到位则降级为"开放数据 vs 国保名录"对比，叙事仍成立
  → 需领导出面协调

路线三（半可控 · 关键）：三体卫星过境任务
  东阳、越城定制过境成像
  → 需提前规划任务点位，申请 2–3 个备选窗口防云
  → ⚠️ 合规提示：国星宇航无测绘资质，数据批量获取与对外服务受限，
     展示用途需提前确认合规口径，现场不承诺数据开放
```

### 11.3 InSAR 数据获取的两条路

| 路径 | 做法 | 成本 | 适用 |
|---|---|---|---|
| **自跑 HPC**（精度可控） | 下载 Sentinel-1 SLC → ISCE2 → MintPy 全流程 | 数十核 · 数百 GB 内存 · 数小时至两天 / AOI | 中期，需精细控制参数 |
| **直接取成果**（快） | 从英国利兹大学 / ESA **COMET LiCSAR** 开放平台检索下载对应 Frame 的合成形变速度图 `velocity.tif` | 近零 | 短期起步、快速验证 |

> **建议**：短期走 LiCSAR 快速拿到形变底图跑通全链路，中期再自跑 HPC 以获得可控参数与更长时序。
> 浙江区域的 Track / Frame 编号**需在 ASF Vertex 或 LiCSAR 门户实际检索**，不可套用 CH8 的广州 Track 040 / Frame 04950。

### 11.4 参考点选择（InSAR 成败关键）

整个速率场是**相对参考点**的。参考点若也在沉降，全场整体偏移。
- 越城 AOI 建议参考点：老城区基岩出露或长期稳定硬地（如会稽山山麓稳定点）
- 参考点选定后必须写进资产 `properties.reference_point` 并在报告中注明

---

## 十二、分阶段落地路线图

| 阶段 | 周期 | 目标 | 关键动作 | 交付物 |
|---|---|---|---|---|
| **P0 底座复用** | 1 周 | 把 CH8 已跑通的链路 AOI 换成绍兴/东阳 | 复用 Cesium + GEE 瓦片 + 点击定损卡骨架 | 可点击 demo |
| **P1 点位与语义** | 2 周 | L1/L2 图层 + AEF 跨省筛查 | 开放数据管线（3 人日）+ AEF 筛查（2 人日）+ 抽样核验 | 融合点位资产 + 覆盖率数字 + 准确率 |
| **P2 风载链路** | 2 周 | CH9-A 全通 | 工况知识库接口对接 + 累计概率计算 + 薄弱点渲染 | 卢宅风险研判可演示 |
| **P3 形变链路** | 4–6 周 | CH9-B 全通 | LiCSAR 取数 或 自跑 HPC → 单体归因 → 五指标资产化 | 越城单体风险排序 |
| **P4 双物理耦合** | 4 周 | 三条链路互校正 | 材料劣化参数注入、形变—病害因果验证、AEF 归因交集 | 耦合研判报告 |
| **P5 标准共研** | 3–12 月 | 补上判定标准的空白 | 联合省古建院、东南大学、香港大学（施钧辉团队）研制古建遥感形变风险判定方法 | 行业标准草案 |
| **P6 规模化** | 1 年+ | 省级 → 跨省 | 山西、徽州、江苏复制；对接"中国文物云" | 可复制技术范式 |

### 12.1 工作量估算

| 模块 | 人日 |
|---|---|
| 点位融合管线 | 3 |
| AEF 跨省筛查 | 2 |
| AEF 变化检测 | 3 |
| 单体归因脚本 | 4 |
| InSAR 离线处理（LiCSAR 路径） | 3 |
| InSAR 离线处理（自跑 HPC 路径） | +8 |
| 风载知识库接口对接 | 2 |
| 五层聚合接口 | 3 |
| Cesium 图层与交互（复用 CH8 骨架） | 6 |
| 报告模板与审核流 | 2 |
| **合计（LiCSAR 路径）** | **28** |
| **合计（自跑 HPC 路径）** | **36** |

---

## 十三、风险与红线

### 13.1 四条红线

**红线一：不碰古建内部三维精细重建与微观裂缝透视**
遥感做不到——分辨率、视角、穿透能力都不支持。卫星影像侧摆角仅 5–10°，难获取侧面细节。
> 替代话术：建筑内部与构件级细节由无人机 4K 影像与基层巡检照片解决，这是天地一体里"地"的那一半。

**红线二：现场绝不跑重计算**
有限元、InSAR、变化检测全部预计算固化。现场只做查表、渲染、轻量推理（病害识别 <2s 可实时）。

**红线三：形变精度口径统一**
「毫米级年速率、厘米级单期位移」，且必须说明是 **LOS 向相对形变**。绝不说"绝对毫米级"。

**红线四：不出具结构安全鉴定结论**
只输出相对风险排序与优先核查建议。所有报告保留**人工专家复核**环节。

### 13.2 方法论风险清单

| 风险 | 说明 | 应对 |
|---|---|---|
| GRD ≠ SLC | GEE 上快速调用的 GRD 只有强度信息，只能做变化检测粗筛，**不能**做毫米级形变测量 | 明确区分"发现层"与"测量层" |
| 短基线单次干涉伪信号 | 24 天基线单对干涉，真实形变可能仅 1–2 mm，而大气延迟噪声可达 10–30 mm，简单折算年速率会放大十几倍 | 必须多时相 PS/SBAS + ERA5 大气校正 + 参考点标定 |
| 单体相干点不足 | 古建单体尺度小、多被植被遮挡，缓冲区内可能采不到 5 个以上高相干点 | 显式返回 `data_insufficient`，**不外推、不编造**；改用无人机或地面手段 |
| 阈值不是真理 | 0.75 相干、±3 mm/yr、1/300 角变形均为经验值 | 报告中写清所用阈值，避免"阈值一改结论就变"的质疑 |
| 数据空窗 | 2021-12 ~ 2024-12 单星期，历史时序变稀 | 报告标注该区间不确定度上升 |
| 三体测绘资质 | 国星宇航无测绘资质，数据批量获取与对外服务受限 | 展示用途提前确认合规口径 |
| 修缮建议责任边界 | 直接关系文物本体安全，标注数据量级有限 | 保留人工专家复核，不做无审核端到端生成 |

### 13.3 专家追问预案

| 追问 | 标准答案要点 |
|---|---|
| Sentinel-1 分辨率几十米，怎么测单栋建筑？ | 分辨率 ≠ 形变测量精度。测的是相干点的相位变化，微波波长 5.55 cm，毫米级形变即产生可观测相位差。单体归因靠 3 m 缓冲区内的相干点统计 |
| 12 天重访？1B 不是坏了吗？ | 1B 2021 年退役，1A 今年 6 月 29 日退役。当前为 1C+1D 星座，标称重访 6 天，历史时段 12 天 |
| 1/300 阈值哪来的？古建能用吗？ | 来自建筑地基变形规范体系，剑川古镇 InSAR 研究亦采用。**古建专用阈值国内外都还没有**，所以输出的是相对风险排序而非鉴定结论——这也正是我们想牵头联合研究的方向 |
| 有限元是现场算的吗？ | 不是，是与东南大学共建的预计算知识库，40+ 基本型 × 70+ 工况维度，3000+ 组合提前算完。现场是秒级查表 |
| AEF 跨省准确率多少？ | 抽样 N 个候选人工核验，准确率约 XX%。这是**候选线索**不是认定结论，需文物部门实地核实 |
| 这个能推到全国吗？ | 数据层可以（开放数据 + Sentinel-1 全球覆盖）；算力层依托万卡集群；标准层还需联合研究。省级是中期目标，全国是长期 |

---

## 十四、CH9 与展台海报的映射关系

| 海报页面 | 对应 CH9 模块 |
|---|---|
| P1 三能力卡（0.3 m / 48h→40min / 5 层→1 点） | §1.3 三者分工；§8.2 五层数据对齐接口 |
| P1 场景带（古建筑保护高亮 + 五个灰场景） | CH9 为已实现场景；其余对应 CH1–CH8 与后续规划 |
| P2 球上五层图层 L1–L5 | §9.1 图层体系（严格同名同序） |
| P2 时间轴 2019—2026 可回放 | §3.2 InSAR 时序 + §3.4 AEF 年际变化 |
| P3 恒济台门数字档案六行 | §8.2 `/api/heritage/building/{id}` 的 layers 结构 |
| P3 现场巡检台账（ZP-08） | L4_defect.ledger_id 字段 |
| P3 风载荷仿真薄弱点云图 | L5_structural.weak_points |

> **一致性要求**：海报上的每一个数字，都必须能在 CH9 的接口里找到对应字段。海报是 CH9 的对外切片，不是独立物料。

---

## 十五、参考文献与标定基准

### 1. InSAR 与文化遗产形变监测（CH9 方法论直接对标）

1. **Evaluating the stability of architectural heritage from the perspective of InSAR: a practical study on Jianchuan Ancient Town.** *npj Heritage Science*, 2024.
   > ★ **CH9 单体归因法的直接来源**：72 景 Sentinel-1（2017-08~2019-12）+ StaMPS SBAS-InSAR + GACOS 大气校正；无人机正射勾建筑轮廓，**3 m 缓冲区**采相干点；五指标（最大沉降速率、沉降速率差、角变形、倾斜度、K-means 时序聚类）打分分级（5–9 稳定 / 10–14 中等 / 15–20 不稳定）；角变形阈值 **1/300 与 1/150**；93% 以上相干点速率在 −5~+5 mm/yr。

2. Tapete, D. et al. **Satellite radar interferometry for monitoring and early-stage warning of structural instability in archaeological sites.** *Journal of Geophysics and Engineering*, 2012, 9(4).

3. **Satellite radar interferometry and in-situ measurements for static monitoring of historical monuments: The case of Gubbio, Italy.** *Remote Sensing of Environment*, 2019.

4. Le, T.S. et al. **TerraSAR-X Data for High-Precision Land Subsidence Monitoring: A Case Study in the Historical Centre of Hanoi, Vietnam.** *Remote Sensing*, 2016, 8(4), 338.

5. **山西段明长城 SBAS-InSAR 形变监测研究.** 2023.（国内线性文化遗产直接对标）

### 2. 算法基线

6. Berardino, P. et al. **A new algorithm for surface deformation monitoring based on small baseline differential SAR interferograms (SBAS).** *IEEE TGRS*, 2002.

7. Yunjun, Z., Fattahi, H., & Amelung, F. **Small baseline InSAR time series analysis: Unwrapping error correction and noise reduction.** *Computers & Geosciences*, 2019, 133, 104331.

8. **AlphaEarth Foundations: An embedding field model for accurate and efficient global mapping from sparse label data.** arXiv:2507.22291, 2025.
   > 64 维嵌入 · 10 m · 单位球面 · 跨年可比；15 项评测平均误差下降约 23.9%；k-NN / 线性分类器直接拟合嵌入即可，无需微调——**CH9-C 零微调迁移的理论依据**。

### 3. 标准与规范

9. **GB/T 50165-2020**《古建筑木结构维护与加固技术标准》
10. **DB11/T**《古建筑结构安全性鉴定技术规范 第1部分：木结构》（北京市地方标准）
11. **《文物建筑健康监测技术规范》**（中国文物保护技术协会团体标准）
12. 上海市工程建设规范《历史建筑安全监测技术标准》
13. 《全国重点文物保护单位文物建筑预防性保护技术导则（试行）》，国家文物局，2025

### 4. 风灾与气象

14. **台风大风低矮房屋易损性及智能网格预报的应用.** 《气象》, 2020.
15. **强风作用下群体民居围护结构破坏特征.** 《沈阳工业大学学报》, 2020.

### 5. 建筑物提取

16. **基于 MAEU-CNN 的高分辨率遥感影像建筑物提取.** 《地球信息科学学报》, 2022, 24(6).
17. **基于多任务学习的高分辨率遥感影像建筑物提取（Mask R-CNN + U-Net）.** 《地球信息科学学报》, 2021, 23(3).

---

## 附录 A · 待确认清单

| # | 事项 | 责任方 | 影响 |
|---|---|---|---|
| 1 | 浙江区域 Sentinel-1 Track / Frame 编号 | 之江地空中心 | InSAR 数据检索 |
| 2 | 绍兴老城区地质钻孔与地下水位序列 | 需向自然资源局/地勘院索取 | 形变归因与物理仿真标定 |
| 3 | 越城 InSAR 参考点具体位置 | 之江地空中心 | 全场速率基准 |
| 4 | 三体星上模型上传能力（体积上限、下传时延） | 三体团队 | "星上在轨计算"口径能否成立 |
| 5 | 国星宇航测绘资质对展示的具体约束 | 法务 | 合规口径 |
| 6 | 卢宅所属基本型 ID 与变体 ID | 中试基地 | 风载查表 key |
| 7 | 恒济台门的文保级别、年代、结构形式 | 中试基地 / 绍兴文物局 | 档案卡字段 |
| 8 | 建筑单体轮廓矢量是否已有（或需从影像提取） | 中试基地 | 归因链路起点 |
| 9 | 89 万 / 76.7 万口径最终采用哪个 | 项目组统一 | 全场数字一致性 |
| 10 | 病害识别模型第三方评测证书是否取得 | 中试基地 | 能否说"经权威机构评测" |

---

## 附录 B · 数据入口速查

| 数据 | 入口 |
|---|---|
| Sentinel-1 SLC | Copernicus Data Space Ecosystem / ASF DAAC (HyP3) |
| InSAR 成品形变图 | COMET LiCSAR（利兹大学 / ESA） |
| Copernicus DEM GLO-30 | Copernicus Data Space Ecosystem |
| ERA5 | Copernicus Climate Data Store (CDS API) |
| AEF 嵌入 | GEE: `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` |
| CMA 台风最佳路径 | `tcdata.typhoon.org.cn` |
| CMA 实时台风 | `typhoon.nmc.cn` |
| CMA 数据服务 | `data.cma.cn` |
| 国保空间数据 | 国家地球系统科学数据中心 `geodata.cn` |
| OSM 古建标签 | Overpass API，`historic=*` / `building=temple\|shrine\|pagoda` |
| Wikidata 文保 | SPARQL 端点 |

---

*本文档中标注 TBD / XX 的为待实测填充项，必须由实际管线跑出真实值后回填，不得估算。*
*所有对外数字以 §11.1 口径统一表为准。*
