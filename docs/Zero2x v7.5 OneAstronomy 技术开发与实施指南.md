Zero2x v7.5 OneAstronomy 技术开发与实施指南

版本：v1.7 | 状态：主开发执行标准（Main）| 更新时间：2026-03-24

文档关系（请以本文件为主）：
- 科学叙事/愿景蓝图：`docs/Zero2x v7.5：OneAstronomy 驱动的数字孪生宇宙与科学示范蓝图.md`
- Stage 2 验收规范（Docker Dev、Demo 1–4）：`docs/zero2x/Zero2x v7.5 技术方案：OneAstronomy 天文架构与场景实现规范.md`

---

## -1) 当前状态总览（必须保持“进度清晰、可回归”）

说明：本节用于快速判断“现在能演什么 / 下一步该做什么”，并与 Vitest / Docker Dev 门禁对齐。

已完成（代码已落地 + Vitest 门禁已存在）：
- 四幕剧“一键剧本”（`demo:oneastro_story` + `EXECUTE_ONEASTRO_STORY_FLOW` / `STOP_ONEASTRO_STORY_FLOW`）
- 宏观天球基底：Sky-Sphere（`MACRO_SKY_RADIUS = 100`），并禁止螺旋盘默认分布与 RA/Dec 压扁系数
- 红移爆裂：真·径向膨胀（Radial Expansion）+ `depthFade` 抑制远处过曝
- Cosmic Web 视觉重构：宏观渲染从 `InstancedMesh(SphereGeometry)` → `THREE.Points`（soft-particle shader）
- 电影级渲染特调门禁（Cinematic Polish）：Overlap Trick（大光晕+低透明度）+ Heatmap Palette + Dolly Zoom + Bloom tighten/restore
- GOTTA 捕获：网络 schema + Spline Dive（CatmullRomCurve3）
- Inpaint：World Anchor（payload/world-pos 或 ra/dec；可回退 GOTTA 最近目标）
- Astro-GIS Phase 1–3：图层状态树（layer store）+ Deep Sky Background（单 Three.js 管线 / Native Skybox）+ SIMBAD Catalog Points 叠加 + 后端契约测试/Dev&Prod smoke
- Deep Sky Background（Texture Skybox）资产准备：ESO 一键脚本（`tools/prepare_eso_milkyway_8k.sh`）+ 生成物 gitignore（避免误提交大文件）
- Deep Sky Background（Texture Skybox）工程硬约束已收敛：`renderOrder = -999` 绝对垫底 + `BackSide` + `depthWrite/test:false` + 贴图异步加载完成后强制回刷 layer-state（修复 Earth→Sky 首次切换“贴图加载了但不显示”）
- Phase 2.7：Cinematic Polish 工程化（关键参数纳入 layer store + STOP/取消路径 restore baseline，避免长期漂移）
- Phase 2.7：Catalog 可用性增强（hover/pick HUD + 大视场点数上限 + 确定性抽样，避免卡顿/闪烁）
- Phase 2.7：Provider 扩展（VizieR 端点 + 前端图层/参数 UI + pytest 契约门禁）
- Phase 2.8（部分）：Cinematic Polish 2.0（Fat Halo + Void Exaggeration + 点大小上限解锁 + Bloom tighten 参数升级）

下一步（必须先写 Gate 再改实现）：
- Astro-GIS（增强 / Phase 2.8 候选）：Catalog online provider 扩展（VizieR 多 catalog/更多列；安全 ADQL 白名单）+ label 常驻/过滤（mag/otype）+ 性能剖析（视场变化/抽样/交互拾取成本）
- Cinematic Polish（增强 / Phase 2.9 候选）：Preset 化（多套 palette/bloom/dolly 参数一键切换）+ 更细的“恢复基线”门禁（覆盖更多中断路径与异常回退）

## 0) 核心设计哲学（从蓝图整合而来）

本项目不追求“碎片化特效 Demo”，而是以 OneAstronomy 为核心，把可视化演示升级为“计算重塑（Compute-driven）”的科研工作流。

三条不可动摇的原则：

1) One Universe（绝对连续的单一宇宙空间）
- 目标态：所有科学事件发生在同一空间坐标系与同一渲染上下文内；转场只允许通过相机运动（FlyTo/Zoom）实现“一镜到底”。

2) Micro-Real-Data（微型真实数据注入）
- 目标态：摒弃 `Math.random()` 作为“宇宙数据源”，用可公开复现的数据切片（SDSS/Gaia 等）驱动点云与红移属性。

3) Workflow as Narrative（科研流叙事）
- 目标态：把“数据获取 → 模型特征提取 → 物理演算 → 发现新知”变成可被 Copilot 驱动的连贯任务剧本。

---

## 1) 架构基座与核心公约（当前实现 vs 目标态）

### 1.1 渲染上下文（Singleton Context）

目标态（Phase 3）：
- 单一 `THREE.Scene()` + 单一渲染器上下文，所有任务只是在同一个场景树中“出现/退让/销毁”。

当前基线（Phase 2 / 已落地）：
- 由于宏观深空与微观晶格的渲染差异，当前实现采用 macro/micro 双场景（见 `frontend/src/views/workbench/engines/ThreeTwin.vue` + `executeQuantumDive`）。
- **公约**：不允许通过路由跳转/重载页面来切换任务；动作必须由 `astroStore.currentAgentAction` 驱动，在同一组件生命周期内完成。

### 1.2 坐标与尺度公约（可测试、可复现）

项目已有的天文坐标工具：
- `frontend/src/utils/astronomy/coordinateMath.js`
- 现有门禁：`frontend/tests/coordinateMath.test.js`

约定：
- RA/Dec 以度为输入，内部统一转换为单位向量。
- 距离使用 log-scale 映射（`logScaleDistance()`），避免宇宙尺度下的数值爆炸与 Z-fighting。

### 1.3 场景霸权（Scene Authority）——必须用代码“强制执行”

