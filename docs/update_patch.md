Zero2x v7.5 视觉与交互终极修复 Patch

文档定位：针对当前 v7.5 开发中出现的“天球遮挡前景(Z-Sorting Bug)”、“鼠标拖拽失效”、“8K底图黑屏/隐身”等问题的终极代码级修复指南。
目标模块：ThreeTwin.vue (渲染管线与运镜)、CSS (DOM层级)、threeTwinWiring.test.js (TDD 门禁)。

紧急修复一：终结孪生界面“鼠标交互失效”

在引入复杂运镜和全屏 HUD 后，如果 3D 画布无法响应鼠标的拖拽和缩放，几乎 100% 是由以下两个工程冲突引起的，必须立即修复：

1.1 DOM 层级与事件拦截 (CSS Pointer Events)

Vue 的 UI 覆盖层极易拦截底层的鼠标事件。
修复方案：确保 ThreeTwin.vue 画布层具有强行接管鼠标事件的能力，同时剥夺其上方透明罩层的拦截。

/* 在全局样式或对应的 Vue 组件 <style> 中严格申明 */
.three-twin {
    pointer-events: auto !important;
    z-index: 10; /* 确保不被底层的非活动 DOM 压住 */
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

如果代码中出现了 camera.lookAt()，它会与 OrbitControls 争夺相机的控制权，导致鼠标一拖拽画面就死锁弹回。
修复方案：全面排查 ThreeTwin.vue，在所有 gsap.to(camera, ...) 的运镜动画中，绝对禁止直接操作 camera.lookAt，必须转为操作 controls.target。

// ❌ 必须删除的错误写法（会导致鼠标失效）：
gsap.to(camera.position, {
    x: 10, y: 10, z: 10,
    onUpdate: () => camera.lookAt(0, 0, 0) // 致命冲突！
});

// ✅ 正确写法（完美兼容 OrbitControls）：
gsap.to(controls.target, {
    x: 0, y: 0, z: 0,
    duration: 2.0,
    ease: "power2.inOut",
    onUpdate: () => controls.update() // 更新 target 时必须调用 controls.update()
});
gsap.to(camera.position, { x: 10, y: 10, z: 10, duration: 2.0, ease: "power2.inOut" });


核心重构二：Native 天球加载与渲染层级压制 (解决前景被遮挡)

因为 Three.js 根据物体中心点 (0,0,0) 排序透明物体，会导致巨大的天球被误判为“离相机更近”从而遮挡前景。必须用 renderOrder 强行规训！

2.1 修复天球的绝对底层渲染

// 1. 相机视距扩容 (防裁剪)
// 在 initEngine() 中初始化相机时，将 far 扩大到 50000
camera = markRaw(
  new THREE.PerspectiveCamera( 60, width / height, 0.1, 50000 ) // 默认 10000 会切掉天球
);

// 2. 贴图加载与绝对压制逻辑
let skyboxMesh = null; 

function applySkyboxPreset(scene, useTexture = false) {
    if (!useTexture) {
        if (skyboxMesh) skyboxMesh.visible = false;
        return;
    }
    
    if (skyboxMesh) {
        skyboxMesh.visible = true;
        return;
    }

    const textureLoader = new THREE.TextureLoader();
    textureLoader.load('/assets/eso_milkyway_8k.jpg', (texture) => {
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.generateMipmaps = true;
        texture.minFilter = THREE.LinearMipmapLinearFilter;
        
        const sphereGeo = new THREE.SphereGeometry(8000, 64, 64);
        
        const sphereMat = new THREE.MeshBasicMaterial({ 
            map: texture, 
            transparent: true, 
            opacity: 0.8, // 初始透明度
            color: 0x888888, // 适度压暗，保留银河轮廓
            side: THREE.BackSide,
            depthWrite: false,
            depthTest: false
        });
        
        skyboxMesh = new THREE.Mesh(sphereGeo, sphereMat);
        
        skyboxMesh.frustumCulled = false; 
        
        // 🚨 绝对核心修复：强行设置为 -999，打破中心排序 BUG，保证永远第一个渲染！
        skyboxMesh.renderOrder = -999; 
        
        scene.add(skyboxMesh);
    });
}


2.2 前景 Demo 的 Z-Index 提升

为了万无一失，请在 ThreeTwin.vue 中找到您的 Demo 元素（CSST面片、Inpaint面片、Macro点云），给它们加上正数的 renderOrder：

// 保证宏观点云在天球之上
if (macroPoints) macroPoints.renderOrder = 0; 

// 保证 CSST 飞出面片和 Inpaint 面片具有最高渲染层级
if (csstGroup) csstGroup.renderOrder = 99;
if (_inpaintMesh) _inpaintMesh.renderOrder = 99;


核心重构三：场景霸权 (Scene Authority) 与动态呼吸

即使渲染层级对了，如果背景天球过亮，由于 AdditiveBlending 的特性，前景高光依旧会发灰、发白。必须在触发具体 Demo 时执行“背景退让”。

3.1 触发任务时的背景压暗 (Dimming)

在 ThreeTwin.vue 的各个执行函数中补齐 GSAP 动画：

// 1. 当触发 CSST 分解 (Demo 1) 或 Modal Inpaint (Demo 3) 时：
function _executeCSSTDecompose() {
    // ... 前景面片展开动画 ...
    
    // 🚨 场景霸权：压暗背景，突出前方全息图层
    if (skyboxMesh && skyboxMesh.material) {
        gsap.to(skyboxMesh.material, { opacity: 0.15, duration: 1.5 });
    }
    // 点云也退让
    gsap.to(macroPoints.material.uniforms.u_opacity, { value: 0.1, duration: 1.5 });
}

// 2. 当触发 Redshift Burst (Demo 2) 时：
async function _executeRedshiftBurst(payload) {
    // ... 粒子拉伸与相机 FOV 畸变动画 ...
    
    // 🚨 场景霸权：宇宙网本身会发强光，天球底图必须深呼吸退让
    if (skyboxMesh && skyboxMesh.material) {
        gsap.to(skyboxMesh.material, { opacity: 0.1, duration: 2.0 });
    }
}

// 3. 当清理任务回归宏观态时 (STOP 动作)：
function _stopCsstDecomposition() {
    // ... 清理前景 ...
    
    // 🚨 恢复天球默认亮度
    if (skyboxMesh && skyboxMesh.material) {
        gsap.to(skyboxMesh.material, { opacity: 0.8, duration: 1.5 });
    }
    gsap.to(macroPoints.material.uniforms.u_opacity, { value: 0.8, duration: 1.5 });
}


核心重构四：TDD 门禁断言 (Wiring Gate Assertion)

为了防止未来代码劣化、材质属性被误改，或被错误引入外部 DOM，必须在测试套件（如 threeTwinWiring.test.js）中加入严格的断言。

// 伪代码：在测试中加入针对 Texture Preset 的断言
test('Skybox Preset should strictly use Single WebGPU Pipeline and correct Render Order', () => {
    // 1. 触发 action 切换到 Texture 档
    // astroStore.dispatchAgentAction({ type: 'ENABLE_TEXTURE_SKYBOX' })
    
    // 2. 断言 Three.js 场景中包含目标天球网格，且 RenderOrder 绝对垫底
    const skybox = scene.children.find(c => c.isMesh && c.geometry.type === 'SphereGeometry' && c.renderOrder === -999);
    expect(skybox).toBeDefined();
    
    // 3. 核心规训断言：必须关闭深度读写、内部渲染、防剔除
    expect(skybox.material.depthWrite).toBe(false);
    expect(skybox.material.depthTest).toBe(false);
    expect(skybox.material.side).toBe(THREE.BackSide);
    expect(skybox.frustumCulled).toBe(false);
    
    // 4. 单管线防线断言：文档中绝对不存在 aladin 等非 WebGPU 画布的节点
    expect(document.querySelector('#aladin-lite-container')).toBeNull();
});


验收核对单 (Acceptance Checklist)

[ ]  图层覆盖修正：加载 Texture 预设后，银河全景图绝对服帖在最深处背景，CSST 面片和红移点云清晰地悬浮其上方，无任何交叠和发灰遮挡现象。

[ ]  呼吸感验证：触发 Demo 1 或 Demo 2 时，银河背景能丝滑地变暗至 15% 左右，将视觉高光完美让给当前的科学任务。

[ ]  交互顺畅验证：无论在加载中还是运镜后，使用鼠标左键拖拽、右键平移、滚轮缩放均丝滑顺畅，无死锁跳跃。

[ ]  工程防腐验证：运行 npm test，Skybox 相关的 renderOrder === -999 及 BackSide 断言必须全绿。