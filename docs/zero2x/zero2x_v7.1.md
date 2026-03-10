Zero2x 021 v7.2：Copilot 驱动的通用科研工作台与空间交互蓝图

核心愿景：视窗即现场，代码即算力
摒弃传统的单学科工具拼凑，Zero2x 正构建全新的 AI-Native 通用科研工作台。依托 021 基础模型的跨模态推理能力，我们打破了从广袤空天（$10^{20}$m）到微观分子（$10^{-9}$m）的物理壁垒。系统采用**“全尺度万能底座 (Omni-Scale Base) + 显性双态 UI + Copilot 空间智能副驾”**的下一代交互范式。

零、 状态更新与下一步计划 (As-built 跟踪)

本节保留 v7.1 工程约束与交付追踪体系。

快照（可运行 + 有门禁，截止 2026-03-10）

- v7.1+ 体验稳定化：Global Standby / Intent-Driven Dive / Command Palette / HUD 顶栏 / Lab-Theater 门控均已落地。
- v7.2 Phase 4 已收口：Swipe 空间态 + 情境时间轴 HUD + Hybrid Router（默认关闭，flag+key 才触网，异常回退 stub）。
- Phase 4 清债完成：移除遗留 EXECUTE 文案；Swipe 已面板化（无 Left/Right 选择器，左侧纯净底图、右侧叠加所有启用图层）；Hybrid Explore 离线门禁已补齐。
- 回归门禁：前端 Vitest、后端 Pytest 保持全绿。

已完成（明细保留，用于追溯）

UI / 交互（前端）

右侧 Copilot Chat 已完成三段式结构：Header / Chat History / Input Zone（chips 紧贴 textarea 上方，气泡左右分离，CoT 手风琴可折叠）。

已落地（v7.1+ 体验升维，前端优先级最高）：

- Global Standby：进入 /workbench 后默认深空轨道视角待机（慢速旋转），不再“进入即跳本地”。
- Intent-Driven Dive：仅在 Copilot 工具事件触发 fly_to/camera_fly_to 后才停止待机并俯冲到目标区域。
- Cmd/Ctrl+K Command Palette：输入区默认折叠胶囊；唤醒后多行自适应 + 毛玻璃指令列表；执行后自动折叠。
- 赛博 HUD 顶栏：顶部导航采用 glass + scanline HUD 视觉（不影响 Twin 拖拽），提供 Lab/Theater 门控、Scale Toggle 与命令面板入口。
- Lab Mode 状态保持：执行流程不再强制切换 Theater；Theater 仅由显式拨片/F11 触发。
- 术语升级：UI 可见文案 Macro → Sky（内部 scale key 仍为 macro，避免破坏数据/逻辑）。

交互细节（补充）：为减少视觉干扰，移除了输入区上方常驻的“演示 chips 条”，演示列表统一收敛到 Cmd/Ctrl+K 的 Command Palette 内。

确保 HUD overlay 默认 pointer-events: none，面板选择性 pointer-events: auto，保证 Twin 可拖拽交互。

Demo 全覆盖（12+2 = 14）

前端场景注册已覆盖 14 个 demo context（含新增 Demo 13 global）。

Backend v7 Copilot stub：/api/v7/prompts 提供 prompt chips；/api/v7/tools 注册“地学工具 + UI 工具”；/api/v7/copilot/execute 确定性路由。

TDD 门禁（已启用）

前端 Vitest：CopilotChatPanel UI 回归测试、场景注册回归测试。

后端 Pytest：v7 Copilot 合同测试。

工具调用 → 结构化产物（Phase 1 最小闭环已落地）

UI 工具定义与执行：add_cesium_imagery/vector, show_chart, generate_report, execute_editor_code 均已在纯函数映射层打通。并能稳定写入左侧的统一资产面板 (Unified Artifacts)。

工具命名兼容：文档中使用的 `fly_to` 与工程内的 `camera_fly_to` 语义一致；后端 tools 列表与前端 handler 均支持两者兼容（推荐蓝图名 `fly_to`；保留 `camera_fly_to` 作为历史/兼容名）。

As-built（补充，截止 2026-03-06）：

