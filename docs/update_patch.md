Zero2x v7.5 视觉与交互终极修复 Patch

文档定位：针对当前 v7.5 开发中出现的“鼠标拖拽失效”、“Native底图脏乱/穿插”以及“宇宙网缺乏电影级纵深感”问题的终极代码级修复指南。
目标文件：主要修改 src/views/workbench/engines/ThreeTwin.vue 及相关 CSS，并建立严格的 TDD 门禁。

紧急修复一：终结孪生界面“鼠标交互失效”

在引入全屏 Native 底图和复杂运镜后，如果 3D 画布无法响应鼠标的拖拽和缩放，几乎 100% 是由以下两个工程冲突引起的，必须立即修复：

1.1 DOM 层级与事件拦截 (CSS Pointer Events)

Vue 的 UI 覆盖层（如 HUD 容器）极易拦截底层的鼠标事件。
修复方案：确保 ThreeTwin.vue 画布层具有强行接管鼠标事件的能力，同时剥夺其上方透明罩层的事件。

/* 在全局样式或对应的 Vue 组件 <style> 中严格申明 */
.three-twin {
    pointer-events: auto !important;
    z-index: 10; /* 确保不被底层 DOM 压住 */
}

.hud-layer {
    /* 整个 HUD 的透明空白区绝对透传点击至 Three.js */
    pointer-events: none !important;
    z-index: 20; 
}

.hud-layer > * {
    /* HUD 内具体的按钮、面板自己声明接收点击 */
    pointer-events: auto;
}


1.2 消除 OrbitControls 与 GSAP 的运镜死锁 (致命冲突)

如果代码中出现了 camera.lookAt()，它会与 OrbitControls 争夺相机的控制权，导致鼠标一拖拽画面就锁死。
修复方案：全面排查 ThreeTwin.vue，在所有 gsap.to(camera, ...) 的运镜动画中，绝对禁止直接操作 camera.lookAt，必须转为操作 controls.target。

// ❌ 必须删除的错误写法（会导致鼠标失效）：
gsap.to(camera.position, {
    x: 100, y: 50, z: 100,
    onUpdate: () => camera.lookAt(0, 0, 0) // 致命冲突！
});

// ✅ 正确写法（完美兼容 OrbitControls）：
gsap.to(controls.target, {
    x: 0, y: 0, z: 0,
    duration: 2.0,
    ease: "power2.inOut",
    onUpdate: () => controls.update() // 更新 target 时必须调用 controls.update()
});
gsap.to(camera.position, { x: 100, y: 50, z: 100, duration: 2.0, ease: "power2.inOut" });


核心重构二：Native 影像底图 (Skybox) 的工程化与两档切换策略

坚决抵制 DOM/Canvas underlay（如 Aladin Lite）。我们采用 “两档切换 (Two-Gear Strategy)”：默认态为 Procedural+Black，按需通过 Preset 开启 Native 8K Equirectangular Texture。

2.1 物理隔离与底图压暗特调

在 ThreeTwin.vue 中封装 Skybox 的按需加载机制，并对其施加渲染管线级别的规训：

let skyboxMesh = null; // 提升为模块级变量，方便后续动画控制透明度

function loadNativeSkyboxTexture(scene) {
    if (skyboxMesh) {
        skyboxMesh.visible = true;
        return;
    }

    const textureLoader = new THREE.TextureLoader();
    textureLoader.load('/assets/eso_milkyway_8k.jpg', (texture) => {
        texture.mapping = THREE.EquirectangularReflectionMapping;
        texture.colorSpace = THREE.SRGBColorSpace;
        
        // 1. 使用极其巨大的几何体，内部面反转，包裹整个世界
        const sphereGeo = new THREE.SphereGeometry(8000, 64, 64);
        sphereGeo.scale(-1, 1, 1); 
        
        const sphereMat = new THREE.MeshBasicMaterial({ 
            map: texture, 
            transparent: true, 
            opacity: 0.85,
            
            // 🚨 视觉特调 1：底图压暗 (Tinting)！
            // 防止底图本身太亮而抢走 3D 点云的光芒。强行将其压成幽暗深邃的灰蓝色。
            color: new THREE.Color(0.15, 0.18, 0.25), 
            
            // 🚨 视觉特调 2：深度隔离！绝对禁止与星系点云发生物理穿插
            depthWrite: false,
            depthTest: false
        });
        
        skyboxMesh = new THREE.Mesh(sphereGeo, sphereMat);
        
        // 🚨 视觉特调 3：强制渲染管线垫底
        skyboxMesh.renderOrder = -99; 
        
        scene.add(skyboxMesh);
    });
}


