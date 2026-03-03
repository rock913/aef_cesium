# Zero2x 升级规划（Issue-style Tracking）

分支：`021/zero2x-upgrade`

目标：在不推倒现有 Cesium Demo 的前提下，把本仓库升级为 Zero2x 网站（根路径叙事 + Omni-Bar 引导，重应用挂载到 `/demo`），并标准化 Dev/Prod 的 Docker 运行与验收。

端口约定：

- Dev：前端 8404 / 后端 8405
- Prod（Docker 版）：前端 8406 / 后端 8407

---

## 当前状态（更新于 2026-03-02）

- ✅ 分支：`021/zero2x-upgrade` 已作为升级承载分支
- ✅ Milestone M0（端口与环境基线）已完成并验收通过
  - Dev：`make docker-dev-up` + `make docker-dev-check` 全绿（8404/8405，含 `/api/*` 代理）
  - Prod：`make docker-prod-up` + `make docker-prod-check` 全绿（8406/8407，nginx 同源反代 `/api/*`）
- ✅ Milestone M1（Zero2x 网站骨架 48h MVP）已落地
  - `/` → Zero2x Landing（含 Omni-Bar stub、五幕叙事与 CTA）
  - `/demo` → 现有 Cesium Demo 保留
  - 前端 vitest、后端 pytest 已回归通过（集成类按默认条件跳过）

### 本日新增进展（Landing 质感与可见性修复）

- ✅ HeroVisual（Three.js 兜底）结构性控光：由“实心叠加”改为“戴森球外壳分布（Dyson shell）”
  - dense 星云点与 neural 节点均只分布在外壳（强制 inner radius），从源头消灭球心 overdraw → 解决“中心白爆/放射刺”。
  - glow 渐变起点弱化为环境光（极低 alpha），避免假超新星。
- ✅ Landing 标题字体修复：渐变文字从 `text-shadow` 改为 `filter: drop-shadow(...)`
  - 解决 `background-clip: text` + `color: transparent` 下阴影“透上来”污染渐变的问题（字变脏/发黑）。
  - 同步增强 `zero2x` 渐变强度：升级为多 stop 渐变，并补齐 `-webkit-text-fill-color: transparent` 兼容。
- ✅ Omni-Bar 对齐原型：提示行使用 `<kbd>` 样式；`Run/进入第二幕` 在输入行内（md+ 显示），移动端继续隐藏。
- ✅ 门禁：前端 `npm test`（vitest）持续全绿（21 files / 62 tests）。
- ✅ 修复：Docker Dev 前端依赖与 Node 版本基线
  - 解决 Vite overlay 报错：`Failed to resolve import "three"`（容器内 node_modules 卷残缺导致）
  - 解决 Vite 7 在 Node 18 下启动失败（`Vite requires Node >=20.19` / `crypto.hash is not a function`）

### 完成度评估（对照“高阶视觉欺骗 / Hero + Omni-Bar”方案）

- ✅ 目标 1：首屏“呼吸态发光球体 + 星尘氛围”（无需真实模型管线）
  - 已实现：`HeroVisual` 三层策略（A-plan 可替换素材 WebM/WebP → CSS fallback → Three.js 点云球体 + 星尘）。
  - 已实现：Three.js 采用动态加载（`await import('three')`），并包含 WebGL 能力检测与卸载清理。
  - 说明：按“第三方也能稳定看到动效”的需求，当前默认忽略 `prefers-reduced-motion`（不再自动禁用动效）。
  - 已实现：素材投放目录与命名约定（`frontend/public/zero2x/hero/`、`frontend/public/zero2x/ui/`）。

- ✅ 目标 2：Omni-Bar（⌘K / Ctrl+K 聚焦 + Enter stub plan）
  - 已实现：Landing Omni-Bar（全局快捷键捕获、聚焦、Enter 触发 stub 结果）。
  - 已实现：仍保持“离线可运行”与“无外部 CDN 强依赖”（不引入 Tailwind CDN / GSAP CDN）。

