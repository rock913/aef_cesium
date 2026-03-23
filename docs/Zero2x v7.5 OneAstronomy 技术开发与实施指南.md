Zero2x v7.5 OneAstronomy 技术开发与实施指南

版本：v1.1 | 状态：主开发执行标准（Main）| 更新时间：2026-03-20

文档关系（请以本文件为主）：
- 科学叙事/愿景蓝图：`docs/Zero2x v7.5：OneAstronomy 驱动的数字孪生宇宙与科学示范蓝图.md`
- Stage 2 验收规范（Docker Dev、Demo 1 & Demo 3）：`docs/zero2x/Zero2x v7.5 技术方案：OneAstronomy 天文架构与场景实现规范.md`

---

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

1) 宏观宇宙“尺度失真”必须被避免
- 症状：InstancedMesh 的球体过小 + 相机默认距离过远 → 星系点变成 sub-pixel，画面像“几颗暗点”。
- 约束：宏观星海实例的几何半径必须保证在默认相机距离下仍可见（工程上以 ThreeTwin 的 SphereGeometry 半径门禁约束）。

2) CSST 分解必须“强制圆形裁切”，彻底消灭方形边缘
- 症状：即使有 vignette/edge feather，如果纹理边缘不够黑或裁切不够狠，Additive 仍可能露出四角。
- 约束：CSST plane 的 fragment shader 必须包含 circle mask（基于 UV 距离的 `smoothstep(0.45, 0.25, d)`）并与 edge feather / vignette 相乘。

3) CSST 分解必须具备空间感（避免 2D 贴纸感）
- 症状：三层面片正对相机，只做 z 轴轻微错开，会读成“叠放卡片”。
- 约束：三层 plane 必须带倾斜角（例如 `rotation.x = PI/5`）并以 y+z 组合拉开；相机运镜必须带侧向偏移（dir×up 的 side 向量）形成“解剖视角”。

---

## 2) 科学示范任务（从蓝图整合为工程任务书）

四个任务以“科学叙事”为主线，工程上统一映射为：Copilot 指令 → `astroStore` action → `ThreeTwin.vue` 执行。

### 2.0 Demo 映射与状态（四大任务 = 四个 Demo）

| Demo | 任务名 | Action（建议/目标） | 当前状态（2026-03-20） |
|---|---|---|---|
| Demo 1 | CSST 复杂星系精细结构分解 | `DECOMPOSE_CSST_GALAXY` / `STOP_CSST_DECOMPOSITION` | Implemented（已落地：可触发/可清理/可验收） |
| Demo 2 | 红移立体爆裂（Cosmic Web / Redshift Burst） | `EXECUTE_REDSHIFT_PREDICTION` | Implemented（Stage 2 已落地） |
| Demo 3 | GOTTA 瞬变源捕获（样条跃迁 + 时域 HUD） | `CAPTURE_TRANSIENT_EVENT` | Not Started（规划中） |
| Demo 4 | 模态互生 Inpaint（扫描扩散） | `START_MODAL_INPAINT` / `STOP_MODAL_INPAINT` | Implemented（Stage 2 已落地） |

说明：
- 旧文档中曾以“Demo 1 红移 / Demo 3 Inpaint”作为 Stage 2 验收编号；为了与“四大任务=四个 Demo”一致，本主文档采用 Demo 1–4 的新映射。
- 代码与 Command Palette 的展示文案若仍沿用旧编号，视为 UI 命名债（后续统一）。

### 序幕：宇宙基底的唤醒（The Data Fabric）

目标：进入 workbench 后，看到“真实数据驱动”的二维天球基底，而不是纯随机点。

工程约束：
- 微型数据池（2–5MB）放在 `frontend/public/data/astronomy/`
- 首帧渲染必须可用；数据加载可渐进增强。

### 任务 1：CSST 复杂星系精细结构分解（DECOMPOSE_CSST_GALAXY）

目标：相机推进到目标，出现可读的三层分解图（Bulge/Disk/Bar），并能在任务切换时被清理。

验收（Docker Dev / E2E）：
- Workbench → Presets 选择 `[v7.5] OneAstronomy · CSST Galaxy Decompose (Demo 1)`：画布内出现三层分解面片（Bulge/Disk/Bar），边缘无方形截图边界（circle mask + vignette + edge feather）。
- 运镜与层次：相机以侧上方“解剖视角”推进，三层面片具备明显空间分离（倾斜 + y/z 拉开），不应读成三张重叠卡片。
- 触发 `redshift` 或 `inpaint start`：CSST 分解面片必须自动清理（Scene Authority）。
- 运行代码指令 `csst stop`：必须能显式清理 CSST 图层并恢复 macro 亮度。

### 任务 2：精密宇宙学与红移立体爆裂（EXECUTE_REDSHIFT_PREDICTION）