2.2 TDD 门禁断言 (Wiring Gate Assertion)

为了防止未来代码劣化或被错误引入外部 DOM，必须在测试套件（如 threeTwinWiring.test.js）中加入严格的断言：

// 伪代码：在 Wiring Gate 中断言 Native Skybox 的合法性
test('Skybox Preset should strictly use Single WebGPU Pipeline without DOM underlays', () => {
    // 1. 断言触发 preset: 'texture' 时，Three.js 场景中包含目标网格
    expect(scene.children.some(c => c.isMesh && c.geometry.type === 'SphereGeometry')).toBe(true);
    
    const skybox = scene.children.find(c => c.geometry.type === 'SphereGeometry');
    
    // 2. 核心规训断言：必须关闭深度读写与提前渲染
    expect(skybox.material.depthWrite).toBe(false);
    expect(skybox.material.depthTest).toBe(false);
    expect(skybox.renderOrder).toBeLessThan(-10);
    
    // 3. 断言贴图映射方式绝对正确
    expect(skybox.material.map.mapping).toBe(THREE.EquirectangularReflectionMapping);
    
    // 4. 防线断言：文档中绝对不存在 aladin 等非 WebGPU 画布的 ID
    expect(document.querySelector('#aladin-lite-container')).toBeNull();
});


核心重构三：电影级 3D 宇宙网 (Cosmic Web) Shader 与运镜

为了将 50,000 个平平无奇的数据点“烧”出耀眼的丝状网络结构，并展现“曲速引擎”般的沉浸感，请直接替换当前的宏观着色器与运镜代码。

3.1 终极宇宙网 Shader (胖光晕 + 空洞夸张 + 热力学调色)

直接覆盖 macroPoints 的 THREE.ShaderMaterial：

