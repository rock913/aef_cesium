Zero2x v7.5 架构蓝图：基于 HEALPix 与大模型的下一代天文数字孪生工作台（落地版）

文档代号：Phase 2.0 - "Omni-Sphere & WebGPU"

本蓝图以《Zero2x v7.5 技术方案：OneAstronomy 天文架构与场景实现规范》为主规格，并与本仓库现状对齐：**不推倒重来**，在既有 `/workbench` 壳上演进出 OneAstronomy（天文态）。

---

## 0. 工程落地口径（必读）

唯一约束源：根目录 `AI_CONTEXT.md`。

硬约束摘要：

- Agent 驱动：业务动作来自 `frontend/src/stores/astroStore.js` 的 `currentAgentAction`
- 无按钮化：不在 3D 画布上层新增 `<button>/<select>`；复用 Workbench 玻璃拟态面板
- 双引擎一镜到底：Cesium 近地 / Three 深空，交接需相机姿态严格一致
- HEALPix 仅作索引：视锥索引 + 分块加载，不作为渲染网格
- WebGPU-first（允许显式降级）：默认 WebGPU；不支持时进入 fallback（关闭 compute/N‑Body）

---

## 1. 目录映射（本仓库真实路径）

v7.5 的实现应尽量落在既有 workbench 体系内，避免另起炉灶：

- Workbench 容器：`frontend/src/WorkbenchApp.vue`
- 引擎路由（交接容器）：`frontend/src/views/workbench/EngineRouter.vue`
- 引擎缩放路由（现有）：`frontend/src/views/workbench/EngineScaleRouter.vue`
- Three 引擎：`frontend/src/views/workbench/engines/ThreeTwin.vue`
- Action Store（新增/已落地）：`frontend/src/stores/astroStore.js`

建议新增（按阶段落地）：

- 坐标数学：`frontend/src/utils/astronomy/coordinateMath.js`
- 交接对齐：`frontend/src/utils/astronomy/engineHandover.js`
- Astro‑Tiles/HEALPix worker：`frontend/src/views/workbench/engines/astro/`（或相邻目录）

---

## 2. 核心底座革命：打造天文学的“CesiumJS”

传统 Web3D 引擎处理宇宙空间的两个硬问题：

- 精度：尺度跨越导致浮点溢出 / Z‑fighting
- 调度：海量数据的视区索引与 LOD

v7.5 的底座突破来自三个“分层解耦”：

### 2.1 HEALPix 作为索引层（Astro‑Tiles）

设计理念：采用 HEALPix（等面积像素化）作为 **数据加载索引**。

- 低 LOD：宏观视角加载低 $N_{side}$ 的密度/影像（可为 HiPS/预切片）
- 高 LOD：对数相机拉近后，以视锥覆盖的 pixel index 集合为 key 拉取更细分块
- Worker：HEALPix 计算与索引解析放入 WebWorker，避免主线程抖动

注意：HEALPix **不等于**“必须渲染出来的网格”。渲染层可选：点云、instancing、HiPS 贴图、体渲染等。

### 2.2 统一坐标系（地球为原点）

Three 世界原点 `(0,0,0)` 永远是地球。所有天体数据（RA/Dec/Distance 或 redshift）必须转换成地心笛卡尔，并可使用对数缩放避免爆表。

### 2.3 对数相机与视觉锚点

- Logarithmic Camera：滚轮步长随距离按比例变化（例如 15%）
- Galactic Grid：球形发光网格（RA/Dec 或银道坐标）作为“宇宙地板”
- Cosmic Scale HUD：显示当前视野对应物理尺度（AU/pc/kpc/Mpc）

---

## 3. 渲染引擎升级：WebGPU‑first + Compute（带降级门禁）

目标：将“百万级粒子/点云 + 后处理 +（可选）compute”保持在可用硬件上的稳定帧率。

- 默认：Three `WebGPURenderer`
- 降级：当 `navigator.gpu` 不可用/adapter 失败，切到 `WebGLRenderer`（仅静态点云/instancing）并进入 `astroStore.mode='fallback'`
- 安全提示：WebGPU 在主流浏览器需要安全上下文（HTTPS 或 localhost）

Compute（WGSL）建议策略：

- 先在沙盒验证，再回注主干
- 资源绑定隔离：避免同一 buffer 同时 read_write 与 render 读取（降低兼容风险）

---

## 4. 智算融合：AION‑1 驱动的四大核心场景（Action 合约）

四大 Demo 必须以 action 合约驱动，避免“按钮耦合”。建议 action type 与 `astroStore` 对齐：

### 4.1 Demo 1：深空巡天与红移爆裂（Cosmic Web）

- 触发：`EXECUTE_REDSHIFT_PREDICTION`
- 数据：视区 HEALPix 索引 -> 预加载星系数组（可先 mock）
- 视觉：二维球面（缺乏深度）-> GSAP 拉伸到对数深度三维（3.5s）

### 4.2 Demo 2：强引力透镜检索（Zero‑Shot Search）

- 触发：`SEARCH_SIMILAR_LENS`
- 数据：Top‑5 目标坐标（RA/Dec）-> 仅加载 5 个天区
- 运镜：CatmullRomCurve3 + FOV warp（虫洞折跃感）

### 4.3 Demo 3：跨模态扫描波纹（Modal Inpainting）

- 触发：`START_MODAL_INPAINT` / `STOP_MODAL_INPAINT`
- 状态：`astroStore.aionModelState.isGenerating`
- Shader：以视区中心为原点，时间驱动扩散波纹，内外采样不同模态纹理，边缘噪声 + HDR 强度供 Bloom

### 4.4 Demo 4：端侧 N‑Body（Physics‑Informed Twin）

- 触发：`SIMULATE_GALAXY_COLLISION`
- 计算：WebGPU compute 更新 10–20 万粒子（根据硬件上限动态缩放）
- 渲染：GPU buffer 直通 vertex shader，目标 60FPS

---

## 5. 升级路径与验收门禁（可执行）

里程碑建议与门禁（与工作流文档一致）：

- M0（Workflow Upgrade）：`AI_CONTEXT.md` + `astroStore` + 三份文档口径统一
- M1（MVP 壳结构）：EngineRouter 双栈交接 + WebGPU-first 初始化 + 坐标/交接函数第一版 + 最小测试
- M2（Demo 1&3）：红移爆裂与扫描波纹 shader
- M3（Demo 2&4）：透镜检索折跃运镜与 N‑Body compute

验收门禁：

- `frontend`: `npm test`（vitest）不退化
- 不新增 3D 画布按钮交互
- handover 叠画时背景重合（主观验收；可选截图差分）

总结：Zero2x v7.5 的关键不是“再写一个星空 Demo”，而是建立一套可复用的 OneAstronomy 底座：以 HEALPix 为索引骨架、以 WebGPU 为算力肌肉、以 AION‑1 为智能大脑，并在现有 Workbench 架构内实现跨引擎的一镜到底。