目标：批量红移数据到达后，点云在三维空间“爆裂展开”，并配合运镜形成宏观震撼。

### 任务 3：GOTTA 瞬变源捕获（CAPTURE_TRANSIENT_EVENT）

目标：远处闪烁目标 + 样条曲线跃迁运镜 + 时域 HUD（可先 mock）。

### 任务 4：模态互生 Inpaint（START_MODAL_INPAINT / STOP_MODAL_INPAINT）

目标：扫描扩散替换纹理，具备边缘噪声；在 Additive 模式下无方形边界。

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

### 3.2 GOTTA 瞬变源光变曲线 (Mock JSON)

格式：gotta_transient_event.json

{
  "eventId": "GOTTA-2026a",
  "ra": 83.63, "dec": 22.01,
  "type": "Supernova Ia",
  "lightcurve": { "time": [0,1,2,3,4,5], "flux": [10, 45, 120, 95, 40, 15] }
}


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

---

## 5) TDD 详细研发（按“红-绿-重构”执行）

本仓库现有 TDD 风格偏“wiring gate（字符串/结构门禁）”，先保证集成不碎，再逐步引入可运行的更细粒度单测。

### 5.1 必须新增/维护的 Vitest 门禁（建议直接落在现有测试文件）

1) `frontend/tests/threeTwinWiring.test.js`
- 断言 inpaint 使用 `AdditiveBlending`、`depthTest: false`
- 断言 inpaint plane 处于世界空间（例如 `.position.set(0, 0, 15)`）
- 断言 shader 内含 edge feather / vignette（避免回归“截图边界”）
- 断言 “霸权 2.0”存在：`u_redshift_scale` 在 `_startModalInpaint()` 内被 tween 回 0

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

---

## 6) Copilot 叙事主导（工程约定）

右侧 Copilot 面板不只是日志输出，而是“科学解说员”。每个任务触发时建议输出：
- 数据阶段：加载/解析/映射完成
- 模型阶段：请求/推理/回传完成
- 物理阶段：约束校验/退让规则执行
- 视觉阶段：运镜/后处理/任务清理完成

序幕：宇宙基底的唤醒 (The Data Fabric)

执行逻辑：页面挂载时，fetch 上述 sdss_micro_sample.json，使用 InstancedMesh 渲染成一个半径为 100 的大球面。此时不应用 redshift。

// 初始化：读取 JSON，映射为球面点云
const rawData = await fetch('/data/astronomy/sdss_micro_sample.json').then(r => r.json());
const dummy = new THREE.Object3D();
const redshifts = new Float32Array(rawData.length);

rawData.forEach((item, i) => {
  const [ra, dec, z] = item;
  redshifts[i] = z; // 存入 attribute，但初始 uniform u_redshift_scale = 0
  const pos = raDecToCartesian(ra, dec, 100); // 半径固定为 100 (2D天球)
  dummy.position.copy(pos);
  dummy.lookAt(0,0,0);
  dummy.updateMatrix();
  instancedMesh.setMatrixAt(i, dummy.matrix);
});
instancedMesh.geometry.setAttribute('aRedshift', new THREE.InstancedBufferAttribute(redshifts, 1));


任务 1：CSST 复杂星系精细结构分解

触发指令：DECOMPOSE_CSST_GALAXY

视觉逻辑：相机飞向特定的星系坐标，弹出三个层叠的半透明 PlaneGeometry，分别代表核球、盘、棒的分解图。

// 1. 运镜飞向目标星系
const targetPos = raDecToCartesian(targetRA, targetDec, 95); // 稍微靠近
gsap.to(camera.position, {
  x: targetPos.x, y: targetPos.y, z: targetPos.z,
  duration: 2.5, ease: "power2.inOut",
  onUpdate: () => camera.lookAt(targetPos) // 紧盯目标
});

// 2. 挂载 CSST 分解图层 (Three.js Group)
csstGroup.position.copy(targetPos);
// Z轴错开展开动画
gsap.to(diskPlane.position, { z: -2, duration: 1.5 });
gsap.to(bulgePlane.position, { z: 0, duration: 1.5 });
gsap.to(barPlane.position, { z: 2, duration: 1.5 });


任务 2：精密宇宙学与红移立体爆裂 (Jean-Paul Kneib 协作)

触发指令：EXECUTE_REDSHIFT_PREDICTION

视觉逻辑：背景星系不再是平面。通过 GSAP 驱动 u_redshift_scale，让粒子沿原点射线方向急速拉远（真实物理深度还原）。

// Shader 顶点核心计算：
// float realDistance = 100.0 + (aRedshift * u_max_depth * u_redshift_scale);
// vec3 finalPos = normalize(localPos.xyz) * realDistance;