定义：任何新任务启动时，必须显式对旧任务执行“退让或销毁”，避免 Demo 之间互相污染。

已落地的 Stage 2 霸权规则（对应修复点）：
- Demo 1（Redshift Burst）触发前：强制停止 Demo 3（避免 inpaint 遮挡/污染）
- Demo 3（Modal Inpaint）触发时：
  - 背景星海 `u_opacity → 0.15`（主动退让）
  - 红移爆裂 `u_redshift_scale → 0`（**层级降维**，避免爆裂粒子“刺穿”inpaint 面片）
- 离开 macro（进入 micro 下潜）时：强制 stop inpaint（避免穿帮）

视觉无界融合（Anti-screenshot rule）：
- 所有二维面片必须：纯黑底 + `AdditiveBlending` + 边缘羽化（edge feather / vignette），消灭任何“方形截图边界”。

### 1.4 视觉可读性门禁（Graphics & Visuals Gates）

当工程链路已经打通（Action/Preset/TDD/E2E），下一阶段的核心风险会转移到“看起来不对”。本项目把关键视觉问题也纳入可回归的工程约束：

1) 宏观宇宙“坍缩 / 过曝”必须被避免
- 坍缩症状：SDSS 只有个位数/几十条时将 draw count 收缩到样本量 → 画面坍缩成几颗暗点。
- 过曝症状：数据量暴增到 2–5 万后，`AdditiveBlending` 叠加溢出 → 画面变成粉白糊糊、丢失暗弱层次。
- 约束（必须同时满足）：
  - tiny sample 禁止收缩宏观 draw count（保留程序化星海作为底座）。
  - 宏观粒子必须“沙子化”：宏观渲染使用 `THREE.Points` + soft-particle shader（点精灵光晕），禁止回退到“可读为糖果球”的球体实例渲染。
  - 宏观 Shader 底色必须极暗，透明度必须收敛（当前实现默认 `u_opacity ≈ 0.25`），高光交给叠加与 Bloom。
  - 红移爆裂期间 Bloom 必须“tighten → restore”（示例：burst 时 `threshold≈0.3, strength≈2.8`，结束后恢复到基线），避免长期过曝与状态漂移。

1.2) 宏观天球基底必须符合物理常识（Sky-Sphere Baseline）
- 症状：默认画面出现“规则的螺旋圆盘/飞碟盘”，会让红移爆裂读成“圆柱体/拉面”。
- 根因：历史遗留的 procedural spiral 种子 +（更隐蔽的）RA/Dec 轴向压扁（例如 `* 0.35`）会强行把天球变成扁盘。
- 约束（必须同时满足）：
  - 默认宏观基底必须是 2D 天球球壳（各向同性），半径以工程常量为准（当前实现为 `MACRO_SKY_RADIUS = 100`）。
  - 禁止保留螺旋盘种子逻辑作为默认分布。
  - 禁止对 RA/Dec 映射做任何“压扁系数”（例如 `dir.z * radius * 0.35`）。

1.1) 红移爆裂必须是真·径向膨胀（Radial Expansion）
- 症状：只在单轴（Y 或 Z）做位移，会读成“漂移/抖动”，没有宇宙膨胀感。
- 约束：顶点着色器必须基于“从原点指向该星系”的方向向量做径向扩张；并加入基于爆裂程度的景深衰减（避免远处过曝）。

2) CSST 分解必须“强制圆形裁切”，彻底消灭方形边缘
- 症状：即使有 vignette/edge feather，如果纹理边缘不够黑或裁切不够狠，Additive 仍可能露出四角。
- 约束：CSST plane 的 fragment shader 必须包含 circle mask（基于 UV 距离的 `smoothstep(0.45, 0.25, d)`）并与 edge feather / vignette 相乘。

3) CSST 分解必须具备空间感（避免 2D 贴纸感）
- 症状：三层面片正对相机，只做 z 轴轻微错开，会读成“叠放卡片”。
- 约束：三层 plane 必须带倾斜角（例如 `rotation.x = PI/5`）并以 y+z 组合拉开；相机运镜必须带侧向偏移（dir×up 的 side 向量）形成“解剖视角”。

### 1.5 电影级渲染特调（Cinematic Polish / 必须可回归）

说明：当 Action/数据/Shader 都“做对”后，画面仍可能读成“散落彩色糖果/均匀沙尘暴”。本节把 update_patch.md 的电影级调优建议固化为工程约束，并要求能被 Vitest wiring gate 防回归。

1) 宇宙网成型秘诀：Overlap Trick（大光晕 + 低透明度叠加）
- 核心：不要试图“清晰画出每一颗星系”；要让密集区靠 AdditiveBlending 自动烧出丝状高光。
- 当前默认（Cinematic Polish 2.0 / 已落地，且应有 Vitest wiring gate）：
  - `u_size ≈ 80`，`u_opacity ≈ 0.25`
  - Fat Halo：`alpha = pow(1.0 - sqrt(r), 2.5)`（长尾让重叠更容易发生）
  - Void Exaggeration：`densityMask`（示例：`sin(vWorldPos.x * 0.015) * ...` + `smoothstep` + `max(0.1, ...)`）
  - 点大小衰减：`gl_PointSize = clamp(u_size * (300.0 / dist), 1.0, 250.0)`
  - `depthFade` 继续保留（避免爆裂时远处过曝）

（历史 / Phase 2.7 基线）曾使用更陡的 `exp(-r * 5.0)` 与更小的 pointSize 上限；当前以 2.0 为准。

2) HDR 纵深读数：Heatmap Palette（三段热力学调色盘）
- 目的：让近/中/远（红移/深度）在色温上形成强纵深感。
- 推荐三段：Near 深邃青蓝 → Mid 紫红 → Far 烈焰橙金，并用 `smoothstep` 进行两段平滑插值。

