# frontend/CONVENTIONS.md — 前端地方法规

> 全局宪法见 `AI_RULES.md` 和 `CLAUDE.md`

## 技术栈

- Vue 3.4+ (Composition API, `<script setup>`)
- Vite 7 (dev server + build)
- CesiumJS 1.114 (3D globe)
- Three.js 0.164 (deep-space engine)
- GSAP 3.13 (animations)
- Monaco Editor 0.52 (code editor)
- Vitest 4 (testing)

## 架构红线 (Hard Boundaries)

1. **Composition API Only**: 严禁使用 Options API（`data()`, `methods: {}`）— 统一 `<script setup>`
2. **No Canvas UI Buttons**: 严禁在 3D canvas 上叠加 DOM 按钮（参考 `AI_CONTEXT.md`）
3. **Dual-Engine Handover**: Cesium → Three 切换通过 opacity crossfade，由 camera altitude threshold 触发
4. **markRaw for Three.js**: 所有 Three.js 对象包裹 `markRaw()`，避免 Vue reactivity 开销
5. **No Vue Router**: 路由通过 `window.location.pathname` 手动分发（避免路由库体积）

## 目录结构

```
frontend/
├── src/
│   ├── main.js                  # 路由分发 (/, /demo, /workbench, /act2)
│   ├── App.vue                  # Demo 主应用
│   ├── WorkbenchApp.vue         # AI-Native 工作台 (lazy)
│   ├── Act2App.vue              # Act 2 叙事场景 (lazy)
│   ├── Zero2xApp.vue            # Zero2x Landing
│   ├── components/              # 共享组件
│   │   └── CesiumViewer.vue     # CesiumJS 3D 查看器（核心）
│   ├── views/workbench/
│   │   └── engines/             # Three.js / WebGPU 引擎
│   │       ├── ThreeTwin.vue    # 深空引擎（4200+ 行）
│   │       ├── quantumDive.js
│   │       ├── threeDispose.js
│   │       └── threeLayerMapping.js
│   ├── stores/                  # Pinia-like reactive stores
│   │   ├── astroStore.js        # OneAstronomy action bus
│   │   └── researchStore.js     # Scale state (earth/macro/micro)
│   ├── services/api.js          # Axios HTTP 客户端
│   └── utils/astronomy/         # 天文学计算工具
├── tests/                       # Vitest 测试（55 文件, ~260 cases）
├── vite.config.js
└── package.json
```

## 测试模式

### 运行测试
```bash
npm test                    # vitest run（单次）
npm run test:watch          # vitest（watch 模式）
npm run test:coverage       # vitest + 覆盖率报告
```

### 测试文件组织
- 测试文件放在 `frontend/tests/`，命名 `*.test.js`
- 测试组织: `describe` 分组, `it` 单测, `expect` 断言
- 纯逻辑测试（坐标计算、数据处理）直接导入源模块
- 组件 wiring 测试通过函数调用 + 状态断言（无需 DOM）

### TDD 流程
1. 先在 `tests/` 写 failing test
2. 在 `src/` 实现代码
3. `npm test` 确认绿灯

## CesiumJS 约定

- `CesiumViewer.vue` 是唯一直接的 Cesium 入口
- 其他组件通过 `CesiumViewer` emit 的事件通信
- Ion token 通过 Vite env (`VITE_CESIUM_TOKEN`) 注入
- Photorealistic 3D Tiles: asset ID 2275207
- 默认 basemap: Google XYZ (test-only mode)

## Three.js 约定

- World origin = Earth center
- RA/Dec → Cartesian 通过 `coordinateMath.js`
- WebGPU 优先，WebGL 回退
- Shader 代码内联为 template literal string

## 命名规范

- Vue SFC: `PascalCase.vue`
- JS 模块: `camelCase.js`
- 测试文件: `camelCase.test.js`（与源文件名对应）
- CSS class: `kebab-case`
- Vue props: `camelCase`
- Emit events: `kebab-case`

## 禁止行为

- ❌ 使用 Options API（`data()`, `methods: {}`）
- ❌ 在 3D canvas 上叠加 DOM 按钮
- ❌ Three.js 对象不包裹 `markRaw()`
- ❌ 在 `CesiumViewer.vue` 外直接操作 Cesium `Viewer` 实例
- ❌ 硬编码 API URL（使用 `api.js` 的 `baseUrl`）
- ❌ 提交 `node_modules/` 或 `dist/`