// 清理任务 1 的遗留
gsap.to(csstGroup.scale, { x: 0, y: 0, z: 0, duration: 0.5 });

// 相机后撤，纵览全宇宙
gsap.to(camera.position, { x: 0, y: 0, z: 250, duration: 3.0 });

// 触发红移大爆裂 (斯隆长城)
gsap.to(instancedMesh.material.uniforms.u_redshift_scale, {
  value: 1.0, 
  duration: 4.0, 
  ease: "power3.inOut" 
});
// 同时改变粒子颜色，红移越大的变成粉紫色


任务 3：GOTTA 智能时域网络与瞬变源捕获

触发指令：CAPTURE_TRANSIENT_EVENT

视觉逻辑：在庞大的三维宇宙网中，某个坐标突然闪烁刺眼的白光。相机使用样条曲线（Spline）跃迁飞去。

// 1. 在指定坐标生成高亮闪烁材质
const gottaPos = raDecToCartesian(gottaRA, gottaDec, 100 + gottaZ * maxDepth);
transientSprite.position.copy(gottaPos);
transientSprite.visible = true;
// 闪烁动画
gsap.fromTo(transientSprite.material, { opacity: 0.2 }, { opacity: 1, yoyo: true, repeat: -1 });

// 2. 样条曲线运镜 (CatmullRom)
const startPos = camera.position.clone();
const midPos = startPos.clone().lerp(gottaPos, 0.5).add(new THREE.Vector3(50, 50, 0)); // 制造弧线跃迁感
const curve = new THREE.CatmullRomCurve3([startPos, midPos, gottaPos.clone().multiplyScalar(0.95)]);

gsap.to({ t: 0 }, {
  t: 1, duration: 3.5, ease: "power2.inOut",
  onUpdate: function() {
    camera.position.copy(curve.getPoint(this.targets()[0].t));
    camera.lookAt(gottaPos);
  },
  onComplete: () => {
    // 唤起 ECharts 绘制光变曲线 HUD
    astroStore.showTransientHUD(gottaData);
  }
});


任务 4：模态互生与物理一致性微调 (Modal Inpainting)

触发指令：START_MODAL_INPAINT

视觉逻辑：雷达扫描波纹掠过，可见光纹理褪变为 X 射线纹理。需要极强的边缘羽化（Vignette）。

// Inpaint WebGPU Shader 片元核心 (伪代码)
void main() {
    vec4 texOpt = texture2D(u_optical, vUv);
    vec4 texXray = texture2D(u_xray, vUv);
    
    // 扫描雷达波纹计算
    float d = distance(vUv, u_center);
    float mask = smoothstep(u_radius + 0.05, u_radius - 0.05, d);
    
    // 模态混合
    vec3 mixedColor = mix(texOpt.rgb, texXray.rgb, mask);
    
    // 边缘羽化遮罩 (Vignette) -> 彻底消除面片感
    float distToCenter = distance(vUv, vec2(0.5));
    float vignette = smoothstep(0.5, 0.3, distToCenter);
    
    gl_FragColor = vec4(mixedColor * vignette, 1.0); 
    // AdditiveBlending 模式下，黑色(0,0,0)即完全透明
}


三、 Copilot 协同叙事与前端状态机约定

开发团队在处理 WorkbenchApp.vue 时，必须将右侧的 021 Copilot 视为“科学解说员”。交互通过预置对话推进：

触发器 (Preset Click)

Store Action (astroStore)

Copilot 打印日志流 (模拟 Agent)

3D 画布响应 (ThreeTwin)

Demo 1 (CSST)

DECOMPOSE_CSST_GALAXY

"接收 CSST 测光数据... 运行 OneAstronomy 进行形态学解构..."

相机飞入 -> 呼出三层分解面片

Demo 2 (Redshift)

EXECUTE_REDSHIFT_PREDICTION

"连线 Jean-Paul Kneib 团队... 预测暗弱星系红移... 正在重构三维宇宙学结构..."

销毁分解图 -> 相机拉远 -> 粒子沿视线拉伸爆裂

Demo 3 (GOTTA)

CAPTURE_TRANSIENT_EVENT

"GOTTA 监测网报警！发现异常时域波形。极速跃迁定位目标源..."

宇宙网某处闪烁 -> 弧线跃迁运镜 -> 呼出光变图

Demo 4 (Inpaint)

START_MODAL_INPAINT

"启动基础模型物理图谱互生... 反推目标 X 射线辐射场分布..."

背景星系变暗(透明度0.1) -> 雷达扫描 X射线替换

技术收尾规范：
- 四大任务全部写在 `frontend/src/views/workbench/engines/ThreeTwin.vue` 中，通过 `watch(() => astroStore.currentAgentAction.value?.actionId, ...)` 驱动。
- 切忌重载页面；任何任务结束都要显式执行清理/退让（Scene Authority）。