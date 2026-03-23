Zero2x v7.5 视觉重构与连续叙事实施指南 (Phase 2.5 & Astro-GIS)

目标：在已跑通的 ThreeTwin.vue 工程骨架上，彻底解决“视觉散点感”、“深度穿插”和“叙事割裂”问题。将 CSST、宇宙学红移、GOTTA 瞬变源和模态互生四大任务串联为一个 “一镜到底的科学探索流”。同时，全面启动并落地涵盖底图与星表的 Astro-GIS 三期架构。

一、 顶层叙事逻辑重构：OneAstronomy 的 4 幕剧

不要让用户漫无目的地点击 Preset。在演示时，遵循以下连续的剧本逻辑，每一次点击都是在上一次状态的延展：

【序幕】宇宙底座加载：50,000 个真实的 SDSS 星系平铺在 2D 天球上。

【第一幕】CSST 数据降临 (Demo 1 已完成)：镜头飞近某一个星系，OneAstronomy 将其“解剖”为核球、盘、棒（您已实现）。（展现大模型对复杂形体的特征提取能力）

【第二幕】精密宇宙学与 Jean-Paul Kneib 协作 (Demo 2 升级)：关闭 CSST 特写，镜头拉远。模型预测 50,000 个星系的红移。全天球星系沿着地球径向（Radial）向外爆发，形成三维斯隆长城。（展现大模型对大尺度结构的推演算力）

【第三幕】GOTTA 时域网络预警 (新增 Demo 3)：在宏伟的 3D 宇宙网中，极远处突然爆发出超新星（闪烁）。相机启动“量子下潜”弧线运镜，极速跃迁至瞬变源坐标。（展现时域天文的秒级响应）

【第四幕】暗物质/射线辐射反推 (Demo 4 升级)：到达瞬变源遗迹（蟹状星云）后，利用 Inpaint 雷达扫描，将可见光褪变为 X 射线。（展现模型跨模态物理一致性生成能力）

二、 核心视觉 Bug 修复：从“散点糖果”到“丝状宇宙网”

当前问题：红移爆裂后，星系看起来像独立的彩色小球，没有融合出宇宙大尺度结构（Cosmic Web）的密度感和丝状网络感。
根本解法：废弃 InstancedMesh(SphereGeometry)，全面拥抱 THREE.Points（点云），利用着色器生成柔和光晕，靠 Additive Blending 自动融合出星系团的亮度。

重构 ThreeTwin.vue 中的宏观渲染引擎：

// 1. 废弃 InstancedMesh，改用 BufferGeometry 构建点云
const geometry = new THREE.BufferGeometry();
const positions = new Float32Array(count * 3);
const redshifts = new Float32Array(count);

for (let i = 0; i < count; i++) {
    const ra = rawData[i*3];
    const dec = rawData[i*3 + 1];
    redshifts[i] = rawData[i*3 + 2];
    
    // 初始投射到一个极小的基准面上，等待红移爆裂拉伸
    const pos = coordinateMath.raDecToCartesian(ra, dec, 100);
    positions[i*3] = pos.x; positions[i*3+1] = pos.y; positions[i*3+2] = pos.z;
}

geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
geometry.setAttribute('aRedshift', new THREE.BufferAttribute(redshifts, 1));