- ✅ 目标 3：Act2 UI 降噪（电影感 / 玻璃拟态）
  - 已实现：Act2 overlay + info card 采用玻璃拟态风格（`backdrop-filter: blur(...)` 等）。
  - 已实现：Cesium 默认控件在 Viewer 初始化阶段关闭（timeline/animation/home/baseLayerPicker/geocoder 等为 false）。
  - 风格建议：后续可进一步把“Back / Demo / Replay”做为可折叠控制（减少常驻文字干扰）。

- ⚠️ 仍欠缺（不阻塞 48h MVP，但会影响“第一眼质感”）
  - 缺口 1：A-plan 设计素材尚未投放（`stardust_bg.webm/webp`、`glow_sphere.webm/webp` 目前为约定路径）。
  - 缺口 2：Omni-Bar 仍为 stub（未形成真正的 command palette / 意图路由；没有“微交互曲线”如 GSAP easing）。
  - 缺口 3：第三幕/第四幕的“视频帧欺骗”尚未落地（目前为占位卡片 + 轻量 DataGalaxy 原型）。

> 注：缺口 2 已在后续迭代中补齐（最小命令面板已完成）。本文档中的“仍欠缺”是按最初规划表述，现已部分达标。

## 下一步（建议执行顺序）

- 1）M1.5 Issue #14.1：第一幕“资产替换包”与微交互加固（优先，最能拉升质感）
  - 目标：在不改代码结构的前提下，用“可替换素材”直接把首屏质感拉满。
  - 输出：投放素材（WebM/WebP）+ 验收截图/录屏。
  - Acceptance Criteria：
    - `frontend/public/zero2x/hero/` 下投放：`stardust_bg.webm`、`stardust_bg.webp`、`glow_sphere.webm`、`glow_sphere.webp`。
    - Dev/Prod 下首屏无 404（浏览器 Network 面板无红字），且首屏仍不引入 Cesium。
    - （可选）若需要遵循无障碍偏好：`prefers-reduced-motion: reduce` 下主视觉提供静态降级（无三维动画/视频）。
  - Tests：延续 vitest wiring 门禁（不做像素级截图测试）。
  - Status：🧩 待开始

- 2）M1.5：Landing Act2 段落“去占位化” + 预告素材（推荐）
  - 目标：让用户下翻看到的是“真实能力预告”，而不是“（占位）”字样；仍不在 `/` 引入 Cesium。
  - 建议方案：Act2 段落内嵌 WebM/WebP loop（飞向鄱阳湖预告）+ 能力点卡片 + 明确 CTA（进入 `/act2?choreo=poyang`）。

- 3）M2 Issue #17：第二幕“卫星/卡片/星尘”素材与动效（只在 `/act2`）
  - 目标：把电影化体验做在 `/act2`，持续加料但不污染 Landing 首屏体积。

- 4）M2 Issue #18：第三幕（微观深潜）占位素材替换为可滚动的“视频帧/卡片”
  - 目标：用轻素材/短 loop 提升“第三幕/第四幕”的可信度。

> 注：Issue #15（Landing scroll feedback）与 Issue #16（Demo 入口降噪）在本分支已达标并有 vitest 门禁；后续仅作为视觉/文案微调项。

### 已落地：Scroll → Route + 黑场转场（体验连续性加固）

- Goal：让 Landing 的“下滑进入第二幕”与“点击 CTA 进入第二幕”在体验上收敛为同一动作，减少 `/` 与 `/act2` 的割裂感。
- Implementation Notes：
  - Landing 通过 IntersectionObserver 识别 Act2 区域进入视窗后触发一次性跳转（session 内仅一次）；仅在向下滚动时触发；`prefers-reduced-motion` 下禁用；支持 `Esc` 取消。
  - 路由切换使用短黑场淡入淡出（不依赖 Vue Router）。


---