3) “超光速张力”：希区柯克变焦（Dolly Zoom）
- 触发时机：`EXECUTE_REDSHIFT_PREDICTION`（Demo 2）执行红移爆裂时。
- 约束：在拉伸粒子的同时，必须动态拉大相机 FOV（例如 `60 → 95`），并 `onUpdate` 调用 `camera.updateProjectionMatrix()`。
- 可选加成：相机轻微 push-in（例如沿 z 轴推进 30），让“时空被拉扯”的透视畸变更明显。

4) Bloom 只点亮“丝状骨架”
- 约束：红移爆裂期间可临时压低 Bloom 阈值并增强强度（示例：`threshold≈0.3, strength≈2.8`），只让密集的星系团/丝状结构发光；结束后必须恢复到基线。

5) Demo 1（CSST）背景呼吸感
- 约束：CSST 分解时宏观背景不应被压到“纯黑虚空”；推荐将宏观不透明度维持在 `0.25–0.30` 区间（仍能读到环境层次）。

### 1.6 交互稳定性门禁（Mouse / Controls / DOM）

说明：update_patch.md 指出的“鼠标失效”属于**工程硬故障**，必须纳入可回归约束。目标是保证：Three.js 画布始终能收到指针事件；OrbitControls 不会被运镜逻辑锁死。

1) DOM 遮挡与 pointer-events
- 约束：任何覆盖在 Three.js 画布之上的全屏层（HUD、占位层）默认必须 `pointer-events: none`；只有具体面板/按钮可 `pointer-events: auto`。
- **基线决策**：坚决抵制“多 Canvas / DOM underlay 叠加”作为天文底图方案；深空背景必须在 Three.js 单一渲染管线内完成（避免交互抢占、像素对齐误差、后处理割裂与移动端兼容问题）。

2) OrbitControls 与 GSAP 运镜公约（硬规则）
- 禁止：在 GSAP `onUpdate` / render loop 中持续调用 `camera.lookAt(...)`（OrbitControls 的“死穴”，会导致拖拽/缩放锁死或弹回）。
- 必须：运镜期间只修改 `controls.target`，并调用 `controls.update()`；必要时短暂 `controls.enabled = false`，运镜结束后恢复。

3) 初始化绑定正确性（最低限）
- 约束：`new OrbitControls(camera, renderer.domElement)` 必须绑定到 `renderer.domElement`，禁止绑定到不稳定/被覆盖的外部容器。

4) 沉浸感推进（“相机入网”）
- 目标：避免“站在宇宙外看发光脑花”。红移爆裂期间建议：更激进的 push-in（例如 `pushInZ≈30–60`，强沉浸可取 60）+ 大 FOV（`60→95`）组合，使丝状结构从镜头两侧掠过。
- 注意：沉浸感调参必须仍满足“Bloom tighten→restore”“baseline restore”门禁，避免长期漂移。

---

## 2) 科学示范任务（从蓝图整合为工程任务书）

四个任务以“科学叙事”为主线，工程上统一映射为：Copilot 指令 → `astroStore` action → `ThreeTwin.vue` 执行。

### 2.0 Demo 映射与状态（四大任务 = 四个 Demo）

| Demo | 任务名 | Action（建议/目标） | 当前状态（2026-03-23） |
|---|---|---|---|
| Demo 1 | CSST 复杂星系精细结构分解 | `DECOMPOSE_CSST_GALAXY` / `STOP_CSST_DECOMPOSITION` | Implemented（已落地：可触发/可清理/可验收） |
| Demo 2 | 红移立体爆裂（Cosmic Web / Redshift Burst） | `EXECUTE_REDSHIFT_PREDICTION` | Implemented（Stage 2 已落地） |
| Demo 3 | GOTTA 瞬变源捕获（样条跃迁 + 时域 HUD） | `CAPTURE_TRANSIENT_EVENT` | Implemented（MVP：样条跃迁 + 标记闪烁 + 示例数据；HUD 后续补齐） |
| Demo 4 | 模态互生 Inpaint（扫描扩散） | `START_MODAL_INPAINT` / `STOP_MODAL_INPAINT` | Implemented（Stage 2 已落地） |

连续叙事一键剧本（Phase 2.5 / 已落地）：
- Preset：`demo:oneastro_story`（Story Flow · 4 Acts · One Take）
- Action：`EXECUTE_ONEASTRO_STORY_FLOW` / `STOP_ONEASTRO_STORY_FLOW`

说明：
- 旧文档中曾以“Demo 1 红移 / Demo 3 Inpaint”作为 Stage 2 验收编号；为了与“四大任务=四个 Demo”一致，本主文档采用 Demo 1–4 的新映射。
- 代码与 Command Palette 的展示文案若仍沿用旧编号，视为 UI 命名债（后续统一）。

### 序幕：宇宙基底的唤醒（The Data Fabric）

目标：进入 workbench 后，看到“真实数据驱动”的二维天球基底，而不是纯随机点。

工程约束：
- 微型数据池（2–5MB）放在 `frontend/public/data/astronomy/`
- 首帧渲染必须可用；数据加载可渐进增强。

数据规模策略（来自 update_patch.md 的落地结论）：
- 若 `sdss_micro_sample.json` 只有个位数/几十条（极小样本），**不得**将宏观 InstancedMesh 的 draw count 收缩到数据条数，否则画面会“坍缩成几颗暗点”。
- 推荐将 SDSS 数据扩展到 2–5 万条（约 1–2MB）用于演示；仓库内可保留 tiny sample 作为“契约样例”，通过脚本一键替换为大样本。

