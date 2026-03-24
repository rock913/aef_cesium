Zero2x 8K 天空盒获取指南与宇宙漫游原理解析

第一部分：8K 银河全景图标准化获取流程

针对 frontend/public/assets/eso_milkyway_8k.jpg 的就绪，为您提供以下两条绝对可靠的落地方案。

方案 A（官方强推）：ESO 官方银河系全景图

1. 官方确源与授权 (ESO/S. Brunier)
ESO（欧洲南方天文台）有一张天文学界最著名的、完全吻合 Equirectangular（等矩形投影）且比例接近 2:1 的全天银河系图。

官方资源页：ESO Milky Way panorama (eso0932a)

投影确认：页面明确标注为 360-degree panorama，完美适配 Three.js 的 EquirectangularReflectionMapping。

版权声明 (Credit)：ESO/S. Brunier。ESO 的图片采用 CC BY 4.0 协议，允许商业与非商业使用，只需在您的 Workbench 关于页面或控制台打印中署名即可。

2. 终端极速下载与预处理
在您的 Linux/Docker 终端中按顺序执行以下命令（包含自动解压、裁切与缩放）：

# 1. 创建目标目录
mkdir -p /mnt/data/hyf/oneearth/cesium_app_v6/frontend/public/assets

# 2. 下载 ESO 官方提供的高画质 JPEG 版（当前为 6000x3000）
# 说明：我们会把它严格缩放/补齐到 8192x4096（Power of Two，纹理对齐更友好）。
# （注意：不用下载原始 18000x9000 的超大 TIFF，前端显存会爆，8K 刚好）
curl -L "https://cdn.eso.org/images/large/eso0932a.jpg" -o /mnt/data/hyf/oneearth/cesium_app_v6/frontend/public/assets/eso_milkyway_source.jpg

# 3. 安装 ImageMagick
sudo apt-get update && sudo apt-get install -y imagemagick

# 4. 强制缩放至严格的 8192x4096 (Power of Two)，并压缩质量至 90 以减小体积
# 注意 \! 是强制忽略微小比例差异，严格输出目标像素，这对 WebGPU 纹理内存对齐非常友好
magick /mnt/data/hyf/oneearth/cesium_app_v6/frontend/public/assets/eso_milkyway_source.jpg -resize 8192x4096\! -quality 90 /mnt/data/hyf/oneearth/cesium_app_v6/frontend/public/assets/eso_milkyway_8k.jpg

# 5. 清理源文件
rm /mnt/data/hyf/oneearth/cesium_app_v6/frontend/public/assets/eso_milkyway_source.jpg


如果你处在无 sudo / 无 root 的受限环境（无法 apt 安装 ImageMagick），推荐使用 Node + sharp 做等价处理：

cd /mnt/data/hyf/oneearth/cesium_app_v6/frontend
npm i -D sharp

node - <<'NODE'
const fs = require('fs');
const sharp = require('sharp');

const src = 'public/assets/eso_milkyway_source.jpg';
const tmp = 'public/assets/eso_milkyway_8k.tmp.jpg';
const out = 'public/assets/eso_milkyway_8k.jpg';

(async () => {
	await sharp(src)
		.resize(8192, 4096, { fit: 'fill' })
		.jpeg({ quality: 90 })
		.toFile(tmp);

	const st = fs.statSync(tmp);
	if (st.size < 1_000_000) throw new Error(`tmp too small: ${st.size}`);

	fs.renameSync(tmp, out);
	console.log('OK', out, 'bytes', st.size);
})();
NODE

rm public/assets/eso_milkyway_source.jpg


如果你没有 ImageMagick，也可以用这段 Python 脚本完成严格缩放（自动解除了大图限制）：

python3 -c "
from PIL import Image
Image.MAX_IMAGE_PIXELS = None # 解除 8K 爆内存警告
img = Image.open('/mnt/data/hyf/oneearth/cesium_app_v6/frontend/public/assets/eso_milkyway_source.jpg')
img_resized = img.resize((8192, 4096), Image.Resampling.LANCZOS)
img_resized.save('/mnt/data/hyf/oneearth/cesium_app_v6/frontend/public/assets/eso_milkyway_8k.jpg', quality=90)
"