## Milestone M0：端口与环境基线（✅ 已完成）

### Issue #1：建立 021 分支与版本边界

- Goal：所有 Zero2x 升级改动只落在 `021/*` 分支；主分支不受影响。
- Acceptance Criteria：
  - `git branch --show-current` 返回 `021/zero2x-upgrade`
  - README 明确 Dev/Prod 端口与命令
- Tests：无

### Issue #2：Dev 端口与 Docker Dev 验收改为 8404/8405

- Goal：`make docker-dev-up` 启动后，`curl` smoke + pytest + vitest 全绿。
- Acceptance Criteria：
  - `make docker-dev-up` 后：
    - `http://127.0.0.1:8404/` 可访问
    - `http://127.0.0.1:8405/health` 返回 200
    - `http://127.0.0.1:8404/api/locations` 可通
  - `make docker-dev-check` 全绿
- TDD：先写/更新 smoke（Makefile）→ 再改 compose/vite/backend defaults
- Status：✅ 已完成（`make docker-dev-check` 全绿）

### Issue #3：提供 Docker Prod（静态 nginx + 后端）8406/8407

- Goal：不依赖宿主 node/python，靠 docker compose 即可跑出“接近生产”的同源反代形态。
- Acceptance Criteria：
  - `make docker-prod-up` 后：
    - `http://127.0.0.1:8406/` 可访问
    - `http://127.0.0.1:8407/health` 返回 200
    - `http://127.0.0.1:8406/api/locations` 可通
  - `make docker-prod-check` 全绿
- Status：✅ 已完成（`make docker-prod-check` 全绿）

### Issue #3.1：前端容器 Node 基线与依赖自愈（✅ 已完成）

- Goal：避免 Docker Dev 因 node_modules 卷残缺或 Node 版本不满足而出现“本地能跑、容器崩溃”的情况。
- Background（已发生问题）：
  - Vite overlay：`[plugin:vite:import-analysis] Failed to resolve import "three"`
  - 原因 1：`docker-compose.dev.yml` 使用 `frontend_node_modules:/app/node_modules` 命名卷，卷可能存在但缺包；旧的启动逻辑仅判断目录是否存在，导致跳过 `npm ci`。
  - 原因 2：前端依赖已升级到 Vite 7 / Cesium 新版，运行期要求 Node `>=20.19`；Node 18 会导致 dev server 启动失败（`crypto.hash is not a function`）。
- Fix（已落地）：
  - 前端 Dockerfile 基线升级为 Node `20.19`（dev/test/prod build stage）。
  - Docker Dev 启动逻辑改为“依赖可解析性探测”：若 `require.resolve('vite')` 或 `require.resolve('three')` 失败则自动 `npm ci`，避免 node_modules 卷半残状态。
- Acceptance Criteria：
  - `make docker-dev-up` 后，Vite 可在 8404 正常启动（无 Node 版本报错）。
  - `HeroVisual` 中 `await import('three')` 在容器内可被解析（无 import-analysis 报错）。
- Status：✅ 已完成（已重建镜像并验证 Vite 正常启动）

---

## Milestone M1：Zero2x 网站骨架（✅ 已完成）

### Issue #4：根路径 `/` 显示 Zero2x Landing，`/demo` 保留现有 Cesium Demo

- Goal：Zero2x 成为默认首页；不破坏现有 Demo。
- Acceptance Criteria：
  - 访问 `/`：出现 Omni-Bar、五幕标题、CTA（Launch My Workspace / Open Demo）
  - 访问 `/demo`：现有 Missions + Cesium 逻辑仍可用
- Tests（vitest，内容门禁）：
  - main 装配逻辑：`/`→Zero2x，`/demo`→AlphaEarth
  - Zero2x 文案存在：`Press ⌘K`、`第二幕：宏观孪生`、`第四幕：数据星海`、`Launch My Workspace`
- Status：✅ 已完成（已补 vitest 门禁）

