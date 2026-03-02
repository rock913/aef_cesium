# demo_site_v3（静态 Demo 站点）

这是一个**纯静态**的多页面 Demo 站点：没有打包/构建步骤、没有 Node 依赖。

入口页通过读取配置文件 `app.config.json` 动态生成顶部 Tab，并用一个 `<iframe>` 加载 `pages/` 下的各个 Demo 页面。

## 快速开始（本地预览）

> 由于入口页会 `fetch("app.config.json")`，请使用本地 HTTP 服务预览（不要直接用 `file://` 打开）。

在本目录（`docs/demo_site_v3/`）下运行：

```bash
python3 -m http.server 8000
```

然后浏览器访问：

- http://localhost:8000/

## 目录结构

```text
demo_site_v3/
  index.html            # 入口：顶部 Tab + iframe 容器
  app.config.json       # 配置：默认页 + 页面列表
  readme.txt            # 原始简版说明（Netlify zip 更新）
  assets/
    app.css             # 顶部栏/Tab/iframe 布局
    app.js              # 读取配置、生成 Tab、切换 iframe
  pages/
    mantle.html         # Plotly Demo（外部 CDN）
    core.html           # Three.js Demo（外部 CDN）
    surface.html        # ES Modules + importmap（内嵌 data: URL 依赖）
    plate_drift.html    # 板块漂移 Demo（大段内联脚本）
```

## 工作原理（导航与加载）

- `assets/app.js` 会：
  - `fetch("app.config.json", { cache: "no-store" })`
  - 根据 `config.pages` 生成顶部 Tab 按钮
  - 点击 Tab：将 `<iframe id="viewer">` 的 `src` 设置为 `pages/<file>`
  - 根据 `config.default` 打开默认页面

`app.config.json` 结构：

```jsonc
{
  "default": "mantle",
  "pages": [
    { "id": "mantle", "title": "Mantle", "file": "mantle.html" }
  ]
}
```

字段说明：
- `default`：默认打开的页面 id
- `pages[]`：页面列表
  - `id`：页面标识（用于匹配默认页、DOM dataset）
  - `title`：Tab 文本
  - `file`：位于 `pages/` 下的 HTML 文件名

## 页面与技术栈概览

以当前配置（见 `app.config.json`）为准：

- `pages/mantle.html`
  - 主要依赖：Plotly（CDN）
  - 外部脚本：`https://cdn.plot.ly/plotly-2.24.1.min.js`

- `pages/core.html`
  - 主要依赖：Three.js + OrbitControls（CDN）
  - 外部脚本：
    - `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js`
    - `https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js`

- `pages/surface.html`
  - 主要依赖：Three.js + OrbitControls（ES Modules）
  - 特点：使用 `<script type="importmap">`，把模块映射到 `data:` URL（base64 内嵌），页面整体更接近“单文件可搬运 Demo”（但文件体积较大）。

- `pages/plate_drift.html`
  - 特点：文件较大，包含大量内联脚本与 UI 控件（时间轴/播放控制等）。
  - 未发现对外部 CDN 的强依赖（除 HTML 命名空间声明外）。

## 如何新增/修改页面

原始流程（来自 `readme.txt`）：
1. 把新页面放进 `pages/`
2. 修改 `app.config.json` 增加一条
3. 把整个目录压缩成 zip，在 Netlify 更新

示例：添加一个新页面 `pages/new_demo.html`：

```jsonc
{
  "default": "mantle",
  "pages": [
    { "id": "surface", "title": "Upper Crust", "file": "surface.html" },
    { "id": "mantle",  "title": "Mantle",      "file": "mantle.html" },
    { "id": "core",    "title": "Core",        "file": "core.html" },
    { "id": "plate drift", "title": "Plate drift", "file": "plate_drift.html" },
    { "id": "new",     "title": "New Demo",    "file": "new_demo.html" }
  ]
}
```

建议：
- `id` 建议使用不含空格的短字符串（当前配置里也存在带空格的 id，可以工作，但维护起来更容易出错）。
- `file` 尽量使用不含空格的文件名（虽然代码对 URL 做了 `encodeURI`，但保持简单更稳）。
- 页面里如果使用相对路径加载资源（图片/数据文件等），请确保相对路径在部署后仍成立。

## 部署（Netlify / 静态托管）

这是一个“纯静态目录”部署：
- 直接把 `docs/demo_site_v3/` **整个目录**打包成 zip 上传/更新即可
- 无需构建命令

注意事项：
- `index.html` 会请求 `app.config.json`，静态托管需允许同源访问该文件。
- `mantle.html` / `core.html` 依赖外部 CDN，离线环境可能打不开；如需离线部署，建议把依赖改为本地文件或内联（参考 `surface.html` 的 importmap 方式）。
