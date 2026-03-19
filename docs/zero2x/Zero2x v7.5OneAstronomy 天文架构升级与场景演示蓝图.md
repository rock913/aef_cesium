Zero2x 021 v7.5：OneAstronomy 天文架构升级与场景演示蓝图
文档代号：Phase 2.0 - "Deep Space & WebGPU"
核心目标：结合 AION-1 天文多模态大模型与前端 WebGPU 计算着色器，将科研工作台的算力与渲染边界从“地球表面”扩展至“百亿光年深空”。在 Phase 2.0 的首个版本中，我们将以**“高视觉张力的 Demo 演示”**为主导，确保在各类常规硬件上均能流畅展现宇宙演化。
一、 技术架构底座大升级 (WebGPU + AION-1)
为了支撑极端的宇宙尺度，系统前端底层必须进行一次非破坏性替换。
1.1 渲染管线升级：从 WebGL 到 WebGPU
弃用 WebGL：在 ThreeTwin.vue 中，将传统的 WebGLRenderer 平滑迁移至 Three.js 最新的 WebGPURenderer。
Compute Shaders (计算着色器)：天体的引力相互作用将脱离 JavaScript 主线程，作为纯粹的并行计算任务驻留在用户本地显卡（GPU）显存中执行。
1.2 WebGPU 硬件兼容与降级指南 (Hardware Compatibility)
为了确保演示系统能在低端笔记本（如 Intel UHD 集成显卡、普通 M1 芯片）上依然跑出 60FPS 的震撼效果，系统需采取以下策略：
查询硬件上限：通过 navigator.gpu.requestAdapter() 获取当前设备的 maxComputeInvocationsPerWorkgroup（最大工作组调用量）。
数值动态缩放：在演示剧本中，不盲目追求千万级粒子。将星系碰撞的演示数值严格控制在 10 万 ~ 50 万质点。这个数量级足以在视觉上形成极其震撼的流体/旋臂效果，且能保证在 95% 的轻薄本上满帧运行。
Fallback 机制：若用户浏览器版本过低不支持 WebGPU，系统将自动回退至 WebGL2 InstancedMesh 的 CPU 预计算动画播放模式。
1.3 AI 认知底座：接入 AION-1 天文基础模型
向 Copilot 注册全新的 天文工具簇 (Astronomical Tool Calling)：
predict_redshift(spectrum_data): 红移预测
classify_galaxy(image_and_spectrum): 星系分类
search_similar_phenomena(target_latent_vector): 相似性搜索
generate_spectrum_from_image(image_data): 图谱互生
二、 天文孪生界面呈现范式 (对比 CesiumJS 地学底座)
在地学模式中，CesiumJS 提供了一个明确的、基于 WGS84 坐标系的巨大椭球体（地球），用户拥有明确的“地面”、“天空”和“重力方向”心智。但在 OneAstronomy 天文模式中，宇宙是无标度（Scale-invariant）且无绝对参照系的。
为了让用户在深空中不至于“迷失方向”，天文孪生底座必须引入以下视觉锚点：
赤道坐标系/银道坐标系网格 (Galactic Grid)：在完全虚空的背景中，必须绘制一张极其微弱的、带有发光刻度的球形网格线（RA/Dec 经纬网），作为宇宙空间的“地板”与参照系。
对数级空间漫游仪 (Logarithmic Camera)：传统的鼠标滚轮在宇宙中是失效的（滚动一下可能前进了 1 光年，也可能前进了 1 亿光年）。必须重写 Camera Controls，基于目标物体的距离自动动态调整鼠标滚轮的步长系数（Distance-based LOD zoom）。
空间光年标尺 (Cosmic Scale Bar)：HUD 左下角动态显示当前视窗的横跨物理距离（如：“当前视野宽：2.5 百万光年”），极大增强用户的尺度震撼感。
三、 核心 Demo 场景大盘与可用数据源 (OneAstronomy)
结合 Copilot 交互架构、公开天文数据源与 WebGPU，规划以下 4 个场景。所有场景的初版均以“预置数据流 + 实时渲染”的 Demo 形式呈现。
Demo 1: 深空巡天与多模态红移测距 (展现图谱解析力)
确切数据源：SDSS DR18 (斯隆数字巡天)。后端预先下载一片天区的星表 CSV（包含 RA, Dec, Z红移值），并在服务器端将光谱图缓存。
数据兼容指南：前端抛弃复杂的数据库查询，直接通过 FastAPI 请求预处理好的 JSON Array。
Copilot 指令："提取当前视场内所有不明发光体的光谱数据，使用 AION 模型进行星系分类与红移预测，并在 3D 空间中按距离重构它们的立体位置。"
可视化震撼点：原本在平面图像上看似挤在一起的 2 万个光点（基于 WebGPU 点云材质），在指令下达后，依据预测的红移值（），在 Z 轴深度上瞬间被平滑“拉伸”开来，重构出类似“斯隆长城”的宇宙网状立体结构。
Demo 2: 强引力透镜的“大海捞针” (展现零样本相似性搜索)
确切数据源：JWST CEERS (韦伯望远镜早期发布数据)。后端预存 100 张典型的星系图像，其中包含 3-5 张引力透镜环。
数据兼容指南：图像通过 AION-1 转化为 512 维隐空间向量，预存入后端的 Milvus/FAISS 向量数据库中备查。
Copilot 指令："锁定画面中心的‘爱因斯坦环’（引力透镜）图像，在巡天数据库中进行高维潜在空间相似性搜索，找出宇宙中相似的引力透镜事件。"
可视化震撼点：点击图像后，系统触发“虫洞跃迁”动画（基于 GSAP 控制的 FOV 极速拉伸）。镜头穿梭后，分裂出几个悬浮的玻璃拟态 UI 视窗，展示搜索出的形态极其相似的引力透镜星系。
Demo 3: 暗物质寻踪与图谱互生视界 (展现模态生成)
确切数据源：Chandra X-ray Observatory (钱德拉X射线天文台) + Hubble (哈勃) 的蟹状星云 (Crab Nebula) 多波段公开对比图。
数据兼容指南：前端无需处理庞大的 FITS 文件。后端预先将光学图与 X 射线图处理为 1024x1024 的 PNG 透明贴图层（Texture）。
Copilot 指令："该区域光学图像被尘埃遮挡。请利用图谱互生技术，从现有光学图像反推生成其不可见的 X 射线光谱，揭示内部中子星。"
可视化震撼点：无界画布在视觉上执行“X光扫描雷达”特效。彩色绚丽的星云光学外壳的 Shader 透明度渐变褪去，核心区域基于 AI 生成的不可见光贴图瞬间显现，爆发出刺眼的紫/白色高频射线粒子渲染。
Demo 4: 银河系与仙女座碰撞演化 (展现 WebGPU 极致算力，适合低端本)
确切数据源：Gaia DR3 (盖亚星表) 的银河系运动学降采样数据 + N-Body 模拟初始态参数。
数据兼容指南：后端将恒星的初始位置  和速度  编码为两张 Float32 格式的二进制纹理贴图（DataTexture），前端 WebGPU 直接读取纹理进行并行运算，极大降低 CPU 瓶颈。
Copilot 指令："导入银河系与仙女座星系的 20 万质点质量分布模型，利用本地 WebGPU 算力，推演未来 40 亿年的引力碰撞过程。"
可视化震撼点（优化后）：前端 Monaco Editor 中生成简短的 WGSL 牛顿引力计算着色器。执行后，依靠普通轻薄本的本地显卡算力，视窗中 20 万颗（而非百万级，确保 60FPS）恒星粒子开始受引力拉扯，交织、撕裂、融合，最终形成巨大椭圆星系。展现“代码即算力”最高维度的终极展示。
四、 左侧统一资产面板 (Unified Artifacts) 在天文态的映射
当切换至 OneAstronomy 态时，左侧的 Tab 栏将自动切换其语境：
🗂️ LAYER & DATA：不再是 GEE 瓦片，变为“多波段巡天图层”。用户可调整光学、X射线、红外层之间的叠加模式（Additive Blending）。
💻 CODE & SCRIPT：增加对 WGSL (WebGPU Shading Language) 的高亮支持，用于直接展示和热重载天体物理演化着色器。
📊 CHARTS & STATS：展示由 AION 模型生成的 2D Echarts 图表，如光谱曲线图（Spectrum Plot）、赫罗图（H-R Diagram）或红移分布直方图。