> 注：提示文案在 UI 上已升级为 `Press <kbd>⌘K</kbd> ...`；vitest 门禁已同步更新为断言 `Press`/`⌘K`/`omnibar-kbd-hint`。

### Issue #5：Omni-Bar（⌘K）交互（MVP stub）

- Goal：提供“像 Cursor 一样”的极简指令入口，但先用 stub 结果。
- Acceptance Criteria：
  - ⌘K / Ctrl+K 聚焦输入框
  - Enter 输出一段 stub 的 Plan
  - CTA 可跳转 `/demo`
- Tests：vitest（内容/关键字符串） + 手工验证键盘交互
- Status：✅ 已完成（stub 交互 + vitest 覆盖）

---

## Milestone M2：叙事增强（🔄 下一阶段）

### Issue #6：第二幕“宇宙→地球”转场（Cesium flyTo 最小可玩）

- Goal：做出一个可复用的 camera choreography：deep space → poyang。
- Acceptance Criteria：
  - Zero2x Landing 的 CTA 跳转到 `/act2?choreo=poyang`
  - `/act2` 自动触发 flyTo 到鄱阳湖，且提供回到 landing 的入口
  - `/demo` 仍可独立访问并保持原有 Missions UI
- Tests：可选（偏视觉）；但应至少覆盖 JS/配置不崩溃。

- Status：✅ 已完成（新增 `/act2` 叙事路由；Landing CTA 已指向 `/act2`；vitest 回归全绿）

### Issue #10：第二幕电影化（滚动驱动的分镜编排骨架）

- Goal：把第二幕从“加载即飞行”升级为“滚动 → 分镜 step → 相机动作”的可扩展骨架，为后续加入信息卡片/卫星/星尘等元素打地基。
- Acceptance Criteria：
  - `/act2` 存在 scrollytelling sections（space/earth/target/summary）
  - 使用 `IntersectionObserver` 将滚动映射到 step，并触发相机动作（不引入 `/demo` 的 Missions/API 工作流）
  - `Replay FlyTo` 能按 step 顺序回放一次
- TDD：
  - `act2Timeline.test.js` 覆盖 step 归一化/顺序/目标解析
  - `act2ScrollyWiring.test.js` 门禁：断言 sections 与 wiring 存在
  - 继续沿用 `act2Isolation.test.js` 防耦合回退

- Status：✅ 已完成（滚动分镜骨架已落地；`npm test` 全绿）

### Issue #11：第二幕信息卡片（渐进式揭示 / Cinematic Cards）

- Goal：在不引入 `/demo` 工作流的前提下，为第二幕增加“镜头叙事信息卡片”，让体验更像电影分镜，而不仅是相机运动。
- Acceptance Criteria：
  - `/act2` 在 Cesium 画面上叠加一张随 `activeStep` 切换的 info card（含过渡动画）
  - 卡片内容随 step（space/earth/target/summary）渐进揭示，并保留明确逃生入口（Landing / Demo）
  - 仍保持隔离：不引入 `apiService` / Missions / demo 状态机
- TDD：
  - `act2InfoCards.test.js` 门禁：info card 存在、内容词条存在、escape hatches 仍在
  - `act2Isolation.test.js` 继续防耦合回退

- Status：✅ 已完成（渐进式 info card + 过渡动画已落地；`npm test` 全绿）

### Issue #11.1：Act2 Overlay 进一步降噪（电影感终版，🧩 待开始）

- Goal：把 Act2 从“开发态 overlay”收敛为“电影感 HUD”，默认只保留一张玻璃拟态信息卡。
- Acceptance Criteria：
  - 默认态：仅保留 info card（或一行 HUD），其它控制（Back/Demo/Replay/Targets/Tours）收纳为可展开菜单。
  - 仍保持隔离：不引入 `/demo` 的 Missions/API/状态机。
  - 不恢复 Cesium 默认控件（timeline/animation/home/baseLayerPicker 等保持关闭）。