方案 B（备选）：Poly Haven (CC0 授权)

如果您希望未来完全规避署名问题，推荐使用 Poly Haven 的太空 HDR 图。

搜索：前往 Poly Haven Skies，搜索 starmap 或 milky way。

获取：下载 8K 的 JPG 格式。尺寸绝对是 2:1，且无版权要求（CC0）。重命名并放在同样目录下即可。

第二部分：架构答疑 —— 一张静态图片如何支撑大规模宇宙漫游？

这是一个非常深刻的 3D 图形学与天文架构问题。

您的疑问：“目前只是一张银河系的图片，它贴在背景上，如果我在工作台里做大尺度（数百万光年）的漫游和红移拉伸，这张图片怎么可能支持这种漫游？”

架构揭秘：视差错觉（Parallax Illusion）与“天空盒的绝对无限远”

在真实宇宙观测和 Three.js 引擎渲染中，我们利用了极其精妙的分层渲染架构来欺骗人眼，营造出无尽漫游的错觉。

1. 天球的物理本质：无限远的参照系

在宇宙空间中，像银河系尘埃带（Milky Way Dust Lanes）、小麦哲伦星系这样极其庞大且遥远的背景天体，相对于观测者微小的移动而言，是不存在透视变化的。

在 ThreeTwin.vue 的代码中，我们将这张 8K 贴图赋予了一个巨大的 SphereGeometry（并且关闭了 depthWrite）。

这意味着，无论相机在 3D 空间中向前飞 100 还是 10,000 个单位，这张背景图片都不会变大或变小。它永远锁定在视野的最深处，只随着你鼠标的**旋转（Rotation）**而转动。

2. 漫游感从何而来？前景 3D 点云的视差（The 3D Foreground）

真正让用户感觉到“我正在宇宙中穿梭漫游”的，不是那张 8K 背景图，而是您那 50,000 个 SDSS 真实红移星系数据（THREE.Points）。

这 50,000 个发光粒子是拥有真实的 (X, Y, Z) 坐标的。

当您拉长相机 FOV 并向前冲刺（Dolly Zoom / 希区柯克变焦）时，离相机近的星系会瞬间放大并从屏幕边缘“嗖”地飞过去，离相机远的星系则移动缓慢。

这就是“视差（Parallax）”。

3. 两者结合的化学反应（The Cinematic Magic）

背景（ESO 8K 贴图）：提供了一个极度真实、深邃、令人敬畏的宇宙深空底色。它告诉大脑：“你在宇宙中”。

前景（5万个红移发光点云）：提供了真实的 3D 空间结构（斯隆长城）。当你在其中穿梭时，光斑从你脸颊擦过。

化学反应：静态的 8K 背景 + 高速穿梭的 3D 点云，完美复刻了《星际穿越》中曲速引擎穿梭的经典画面。如果没有那张背景图，点云就像是在一个黑色的盒子里飞，极其单调；有了贴图打底，宇宙的宏大尺度感瞬间确立。

4. 未来的 Astro-GIS 进阶 (HiPS 瓦片流)

当然，单张 8K 图片是有极限的（当你尝试用望远镜视野极度放大背景某一个像素时，它会模糊）。

现在的阶段：这张 8K 贴图足以支撑我们所有的“大尺度宇宙结构漫游”、“星系爆裂”等 Demo，因为我们是在宏观尺度上飞行。

未来的 Phase 2B：如果我们以后要实现“从全天球放大 10000 倍，直到看清蟹状星云的某一颗星”，我们就会废弃这张 8K 静态图，接入 Native WebGPU HiPS Loader。那时候，背景不再是一张图，而是随着相机 FOV 缩小，动态从服务器拉取更高清的 HEALPix 局部影像块拼接而成（类似宇宙版的 Google Earth）。

但在当前 Zero2x v7.5 冲刺阶段，这套“8K 静态极坐标底图 + 高动态 3D 点云”的双层管线架构，是性价比最高、视觉冲击力最强、且绝对不会穿帮的电影级解决方案。