连续叙事（Phase 2.5 / 四幕剧）：
- 【序幕】50,000 SDSS 星系加载：作为 2D 天球底座（球壳半径按实现调参；当前宏观用 `MACRO_SKY_RADIUS = 100` 的壳层映射；并做 RA 视角对齐偏移以适配默认相机视向）。
- 【第一幕】CSST 数据降临（Demo 1）：镜头飞近并解剖星系（已落地）。
- 【第二幕】精密宇宙学红移爆裂（Demo 2 升级）：关闭 CSST 特写，镜头拉远；星系沿径向膨胀，形成 3D 纤维网。
- 【第三幕】GOTTA 时域网络预警（Demo 3）：远处目标爆闪；相机执行样条弧线跃迁（Spline Dive）。
- 【第四幕】模态互生 Inpaint（Demo 4 升级）：到达目标附近后，就地展开雷达扫描，将可见光褪变为 X 射线。

### 任务 1：CSST 复杂星系精细结构分解（DECOMPOSE_CSST_GALAXY）

目标：相机推进到目标，出现可读的三层分解图（Bulge/Disk/Bar），并能在任务切换时被清理。

验收（Docker Dev / E2E）：
- Workbench → Presets 选择 `[v7.5] OneAstronomy · CSST Galaxy Decompose (Demo 1)`：画布内出现三层分解面片（Bulge/Disk/Bar），边缘无方形截图边界（circle mask + vignette + edge feather）。
- 运镜与层次：相机以侧上方“解剖视角”推进，三层面片具备明显空间分离（倾斜 + y/z 拉开），不应读成三张重叠卡片。
- 触发 `redshift` 或 `inpaint start`：CSST 分解面片必须自动清理（Scene Authority）。
- 运行代码指令 `csst stop`：必须能显式清理 CSST 图层并恢复 macro 亮度。

### 任务 2：精密宇宙学与红移立体爆裂（EXECUTE_REDSHIFT_PREDICTION）

目标：批量红移数据到达后，点云在三维空间“爆裂展开”，并配合运镜形成宏观震撼。

Phase 2.5 数学约束：径向膨胀（Radial Expansion）
- 核心思想：以观测者（原点）为中心，将每个星系沿其方向向量 `dir` 推远。
- 着色器最小模型（伪代码）：

```glsl
float s = clamp(u_redshift_scale, 0.0, 1.0);
float z = clamp(aRedshift, 0.0, 1.0);
float baseDist = length(localPos.xyz);
vec3 dir = baseDist > 0.0001 ? (localPos.xyz / baseDist) : vec3(0.0, 0.0, 1.0);
float currentDist = baseDist + (z * u_max_depth * s);
localPos.xyz = dir * currentDist;
```

- 过曝控制：片元端必须使用极暗底色 + 基于爆裂程度的 `depthFade`，避免 2–5 万点在 Additive 下糊成一坨白光。

### 任务 3：GOTTA 瞬变源捕获（CAPTURE_TRANSIENT_EVENT）

目标：远处闪烁目标 + 样条曲线跃迁运镜 + 时域 HUD（可先 mock）。

Phase 2.5 约束：Spline Dive（弧线跃迁）
- 触发 `CAPTURE_TRANSIENT_EVENT` 后，相机必须使用 `THREE.CatmullRomCurve3` 做弧线飞行，而不是直线 tween。
- 运镜期间**禁止**在 `onUpdate`/render loop 中持续调用 `camera.lookAt(...)`（OrbitControls 死锁风险）。
- 必须：用 `controls.target` 指向目标，并在更新 target 后调用 `controls.update()`；到达后确保 target 与视点一致，避免视点漂移。

### 任务 4：模态互生 Inpaint（START_MODAL_INPAINT / STOP_MODAL_INPAINT）

目标：扫描扩散替换纹理，具备边缘噪声；在 Additive 模式下无方形边界。

Phase 2.5 约束：World Anchor（锚定到 3D 目标）
- `START_MODAL_INPAINT` 必须允许携带 payload 用于锚定：
  - `payload.position` 或 `payload.x/y/z`（世界坐标）
  - 或 `payload.ra/dec`（可选 `payload.z` 用于推深）
- 若未提供 payload，允许回退到最近一次 GOTTA 目标位置（避免“贴在镜头上”的穿帮感）。

---

## 3) 数据源准备与预处理管线（Micro-Real-Data）

原则：把“真实数据切片”变成可在 Docker Dev 里复现的固定资产。

### 3.1 SDSS 星系与红移（用于序幕 + 红移爆裂）

目的：抓取约 2 万个真实星系（RA/Dec/redshift），用于初始二维天球点云与后续立体红移爆裂。

依赖：`pip install astroquery pandas`

脚本建议（放到 `backend/scripts/` 或 `tools/`，并在 README 里说明数据许可证与来源）：

```py
# fetch_sdss_micro_data.py
from astroquery.sdss import SDSS
import pandas as pd
import json

query = """
SELECT TOP 20000
    p.ra, p.dec, s.z as redshift, s.class
FROM PhotoObj AS p
JOIN SpecObj AS s ON s.bestobjid = p.objid
WHERE s.class = 'GALAXY' AND s.z > 0.01 AND s.z < 0.5
"""
res = SDSS.query_sql(query)
df = res.to_pandas()

output_data = []
for _, row in df.iterrows():
    output_data.append([round(row['ra'], 4), round(row['dec'], 4), round(row['redshift'], 4)])

with open('frontend/public/data/astronomy/sdss_micro_sample.json', 'w') as f:
    json.dump(output_data, f)
```

输出路径约定：`frontend/public/data/astronomy/sdss_micro_sample.json`

格式约定（两种都支持；推荐 flat 更省体积/更快解析）：

1) 2D triples（易读）：

```json
[[83.6331, 22.0145, 0.0234], [10.6847, 41.2692, 0.0123]]
```

2) flat array（推荐，体积更小）：

```json
[83.6331, 22.0145, 0.0234, 10.6847, 41.2692, 0.0123]
```

### 3.2 GOTTA 瞬变源光变曲线 (Mock JSON)

输出路径约定：`frontend/public/data/astronomy/gotta_transient_event.json`

格式：`gotta_transient_event.json`

推荐 schema（体现“网络感”）：