- `fly_to` 已作为 `camera_fly_to` 的别名正式进入后端 tools 列表，并在前端 Workbench 事件应用层按同等语义处理。
- 合同门禁已覆盖：后端 tools 列表包含 `fly_to`；前端 Vitest 全绿。

下一步计划 (Phase 2 & 3)

Phase 2：Earth scale 真实打通（以同源瓦片为主）。本仓库不提供 `/api/v1/aef/*`，真实链路以既有 `/api/layers -> /api/tiles/{tile_id}/{z}/{x}/{y}` 为准：

- v7 Copilot execute 优先内部调用 `/api/layers` 获取真实 `tile_url`，并通过 `add_cesium_imagery` 挂载到 Cesium。
- 若 GEE 不可用/返回非 200：必须确定性降级为同源示例 overlay（如 OSM），同时 `generate_report` 解释原因，保证演示链路不崩。
- 后端 Pytest 以“事件形态/工具发射”做合同门禁，不依赖真实 GEE。

As-built（截止 2026-03-06）：Demo 1/3/4/5/周口等已接入上述“真实优先 + 降级可解释”策略；亚马逊 Demo 同时挂载 imagery（真实优先）+ 矢量聚类仍为示例占位。

Phase 3：补齐剩余 Demo 的“可视化最低可用实现（MVR）”。包括 terrain, custom shader, night mode, 3D tiles 等渲染能力，以及 Demo 14 的宏微观双模态虫洞跃迁。

As-built（补充，截止 2026-03-06）：

- 后端 `/api/v7/tools` 已注册 Phase 3 工具：`enable_3d_terrain`, `add_cesium_3d_tiles`, `apply_custom_shader`, `generate_cesium_custom_shader`, `add_cesium_extruded_polygons`, `set_scene_mode`, `play_czml_animation`, `set_globe_transparency`, `add_subsurface_model`, `trigger_gsap_wormhole`。
- 后端 v7 确定性路由已在 Demo 7/11/14 的事件序列中显式发射上述关键工具（MVR 级别，允许 stub result）。
- 前端 Workbench 已能接收并“可见化”这些工具调用（Artifacts 层确定性写入 + Cesium 侧 best-effort 应用：terrain/tileset/night/CZML/透明度/挤出体；虫洞以 macro→micro 量子俯冲动画实现）。
- TDD 门禁已扩展：后端 Pytest 覆盖 Phase 3 tools list + Demo 7/11/14 发射序列；前端 Vitest 覆盖 Phase 3 artifacts 归约逻辑。

Phase 4（v7.2 升级需求，来自 update_patch_0303.md，2026-03-03 版本）：将“对比、时间、LLM”升华为工作台的空间态与交互底座

本阶段不是“加一个功能点”，而是将 Swipe/时间轴/LLM 统一纳入 Twin Canvas 的空间交互范式：

4.1 Swipe（卷帘对比）= Twin Canvas 的一种“特殊空间态”

定位：Swipe 不被当成单一工具按钮，而是 Twin Canvas 的一种稳定空间态（类似 Lab/Theater 之于 UI）。

触发方式：

- 手动（交互层级纠偏）：收敛到图层面板（Unified Artifacts / Layers）的 View Mode：Overlay / Swipe 切换（不在顶栏常驻）。
- Copilot：当识别到“对比/差异/两年”意图时，可通过工具调用自动开启（例如：enable_swipe_mode）。

视觉表现：

- 中央 Twin 视窗出现绝对定位的拖拽分割线与把手（光刃感），拖动实时更新对比位置。

Cesium 底层支撑：

- 使用 `imageryLayer.splitDirection = RIGHT`（Swipe 开启时将业务/AI overlays 统一归入右侧）。
- 使用 `viewer.scene.splitPosition = 0..1`。

验收标准（含 TDD 门禁）：

- 后端 `/api/v7/tools` 注册 `enable_swipe_mode` / `set_swipe_position` / `disable_swipe_mode`（或等价的 enabled=false）。
- 前端能够在 Earth scale 上：开启 Swipe → 左右图层正确分配 → 拖拽分割线实时更新 `splitPosition` → 关闭 Swipe 后恢复 NONE。
- 单测锁定：EngineRouter 中存在 splitDirection / splitPosition 相关处理；Workbench 具备 Swipe HUD 组件与工具映射。

