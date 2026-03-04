Zero2x 021 v7.0: 全尺度空间交互系统与双模态引擎开发蓝图

文档代号：Phase 2 - "Macro to Micro"
当前基线状态：建立在 v6.0（已实现 CesiumJS 闭环、Vitest/Pytest 覆盖、Docker Prod 部署）的稳定基础之上。
核心战略：在不影响 021 Foundation (地学态) 稳定性的前提下，安全、优雅地引入纯 Three.js 渲染引擎，打通 OneAstronomy (深空) 与 OneGenome (微观) 模态，实现“跨尺度、双底座”的下一代科研工作台。

实现进度 (as-built)

截至：2026-03-04

- ✅ Milestone 1 / Week 1 已落地（最小不破坏 v6）：
  - `currentScale` 状态机：`frontend/src/stores/researchStore.js`
  - 引擎互斥路由：`frontend/src/views/workbench/EngineScaleRouter.vue`（`v-if/v-else` 物理互斥挂载）
  - Three.js 极简 Twin + Dispose Gate：
    - `frontend/src/views/workbench/engines/ThreeTwin.vue`
    - `frontend/src/views/workbench/engines/threeDispose.js`
  - Workbench 接入与 UI 切换：`frontend/src/WorkbenchApp.vue`（Top Bar Scale Toggle + Preset scale）
  - TDD 回归：`npm test` 全绿（新增用例覆盖 store / 互斥挂载 / dispose gate）

- ✅ Milestone 2（极简双模态渲染实现 / Week 2）已完成：
  - Bloom 后处理：`EffectComposer + UnrealBloomPass`
    - 实现：`frontend/src/views/workbench/engines/threePostprocessing.js`
    - 接入：`frontend/src/views/workbench/engines/ThreeTwin.vue`
    - 测试：`frontend/tests/threePostprocessing.test.js`
  - 虫洞跃迁（macro -> micro）：GSAP FOV 吸入/释放动画 + 峰值断点切 scene
    - 实现：`frontend/src/views/workbench/engines/quantumDive.js`
    - 接入：`frontend/src/views/workbench/engines/ThreeTwin.vue`
    - 测试：`frontend/tests/quantumDive.test.js`
  - 过程化生成基线（满足蓝图指标）：
    - Macro Scene：InstancedMesh `100000` 星体（轻量几何体，确保可跑）
    - Micro Scene：InstancedMesh `8000` 原子 + `MeshPhysicalMaterial`（transmission/ior）
  - 验收点：
    - `earth` 模式仍为 Cesium，不破坏 v6 Workbench
    - 切换到 `macro`/`micro` 时 ThreeTwin 独占挂载，切回时强制释放 WebGL 上下文
    - `macro -> micro` 自动触发虫洞跃迁（watch currentScale）

1. 架构演进：从单底座到“双擎互斥”架构

v6.0 确立了 EngineRouter.vue 作为工作台的核心引擎网关。为了引入 Three.js 同时规避多 WebGL 上下文带来的内存泄漏，系统确立 互斥渲染与严格上下文管理 机制。

1.1 EngineRouter 尺度流转逻辑

系统的状态管理 (useResearchStore) 将引入新的核心维度 currentScale：

earth (默认)：加载 CesiumTwin.vue。

macro (深空)：加载 ThreeTwin.vue (挂载宏观场景)。

micro (分子)：加载 ThreeTwin.vue (挂载微观场景)。

核心准则：CesiumTwin 与 ThreeTwin 必须通过 v-if / v-else 进行物理级 DOM 互斥挂载。

1.2 内存阻断与销毁门禁 (Dispose Gate)

在切换 currentScale 导致组件卸载 (onBeforeUnmount) 时，必须强制执行硬件级清理：

Three.js 端：递归遍历 Scene 销毁 geometry/material，强制调用 renderer.dispose() 与 renderer.forceContextLoss()。

Vue 3 端：所有 Three.js 核心对象（Scene, Camera, Renderer, Mesh）必须使用 markRaw() 包装，绝对禁止 Vue 的 Proxy 代理劫持海量顶点数据。

