# Zero2x v7.5 Copilot 开发契约（OneAstronomy / Phase 2.0）

> 目的：把“AI‑Native（Agent 驱动）+ 双引擎一镜到底 + 统一坐标系 + HEALPix 仅作索引 + WebGPU-first”变成 **仓库级硬约束**。
> 
> 适用范围：本仓库 `cesium_app_v6`（前端 Vue3+Vite；现有 /workbench 壳与 CesiumTwin 已存在）。

## 1) 技术栈口径（以仓库真实现状为准）

- 前端：Vue 3（Composition API）+ Vite（`frontend/`）
- 地学引擎：CesiumJS（近地、地表、Photorealistic 3D Tiles）
- 天文引擎：Three.js r160+（深空、点云/Instancing/WebGPU）
- 动画：GSAP
- 测试：Vitest（仓库已有）

## 2) AI‑Native 交互绝对约束（无按钮化/Agent 驱动）

- **严禁**在 3D 画布（Cesium/Three canvas）上层新增常规 UI 控件（如 `<button>`, `<select>`）。
  - 允许：仓库既有 HUD/面板（`frontend/src/WorkbenchApp.vue`）承担“指挥舱”功能。
  - 允许：玻璃拟态面板、Monaco、AgentFlow（复用现有 Workbench 架构）。
- 所有业务动作触发必须通过 Store 状态流转：
  - v7.5 天文态动作统一从 `frontend/src/stores/astroStore.js` 发起/消费（`watch(store.currentAgentAction, ...)`）。
  - 禁止在组件内部直接做“按钮触发业务”的新逻辑。

## 3) 双引擎一镜到底（Handover）硬约束

- Cesium 负责近地；Three 负责深空。
- 当 Cesium 相机高度突破阈值（默认 100,000 km，可配置）并检测到继续向上缩放意图时，必须：
  1) 将 Cesium 相机姿态映射到天球视角（RA/Dec）
  2) 对齐 Three 相机（位于原点）四元数 `quaternion`
  3) 使用 CSS/GSAP 做 **两个引擎容器的 opacity 交接**（同时处理 pointer-events）
- 交接必须“画面一镜到底”：两画布重叠时星空背景严格重合，不允许肉眼可见跳变。

## 4) 统一坐标系（数学/空间）硬约束

- Three.js 世界坐标原点 `(0,0,0)` **永远代表地球**。
- 深空天体数据（RA, Dec, Distance / redshift）渲染前必须转为以地球为原点的笛卡尔坐标：
  - 统一由 `frontend/src/utils/astronomy/coordinateMath.js` 提供转换函数。
  - 为避免浮点溢出，允许使用对数深度/对数距离缩放（log distance scaling）。

## 5) HEALPix 仅作为加载索引（非渲染网格）

- HEALPix 的职责是：视锥/视区索引（Frustum Index）与数据分块（Astro‑Tiles）。
- 禁止把 HEALPix 当作“必须渲染的三角网格地形”。渲染层应该是：点云/Instancing/HiPS 贴图等。

## 6) 渲染器策略：WebGPU‑first（允许显式降级）

- 默认目标：`WebGPURenderer`（Three.js `three/webgpu`）。
- **允许降级**：当 `navigator.gpu` 不可用/适配器不可用时，可回退 `WebGLRenderer`（仅保留基础漫游与静态 Instancing）。
  - 降级必须显式进入 `fallback` 模式，并关闭计算着色器/N‑Body 等高负载能力。
  - 文档/代码中不得把降级当作主路径。

## 7) Copilot 唤醒口令

在 Copilot Chat 发送：

```
@workspace 请阅读 #file:AI_CONTEXT.md，并在接下来的实现中严格遵守“Agent 驱动 / 统一坐标 / 双引擎交接 / HEALPix 仅作索引 / WebGPU-first(可显式降级)”约束。回复“已了解”即可。
```