4.2 底部栏重构：废弃 EXECUTE，时间轴升格为“悬浮式情境组件”

结论：`EXECUTE ON TWIN` 冗余，破坏“对话即操作”的心智模型。v7.2 起删除实体执行按钮，执行收敛到右侧 Chat Input（Enter 或 Cmd/Ctrl+K）。

升级策略：删除写死的底部通栏；仅当当前上下文挂载了“时间属性数据”（如近 7 年城建扩张、季节生态变化）时，时间轴作为半透明悬浮控件出现在画面正下方。

验收标准（含 TDD 门禁）：

- 前端不再出现 `EXECUTE ON TWIN` 文案/按钮。
- 时间轴默认不显示；当 `currentContextHasTime` 且 `isTimeSeriesDataReady` 为 true 时才显示（未打通真实时序数据时宁可隐藏，保证演示高级感）。
- TimelineHUD 必须是“受控组件”（progress / isPlaying / isLoading 由父级驱动），避免组件内部自嗨式 setInterval 伪播放。
- 时间轴为中央悬浮控件（不占据全宽底栏），具备最小可用交互：拖动/播放暂停（由外部数据加载队列/引擎时钟驱动）。

4.3 Copilot AI 升级：从“预设剧本”到“混合路由 (Hybrid Router)”

目标：既接入真实大模型（DashScope/Qwen OpenAI-compatible）获得自然语言解释与探索能力，又确保 15 个黄金 Demo 在汇报场景 100% 可控。

混合路由策略：

- 分支 A（硬路由 Demo）：命中演示上下文时，强制执行确定性预设 Tool 链（安全不翻车）+ 可选调用 LLM 生成口语化讲解文案（仅文案可由 LLM 生成）。
- 分支 B（探索态）：未命中时，允许 LLM Tool Calling，但必须受工具白名单/参数校验/超时保护约束。

工程约束：

- 默认保持 v7 的确定性 stub 行为（TDD 合同不变）。
- Hybrid Router 必须可通过 feature flag 启用；测试环境下不得进行真实网络调用。

4.4 开发计划（TDD 优先，推荐按 PR 切片交付）

Slice A：Swipe 空间态（前端为主）

- 测试先行：Vitest 新增 “Swipe plumbing / splitPosition / splitDirection / HUD 可见性” 的合同门禁。
- 后端：/api/v7/tools 注册 enable_swipe_mode / set_swipe_position / disable_swipe_mode；Demo 1 在合适时机发射 enable_swipe_mode（可选）。
- 前端：EngineRouter 落地 Cesium splitDirection + scene.splitPosition；EngineScaleRouter 暴露 setSwipeMode/setSwipePosition；Workbench 映射工具调用 + HUD 拖拽。

Slice B：底部栏 → 悬浮式情境组件（前端为主）

- 测试先行：确保不再出现 EXECUTE ON TWIN；时间轴默认隐藏；当 currentContextHasTime=true 时显示。
- 实现：TimelineHUD 改为无执行按钮的悬浮组件；Workbench 使用场景元数据/挂载数据决定显示。

Slice C：Hybrid Router（后端为主，默认关闭）

- 测试先行：feature flag 打开但缺少 LLM key 时，行为仍与 stub 一致且不报错。
- 实现：保留确定性工具链；仅对 final 文案做可选 LLM 替换（不影响工具调用确定性）。

回归门禁（每次合入必须通过）

- 前端：`npm test`（Vitest run 全绿）。
- 后端：Pytest 至少覆盖 v7 prompts/tools/execute 合同测试。

4.5 完成情况盘点（As-built，对照 update_patch_0303.md，截止 2026-03-10）

说明：本节仅记录“已落地的工程事实（含门禁）”，不改变 v7 的确定性 stub 合同。