```json
{
  "targetEventId": "GOTTA-2026a",
  "events": [
    {
      "eventId": "GOTTA-2026a",
      "ra": 83.63,
      "dec": 22.01,
      "type": "Supernova Ia",
      "lightcurve": { "time": [0, 1, 2, 3, 4, 5], "flux": [10, 45, 120, 95, 40, 15] }
    },
    { "eventId": "VAR-0001", "ra": 80.12, "dec": 18.45, "type": "Variable" },
    { "eventId": "VAR-0002", "ra": 88.76, "dec": 25.31, "type": "Variable" }
  ]
}
```

兼容：也允许旧格式（单个事件对象：`{eventId, ra, dec, ...}`），用于最小样例。


## 4) 研发计划（以 TDD 为中心）

当前分支门禁：前端 `npm test`（Vitest）必须全绿；Docker Dev 端到端验收以 `docs/zero2x/...实现规范.md` 为准。

### Phase 2.1（已完成）：Stage 2 Demo 稳定性加固
- Demo 1 / Demo 3 场景霸权：互斥、退让、离开 macro 自动清理
- inpaint 无边界：Additive + vignette/edge feather

### Phase 2.2（已完成）：Micro-Real-Data 注入（替换随机宇宙）
- 把宏观点云从 `Math.random()` 迁移到 `sdss_micro_sample.json`
- 保持 `aRedshift` attribute 结构不变，保证 Demo 1 动画仍可用
- 约束：新增数据加载不得破坏现有 `threeTwinWiring.test.js` 门禁

### Phase 2.3（已完成）：Demo 1（CSST）分解最小闭环
- Action：`DECOMPOSE_CSST_GALAXY` / `STOP_CSST_DECOMPOSITION`
- 入口：Workbench Preset + run-code 命令通道（`csst` / `csst stop`）
- 霸权：触发 redshift / inpaint 必须清理 CSST 图层

### Phase 2.4（目标态预研）：One Universe（单场景）重构
- 将 macro/micro 双场景切换收敛为单场景树 + 任务层级管理
- 把 quantumDive 从“切 scene”演进为“相机尺度变换 + 任务清理”

### Stage 3：Demo 2 & Demo 4
- Demo 2：检索契约 + 样条运镜骨架 + 最小 HUD
- Demo 4：WebGPU Compute 能力探测 + 降级路径 + 性能基线

### Phase 2.5（已完成）：连续叙事 + 物理一致性补齐
- 红移爆裂升级为真·径向膨胀（Radial Expansion）+ `depthFade` 抑制远处过曝
- GOTTA 引入 CatmullRomCurve3 “Spline Dive” 运镜
- Inpaint 支持 world anchor（payload / GOTTA 回退）并维持 world-space billboard
- 新增“一键四幕剧本” preset + action runner，并支持 STOP 取消
- 修复宏观 SDSS 默认“螺旋圆盘”假象：宏观基底改为 sky-sphere；禁用 RA/Dec 压扁系数

### Phase 2.6（已完成 / TDD 驱动）：Cosmic Web 视觉重构 + Astro-GIS Phase 1

目标 A：Cosmic Web 视觉重构（从“散点糖果”到“丝状宇宙网”）
- 现状问题：球形实例在高密度 Additive 下仍容易读成“独立彩色小球”，难以形成星系团/纤维网的亮度融合。
- 方案：废弃 `InstancedMesh(SphereGeometry)`，采用 `THREE.Points` + soft-particle shader（`gl_PointCoord` 数学光晕），靠 Additive 自融合出密度感。

验收约束（必须满足，且应纳入 Vitest wiring gate）：
- 宏观渲染对象必须是 `new THREE.Points(geometry, material)`；几何必须是 `THREE.BufferGeometry`。
- 必须包含 attribute：`position`（Float32Array）与 `aRedshift`（Float32Array），并在 shader 中读取。
- fragment 必须包含“切角”逻辑（`if (r > 1.0) discard;`），保证点精灵无方形边界。
- vertex 必须包含基于距离衰减的 `gl_PointSize`（近大远小），并做最小像素钳制。
- 红移爆裂仍必须是径向膨胀（Radial Expansion），且仍受 Scene Authority 管控（inpaint 启动会把爆裂收回 0）。

目标 B：Astro-GIS Phase 1（Foundation / 图层状态树）
- 交付物：在 `astroStore` 引入 layer state（visible/opacity/style/source），并由 `ThreeTwin.vue` watch 进行实时映射。
- 最小范围（先不接外部数据源也必须可用）：
  - `layer:macro_sdss`（宏观宇宙网/天球底座）
  - `layer:demo_csst`（CSST 分解面片组）
  - `layer:demo_gotta`（GOTTA transient group）
  - `layer:demo_inpaint`（modal inpaint plane）

当前实现状态（2026-03-23）：
- Cosmic Web 已切换为 `THREE.Points` soft-particle 路径，并由 Vitest wiring gate 防回归。
- Astro-GIS layer store + UI（LayerTree）已落地，并与 ThreeTwin 的运行态映射闭环。
- Astro-GIS Phase 2（Deep Sky Background）与 Phase 3（Catalog）已落地；后端有 pytest 契约门禁，Makefile 含 dev/prod smoke。

### Phase 2.7（已完成 / TDD 驱动）：Cinematic Polish 工程化 + Astro-GIS 交互能力

交付目标 A：Cinematic Polish 工程化（从“硬编码调参”到“可控 + 可恢复 + 可验收”）
- Gate（Vitest wiring gate，先红后绿）：
  - 宏观 Points Shader 的 Overlap Trick（2.0）默认值存在（`u_opacity≈0.25`、`u_size≈80`、`alpha = pow(1.0 - sqrt(r), 2.5)`、`densityMask`、size cap 250）
  - Heatmap Palette 三段插值存在（Near/Mid/Far + `smoothstep` 两段）
  - Redshift Burst 包含 Dolly Zoom（`fov→95` + `camera.updateProjectionMatrix()`）
  - Bloom tighten 可回滚（burst 中 `threshold≈0.3,strength≈2.8`，STOP/结束后恢复到 baseline）