2. Three.js 侧实现：Phase 1.5 极简演示流

在接入真实天文/分子数据（几十 GB 的 Gaia 星表或 PDB 数据）之前，我们复用 Phase 1.5 的过程化生成（Procedural Generation）策略，以 60FPS 的满帧体验跑通全息 UI 调度。

2.1 单画布多场景 (Single Canvas, Multi-Scene)

ThreeTwin.vue 内部仅维护一个 WebGLRenderer，但构建两个独立的 THREE.Scene。

Macro Scene (深空)：使用 THREE.InstancedMesh 生成 10 万颗粒子的螺旋星系，应用 UnrealBloomPass 产生中心辉光。

Micro Scene (晶格)：使用 THREE.InstancedMesh 生成 8000 个物理原子，赋予 THREE.MeshPhysicalMaterial，开启高透射率 (transmission: 0.95) 和折射率 (ior: 1.52) 实现玻璃/水晶质感。

2.2 时空跃迁：虫洞过渡动画

结合已有的 EXECUTE ON TWIN 按钮。当用户在深空态点击“下潜至微观”时，不执行硬切换，而是触发 GSAP 补间动画：

吸入感：gsap.to(camera, { fov: 150, duration: 1.2, ease: "power2.in" })。

断点切换：FOV 最大时，瞬间执行 renderer.render(microScene)。

释放感：gsap.to(camera, { fov: 60, z: 40, duration: 1.5, ease: "power2.out" })。

3. 已有 UI 组件的兼容与升维 (向下兼容 v6)

v6 中沉淀的玻璃拟态 HUD (TheaterHUD, LayerTree, AgentFlow) 必须具备“尺度自适应”能力，不能局限于地学逻辑。

3.1 OmniCommand 与 预置剧本 (Presets) 扩展

在首屏与 Cmd/Ctrl+K 面板中，新增跨尺度剧本。

剧本 D (天文)：context: gaia_cluster -> scale: macro。触发无监督聚类星表演算。

剧本 E (微观)：context: protein_fold -> scale: micro。触发蛋白质结构能量折叠演算。

3.2 LayerTree 的跨模态控制

在 Cesium 中，LayerTree 控制 GEE 瓦片图层和 GeoJSON 边界。在 Three.js 模式下，它将映射到后处理管线和材质参数：

深空态 LayerTree：控制星系螺旋分支的可见性、UnrealBloomPass 的 Threshold/Strength 参数。

微观态 LayerTree：控制不同原子簇的隐藏/显示、调节 MeshPhysicalMaterial 的色散 (Dispersion) 或透明度。

(持久化仍复用 v6 的 z2x:layers sessionStorage)。

3.3 AgentFlow 的指令解耦

左侧的 LLM 对话流 EXECUTE ON TWIN 按钮的底层 action 需根据 currentScale 分发：

earth -> store.dispatchComputeJob() -> 调用 FastAPI 获取 /api/tiles 并 flyTo。

macro -> 触发星系簇高亮着色器更新，控制摄像机围绕目标星云自转。

micro -> 触发晶格重组动画（模拟化学键断裂与重组）。

4. 前端重构架构蓝图 (伪代码参考)

4.1 升级网关：EngineRouter.vue

负责核心的生命周期管理和 DOM 互斥。

<script setup>
import { computed } from 'vue';
import { useResearchStore } from '@/stores/researchStore';
import CesiumTwin from './engines/CesiumTwin.vue';
import ThreeTwin from './engines/ThreeTwin.vue';

const store = useResearchStore();
const currentScale = computed(() => store.currentScale); // 'earth' | 'macro' | 'micro'
</script>

<template>
  <div class="engine-router-container absolute inset-0 z-0 bg-black">
    <!-- 互斥渲染：保证内存安全 -->
    <CesiumTwin v-if="currentScale === 'earth'" class="absolute inset-0" />
    <ThreeTwin v-else-if="['macro', 'micro'].includes(currentScale)" class="absolute inset-0" />
  </div>
</template>


4.2 全新底座：ThreeTwin.vue (集成 GSAP 与后处理)