| 需求条目（update_patch_0303） | 状态 | 工程落点（实现） | 门禁/验收落点 |
|---|---|---|---|
| Swipe 被提升为 Twin Canvas 的空间态（非一次性按钮） | ✅ Done | `swipeEnabled/swipePosition` 作为 Workbench 空间态，离开 Earth/切场景时自动退出 | 前端合同：`frontend/tests/workbenchV72SwipeTimeline.test.js` 锁定 plumbing；后端合同：`tests/test_v7_copilot_api.py` tools list | 
| 手动触发（交互层级纠偏）：Swipe 不在顶栏常驻 | ✅ Done | Swipe 模式开关收敛到面板（Layers 区的 View Mode: Overlay/Swipe），不再提供 Left/Right 选择器 | 前端合同：Vitest 锁定“顶栏无 Swipe 按钮”+ 面板含 View Mode；运行验收：在面板一处完成开关+配置 |
| Copilot 触发：识别“对比/差异/两年”意图可自动开启 | ✅ Done（通过工具事件） | 后端 stub / Hybrid explore 均可发 `enable_swipe_mode`；前端映射 `enable_swipe_mode`/`set_swipe_position`/`disable_swipe_mode` | 后端验收：Demo 1 事件序列包含 `enable_swipe_mode`；工具列表包含三件套 |
| 视觉表现：中央 absolute 分割线 + 把手，拖动实时更新位置 | ✅ Done | `frontend/src/views/workbench/components/SwipeHUD.vue`（pointer drag + keyboard） | 运行验收：拖拽更新；工具 `set_swipe_position` 可编程更新 |
| Cesium 底层：`ImagerySplitDirection` + `scene.splitPosition` | ✅ Done | `frontend/src/views/workbench/EngineRouter.vue`：`_applySwipeState` / `setSwipeMode` / `setSwipePosition01`，并在图层重建后重应用 | 前端合同：测试锁定关键字符串与 expose |
| 底部栏重构：废弃 `EXECUTE ON TWIN` | ✅ Done | Workbench 主 UI 已移除底栏执行；遗留组件中的旧文案已清理 | 前端合同：`frontend/tests/workbenchV72SwipeTimeline.test.js` 锁定“不出现 EXECUTE”；运行验收：无底栏执行按钮 |
| 时间轴升格为 Contextual Widget：默认隐藏，仅在“数据就绪”时出现 | ✅ Done | `currentContextHasTime` + `isTimeSeriesDataReady` + `showTimelineHud`（默认严格隐藏；可通过 flag/参数强制展示以便演示） | 前端合同：Vitest 锁定“TimelineHUD 受控 + 无内部 timer”与“showTimelineHud gate”；运行验收：无数据时不出现 |
| 时间轴受控化（为未来真实时序数据准备） | ✅ Done | TimelineHUD 改为 controlled component（progress/isPlaying/isLoading + emits）；父级负责驱动/加载队列 | 前端合同：Vitest 锁定 props/emits；后续接入 GEE ImageCollection 时无需改 HUD |
| Landing→Workbench 视觉-数据一致：带 context 自动下钻 | ✅ Done | onViewerReady：无 context 时保持 Global Standby；有 `?context=` 时短暂停机后 stopStandby + flyToScenario | 前端合同：`frontend/tests/workbenchStandbyV71.test.js` 锁定“viewer-ready 必进 standby，且无 context 不下钻”；`frontend/tests/workbenchAutoDive0303.test.js` 锁定“context auto-dive” |
| Hybrid Router：分支 A 硬路由 Demo + 可选 LLM 口语化文案 | ✅ Done（默认关闭） | `backend/v7_copilot.py`：`_maybe_hybridize_final_text`（flag+key 才触网；异常回退 stub） | 后端合同：flag=1 但无 key 时仍能返回 final（离线安全） |
| Hybrid Router：分支 B 探索态 Tool Calling（白名单/校验/超时） | ✅ Done（默认关闭） | `backend/v7_copilot.py`：`_maybe_hybrid_explore_events`；`backend/llm_service.py`：OpenAI-compatible tool_calls 解析 | 后端门禁：离线 mock LLM tool_calls 回归测试覆盖 allowlist + args 过滤 + 事件形态稳定 |

4.6 Phase 4 收口清单（As-built，截止 2026-03-10）

