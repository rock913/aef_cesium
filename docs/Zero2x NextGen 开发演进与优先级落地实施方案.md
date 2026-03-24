# Zero2x NextGen 开发演进与优先级落地实施方案

文档定位：将《Zero2x NextGen 演进蓝图》转化为研发团队可执行的开发计划，按优先级排序，提供架构级伪代码与实施路径。

## 状态与计划（滚动更新）

### 最新更新：2026-03-24

本次更新目标：按阶段一（P0）推进“视觉质感收敛 + Earth→Sky 一镜到底交接”，并以 TDD 门禁锁定关键实现，避免回退。

已交付（代码已合入并推送至 `origin/zero2x-v7.5`）：

- P0 视觉精修（Demo 3/4）
  - Inpaint Shader：引入基于 `fwidth` 的抗锯齿（AA）+ film grain + 更薄的 scan 边缘厚度，解决近景“硬边/马赛克感”
  - GOTTA 标记：弃用 `CanvasTexture + SpriteMaterial`，改为程序化 `ShaderMaterial`（SDF 风格）billboard plane，提升近距离边缘质量
- P0 跨域转场（Earth→Sky handover）
  - 在“双引擎常驻挂载 + opacity crossfade”结构上补齐自动触发：监听 Cesium `camera.changed`，当相机高度超过阈值且判断为持续 zoom-out 时，执行相机姿态同步并自动切换 scale 到 `macro`
  - 阈值可配置：`VITE_EARTH_TO_SKY_HANDOVER_HEIGHT_KM`（默认 8000km；更贴近常规缩放可达范围）
  - 总开关：`VITE_EARTH_TO_SKY_HANDOVER=0/1`（便于演示/排障）
  - 排障开关：`VITE_DEBUG_EARTH_TO_SKY_HANDOVER=1` 时输出触发/重置关键日志
- 宏观宇宙视觉稳态（补强项）
  - Macro SDSS 已加入随 zoom 的 auto-tune（点大小/透明度/bloom 基线收敛），降低“光球糊团”复发概率

阶段三（P2）推进（本次补充）：

- Astro-GIS Catalog 拉取从“每帧尝试”升级为“OrbitControls `end` 触发 + debounce + FOV 上限过滤”，避免拖动/缩放时频繁打接口

TDD/门禁：

- 新增 4 个前端测试门禁：
  - `frontend/tests/inpaintShaderQuality.test.js`
  - `frontend/tests/gottaMarkerProceduralShader.test.js`
  - `frontend/tests/earthToSkyAutoHandoverWiring.test.js`
  - `frontend/tests/catalogFetchDebounceOnControlsEnd.test.js`
- Vitest 结果：`npm test` 全绿（59 files / 170 tests）

对应提交（便于回溯）：

- `d141991`：`feat(astro): macro auto-tune by zoom`
- `ce417b2`：`feat(p0): inpaint AA+grain, GOTTA SDF marker, earth→sky handover`

### 本 Sprint（P0）剩余工作（建议按 TDD 继续推进）

P0-1 视觉：参数收敛与回归场景

- 增加一组“视觉回归 checklist”（人工验收即可，不强制自动化）：
  - Inpaint：近距离缩放不出现矩形边/锯齿边；grain 强度不干扰信息
  - GOTTA：标记在各种 DPI/缩放下边缘不抖动；billboard 在运镜时稳定
  - Bloom：macro/overlay 切换时无突然过曝

P0-2 Handover：交接状态机工程化（下一步从“能用”到“稳”）

- 增加可控开关：`VITE_EARTH_TO_SKY_HANDOVER=0/1` 或 UI toggle（便于演示/排障）
- 加入“回落逻辑”：当高度下降到阈值下方（hysteresis）时，允许回切或维持 macro（根据产品策略）
- 明确“释放资源”策略：当前版本优先保证体验不中断；后续可做 Cesium `sleep()`/降频/暂停渲染

### 下个 Sprint（P1）计划（智能工作台 UI + OpenClaw 接入）