- Green（实现落地）：
  - 将 `baseOpacity/palette(near/mid/far)/burst(dollyFov/pushInZ/bloom)` 纳入 Astro-GIS layer store（默认值在 `astroStore`）
  - ThreeTwin 在 STOP / 叙事取消路径中统一调用 `restoreCinematicBaseline`，避免长时间状态漂移

交付目标 B：Astro-GIS Phase 3+（可用性增强：hover/pick + 性能安全）
- Gate（Vitest wiring gate，先红后绿）：
  - Catalog overlay 支持 hover/pick（raycast 最小路径）并以 HTML HUD 显示 `name/mag/otype/ra/dec`
  - 大视场点数硬上限 + 确定性抽样（避免一次渲染数万点造成卡顿/闪烁）
- Green（实现落地）：
  - ThreeTwin 增加 `catalog-hud` overlay + `Raycaster` hover/pick（`pointermove/pointerdown`）
  - 新增 `CATALOG_MAX_RENDER_POINTS` 与 `sampleCatalogSources()`（deterministic sampling）

交付目标 C：Provider 扩展（SIMBAD → VizieR）
- Frontend：新增 layer id `CATALOG_VIZIER`，LayerTree 暴露 `maxRows` 与 `catalog`（默认 `I/239/hip_main`）
- Backend：新增端点 `GET /api/astro-gis/catalog/vizier`（默认 fixture，在线模式可选）
  - 参数：`ra, dec, radius, maxRows, catalog`
  - 安全约束：catalog id 进行白名单格式校验，默认离线 fixture 保证单测/离线部署稳定

验收/回归（建议作为最小交付证明）：
- Backend：`make test-fast`
- Frontend：`cd frontend && npm test`

落地文件索引（便于 Review/回归定位）：
- Frontend
  - Astro-GIS layer ids + Cinematic 默认参数：`frontend/src/stores/astroStore.js`
  - 图层 UI（VizieR 参数：maxRows/catalog）：`frontend/src/views/workbench/components/LayerTree.vue`
  - UI→layer store 同步（VizieR layer/params）：`frontend/src/WorkbenchApp.vue`
  - 引擎实现（HUD、raycast、sampling cap、cinematic baseline restore、VizieR endpoint wiring）：`frontend/src/views/workbench/engines/ThreeTwin.vue`
- Backend
  - Catalog service（fixture/online/caching + VizieR 安全校验）：`backend/astro_gis_catalog.py`
  - API routes：`backend/main.py`
- Tests (Gates)
  - 前端 wiring gate（Phase 2.7 tokens：`catalog-hud`、`sampleCatalogSources`、`restoreCinematicBaseline`、`/api/astro-gis/catalog/vizier` 等）：`frontend/tests/threeTwinWiring.test.js`
  - layer store contract（新增 `CATALOG_VIZIER` 可见性/重置约定）：`frontend/tests/astroGisLayerStore.test.js`
  - 后端契约测试（SIMBAD + VizieR schema / determinism / invalid params→400）：`tests/test_astro_gis_catalog_api.py`

---

## 5) TDD 详细研发（按“红-绿-重构”执行）

本仓库现有 TDD 风格偏“wiring gate（字符串/结构门禁）”，先保证集成不碎，再逐步引入可运行的更细粒度单测。

### 5.1 必须新增/维护的 Vitest 门禁（建议直接落在现有测试文件）

1) `frontend/tests/threeTwinWiring.test.js`
- 断言 inpaint 使用 `AdditiveBlending`、`depthTest: false`
- 断言 inpaint plane 处于世界空间（例如 `.position.set(0, 0, 15)`）
- 断言 shader 内含 edge feather / vignette（避免回归“截图边界”）
- 断言 “霸权 2.0”存在：`u_redshift_scale` 在 `_startModalInpaint()` 内被 tween 回 0
- Phase 2.5：断言红移爆裂为径向膨胀（Shader 内出现 `baseDist` / `currentDist` / `dir` 逻辑）
- Phase 2.5：断言 GOTTA 使用 `CatmullRomCurve3` 做 Spline Dive
- Phase 2.5：断言 `_startModalInpaint(payload)` 支持 payload 锚定（并可回退 GOTTA 最近目标）
- 反回归：断言宏观天球基底为 sky-sphere（包含 `MACRO_SKY_RADIUS = 100`），并禁止出现螺旋盘种子与 RA/Dec 压扁系数（例如 `* 0.35`）
- Phase 2（Deep Sky Background / Two-Gear）：断言 `preset: texture` 存在且满足单管线规训（`TextureLoader` + `SRGBColorSpace` + mipmaps/minFilter + `BackSide` + `depthWrite/test:false` + `renderOrder = -999` + mild tinting），并禁止出现任何 DOM underlay（如 `aladin`）
  - 关键反回归：**禁止**将该贴图当作 envMap 使用（不得出现 `EquirectangularReflectionMapping`）；优先用 `material.side = THREE.BackSide` 而非几何 `scale(-1,1,1)`
  - 关键反回归：贴图异步加载完成后必须回刷一次 layer-state（否则会出现“贴图 ready 但 showTexture 条件从未重新计算”的隐性黑屏）

2) `frontend/tests/engineScaleRouterWiring.test.js`
- 断言 macro→micro 的切换仍通过 `executeQuantumDive` 路径
- 断言离开 macro 会 stop inpaint（避免穿帮）

3) `frontend/tests/coordinateMath.test.js`
- 继续作为“真实数据映射”数学正确性的基础门禁

### 5.2 任务拆解（每个任务都要先写 gate，再实现）

