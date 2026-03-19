🚀 Zero2x 研发工作流跃迁指南：从“手工作坊”到“Agentic 自动化编码”

一、 痛点反思：为什么“网页端 + VS Code Copilot”已经失效？

上下文碎片化 (Context Fragmentation)： 网页端 LLM 无法看到整个工程库。它不知道 EngineRouter.vue 和 v7_copilot.py 之间的契约，导致接口参数频频漏传（如刚才漏掉的 topology）。

缺乏 REPL 闭环 (No Feedback Loop)： LLM 生成了 WGSL，但它自己无法运行验证。必须由您手动保存、刷新浏览器、截图报错、再贴回网页端。这种“跨媒介”交互的延迟极高。

“人肉文件路由”： 复杂的 Feature 往往需要同时修改 3-4 个文件，传统的 Copilot 只能在当前文件做行级补全（Ghost Text），无法执行系统级的重构。

二、 行业最佳实践解析：AI 软件工程师 (SWE-Agent) 的核心哲学

目前以 Claude Code (Anthropic 官方 CLI)、Cursor (AI-first IDE)、Cline (VS Code 插件) 和 OpenHands 为代表的工具，之所以能独立完成复杂的 Issue，是因为它们遵循了以下三个最佳实践：

1. Codebase as Context (代码库即上下文)

AI 不再是被动等待您喂代码，而是主动读取本地文件系统。通过 RAG（检索增强生成）和代码结构分析（AST），AI 在修改 WorkbenchApp 时，会自动检索 EngineRouter 的 defineExpose 看有哪些 API 可用。

2. Action-Oriented (面向动作的执行能力)

AI 具备了工具调用 (Tool Use) 的能力。它们不仅能生成文本，还能执行 read_file, edit_file, run_terminal_command, git_commit。

3. Self-Correction via CLI (通过终端自愈)

AI 在修改完代码后，会自己运行终端命令（如 npm run build 或 python test.py）。如果报错，AI 会直接读取终端的 stderr 错误日志，分析并修改代码，直到编译通过，才将控制权交还给人类。

三、 Zero2x 项目自动化升级策略 (Actionable Roadmap)

为了让 Zero2x 的开发效率提升 10 倍，我们需要进行“武器库换代”和“项目结构改造”。

Phase 1: 武器换代 (Toolchain Upgrade)

全面抛弃“网页端 + 传统 Copilot”，转向 Agentic IDE。

推荐方案 A (低门槛，极速上手)：Cursor IDE

核心功能： Composer (Cmd+I / Cmd+K)。

用法： 您只需在 Composer 中输入：“根据 v7_copilot.py 中新加的 WGSL 逻辑，去更新 WorkbenchApp 和 EngineRouter 以支持动态拓扑。” Cursor 会自动分析这三个文件，直接在 IDE 内生成多文件的 Diff 并在后台应用，您只需点击 Accept All。

推荐方案 B (硬核全自动，适合框架重构)：Claude Code (CLI) 或 Cline 插件

核心功能： 终端驱动的 Autonomous Agent。

用法： 在终端输入 claude "请修复目前 WebGPU 的渲染白屏问题，自行查阅前端错误日志并修改相关 Vue 文件"。Claude Code 会自己在终端里 grep 代码、阅读报错、修改文件、甚至自己运行 Vite 验证。

Phase 2: 上下文工程 (Context Engineering) - 建立机器可读的“宪法”

Agent 工具最怕“幻觉”。为了约束 AI 不去乱改我们好不容易调通的底层逻辑，必须在项目根目录建立 .cursorrules 或 system_prompts.md 文件。

在 Zero2x 项目根目录创建 .cursorrules 文件示例：

# Zero2x Development Rules (For AI Agents)

## 1. 架构边界
- 前端使用 Vue 3 (Composition API, `<script setup>`)。
- 绝不要在 Vue 文件中直接调用 `document.getElementById`，全部使用 `ref`。
- Cesium 引擎层逻辑全部封装在 `EngineRouter.vue` 中，UI 层通过 `defineExpose` 调用，严禁 UI 层直接 import Cesium。

## 2. WebGPU 开发铁律 (Blood Rules)
- WGSL 代码必须 100% 为 ASCII 字符，严禁任何中文注释或 Emoji，否则会导致解析器崩溃。
- Storage Buffer 严禁在同一个 BindGroup 中既可读写又被渲染阶段读取。必须分离 bindings (如 compute 占 binding 0，vertex 占 binding 3)。
- 严禁对 vector 进行 swizzle 赋值 (如 `p.xyz = ...`)，必须重建 vec4。

## 3. 数据与状态
- 演示数据 (Mock) 统一在后端的 `v7_copilot.py` 中生成下发，前端不硬编码任何业务数据。


作用：无论是 Cursor 还是 Claude Code，在执行您的指令前，都会先读取这段“宪法”，彻底杜绝它犯我们刚才经历过的低级语法错误。

Phase 3: 构建“机器可读”的反馈闭环 (The CLI Repl)

为了让 AI 能够“自己排错”，我们需要把原本需要在浏览器里肉眼看报错的流程，部分转移到 CLI (终端) 中。

WGSL 语法校验前置： 不要等浏览器去报 WGSL 的错。可以在项目中引入 naga-cli 或 wgpu-cli。
让 Agent 养成习惯：修改完 WGSL 字符串后，先在终端跑一把验证脚本，确保没有 invalid character 或 type mismatch。

前端静态检查： 确保 npm run type-check 和 eslint 随时待命。Agent 改完 Vue 文件后，让它自己运行命令确认没有引用未定义的变量。

四、 升级后的日常工作流演示 (A Day in the Agentic Workflow)

场景：需要新增一个“全球洋流扩散”的 Demo。

【过去的您 (手工作坊)】

思考 Prompt，去 Gemini 网页端发问。

复制 Gemini 写的 Python 代码到 IDE，寻找要粘贴的行。

复制前端 Vue 代码，发现 CSS 塌陷，手动调 CSS。

去浏览器看效果，发现 WebGPU 报错。

复制报错信息，切回网页端提问... 循环往复 2 小时。

【未来的您 (Agent 架构师)】

打开 Cursor，呼出全屏 Composer (Agent 模式)。

输入指令 (Prompting)： > "@v7_copilot.py @EngineRouter.vue 我们需要新增一个福岛核污染洋流扩散的 Demo。请在后端添加相应的自然语言解析和 Tool calling，然后在前端接收并使用 WebGPU 的 Line-list 拓扑渲染。严格遵守 .cursorrules 中的 WebGPU 安全规范。完成后运行 npm run dev 并确认无编译错误。"

喝杯咖啡 (Agent Working)：

Cursor Agent 开始工作：它自己读取现有文件，修改 Python，修改 Vue，并在后台运行了终端命令。

代码审查 (Review & Approve)：

几分钟后，Agent 给出所有文件的修改 Diff。您只需扫一眼逻辑，点击 Accept All。

浏览器验收： 直接到浏览器看完美的物理洋流效果。

五、 总结与下一步行动

不要把 AI 当作“强化版搜索引擎”（这是网页端的用法）。
要把 AI 当作**“可以直接操作文件系统、可以自己跑终端编译的初级全栈工程师”**。

您的第一步行动建议：
明天上班，下载 Cursor 或在 VS Code 安装 Cline 插件。将我们刚才整理好的 .cursorrules 放进项目根目录。您会发现，接下来的开发将从“体力劳动”瞬间变为“脑力指挥”。