- P1-1 Agent Session Panel（Block 流）
  - 目标：替换简单聊天气泡为 Notebook-like 卡片流（text/tool_call/code/plot）
  - TDD：先写组件渲染/数据结构单测（Block schema、顺序、状态变更）
- P1-2 Monaco 代码块（轻量嵌入）
  - 目标：用于 WebGPU WGSL/Shader 参数微调
  - TDD：对“保存/应用到 WebGPU”的 action 做门禁测试（不依赖真实 GPU）
- P1-3 WebSocket 数据契约
  - 目标：后端推送 agent_step 流式状态包，前端驱动 UI 指令（例如 Draw Bounding Box）
  - TDD：先写 payload 校验与 reducer 测试，再接真实 socket

阶段一：视觉质感与连贯性收敛 (优先级：P0，当前 Sprint)

目标：解决目前遗留的局部视觉瑕疵（颗粒感），并打通从 Cesium 地球到 Three.js 深空的跨引擎“一镜到底”，完成产品的全链路闭环。

1.1 视觉精修：消除 Demo 3 & 4 的前端颗粒感

问题：GOTTA 瞬变源和 Inpaint 模态生成的贴图在近距离观看时边缘生硬、存在马赛克。

开发策略：弃用低分辨率 Canvas 贴图，全面改用基于距离场的 Procedural Shader（程序化着色器），叠加抗锯齿与胶片噪点。

实现状态：已完成（2026-03-24）

- Inpaint：已在 `ThreeTwin.vue` 的 Inpaint fragment shader 中引入 `fwidth` AA + grain + vignette
- GOTTA：已将 transient marker 从 sprite/canvas 改为程序化 shader billboard plane

伪代码落地 (Inpaint Fragment Shader 升级)：

// 在 ThreeTwin.vue 的 Inpaint Shader 中升级边缘羽化与抗锯齿
varying vec2 vUv;
uniform sampler2D u_texA; // 可见光底图
uniform sampler2D u_texB; // X射线推演图
uniform float u_radius;   // 扫描波半径
uniform float u_time;

// 胶片噪点生成器 (Film Grain)
float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

void main() {
    float d = distance(vUv, vec2(0.5));
    
    // 🚨 核心抗锯齿：使用平滑阶跃函数代替硬性 if-else，消除锯齿边缘
    float edgeThickness = 0.015; 
    float mask = smoothstep(u_radius + edgeThickness, u_radius - edgeThickness, d);
    
    vec3 colorA = texture2D(u_texA, vUv).rgb;
    vec3 colorB = texture2D(u_texB, vUv).rgb;
    vec3 mixedColor = mix(colorA, colorB, mask);
    
    // 叠加微弱的高频动态噪点，掩盖贴图本身的马赛克，增加物理真实度
    float grain = hash(vUv * u_time) * 0.08;
    mixedColor += grain;
    
    // 终极 Vignette 羽化，确保面片完美融入深空，不产生方形切边
    float vignette = smoothstep(0.48, 0.35, d);
    
    gl_FragColor = vec4(mixedColor, vignette);
}


1.2 跨域转场：Earth to Sky 一镜到底交接 (The Handover)

问题：目前地球和深空是两个割裂的路由/状态。

开发策略：在 EngineRouter.vue 中同时挂载 Cesium 和 Three.js。通过监听 Cesium 的相机高度，达到阈值时利用 CSS Opacity 交叉淡化，同时同步相机位姿。

实现状态：已完成（2026-03-24）

- 当前工程以 `EngineScaleRouter.vue` 为双引擎常驻挂载容器（Cesium + Three），并通过 opacity cross-fade 切换可见性
- 已补齐自动 handover：监听 Cesium `camera.changed`，检测 zoom-out 趋势并在高度超过 `VITE_EARTH_TO_SKY_HANDOVER_HEIGHT_KM` 后自动切换 scale 到 `macro`，并调用 `syncCesiumToThreeCamera` 同步相机朝向