- TDD：
  - `act2InfoCards.test.js` 继续门禁：info card 仍在。
  - 新增/调整门禁（如需要）：断言折叠菜单存在且默认收起。
- Status：✅ 已完成（HUD 默认收起；信息卡片常驻；控制收纳到 Menu）

### Issue #12：第二幕多目标（Target Variants / URL 同步切换）

- Goal：让第二幕 choreo 不再只绑定单一地点（poyang），而是支持多个目标点，并在 UI 内可一键切换（同步 URL），为后续“案例库/路径导航”做铺垫。
- Acceptance Criteria：
  - `/act2` 提供目标 chips（至少 `poyang / yancheng / yangtze`），点击后更新 `?choreo=`
  - 切换目标后按当前 `activeStep` 重新触发一次镜头（保持叙事连续性）
  - 目标解析逻辑为纯函数模块（不引入 Cesium / 不触碰 `/demo` 数据层）
- TDD：
  - `act2Timeline.test.js` 覆盖新目标解析
  - `act2TargetsWiring.test.js` 门禁：chips + `history.replaceState` + `?choreo=` 写入

- Status：✅ 已完成（多目标切换 + URL 同步已落地；`npm test` 全绿）

### Issue #13：第二幕推荐路径（Tours / 一键按序回放）

- Goal：把多个目标点组织成“推荐路径”，一键按序回放（切换 `?choreo=` 并触发镜头回放），让第二幕像电影的“路线分镜”。
- Acceptance Criteria：
  - `/act2` 的 `target` 分镜包含 Recommended Path（至少 2 条 tours）
  - 点击 tour 后按序执行：`setTarget(target)`（同步 URL）→ `replay()`（镜头回放）
  - 仍保持隔离：不引入 `/demo` 的 Missions/API/状态机
- TDD：
  - `act2ToursWiring.test.js` 门禁：tours 存在、playTour 使用 `setTarget + replay`、URL 同步仍走 `replaceState`

- Status：✅ 已完成（tours UI + 顺序回放已落地；`npm test` 全绿）

### Issue #7：第四幕数据星海（假数据 + 交互）

- Goal：用假 embedding 节点实现“点亮/飞向簇”的未来感。
- Acceptance Criteria：
  - 500+ 节点渲染不卡死
  - 搜索框输入触发聚焦某簇

- Status：✅ 已完成（Landing 已集成 DataGalaxy；含搜索聚焦簇；vitest 回归全绿）

---

## Milestone M1.5：Landing 视觉与入口治理（🧩 补齐体验）

### Issue #14：第一幕主视觉完善（Hero Visual Pack）

- Goal：把第一幕做成“产品首屏”，对齐 v4：发光球体/星尘/高级排版。
- Acceptance Criteria：
  - 首屏存在可替换的主视觉层（球体与星尘，允许先用 WebM/WebP/Lottie）
  - 明确素材放置路径与命名规则（便于设计迭代）
  - 不引入 Cesium（Landing 仍必须轻量）
- Implementation Notes：
  - Landing 已挂载 `HeroVisual`（Three.js 点云球体 + 星尘，含 WebGL 能力检测与 unmount 清理）。
  - 说明：当前为保证“第三方也能稳定看到动效”，默认不因 `prefers-reduced-motion` 自动禁用动效；如需无障碍遵循，可在 #14.1 中补回可选开关。
  - 可替换素材目录已建立：`frontend/public/zero2x/hero/` 与 `frontend/public/zero2x/ui/`（含 README 命名约定）。
- TDD：
  - `landingHeroVisual.test.js` 门禁：HeroVisual wiring + three 动态加载 + 资产目录存在
- Status：✅ 已完成（MVP 版本已落地；后续可按素材替换进一步提升质感）

#### Issue #14 补充：结构性过曝修复（2026-03-02）

