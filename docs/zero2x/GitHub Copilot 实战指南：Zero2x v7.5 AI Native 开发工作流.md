GitHub Copilot 实战指南：Zero2x v7.5 AI Native 开发工作流（仓库适配版）

本指南把 OneAstronomy（v7.5 / Phase 2.0）从“理念”降落到 **本仓库可直接执行** 的 Copilot S.O.P。

本仓库核心前提（必须记住）：

- **不推倒重来**：保留现有 `/workbench` 工作台壳与 CesiumTwin（见 `frontend/src/WorkbenchApp.vue`、`frontend/src/views/workbench/EngineRouter.vue`）。
- **Agent 驱动（无按钮化）**：不在 3D 画布上层新增按钮；业务动作通过 store 的 `currentAgentAction` 状态流转触发。
- **双引擎一镜到底**：Cesium 近地、Three 深空；交接必须相机姿态严格一致。
- **HEALPix 仅作索引**：用于视锥/视区的加载索引与数据分块，不作为渲染网格。
- **WebGPU-first（允许显式降级）**：默认 WebGPU；设备不支持时进入 fallback 模式（关闭 Compute/N-Body 等）。

---

## 步骤 0：分支与约束源（必须先做）

👉 统一在 v7.5 主开发分支上推进：

- 分支名建议：`zero2x-v7.5`

👉 约束源文件（唯一权威）：

- 根目录 `AI_CONTEXT.md`

Copilot 唤醒口令：

```
@workspace 请阅读 #file:AI_CONTEXT.md，并在接下来的实现中严格遵守“Agent 驱动 / 统一坐标 / 双引擎交接 / HEALPix 仅作索引 / WebGPU-first(可显式降级)”约束。回复“已了解”即可。
```

---

## 步骤 1：Contract-First（先写契约与骨架，再写场景）

目标：先把“交接棒 + 坐标数学 + Action Bus”固定下来，避免后续组件割裂。

### 1.1 Action Bus（Agent 驱动入口）

- Store：`frontend/src/stores/astroStore.js`
- 约定：所有天文业务动作通过 `dispatchAgentAction({ type, payload })` 触发；组件只 `watch(store.currentAgentAction, ...)` 响应。

### 1.2 坐标数学（统一坐标系）

建议新增（后续会在阶段 1 MVP 落地）：

- `frontend/src/utils/astronomy/coordinateMath.js`
   - `raDecToUnitVector(raDeg, decDeg)`
   - `raDecDistanceToCartesianLog(raDeg, decDeg, distanceMpc, opts)`

### 1.3 引擎交接（Cesium -> Three 相机对齐）

建议新增（阶段 1 MVP 落地）：

- `frontend/src/utils/astronomy/engineHandover.js`
   - `syncCesiumToThreeCamera(cesiumCamera, threeCamera, opts)`

约束：

- 读 Cesium 当前 heading/pitch/roll，并推导视线方向映射到 RA/Dec（或等价的天球方向）。
- 写 Three 相机 `quaternion`，保证两画布重叠时背景严格重合。

---

## 步骤 2：从现有 Workbench 演进（不新开一套 UI）

本仓库已有 Workbench 壳与 HUD 面板；v7.5 只“扩展引擎能力”，不另外创建一套按钮交互。

关键挂载点：

- 引擎容器（现有）：`frontend/src/views/workbench/EngineRouter.vue`
   - 当前状态：Cesium + WebGPU Sandbox overlay
   - v7.5 目标：在同一文件/同一路由内演进到“CesiumTwin / ThreeTwin 的交接路由”

- Three 引擎（现有）：`frontend/src/views/workbench/engines/ThreeTwin.vue`
   - 当前状态：WebGL + 后处理（Bloom）+ micro/macro 演示
   - v7.5 目标：增加 WebGPU-first 初始化与 fallback 模式；引入对数相机与 Astro-Tiles 加载器

---

## 步骤 3：SDD（Script-Driven Development）Prompt 库（仓库适配）

注意：以下提示词都要求“无按钮化”，动作来自 `astroStore.currentAgentAction`。

### 场景 0：起飞与一镜到底交接（The Great Handover）

```
@workspace 请基于 #file:AI_CONTEXT.md 与现有 #file:frontend/src/views/workbench/EngineRouter.vue
把 EngineRouter 升级为“Cesium 容器 + Three 容器”的双栈结构：两个绝对定位全屏 div 叠放，使用 opacity + pointer-events 控制显隐。

要求：
1) 在 Cesium 渲染循环中监听相机高度（camera.positionCartographic.height）。
2) 当高度 > 100000km 且检测到继续向上滚轮意图时：调用 syncCesiumToThreeCamera 对齐视角。
3) 使用 GSAP 在 1.5s 内完成 Cesium -> Three 渐变交接。
4) 交接完成后，事件控制权移交给 Three 的对数相机控制器。
```