伪代码落地 (EngineRouter.vue 逻辑)：

// 监听 Cesium 相机高度 (伪代码)
watch(() => cesiumStore.cameraHeight, (height) => {
    // 当高度突破阈值（默认 8000km，可通过 env 配置）且处于向上拉升状态
    if (height > HANDOVER_HEIGHT_KM && userIsZoomingOut) {
        // 1. 获取 Cesium 当前相机姿态并换算为赤道坐标 RA/Dec
        const { ra, dec } = getRaDecFromCesium(cesiumCamera);
        
        // 2. 将 Three.js 的相机对齐到该视角
        syncThreeCameraToRaDec(threeCamera, ra, dec);
        
        // 3. 执行交叉淡化 (Cross-fade)
        gsap.to(cesiumCanvasRef.value, { opacity: 0, duration: 1.5 });
        gsap.to(threeCanvasRef.value, { 
            opacity: 1, 
            duration: 1.5, 
            onComplete: () => {
                // 4. 彻底销毁或休眠 Cesium 上下文释放内存
                cesiumStore.sleep();
                astroStore.setMode('macro'); // 唤醒 Three.js 宏观宇宙
                
                // 5. 触发向后狂飙的曲速运镜，迎接红移星空
                gsap.to(threeCamera, { fov: 90, duration: 2.0 });
                gsap.to(threeCamera.position, { z: 250, duration: 3.0, ease: 'power2.out' });
            }
        });
    }
});


阶段二：智能工作台 UI 重构与 OpenClaw 接入 (优先级：P1)

目标：将右侧单薄的聊天框升级为专业的“Agent Session (智能体会话)”，嵌入 Monaco 代码高亮，真正体现科研工作台的价值。

2.1 UI 升级：基于 Block 的会话面板

开发策略：弃用简单的气泡对话，采用类似 Jupyter Notebook 的卡片流。每个卡片可以是一个“思考链步骤”、“一个图表”或“一段 Monaco 渲染的代码块”。

伪代码落地 (AgentSessionPanel.vue)：

<template>
  <div class="agent-session-panel w-96 bg-black/50 backdrop-blur-md border-l border-blue-500/20">
    <div v-for="block in sessionBlocks" :key="block.id" class="session-block p-4">
      
      <!-- 文本对话 -->
      <div v-if="block.type === 'text'" class="text-sm text-gray-200">
        {{ block.content }}
      </div>
      
      <!-- 工具调用思考链 -->
      <div v-if="block.type === 'tool_call'" class="tool-call text-xs text-blue-400 font-mono bg-blue-900/20 p-2 rounded">
        > OpenClaw Agent calling: {{ block.toolName }}({{ block.params }})
        <LoadingSpinner v-if="block.status === 'running'" />
      </div>

      <!-- 轻量级 Monaco 代码渲染块 (不嵌入整个 VSCode) -->
      <div v-if="block.type === 'code'" class="code-editor-widget mt-2">
        <MonacoEditor :code="block.code" language="wgsl" :readOnly="false" @save="triggerWebGPURecompile" />
        <button class="run-btn bg-blue-600 hover:bg-blue-500 text-xs px-2 py-1 mt-1 rounded">
          Apply to WebGPU
        </button>
      </div>
      
    </div>
  </div>
</template>


2.2 OpenClaw 后端架构握手

开发策略：后端基于 OpenClaw 框架封装天文 API，前端通过 WebSocket 接收流式的状态包。

数据契约 (WebSocket Payload)：

{
  "type": "agent_step",
  "sessionId": "session_998",
  "agentState": "EXECUTING_TOOL",
  "toolName": "fetch_simbad_catalog",
  "toolInput": {"ra": 83.63, "dec": 22.01, "radius": 0.5},
  "uiDirective": {
    "action": "DRAW_BOUNDING_BOX",
    "target": "three_canvas"
  }
}


阶段三：动态数据流与真正的天文大基座 (优先级：P2)

目标：摆脱静态 JSON，接入真正的虚拟天文台标准（HiPS / TAP），实现无极漫游。