- Root cause：粒子/连线在球心高密度叠加造成 overdraw，即使 toneMapping/opacity 也只能缓解。
- Fix：将 dense 与 neural 分布改为外壳（Dyson shell），物理上移除球心点；并弱化中心 glow 渐变起点。
- Outcome：中心白爆与放射刺显著下降，文字可读性恢复（不靠“硬压暗”）。

### Issue #14.1：第一幕“资产替换包”与微交互加固（🧩 待开始）

- Goal：把 Issue #14 的“工程实现”升级为“对外可展示的产品首屏”，优先靠素材与微交互达成。
- Implementation Notes：
  - 素材优先级：WebM（体积/质量）> WebP（兜底）> Three.js（生成式兜底）。
  - 不引入外部 CDN：素材随仓库版本管理（或由部署流程注入），确保离线/内网可演示。
- Acceptance Criteria：
  - `frontend/public/zero2x/hero/` 下投放：`stardust_bg.webm`、`stardust_bg.webp`、`glow_sphere.webm`、`glow_sphere.webp`。
  - Dev/Prod 下首屏无 404（浏览器 Network 面板无红字），且首屏仍不引入 Cesium。
    - （可选）若需要遵循无障碍偏好：`prefers-reduced-motion: reduce` 下主视觉提供静态降级（无三维动画/视频）。
- Tests：延续 vitest wiring 门禁（不做像素级截图测试）。
- Status：🧩 待开始

  ---

  ## 现象分析：为什么下翻到“第二幕”还是占位文字？

  你在 Landing 页面下翻看到的“第二幕：宏观孪生（…占位）”属于 `/` 的叙事段落（Zero2xApp 的 Act sections），它的角色是“叙事骨架 + CTA”，并不会在 Landing 内加载 Cesium。

  当前设计有意保持：

  - **Landing 轻量**：不在 `/` 引入 Cesium，避免首屏变重、影响 TTI；真正的电影化体验在 `/act2`。
  - **Act2 区块文案仍保留了“占位”描述**：说明这里是“预告/目录”，而不是实际场景。

  如果你期望“下翻到 Act 2 时立刻进入真正的第二幕”，那会受到以下门槛影响：

  - **一次性触发机制**：自动跳转只会在 session 内触发一次（使用 `sessionStorage` 做去抖）；你可能已经触发过一次或在同一标签页里反复测试。
  - **阈值偏保守**：IntersectionObserver 需要 Act2 区块达到较高可见比例才触发；不同屏幕高度/滚动方式可能达不到阈值。
  - **无障碍偏好门槛**：Landing 的“滚动触发跳转”可能会尊重 `prefers-reduced-motion`（更保守的导航策略），导致只展示占位段落而不自动跳转。

  ### 升级方向（不破坏“Landing 轻量”前提）

  推荐从“预告可视化”升级，而不是直接把 Cesium 搬进 `/`：

  1) **替换占位文案 → 真实内容卡片**（低成本、高收益）
    - 把“（占位）”字样移除，改成清晰的能力点 + 数据源 + 交互说明（仍不加载 Cesium）。

  2) **Act2 预告素材层**（视频帧欺骗 / WebM 优先）
    - 在 Act2 段落内嵌一个轻量 WebM/WebP（或短 loop），展示“飞向鄱阳湖”镜头预告。
    - 仍保持离线可运行（素材随仓库或部署注入）。

  3) **升级“进入第二幕”的触发策略**
    - 保留自动跳转，但增加明显的“Enter Act2”按钮与倒计时提示；或降低阈值/增加手势提示。
    - 将 reduced-motion 的门槛改为“默认不过度自动跳转，但按钮仍可进入”。

  4) **真正的第二幕持续加料在 `/act2`**
    - 在 `/act2` 内做分镜素材/星尘/HUD/卡片，而不是在 `/` 里加载 Cesium。


### Issue #15：Landing 下滑反馈（Scroll Progress / Highlight）