任务 A：Micro-Real-Data（SDSS）接入
- Red：新增 wiring gate：`ThreeTwin.vue` 出现 `fetch('/data/astronomy/sdss_micro_sample.json')` 与对 `raDecDistanceToCartesian`/`raDecToUnitVector` 的调用
- Green：实现加载 + instancing 填充 + attribute 写入
- Refactor：把“数据解析/映射/填充”抽成纯函数（便于未来做真正的运行态单测）

任务 B：Demo 2（检索 + 运镜）骨架
- Red：新增 wiring gate：action type、调用样条运镜 helper、失败兜底
- Green：先 mock 数据（不等后端），确保运镜可触发且可停止
- Refactor：将运镜库封装为可复用函数，避免散落 gsap timeline

任务 C：Demo 3（inpaint）鲁棒性回归
- Red：门禁覆盖“无方形边界”“离开 macro 自动清理”“触发 inpaint 收缩 redshift”
- Green：保持现有实现
- Refactor：把“场景霸权规则”集中到一处，避免分散在多个函数里难以维护

任务 D：update_patch.md 终极修复收敛（交互 + 天球层级 + 8K 贴图稳定性）

目标：把“鼠标失效 / 天球遮挡 / 8K 贴图黑屏或不显示 / 切换场景后状态漂移”等高频故障，固化为可回归的工程硬约束。

- Red（先写 Gate）：在 `frontend/tests/threeTwinWiring.test.js` 增加/加严以下门禁（wiring tokens 即可）
  - Canvas 与 HUD：必须存在 `.three-twin { pointer-events: auto !important; z-index: 10; }`，且 HUD/overlay 默认 `pointer-events: none`
  - OrbitControls 死锁：禁止出现 `camera.lookAt(`，运镜必须通过 `controls.target` + `controls.update()`
  - Texture Skybox：必须满足 `BackSide` + `depthWrite/test:false` + `renderOrder = -999` + mipmaps/minFilter + mild tinting（`0x888888`）
  - Texture Skybox 异步一致性：必须存在“贴图加载完成后回刷 layer-state”的逻辑（防 Earth→Sky 首次切换不显示贴图）
  - 相机裁剪面：`PerspectiveCamera(..., 0.1, 50000)`（或等价）防天球裁剪

- Green（实现落地）：只做最小代码改动满足 Gate
  - Deep Sky Texture onLoad 回调内：加载完成后调用一次 `_applyAstroGisLayerState(astroStore.astroGis.value)` 或 bump `astroGis.version`
  - Skybox `renderOrder` 固定为 `-999`（强制垫底）；前景资产维持正 renderOrder（inpaint/markers/catalog 等）
  - 保持“单管线”：禁止引入 DOM underlay（Aladin/多 canvas）

- Refactor（可选，且不改变外部行为）：抽离小函数，让规训更难被误改
  - `applyDeepSkyDimming({ targetDim, duration })`
  - `ensureTextureSkybox({ texturePath })`（onLoad 内统一处置：mipmaps/filters/colorspace/renderOrder/opacity sync）

---

## 6) Copilot 叙事主导（工程约定）

右侧 Copilot 面板不只是日志输出，而是“科学解说员”。每个任务触发时建议输出：
- 数据阶段：加载/解析/映射完成
- 模型阶段：请求/推理/回传完成
- 物理阶段：约束校验/退让规则执行
- 视觉阶段：运镜/后处理/任务清理完成

序幕：宇宙基底的唤醒 (The Data Fabric)

执行逻辑：页面挂载时，fetch `sdss_micro_sample.json`，将 (RA, Dec) 映射到固定半径的天球球壳（当前实现为 `MACRO_SKY_RADIUS = 100`），并把红移写入 `aRedshift`（初始 `u_redshift_scale = 0`）。

关键约束：
- 必须使用天球球壳（各向同性），禁止任何轴向压扁系数（例如 `* 0.35`）。
- tiny sample 只能“局部注入”，不能把宏观 draw count 收缩到样本量（避免画面坍缩）。

实现约定（避免伪代码重复；以真实代码为准）：

- 所有任务在 `frontend/src/views/workbench/engines/ThreeTwin.vue` 内执行，并由 `astroStore.currentAgentAction` 驱动。
- Demo→Action 映射以 `frontend/src/stores/astroStore.js` + Workbench Preset 为准。
- Copilot 输出只要求“可解释 + 可追溯”：数据阶段/模型阶段/物理阶段/视觉阶段四段日志即可。

必须满足的叙事/工程约束（门禁已存在或应补齐）：

- 序幕（数据织物）：`/data/astronomy/sdss_micro_sample.json` 加载失败不得阻塞首帧；tiny sample 不得坍缩宏观 draw count。
- Demo 1（CSST）：必须 circle mask + edge feather/vignette；必须 tilt + side-view 运镜避免贴纸感；触发 redshift/inpaint 必须自动清理（Scene Authority）。
- Demo 2（Redshift Burst）：必须真·径向膨胀；必须 Dolly Zoom（FOV pull + `camera.updateProjectionMatrix()`）；Bloom tighten 必须能 restore baseline。
- Demo 3（GOTTA）：必须 CatmullRomCurve3 样条跃迁；到达后必须同步 `controls.target`，避免视点漂移。
- Demo 4（Inpaint）：必须 Additive + depthTest/write 关闭 + 强边缘羽化；必须支持 world anchor payload，并允许回退 GOTTA 最近目标。

---

## 7) Astro-GIS（对标 Cesium 的天文图层化）——分期落地

愿景：把 OneAstronomy 从“特效 Demo”升级为可扩展的虚拟天文台：影像底图（未来可演进为 HiPS/巡天贴图，但必须保持单 Three.js 管线）+ TAP/SIMBAD/VizieR（星表要素）+ Three.js（业务 3D 图层）。

Phase 1（Foundation / 已完成）：图层状态树（Astro Layer Store）
- 目标：在 `astroStore` 建立标准的 layer state（visible/opacity/style/source），并由 `ThreeTwin.vue` 将其映射到 Three.js 资产。
- 当前落地：LayerTree UI 可控显隐/透明度；并与 Demo 场景霸权规则兼容。