- ✅ 清债：全仓库不再出现 `EXECUTE ON TWIN`（含遗留面板组件）。
- ✅ Swipe 面板化（完成交互层级纠偏）：Unified Artifacts / Layers 区提供 View Mode（Overlay/Swipe），并与引擎空间态联动（左纯净底图、右侧叠加启用图层）。
- ✅ Hybrid Explore 门禁补齐：后端回归测试通过 mock/monkeypatch 固定 tool_calls，验证 allowlist + args schema 过滤，且保持离线不触网。

4.7 延展项（As-built，截止 2026-03-10）

- ✅ Swipe 图层候选扩展：面板候选从“硬编码白名单”改为基于当前 Layers 列表动态推导（并优先展示 enabled 图层）。
- ✅ 文档与门禁同步：前端 Vitest 新增合同断言，锁定“无选择器 + overlays 统一右侧”的空间态合同。
- ✅ Hybrid Explore 渐进上线：后端探索态新增软速率限制 + 硬超时包裹 + tool_calls 数量上限 + args size cap（仍保持默认关闭 + 无 key 不触网 + 异常回退 stub）。

4.8 下一步建议（可选）

- Swipe 进一步增强（非必需）：当 overlays 很多时，可提供“右侧 overlays 分组/折叠”与“一键只看 AI overlays”的便捷开关（但仍保持无 Left/Right 选择器）。
- AI 图层可见性提示：当 `ai-imagery` 的 `tile_url` 为空但用户已启用时，在面板提示“尚未生成 AI overlay（需要一次 add_cesium_imagery 事件）”。

4.9 增量升级建议（来自 update_patch_0303.md 最新反馈，建议优先级高）

说明：下列三项是对“空间态 + 演示稳定性 + 探索态真实感”的补齐。优先级高于纯功能扩展。

4.9.1 Swipe 与 AI 矢量图层的结合（Vector/Entity 也需可被卷帘）

- 痛点：Cesium 的 `splitDirection/splitPosition` 仅对 `ImageryLayer` 生效；GeoJSON/Entity（矢量）默认不会被卷帘裁剪。
- 建议：引入“矢量侧裁剪”能力：
	- 优先：对可用的 Primitive/Tileset（如 3D Tiles / Primitive-based overlay）挂载 `ClippingPlaneCollection`（做到几何级裁剪）。
	- 退化：若 overlay 仍为 Entity/DataSource，则以“屏幕空间裁剪”做演示级近似（基于 entity centroid 的屏幕 x 与 `splitPosition` 决定 show/hide）。
- 验收/门禁：前端合同测试锁定 EngineRouter 存在矢量裁剪/退化逻辑入口，并在 Swipe position 更新时同步更新裁剪状态。

4.9.2 禁用 Cesium 默认双击追踪（避免 Boundary 双击导致视角灾难）

- 痛点：Cesium 默认 `LEFT_DOUBLE_CLICK` 会触发 trackedEntity/飞行锁定，演示中常导致“平切/地下仰视”。
- 建议：EngineRouter 初始化时移除默认双击 action；可选将双击接管为“优雅 flyTo（俯视 -45°）”。
- 验收/门禁：前端合同测试锁定 `removeInputAction(LEFT_DOUBLE_CLICK)` 存在。

4.9.3 Copilot 自由输入不再跑 Stub 剧本（探索态与演示态解耦）

- 痛点：自由输入无论内容都会触发 `runExecute()`（硬编码剧本），覆盖真实 events/final text，形成“伪 AI 死循环”。
- 痛点：
	- 自由输入无论内容都会触发 `runExecute()`（硬编码剧本），覆盖真实 events/final text，形成“伪 AI 死循环”。
	- 另一个常见翻车点：前端过度依赖 `events[].type === 'final'`，当后端只是闲聊/未发 final 事件时，UI 会出现“无响应/空白”。
- 建议：
	- Preset（演示剧本）仍走 `runExecute()`，确保 100% 可控。
	- Free Chat（自由输入）仅渲染后端返回（优先 `resp.reply/resp.text`，其次 `events.final`），不再启动 stub 打字机。
	- 若后端仅返回 tool events 但无自然语言回复，必须提供拟人化兜底文案（避免空白）。
- 验收/门禁：
	- 前端合同测试锁定 onCopilotSubmit：不再无条件调用 `runExecute()`；并且存在 `resp.reply/resp.text` 的文本回落策略。
	- onCopilotSelectPreset 仍可触发剧本。