<script setup>
import { onMounted, onBeforeUnmount, ref, markRaw, watch } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import gsap from 'gsap';
import { useResearchStore } from '@/stores/researchStore';

const container = ref(null);
const store = useResearchStore();

// 使用 markRaw 阻断 Vue Proxy
let renderer, camera, controls, macroScene, microScene, activeScene;
let animationId;

onMounted(() => {
  initEngine();
  buildMacroScene(); // 内部使用 InstancedMesh 生成 10 万粒子
  buildMicroScene(); // 内部使用 InstancedMesh + Transmission 材质
  activeScene = store.currentScale === 'macro' ? macroScene : microScene;
  animate();
});

// 监听 Store 变化，执行虫洞跃迁动画
watch(() => store.currentScale, (newScale, oldScale) => {
  if (oldScale === 'macro' && newScale === 'micro') {
    executeQuantumDive();
  } else {
    // 处理其他平滑切换
    activeScene = newScale === 'macro' ? macroScene : microScene;
  }
});

function executeQuantumDive() {
  gsap.to(camera, {
    fov: 150, duration: 1.2, ease: "power2.in",
    onUpdate: () => camera.updateProjectionMatrix(),
    onComplete: () => {
      activeScene = microScene;
      camera.position.set(0, 0, 5); // 调整微观视角
      gsap.to(camera, {
        fov: 60, z: 40, duration: 1.5, ease: "power2.out",
        onUpdate: () => camera.updateProjectionMatrix()
      });
    }
  });
}

function initEngine() {
  renderer = markRaw(new THREE.WebGLRenderer({ antialias: true, alpha: false }));
  renderer.setSize(window.innerWidth, window.innerHeight);
  container.value.appendChild(renderer.domElement);
  
  camera = markRaw(new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 10000));
  camera.position.set(0, 50, 100);
  
  controls = markRaw(new OrbitControls(camera, renderer.domElement));
  macroScene = markRaw(new THREE.Scene());
  microScene = markRaw(new THREE.Scene());
}

function animate() {
  animationId = requestAnimationFrame(animate);
  controls.update();
  renderer.render(activeScene, camera);
}

// 极其关键：硬件级内存回收门禁
onBeforeUnmount(() => {
  cancelAnimationFrame(animationId);
  if (renderer) {
    renderer.dispose();
    renderer.forceContextLoss();
    renderer.domElement.remove();
  }
  // 遍历清理几何体和材质逻辑...
});
</script>

<template>
  <div ref="container" class="w-full h-full"></div>
</template>


5. 下一步执行计划（里程碑排期）

在保持 v6 现有功能绿灯（P0-P2 已回归）的基础上，推进 P3/P4 与 Phase 2：

Milestone 1: 基础设施升维 (Week 1)

重构 Store 加入 currentScale 状态机。

实现 EngineRouter.vue 的严格生命周期管理与 v-if 互斥。

编写并跑通 ThreeTwin.vue 的 WebGL 上下文挂载与强制卸载 (forceContextLoss) 单元测试。

Milestone 2: 极简双模态渲染实现 (Week 2)

在 ThreeTwin.vue 中实装基于 InstancedMesh 的 10 万粒子星系（不加载外部模型）。

实装晶格点阵与 MeshPhysicalMaterial 物理级玻璃材质。

引入 GSAP，完美还原“FOVs 拉伸虫洞跃迁”视觉特效。

Milestone 3: 业务中枢 (HUD) 兼容 (Week 3)

更新 OmniCommand 添加新剧本。

P3 任务并行：完善 LayerTree 的可解释 UI（图例、色标），并实现其对 Three.js 的 bloomPass.threshold 和 material.opacity 的属性映射。

P4 任务并行：增强 EXECUTE ON TWIN（Task Queue），使 AgentFlow 能稳定触发 Three.js 的矩阵变换动画。

Milestone 4: 演进至真实数据验证 (Future Phase 2.5)

引入 crystvis-js 核心逻辑，通过后端解析真实的 .pdb / .cif 晶体文件传递给前端渲染。

引入三维空间八叉树加载机制，准备对接小型局部星表真实数据。