- Goal：滚动时页面必须“在更新”：进度、当前幕高亮、渐隐渐显。
- Acceptance Criteria：
  - 滚动时可见的 Act 进度/高亮（scrollspy）
  - 不依赖 GSAP 也可先达标（IntersectionObserver 方案）
- TDD：
  - `landingScrollspy.test.js` 门禁：存在 scrollspy + IntersectionObserver wiring
- Status：✅ 已完成（已补 scrollspy 导航与门禁测试；`npm test` 全绿）

### Issue #16：减少 `/demo` 入口（De-emphasize Demo Entry）

- Goal：减少 Landing 首屏对 `/demo` 的强曝光，默认路径走“叙事 → 工作台”。
- Acceptance Criteria：
  - 移除首屏主按钮级别的 Demo 入口；保留低噪入口（如页脚）
  - 仍能快速到达 `/demo`（工具化验证系统可用）
- TDD：
  - `landingScrollspy.test.js` 门禁：不出现首屏 Open Demo 主按钮；仍保留 `/demo` 链接
- Status：✅ 已完成（Demo 入口已降噪至页脚；`npm test` 全绿）

### Issue #19：Omni-Bar 命令面板（从 stub → 可用）

- Goal：让 Omni-Bar 成为“最小可用的命令入口”，形成意图 → 路由/动作的闭环（即便仍是视觉欺骗，也要可演示）。
- Acceptance Criteria：
  - 支持最小命令集（示例）：
    - `act2` / `earth` → 跳转 `/act2?choreo=poyang`
    - `workbench` → 跳转 `/workbench`
    - `demo` → 跳转 `/demo`
    - `help` → 展示可用命令提示
  - 输入鲁棒：允许前后空格、大小写不敏感；未知命令给出可理解的提示。
  - 保持离线可运行：不引入外部 CDN 强依赖（Tailwind/GSAP 可选但非必须）。
- TDD（vitest）：
  - 新增 `omnibarCommands.test.js`：命令解析为纯函数；路由行为可通过 mock window/location 或 router stub 门禁。
- Status：✅ 已完成（支持 help/demo/workbench/act2 命令；输入鲁棒；vitest 门禁新增通过）

---

## Milestone M3：AI-Native 工作台（渐进式，🔄 后续）

### Issue #8：工作台壳（三栏布局 + Typewriter）

- Goal：把“Agent Flow / 3D Preview / Papers”三栏做成可信的 IDE 面板。
- Acceptance Criteria：
  - 打字机效果模拟流式生成
  - 不加载 Monaco（先壳后芯）

- Status：✅ 已完成（新增 `/workbench` 工作台壳，含 typewriter stub）

### Issue #9：Monaco Editor 按需加载

- Goal：只在工作台真正进入时加载 Monaco，避免首页首屏变重。
- Acceptance Criteria：
  - Landing 首屏 bundle 不包含 Monaco
  - 打开工作台后才加载

- Status：✅ 已完成（动态 import `monaco-editor`，仅在 `/workbench` 进入时加载）

---

## Definition of Done（所有 Issue 通用）

- Dev/Prod 的 make smoke 全绿
- `pytest` 与 `frontend npm test` 通过
- 文档同步：README + zero2x_v4
- 不引入“必须联网才能跑”的硬依赖（除非明确标注为可选）

## Security & Dependency Hygiene（滚动）

- ✅ 2026-03-02：前端执行激进修复 `npm audit fix --force`
  - 结果：`npm audit` 0 vulnerabilities
  - 依赖对齐：Vite 7 + Vitest 4，并升级 `@vitejs/plugin-vue` 到 6.x 以匹配 Vite 7
  - TDD：`npm test` 全绿；构建：`npm run build` 通过

- ✅ 2026-03-02：修复 Docker Dev 前端运行时不稳定（Node 版本/依赖解析）
  - Node 基线：前端相关容器升级到 Node `20.19`（满足 Vite/Cesium engines）
  - node_modules 卷自愈：启动时探测 `vite/three` 可解析性，缺失则自动 `npm ci`