4.9.4 Engine 图层加载并发化（切场景避免白屏排队）

- 痛点：切换场景时，图层加载若按 `for ... await` 串行执行，会导致 GeoJSON/imagery 互相排队，形成明显白屏等待。
- 建议：将 Boundaries / AI Vector / 各 imagery overlay 的加载包装成任务池，使用 `Promise.allSettled(loadTasks)` 并发执行；最后统一做 reorder + swipe state re-apply。
- 验收/门禁：前端合同测试锁定 EngineRouter 存在 `Promise.allSettled` 的并发加载路径，且 token cancellation（applyToken）仍生效。

4.9.5 场景切换强制 FlyTo（避免 preset 无 fly_to 时镜头不动）

- 痛点：点击 preset 仅改变 `contextId`，如果 prompt 没触发 `fly_to/camera_fly_to` 工具事件，镜头可能停留在旧场景（认知割裂）。
- 建议：在 Workbench 顶层监听 `scenario.id` 变化（非初次），viewerReady 后延迟约 100ms 强制 `stopGlobalStandby()` + `flyToScenario()`。
- 验收/门禁：前端合同测试锁定 watcher 存在，且包含 `setTimeout(..., 100)` 与 `flyToScenario` 调用。

As-built（已落地，截止 2026-03-10）

- ✅ 矢量卷帘（退化实现）：`frontend/src/views/workbench/EngineRouter.vue` 在 Swipe 模式下对 `ai-vector` GeoJSON 以屏幕空间中心点做 show/hide（与 `scene.splitPosition` 同步）。
- ✅ 禁用双击追踪：`frontend/src/views/workbench/EngineRouter.vue` 在 viewer-ready 时移除 `LEFT_DOUBLE_CLICK` 默认 action。
- ✅ Free Chat 解耦 stub：`frontend/src/WorkbenchApp.vue` 的 onCopilotSubmit 仅应用后端 events/final，不再调用 `runExecute()`。
- ✅ Free Chat 文本回落：优先渲染 `resp.reply/resp.text`，再回落到 `events.final`，仍无文本时给出拟人化兜底（避免空白）。
- ✅ 切场景图层加载并发化：`frontend/src/views/workbench/EngineRouter.vue` 的 applyLayersAsync 使用 `Promise.allSettled` 并发加载 overlays，减少排队白屏。
- ✅ 场景切换强制 FlyTo：`frontend/src/WorkbenchApp.vue` 监听 `scenario.id` 变化，在 viewerReady 后强制 stopStandby + flyToScenario（即使 prompt 未发 fly_to）。
- ✅ 门禁：`frontend/tests/workbenchV72SwipeTimeline.test.js` 断言三项合同均存在。

一、 架构演进：全尺度万能底座 (Omni-Scale Foundation)

为了全面兼容四大核心学科，工作台底层视窗不再绑定单一引擎，升级为受 021 模型自动调度的**“万能渲染容器”**。

1.1 空天视界 (Sky-Sphere)

🌍 空天态 (Sky / 021-Earth)：引擎 CesiumJS。处理全球地形、卫星遥感特征与天基算力投射。

🌌 天文态 (OneAstronomy / 021-Space)：引擎 Three.js。渲染星系、宇宙微波背景与引力波。

1.2 微观深潜 (Micro-Sphere)

🧬 基因态 (OneGenome / 021-Bio)：引擎 Three.js。分子晶格与 DNA 构象预测。

🧊 材料态 (OnePorous / 021-Material)：引擎 Three.js。航天材料应力拓扑分析。

二、 UI 架构重构：空间计算 IDE (Spatial IDE)

全面汲取 Cursor 与 VS Code 的精髓，采用严格的**“左-中-右”流式网格系统**，同时结合大屏演示诉求引入**“双态引擎”**。

2.1 界面双态引擎 (Dual-State UI) 与显性演示门控

系统顶栏设计了极具科技感的**“状态切换拨片”**，解耦了场景执行与 UI 状态，将控制权完全交还给演示者：