3.1 视场防抖与动态星表加载

开发策略：监听 OrbitControls 的 change 和 end 事件。当用户停止拖动时，计算当前视场的边界，向后端的 TAP/VizieR 代理服务器发起请求。

伪代码落地 (CatalogLoader.js)：

import { debounce } from 'lodash';

// 监听相机停止移动
controls.addEventListener('end', debounce(async () => {
    // 1. 获取当前中心点和 FOV 半径
    const targetDir = new THREE.Vector3(0,0,-1).applyQuaternion(camera.quaternion);
    const { ra, dec } = cartesianToRaDec(targetDir);
    const radiusDeg = camera.fov / 2;
    
    // 2. 避免大视场请求导致崩溃，只在深度放大时请求
    if (radiusDeg > 15) return; 

    // 3. 动态拉取 VizieR 数据 (使用代理避免跨域)
    const response = await fetch(`/api/astro-gis/catalog?ra=${ra}&dec=${dec}&r=${radiusDeg}`);
    const catalogData = await response.json();
    
    // 4. 更新 Three.js 的 PointCloud 或 InstancedMesh
    astroStore.updateDynamicCatalog(catalogData);
}, 600)); // 600ms 防抖


阶段四：空间计算与端侧推演 (优先级：P3，中长期 R&D)

目标：为未来的 XR/Vision Pro 设备适配自然交互，并将算力彻底下放至端侧。

4.1 Gaze (注视点) 射线交互

开发策略：取代传统的鼠标 Raycaster，在 XR 环境下接入 WebXR API 获取用户的 Gaze Pose。

伪代码逻辑：

function onXRSessionStart(session) {
    session.requestAnimationFrame((time, frame) => {
        // 获取用户眼球注视方向的射线
        const viewerPose = frame.getViewerPose(referenceSpace);
        const gazeRay = new THREE.Raycaster();
        gazeRay.set(viewerPose.transform.position, viewerPose.transform.orientation);
        
        // 与宏观宇宙网进行相交检测
        const intersects = gazeRay.intersectObject(macroPoints);
        if (intersects.length > 0) {
            // 凝视超过 2 秒，触发大模型分析指令
            if (gazeDuration > 2000) {
                 astroStore.dispatchAgentAction({
                     type: 'ANALYZE_GAZE_TARGET',
                     payload: intersects[0].point
                 });
            }
        }
    });
}


4.2 N-Body WebGPU Compute 端侧推演

开发策略：在 Demo 4 中彻底抛弃后端的物理仿真引擎，编写 WGSL Compute Shader 在用户本地浏览器进行百万级星体引力迭代。这将是系统的核心技术壁垒。

// WGSL N-Body 引力核心示例 (在 Monaco 编辑器中供科学家微调)
@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let index = global_id.x;
    var p1 = positions[index];
    var force = vec3<f32>(0.0);
    
    // 遍历计算引力 (在实际生产中会使用共享内存优化)
    for (var i = 0u; i < arrayLength(&positions); i = i + 1u) {
        if (i == index) { continue; }
        let p2 = positions[i];
        let d = p2.xyz - p1.xyz;
        let distSq = dot(d, d) + SOFTENING_SQUARED; // 软化因子防奇点
        force += G * p2.w * normalize(d) / distSq;
    }
    
    // 更新速度与位置
    velocities[index] += force * dt;
    positions[index].xyz += velocities[index] * dt;
}


执行总结与人力分配建议

当前 Sprint (本周)：集中前端 3D 工程师处理 阶段一 (P0)。直接使用提供的 Shader 修正视觉边缘，补充 EngineRouter 的交接逻辑。

下一个 Sprint (下周)：前端 Vue 工程师与大模型后端工程师联调 阶段二 (P1)。引入 Monaco 组件，打通 OpenClaw 的 WebSocket 通信链路。

架构储备：研发负责人开始针对 阶段三 (P2) 的 CDS 接口/代理服务进行调研，确保星表动态拉取的时效性。