const material = new THREE.ShaderMaterial({
    uniforms: {
        u_redshift_scale: { value: 0.0 },
        u_max_depth: { value: 52.0 },
        u_opacity: { value: 0.25 }, // 降低基础透明度，靠 Additive 重叠发光
        u_size: { value: 80.0 }     // 巨大的初始光晕尺寸
    },
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false, // 避免点与点之间互相遮挡
    vertexShader: `
        attribute float aRedshift;
        uniform float u_redshift_scale;
        uniform float u_max_depth;
        uniform float u_size;
        
        varying float vRedshift;
        varying vec3 vWorldPos; 
        
        void main() {
            vRedshift = aRedshift;
            vec3 dir = normalize(position);
            
            // 真实的径向红移膨胀
            float currentDist = length(position) + (aRedshift * u_max_depth * u_redshift_scale);
            vec3 finalPos = dir * currentDist;
            
            vWorldPos = finalPos; // 传给片元用于空洞噪声计算
            
            vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);
            gl_Position = projectionMatrix * mvPosition;
            
            // 近大远小的透视粒子，且允许极度放大 (产生宏大的重叠)
            gl_PointSize = u_size * (300.0 / length(mvPosition.xyz)); 
            gl_PointSize = clamp(gl_PointSize, 1.0, 250.0); 
        }
    `,
    fragmentShader: `
        varying float vRedshift;
        varying vec3 vWorldPos;
        uniform float u_redshift_scale;
        uniform float u_opacity;
        
        void main() {
            vec2 cxy = 2.0 * gl_PointCoord - 1.0;
            float r = dot(cxy, cxy);
            if (r > 1.0) discard;
            
            // 胖光晕平滑长尾衰减 (极利于产生网络感重叠)
            float alpha = pow(1.0 - sqrt(r), 2.5); 
            
            float zBurst = clamp(vRedshift * u_redshift_scale, 0.0, 1.0);
            
            // 空洞夸张黑魔法：用空间坐标低频噪声强行压暗某些区域，逼出亮丝
            float noise = sin(vWorldPos.x * 0.015) * sin(vWorldPos.y * 0.015) * sin(vWorldPos.z * 0.015);
            float densityMask = smoothstep(-0.2, 0.6, noise); 
            densityMask = max(0.1, densityMask); // 保持微弱底光
            
            // HDR 热力学调色盘：青蓝 -> 紫红 -> 烈焰金
            vec3 colorNear = vec3(0.01, 0.15, 0.6);   
            vec3 colorMid = vec3(0.8, 0.05, 0.4);     
            vec3 colorFar = vec3(1.0, 0.6, 0.05);     
            
            vec3 finalColor = mix(colorNear, colorMid, smoothstep(0.0, 0.4, zBurst));
            finalColor = mix(finalColor, colorFar, smoothstep(0.4, 1.0, zBurst));
            
            // 爆裂核心额外增亮，且被密度遮罩约束
            finalColor += (colorFar * zBurst * 1.5 * densityMask);
            
            // 距离深度的物理衰减
            float depthFade = 1.0 - (zBurst * 0.3);
            
            gl_FragColor = vec4(finalColor * alpha, u_opacity * densityMask * depthFade);
        }
    `
});


3.2 Demo 2 运镜强化：相机冲刺与希区柯克变焦

替换原有的 _executeRedshiftBurst 方法，实现“动态退让底图”、“广角拉伸”和“冲入星际”的三重震撼。

async function _executeRedshiftBurst(payload) {
    // 0. 场景霸权：压暗 Native 天球底图，将视觉高光完全让给即将爆裂的 3D 宇宙网
    if (skyboxMesh && skyboxMesh.material) {
        gsap.to(skyboxMesh.material, { opacity: 0.1, duration: 2.0 });
    }

    // 1. 触发红移数据拉伸
    gsap.to(macroMesh.material.uniforms.u_redshift_scale, {
        value: 1.0, duration: 4.5, ease: "power2.inOut"
    });
    
    // 2. 动态拉伸 FOV，制造“曲速引擎/星门失重”的广角畸变错觉
    gsap.to(camera, {
        fov: 95, 
        duration: 4.5, 
        ease: "power2.inOut",
        onUpdate: () => camera.updateProjectionMatrix()
    });
    
    // 3. 相机冲刺突进：不要停留在外围看，强行推入宇宙网深处！
    // 假设初始位置在 Z=250，向内冲刺 80 个单位
    gsap.to(camera.position, {
        z: camera.position.z - 80, 
        duration: 4.5,
        ease: "power2.inOut"
    });
    
    // 4. Bloom 特调：压紧阈值，只让密集的星系团发生爆闪，空洞区保持黑暗
    if (bloomPass) {
        gsap.to(bloomPass, { threshold: 0.35, strength: 2.5, duration: 2.0 });
    }
}


验收检查清单 (Checklist)：

[ ] 触发 Preset: texture 时，控制台不报任何跨域/ DOM 错误，且 TDD 门禁测试全绿。

[ ] 鼠标在任何时刻拖拽 3D 画布，系统响应如丝般顺滑（无 camera.lookAt 死锁）。

[ ] 刚加载时，深空背景贴图不会亮瞎眼，而是呈现出被 Tinting 压过的深邃神秘灰蓝色。

[ ] 执行 Demo 2（红移爆裂）时，背景底图自动变暗退让，相机会一边拉长广角，一边向前冲刺，带领视线一头扎进耀眼的 3D 宇宙脉络中！