- 🛠️ 硬核作业态 (Lab Mode - 默认)：左右实体面板停靠，呈现代码、产物与事件过程，强调白盒可解释。
- 🎬 沉浸演示态 (Theater Mode)：一键折叠两侧面板，Twin Canvas 全屏，优先汇报稳定与观感。

2.2 全局视界降临 (Global-to-Local Spatial Flow)

- Global Standby：进入 /workbench 默认轨道待机（慢速旋转），不“进入即跳本地”。
- Cinematic Auto-Dive（来自 update_patch_0303）：当用户从 Landing 携带明确意图（例如 `/workbench?context=yuhang`）进入时，先短暂停机形成“蓄势”，随后自动停止待机并 FlyTo 到该场景，避免“数据已切换但镜头仍在太空”的认知割裂。
- Intent-Driven FlyTo：除上述“带 context 的首次入场自动下钻”外，其余情况下仅当工具事件触发 `fly_to/camera_fly_to` 时才俯冲到目标区域。

2.3 三栏流式布局 (Left-Center-Right)

- 左侧 Unified Artifacts：Layers / Code / Charts / Reports（统一承接 tool 产物）。
- 中央 Twin Canvas：纯净引擎视窗 + 极简 HUD（Swipe/Timeline 等情境控件）。
- 右侧 Copilot Chat：Header / History / Input Zone（Prompt Chips 与多行输入）。

三、 核心 Demo 场景大盘（12+2 = 14，简表）

第一阵列：经典传承（OneEarth）

- Demo 1 余杭城建审计：`fly_to` → `add_cesium_imagery` → `generate_report`
- Demo 2 亚马逊零样本聚类：`add_cesium_vector`
- Demo 3 毛乌素生态穿透：`add_cesium_imagery`
- Demo 4 盐城红线：按 v7.1 稳定链路集成
- Demo 5 周口内涝：按 v7.1 稳定链路集成
- Demo 6 塔拉滩光伏：按 v7.1 稳定链路集成

第二阵列：前沿开拓（空天视界）

- Demo 7 珠峰冰原：`enable_3d_terrain` + `add_cesium_3d_tiles`
- Demo 8 夏威夷形变：`apply_custom_shader`
- Demo 9 刚果碳汇：`add_cesium_extruded_polygons`
- Demo 10 纽约热岛：`show_chart`
- Demo 11 马六甲暗夜：`set_scene_mode('night')` + `play_czml_animation`
- Demo 12 澳洲地下：`set_globe_transparency` + `add_subsurface_model`

第三阵列：系统级张力

- Demo 13 Global 代码热生成：`execute_editor_code`
- Demo 14 宏微观虫洞：`trigger_gsap_wormhole`

四、 核心架构落地（用“真实工程指向”替代长伪代码）

为保持蓝图简洁，本节不再粘贴大段 UI 伪代码；以“可跳转到工程实现”的指向为准。

4.1 工作台壳与三栏布局

- 主入口与全局状态：`frontend/src/WorkbenchApp.vue`（Lab/Theater、HUD、Artifacts 面板、引擎容器、Swipe/Timeline 空间态联动）。
- 引擎适配与 Cesium 行为：`frontend/src/views/workbench/EngineRouter.vue`（Swipe splitDirection/splitPosition 应用、图层重建后重应用）。

4.2 Copilot Chat（输入/历史/门禁）

- 右侧 Chat UI：`frontend/src/views/workbench/components/CopilotChatPanel.vue`。
- v7.2 HUD：`frontend/src/views/workbench/components/SwipeHUD.vue`、`frontend/src/views/workbench/components/TimelineHUD.vue`。

4.3 统一资产面板（Layers/Artifacts）

- 面板与 Tabs：`frontend/src/views/workbench/components/UnifiedArtifactsPanel.vue`。
- Swipe 模式开关：位于 Layers 区（与 Workbench swipe 空间态双向绑定；不再提供 Left/Right 选择器）。

4.4 后端 Hybrid Router 与离线门禁

- Hybrid Router 与探索态过滤：`backend/v7_copilot.py`。
- OpenAI-compatible tool_calls 解析：`backend/llm_service.py`。
- 合同/回归门禁：`tests/test_v7_copilot_api.py`（离线 mock tool_calls，校验 allowlist + args 过滤）。