// 2. 点云专属 ShaderMaterial (The Magic)
const material = new THREE.ShaderMaterial({
    uniforms: {
        u_redshift_scale: { value: 0.0 },
        u_max_depth: { value: 52.0 },
        u_opacity: { value: 0.8 },
        u_size: { value: 15.0 } // 控制光晕基础大小
    },
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    vertexShader: `
        attribute float aRedshift;
        uniform float u_redshift_scale;
        uniform float u_max_depth;
        uniform float u_size;
        varying float vRedshift;
        
        void main() {
            vRedshift = aRedshift;
            vec3 dir = normalize(position);
            
            // 径向红移膨胀
            float currentDist = length(position) + (aRedshift * u_max_depth * u_redshift_scale);
            vec3 finalPos = dir * currentDist;
            
            vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);
            gl_Position = projectionMatrix * mvPosition;
            
            // 近大远小：根据距离衰减粒子大小
            gl_PointSize = u_size * (250.0 / -mvPosition.z); 
            // 确保光晕最小也有 1px，避免消失
            gl_PointSize = max(1.0, gl_PointSize); 
        }
    `,
    fragmentShader: `
        varying float vRedshift;
        uniform float u_redshift_scale;
        uniform float u_opacity;
        
        void main() {
            // 在 GPU 内部画一个柔和的发光圆（Soft Particle）
            // 抛弃贴图，直接用数学生成高斯模糊边缘
            vec2 cxy = 2.0 * gl_PointCoord - 1.0;
            float r = dot(cxy, cxy);
            if (r > 1.0) discard; // 切掉正方形的四个角
            
            // 核心发光算法：中心极亮，边缘柔和衰减
            float alpha = exp(-r * 3.0); 
            
            float zBurst = clamp(vRedshift * u_redshift_scale, 0.0, 1.0);
            vec3 baseColor = vec3(0.05, 0.2, 0.5); // 深邃暗蓝底色
            vec3 burstColor = vec3(0.9, 0.1, 0.5); // 粉紫高光
            
            vec3 finalColor = mix(baseColor, burstColor, zBurst);
            
            // 远处的点变暗，增加景深层次
            float depthFade = 1.0 - (zBurst * 0.3);
            
            gl_FragColor = vec4(finalColor * alpha, u_opacity * depthFade);
        }
    `
});

const macroPoints = new THREE.Points(geometry, material);
scene.add(macroPoints);


三、 Astro-GIS 架构演进与全阶段落地策略

Astro-GIS 是 Zero2x 迈向专业级虚拟天文台（Virtual Observatory）的核心底座，其对标地学 GIS 的对应关系为：HiPS (对应 TMS/XYZ 影像) + TAP/SIMBAD (对应 GeoJSON/WFS 矢量要素)。我们将分三个 Phase 逐步落地。

Phase 1: 天球坐标系与图层状态树抽象 (Foundation)

此阶段旨在剥离硬编码，在 astroStore.js 中抽象出一套标准的图层控制流，接管所有 3D 渲染资产的显隐与透明度。

// 在 astroStore.js 中新增
export const ASTRO_LAYERS = Object.freeze({
  HIPS_BASE: 'layer:hips_base',       // 预留给 Aladin Lite 底图
  MACRO_SDSS: 'layer:macro_sdss',     // 3D 点云宇宙网
  DEMO_CSST: 'layer:demo_csst',       // Demo 1 的分解面片
  DEMO_GOTTA: 'layer:demo_gotta',     // Demo 3 的闪烁超新星
  DEMO_INPAINT: 'layer:demo_inpaint', // Demo 4 的星云面片
  CATALOG_SIMBAD: 'layer:catalog_simbad' // 预留给星表要素
});

const state = reactive({
  layerState: {
    [ASTRO_LAYERS.HIPS_BASE]: { visible: false, opacity: 1.0, currentSurvey: 'P/DSS2/color' },
    [ASTRO_LAYERS.MACRO_SDSS]: { visible: true, opacity: 0.8 },
    // ... 其他图层状态 ...
  }
});


实施动作：利用 Vue 的 watch，在 ThreeTwin.vue 中将 astroStore.layerState 实时映射为对应 Three.js 对象的 .visible 和 .material.uniforms.u_opacity.value。

Phase 2: HiPS 影像底图接入与视场同步 (The Deep Sky Background)

利用现成的 Aladin Lite v3 作为深空背景底图（Canvas Z-index: 0），Three.js 作为前端 3D 业务图层（Z-index: 1，背景透明），实现两者的完美叠加。

