Zero2x 宏观孪生分镜指南（对齐仓库实现）：方案 A（晨昏线 / 太空边缘）

更新于：2026-03-03

本文目标：把“方案 A”的镜头脚本落到本仓库真实的 `/act2` 分镜状态机实现中，保证开发/验收时每一幕都能被客观复现（不靠手动拖相机）。

---

## 1) 核心叙事（Storyboard）

方案 A 的核心视觉心理学是“犹抱琵琶半遮面”与“空间悬念”。

通过将地球压在画面底部：

- 给 8K 银河系天空盒留出展示舞台
- 用地球大气层边缘（晨昏线）暗示“下一步即将降维”

🎬 镜头脚本：

- Scene 1：太空边缘（Edge of Space）
    - 画面：上方 80% 星海；下方 20% 晨昏线弧光
    - 隐喻：OneAstronomy（深空）与 GeoGPT（地球）的物理交界

- Scene 2：巨兽升起（The Rise of Earth）
    - 动作：镜头前推 + pitch down
    - 画面：地球弧线从底部缓缓升起并填满屏幕

- Scene 3：目标锁定（Target Lock）
    - 动作：穿透大气层，俯冲到目标区域（默认鄱阳湖）

---

## 2) 在本仓库中“分镜状态机”的位置

本仓库的 `/act2` 不是直接写 `viewer.camera.flyTo(...)`，而是通过一个“可测试的 timeline helper”驱动相机：

- 分镜纯函数（不 import Cesium）：`frontend/src/utils/act2Timeline.js`
    - 核心入口：`applyAct2Step(viewerApi, stepId, choreoName)`
    - step id 固定为：`space → earth → target → summary`

- 页面装配：`frontend/src/Act2App.vue`
    - 滚动（IntersectionObserver）决定 `activeStep`
    - 每次 step 切换调用 `applyAct2Step(...)`

- Cesium Viewer 包装层：`frontend/src/components/CesiumViewer.vue`
    - 对外暴露 `flyTo({ lat, lon, height, heading_deg, pitch_deg, easing }, durationSeconds)`
    - 对外暴露 `applyAct2StoryboardPresetA({ timeIso })`（用于“晨昏线氛围锁定”）

---

## 3) 方案 A 的参数表（与 stepId 一一对应）

说明：

- `height` 对应“相机距离/范围”（本仓库使用 `flyToBoundingSphere + HeadingPitchRange` 保证目标经纬度居中）
- `pitch_deg` 角度单位为度（Deg）
- `easing` 为字符串（在 CesiumViewer 内映射到 Cesium.EasingFunction）

### Step `space`（Scene 1：Edge of Space）

- lon/lat：`116.39, 39.9`
- height：`25,000,000`
- pitch：`-15°`
- duration：`2.0s`

### Step `earth`（Scene 2：The Rise of Earth）

- lon/lat：`116.39, 39.9`
- height：`10,000,000`
- pitch：`-90°`
- duration：`3.5s`
- easing：`QUADRATIC_IN_OUT`

### Step `target`（Scene 3：Target Lock）

- destination：由 `resolveAct2Target(choreoName)` 决定（默认 `poyang`）
- height：`200,000`
- pitch：`-65°`
- duration：`3.0s`
- easing：`CUBIC_OUT`

---

## 4) 视觉大片感：晨昏线光影与大气层调优（仓库实现版）

### 4.1 必须做的“锁时 + 光照 + 大气层”

在 Cesium viewer 初始化完成后立即应用（即 Act2 页面 viewer-ready 时）：

- 开启地球光照：`viewer.scene.globe.enableLighting = true`
- 显示大气层：`viewer.scene.skyAtmosphere.show = true`
- 锁定晨昏线时间：`2026-03-03T10:30:00Z`（可后续微调）
- 强化边缘泛光（偏紫/蓝科技感）：
    - `hueShift = -0.1`
    - `saturationShift = 0.3`
    - `brightnessShift = 0.4`

本仓库已封装为：`CesiumViewer.applyAct2StoryboardPresetA({ timeIso })`

### 4.2 8K SkyBox（素材层）

本指南只规定“镜头语言与调参策略”，8K SkyBox 素材是否投放/如何投放取决于部署与资源包策略。
若要实现“上方 80% 深邃银河”，请优先在 CesiumViewer 初始化阶段配置 SkyBox（避免运行时替换导致闪烁）。

---

## 5) 验收方式（非主观）

1) 打开：`/act2?choreo=poyang`
2) 不拖拽相机，仅滚动分镜卡片：
     - 进入 `space` 时：地球应仅占底部边缘并可见晨昏线
     - 进入 `earth` 时：地球应“升起”填满画面
     - 进入 `target` 时：俯冲到目标区域并稳稳停住

💡 预期演示效果：

黑场淡入 → 先见星海与底部弧光 → 地球磅礴升起 → 俯冲锁定鄱阳湖（或其它 choreo 目标）。