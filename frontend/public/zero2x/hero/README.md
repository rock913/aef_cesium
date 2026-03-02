# Zero2x Hero Assets (Issue #14)

这个目录用于 **第一幕主视觉** 可替换素材（设计迭代友好，前端无需改业务代码即可替换）。

建议命名（任选其一实现即可，按需逐步升级）：

- `stardust_bg.webm`：背景星尘循环（5–8s，1920×1080，允许无 alpha）
- `stardust_bg.webp`：背景星尘静态兜底（离线/低端设备）
- `glow_sphere.webm`：中心发光球体（900×900 或 1200×1200，透明 alpha 可选）
- `glow_sphere.webp`：中心球体静态兜底

注意：
- Landing 必须保持轻量，不应引入 Cesium。
- 如果提供视频素材，优先 WebM；无视频时 `HeroVisual` 会退化到 Three.js/或纯 CSS。