### 场景 1：深空巡天与红移爆裂（The 3D Cosmic Web）

```
@workspace 我要实现场景一 CosmicWeb（v7.5）。不新增任何 button。
请在 ThreeTwin（或其子组件）中 watch(useAstroStore().currentAgentAction)。
当 action.type === 'EXECUTE_REDSHIFT_PREDICTION'：
1) 基于当前相机 FOV 计算视区 HEALPix 索引集合（先 stub）。
2) 预加载该视区星系数据（先 mock）。
3) 使用 GSAP 将点云从“二维虚拟球面”缓动拉伸到 cartesianLog（对数深度）坐标，耗时 3.5s。
```

### 场景 2：透镜检索与虫洞跃迁（Zero‑Shot Search）

```
@workspace 场景二 LensSearch：监听 action.type === 'SEARCH_SIMILAR_LENS'。
后端返回 Top-5 (ra, dec)。只加载这 5 个天区（HEALPix 索引）。
运镜：CatmullRomCurve3 + GSAP 动态拉伸 camera.fov，制造折跃效果。
到达后恢复正常 fov，并把结果写回 store（以便 Workbench 面板展示）。
```

### 场景 3：跨模态扫描波纹（Modal Inpainting）

```
@workspace 场景三 ModalInpaint：不需要鼠标交互。
组件 watch(useAstroStore().aionModelState.isGenerating)。
当 isGenerating=true：在 Fragment Shader 里生成随时间扩大的扫描波纹：
波纹内采样 X-ray 纹理，外部采样 Optical 纹理，边缘加入高频噪声并为 Bloom 提供 HDR 强度。
```

### 场景 4：端侧 N‑Body（Physics‑Informed Twin）

```
@workspace 场景四 GalaxyCollision：监听 action.type === 'SIMULATE_GALAXY_COLLISION'。
WebGPU Compute Shader 更新 10万粒子的位置/速度（降级模式关闭）。
计算结果留在 GPU buffer 中，直接在 Vertex Shader 读取并渲染，目标 60FPS。
```

---

## 步骤 4：WGSL 调试“沙盒化”（适配 Vite 工程）

原始的“双击 html 即可运行”在现代 ESM/Vite/Three/WebGPU 环境下通常不可行。

建议策略：

- 把沙盒 HTML 放到 `frontend/public/sandbox/`（作为静态资源）
- 通过 `npm run dev` 启动后访问：`/sandbox/nbody_test.html`

沙盒目标：验证 Compute shader 的 WGSL 语法与数值稳定性，再封装回 `frontend/src/views/workbench/engines/` 或 `frontend/src/shaders/`。

---

## 步骤 5：TDD 门禁（先数学、再视觉、再大计算）

v7.5 最容易出错的是坐标系/对数缩放与相机对齐；测试应该优先覆盖这些基础。

建议新增（阶段 1 MVP）：

- `frontend/src/utils/astronomy/coordinateMath.test.js`
   - 春分点：RA=0, Dec=0
   - 北天极：Dec=90
   - 南天极：Dec=-90
   - 对数距离缩放：`log(distance)` 比例与单调性断言（防坐标爆表）

---

## 实施计划（先工作流升级，再场景落地）

里程碑 M0（Workflow Upgrade，1 天）：

- `AI_CONTEXT.md` 成为唯一约束源
- `astroStore` Action Bus 打通（仅骨架）
- 三份 v7.5 文档口径统一（路径/策略/降级/门禁）

里程碑 M1（MVP 壳结构，3 天）：

- EngineRouter 双栈容器（Cesium/Three）+ opacity handover
- WebGPU-first 初始化与 fallback 模式（写入 astroStore.mode）
- 坐标数学与相机对齐函数出第一版（带最小测试）

里程碑 M2（Demo 1 & 3，1 周）：

- 红移爆裂（点云 10 万）
- 扫描波纹 Shader（HDR + Bloom）

里程碑 M3（Demo 2 & 4，1 周）：

- 透镜检索运镜（样条 + FOV warp）
- N‑Body Compute（10–20 万粒子）

验收门禁（持续保持）：

- `frontend`: `npm test`（vitest）不退化
- `/workbench` 不引入 3D 画布按钮交互
- handover 叠画时背景重合（主观验收 + 可选截图差分）