// 伪代码：在 ThreeTwin.vue 或专门的 AladinWrapper.vue 中
let aladin;
onMounted(() => {
    // 1. 初始化 Aladin Lite (挂载在底层 div)
    aladin = A.aladin('#aladin-lite-container', { 
        survey: 'P/DSS2/color', // 默认光学巡天
        fov: 60, target: '0 0'
    });

    // 2. 核心黑魔法：Three.js 相机向 Aladin 的视场 (FOV) 与赤道坐标 (RA/Dec) 同步
    controls.addEventListener('change', () => {
        // 从 Three.js camera quaternion 提取当前的 RA 和 Dec
        const targetDir = new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
        const { ra, dec } = coordinateMath.cartesianToRaDec(targetDir);
        
        // 提取 FOV 并做适度换算
        const currentFov = camera.fov;
        
        // 驱动底图跟随
        aladin.gotoRaDec(ra, dec);
        aladin.setFov(currentFov);
    });
});


实施动作：完成同步后，Zero2x 将瞬间拥有可见光、微波、红外、X 射线等数百种全天区真实背景图谱切换能力。

Phase 3: Catalog 要素层与动态请求 (The Vector Features)

当用户拉近视角时，动态加载当前视口内的星表数据（如 SIMBAD 或 VizieR）。

// 伪代码：防抖视口监听与数据请求
import debounce from 'lodash/debounce';

const fetchCatalogData = debounce(async (ra, dec, fov) => {
    // 换算为请求半径 (radius in degrees)
    const radius = fov / 2;
    // 请求 CDS TAP 接口获取视场内星体
    const res = await fetch(`https://simbad.u-strasbg.fr/simbad/sim-tap/sync?request=doQuery&lang=ADQL&query=SELECT ra, dec, main_id, otype FROM basic WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', ${ra}, ${dec}, ${radius}))=1`);
    const data = await parseVOTable(res);
    
    // 将数据渲染为 Three.js 的 Sprite 或 文本 Label
    renderCatalogMarkers(data);
}, 500); // 停止拖动 500ms 后触发

controls.addEventListener('end', () => {
    const { ra, dec } = getCurrentCameraRaDec();
    fetchCatalogData(ra, dec, camera.fov);
});


四、 Astro-GIS 对四幕科学叙事的全面赋能

当完整的 Astro-GIS 架构落地后，现有的 4 幕科学叙事将被彻底激活，从“视觉特效”升维为“具备真实天文学验证闭环的专业流程”：

第一幕 (CSST分解) 的飞跃：
以前，CSST 目标星系背后是一片虚空。有了 Phase 2 (HiPS) 之后，相机飞向目标坐标时，Aladin 背景会自动同步放大，显露出该星系在真实宇宙中（如 DSS2 光学影像）的真实面貌。此时再浮现出我们的 3D 分解面片，“模型生成结果”与“真实背景影像”的完美叠合，让分解结果变得无可辩驳。

第二幕 (Redshift爆裂) 的降维打击：
在爆裂前，50,000 个星系点云（Phase 1）可以完美对齐在 HiPS (Phase 2) 的 2D 真实全天影像上。当启动红移爆裂时，点云从 2D 的 HiPS 底图中**“挣脱”并向前飞出**，化为立体的 3D Cosmic Web，这是一种极其震撼的“从 2D 观测到 3D 洞察”的降维展现。

第三幕 (GOTTA瞬变源) 的真实感：
借助 Phase 3 (Catalog) 能力，当出现 GOTTA 报警时，Copilot 不仅能提供假想数据，还能实时调用 SIMBAD 接口，查询报警坐标周边已知的星系和天体，生成一张实时的“目标天区档案卡（Contextual HUD）”，极大增强时域发现的真实业务感。

第四幕 (Inpaint模态互生) 的交叉验证：
当前我们是在用 AI 预测 X 射线图谱。在 Astro-GIS 的支持下，我们可以增加一步交叉验证的叙事：先让 Aladin 切换到真实的 Chandra X-ray 巡天底图（Phase 2），然后叠加上我们大模型生成的 Inpaint 面片，向观众展示两者形态的高度一致性！这是对“OneAstronomy 物理一致性”最强大的背书。

实施建议：
建议当前冲刺期（1-2周内）优先打满 Phase 1 图层控制树 并落地 THREE.Points 视觉重构（即第二部分的内容）。待 Demo 的 4 幕叙事跑通顺畅后，在下一个里程碑正式引入 Aladin Lite (Phase 2)，完成真正的虚拟天文台进化。