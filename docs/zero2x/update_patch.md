# Zero2x 去占位化补丁包（执行手册）

目标：把当前仓库从“工程占位页”升级为**可对外演示的微电影黄金路径**，并确保 Dev/Prod 都稳定可复现（不依赖外部 CDN）。

对齐现状（2026-03-02）：

- 已具备路由骨架：`/`（Landing）→ `/act2`（电影化 Cesium）→ `/workbench`（工作台壳）→ `/demo`（验证系统）
- 已具备黑场转场工具：`frontend/src/utils/navFade.js`（Fade to Black + Esc cancel）
- 已具备 vitest 门禁体系（内容/装配/隔离）

本文件把“口头需求”翻译为**可验收**的工程任务、素材投放规范与 TDD 门禁。

---

## 1) 黄金演示路径（Golden Path）—— 必须硬连线

唯一正确的演示流程：

1. 起点：Landing `/`
2. 输入：在 Omni-Bar 输入一句话意图（例：“帮我分析鄱阳湖流域生态与候鸟迁徙”）
3. 触发：按 Enter
4. 转场：黑场淡出（约 0.5s）
5. 高潮：进入 `/act2?choreo=poyang`，Cesium 从深空飞向鄱阳湖
6. 信息：右侧 Info Card 显示**真实案例文案**（非“测试占位”）
7. 落脚：在 Act2 最后一步提供 CTA → 黑场进入 `/workbench`
8. 结束：工作台自动播放 typewriter demo（展示 Agent workflow）

验收标准（可客观检查）：

- Landing Enter 后，必须进入 `/act2?choreo=poyang`（不允许仅停留在 stub 文本）
- Act2 最后一步必须有 CTA 能进入 `/workbench`
- `/workbench` 首次进入 1 秒内开始自动播放 demo 文本

实现位置（当前代码落点）：

- Landing：`frontend/src/Zero2xApp.vue`
- 黑场：`frontend/src/utils/navFade.js`
- Act2：`frontend/src/Act2App.vue`
- Workbench：`frontend/src/WorkbenchApp.vue`

---

## 2) 去占位化：禁止对外可见的“占位/Placeholder/Stub”

定义：对外演示时，页面中不得出现“占位/Placeholder/测试占位/MVP Stub/TODO(MVP)”等文字。

允许：内部代码注释、测试描述、README 技术说明。

验收标准：

- Landing 五幕区块必须是“预告片式图文”，而不是工程说明。
- Act2 Info Card 必须是案例文案（至少鄱阳湖 case 完整）。
- Workbench 三栏必须是“演示语义”，不出现 Placeholder 字样。

---

## 3) 素材投放规范（Assets Drop Spec）

原则：**先稳定、再升级**。先用本地资产保证 0 404 + 可演示；之后设计替换不改代码。

### 3.1 素材目录

- Hero（第一幕主视觉）：`frontend/public/zero2x/hero/`
- Landing 预告片海报（第二/三幕）：`frontend/public/zero2x/ui/`

### 3.2 文件命名（固定文件名 = 低摩擦替换）

- `frontend/public/zero2x/ui/act2_earth.svg`
- `frontend/public/zero2x/ui/act3_dna.svg`

替换建议（后续设计升级）：

- 同名替换为 `act2_earth.webp` / `act2_earth.webm`
- 同名替换为 `act3_dna.webp` / `act3_dna.webm`

> 约束：不引入外链 CDN；素材必须随仓库或随部署注入。

### 3.3 推荐规格

- WebM（首选）：5–8 秒循环、H.264 或 VP9、最好无音频
- WebP（兜底）：1920×1080（或 1920×720），深色主题
- SVG（当前版本）：体积小、可演示、可随时替换

### 3.4 移动端适配要求

- 海报区 CTA 在窄屏必须纵向堆叠，主按钮全宽，避免误触。
- Workbench 三栏在 `<=980px` 必须自动变为单列，并允许纵向滚动。

---

## 4) TDD / vitest 门禁（必须持续全绿）

### 4.1 Landing 门禁

- `frontend/tests/landingScrollspy.test.js`
  - 断言 scrollspy 存在（IntersectionObserver wiring + activeAct）
  - 断言 `/demo` 入口降噪：Hero 不出现主按钮级 demo

- `frontend/tests/landingHeroVisual.test.js`
  - HeroVisual 仍可动态 import three + 清理
  - Hero 资产目录 README 存在（可替换素材约定不破坏）

### 4.2 Omni-Bar 门禁

- `frontend/tests/omnibarCommands.test.js`
  - help/demo/workbench/act2 命令解析稳定
  - free-form intent 仍能生成 plan 文本（不要求固定措辞，但需包含 Intent）

### 4.3 Act2 门禁

- `frontend/tests/act2InfoCards.test.js`
  - Info Card 存在
  - escape hatches（Landing/Demo）存在
  - 最后一步存在 `/workbench` CTA（新增门禁）

---

## 5) 演示脚本（给 PM/领导演示的鼠标路径）

1. 打开 `/`
2. Omni-Bar 输入一句话意图 → Enter
3. 等黑场 → 自动进入 `/act2?choreo=poyang`
4. 镜头到位 → 读右侧 case 文案
5. 到最后一步 → 点击“在工作台中生成专属 Agent”
6. 黑场 → `/workbench` 自动播放 demo

完成条件：一镜到底，无“占位/工程味”露出。