Phase 2（Deep Sky Background / 里程碑）：单管线深空背景（Native Skybox）
- **正确方案（本项目基线 / 已实现）**：Deep Sky Background 必须作为 Three.js 场景内的背景资产（翻转天球/skybox shader），与宏观点云同一渲染上下文、同一后处理链路。
- 关键收益：无多 Canvas 叠加；不抢 OrbitControls 指针事件；Bloom/色调映射/截图一致；移动端层级更稳定。

两档切换策略（Two-Gear Strategy / 来自 update_patch.md，已工程化）：
- Gear 1（默认态）：`preset: procedural | black`
  - 目的：首帧稳定、离线可用、低资源占用。
  - 约束：必须仍在 Three.js 单管线内（翻转天球 + shader），禁止 DOM/Canvas underlay。
- Gear 2（按需开启）：`preset: texture`（Native 8K Equirectangular Texture）
  - 目的：在演示需要“真实巡天影像质感”时启用，但仍保持 One Universe 的单一渲染上下文。
  - 工程规训（必须满足，且建议由 Vitest wiring gate 防回归）：
    - 贴图加载：`THREE.TextureLoader()`；`texture.colorSpace = THREE.SRGBColorSpace`
      - 重要：本项目将该资源作为 `MeshBasicMaterial.map` 的**普通贴图**使用，**禁止**设置 `EquirectangularReflectionMapping`（那是 envMap 反射用，会引入错误假象与亮度/方向问题）
    - 几何：超大天球（equirect pano → sphere map），优先用 `material.side = THREE.BackSide` 渲染内表面（不强依赖几何翻转）
    - 材质：`THREE.MeshBasicMaterial` 且 `depthWrite: false`、`depthTest: false`（绝对深度隔离，避免与点云穿插）
    - 采样质量：`texture.generateMipmaps = true` + `texture.minFilter = THREE.LinearMipmapLinearFilter`
    - 内表面渲染：优先用 `material.side = THREE.BackSide`（避免几何翻转带来的包围盒/剔除异常）
    - 底图压暗（Tinting）：建议使用温和灰度（例如 `0x888888`）+ `opacity ≈ 0.8`，避免“乘黑”导致 8K 底图全黑/隐身
    - 渲染顺序：`renderOrder = -999`（强制打破透明物体中心排序；确保天球永远最先渲染、不遮挡前景）
    - 相机裁剪面：若存在大尺度拉远/跃迁，建议将 `camera.far` 扩大到 `>= 50000`，避免天球被裁剪或离开天球后读成纯黑
    - 异步加载一致性：贴图加载完成后必须回刷一次 layer-state（或 bump 版本）以重新计算 `showTexture`，避免“切换到 sky 后贴图完成但仍停留在 procedural fallback”
  - 资产约定：纹理文件不应强绑定到仓库（许可证/体积风险）；推荐由部署方放入 `frontend/public/assets/` 并通过 `texturePath` 配置加载。
  - 一键生成（推荐）：在仓库根目录执行 `bash tools/prepare_eso_milkyway_8k.sh`，会自动下载 ESO 源图、缩放到 8192×4096、原子写入并清理源文件（生成物已被 .gitignore 排除）。
- 演进方向（未来 Phase 2.x）：若需要“真实巡天影像（HiPS/DSS2/WISE 等）”，应以单管线方式实现（例如：服务端瓦片/拼接 → 贴图到天球；或直接在 Three.js 内做 HiPS tile selection + texture atlas），而非引入外部 DOM/Canvas underlay。

弃用声明：
- Aladin Lite underlay 方案在本项目中视为弃用/不再推荐（多 Canvas 叠加违背 One Universe 的单一渲染上下文原则，并引入交互与后处理分裂）。

Phase 3（Vector Features / 里程碑）：Catalog 要素层（SIMBAD/VizieR）
- 目标：视场停止（debounce）后请求当前 FOV 区域的星表数据，渲染为 Instanced/Sprite/Label，并可被图层状态树统一管理。

后端接口与模式约定（Catalog / SIMBAD & VizieR）：

通用约定：
- 默认模式：离线 deterministic fixture（CI/离线环境稳定，且契约可回归）
- Online 模式：显式开启才走网络；失败默认回退 fixture（可配置为不回退）

SIMBAD：
- Endpoint：`GET /api/astro-gis/catalog/simbad?ra=...&dec=...&radius=...&maxRows=...`

VizieR：
- Endpoint：`GET /api/astro-gis/catalog/vizier?catalog=I/239/hip_main&ra=...&dec=...&radius=...&maxRows=...`
- 现阶段在线模式范围（Phase 2.7）：仅允许 `catalog=I/239/hip_main`（Hipparcos 主表），避免泛化 ADQL 带来的安全与稳定性风险。

Online 模式（对 SIMBAD/VizieR 共同生效）：
- `ASTRO_GIS_CATALOG_MODE=online`（否则默认 `fixture`）
- `ASTRO_GIS_CATALOG_ONLINE_TIMEOUT_S=8`（秒；VizieR 默认可略高，实际实现为 best-effort）
- `ASTRO_GIS_CATALOG_ONLINE_FALLBACK=1`（默认 1；设 0 则 online 失败直接抛错）

上游 TAP Sync URL（可覆写）：
- `ASTRO_GIS_SIMBAD_TAP_SYNC_URL=https://simbad.cds.unistra.fr/simbad/sim-tap/sync`
- `ASTRO_GIS_VIZIER_TAP_SYNC_URL=https://tapvizier.u-strasbg.fr/TAPVizieR/tap/sync`

缓存（在线模式推荐开启；对 SIMBAD/VizieR 共同生效）：
- `ASTRO_GIS_CATALOG_CACHE_TTL_S=30`（秒，默认 30）
- `ASTRO_GIS_CATALOG_CACHE_MAX_ITEMS=256`（默认 256）