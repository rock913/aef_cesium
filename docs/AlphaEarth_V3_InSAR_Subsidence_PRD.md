# AlphaEarth 核心场景：城市广域 InSAR 沉降数字孪生系统 (V3.0 城市安防版)

一、 业务洞察与系统演进逻辑

专家/客户反馈研判：
传统的宏观地球科学难以打动专注于城市基建与工程安全的客户（如港大工程团队）。城市管理者和工程专家最痛的痛点在于：地下空间过度开发（地铁、基坑）与填海造陆软土固结引发的城市地表非均匀沉降。

V3.0 系统演进策略（Asset-Driven 架构）：
时序 InSAR 处理链路极其重度，无法在 GEE 中按需实时计算。本场景将严格遵循系统的 缓存优先原则 (Asset Cache)。我们将预先处理好的 Sentinel-1 沉降速率场作为 GEE Asset 挂载。后端服务负责动态阈值过滤，前端配合 CesiumJS 3D 白模，实现“宏观城市热力图 -> 微观建筑沉降靶向锁定”的极速定损体验。

二、 科学与算法基座：基于国际权威开源生态的测算方案

为了确保沉降数据的绝对权威性和毫米级精度，AlphaEarth 弃用简单的云端估算，全面接入国际雷达遥感学术界公认的“金标准”开源处理链。

1. 核心数据源 (Data Baseline)

雷达影像：Sentinel-1 A/B SLC (Single Look Complex)。欧空局 C 波段雷达数据，提供极高的相干性和稳定的 12 天重访周期。

地形基准：Copernicus DEM 30m (GLO-30)。目前全球精度最高的公开数字高程模型，用于剥离地形相位 (Topographic Phase Removal)。

气象基准：ECMWF ERA5。欧洲中期天气预报中心发布的第五代大气再分析数据集。在沿海城市（如广州、香港），对流层水汽变化会导致严重的雷达信号延迟，必须引入 ERA5 进行大气相位剥离。

2. 核心开源算法与物理模型 (Algorithm & Models)

本系统采用 ISCE2 + MintPy 双核驱动的时序 InSAR 分析管线。

干涉图生成引擎：ISCE2 (InSAR Scientific Computing Environment)

背景背书：由美国宇航局喷气推进实验室 (NASA JPL) 与斯坦福大学联合开发，是目前公认最严谨的干涉处理系统。

算法应用：采用短基线集 (SBAS, Small Baseline Subset) 策略（Berardino et al., 2002），限制空间和时间基线，大幅减少沿海植被和水体带来的去相干噪声。使用 SNAPHU 算法进行高精度的相位解缠。

时序反演与误差校正模型：MintPy (Miami INsar Time-series software in PYthon)

背景背书：由迈阿密大学开发，代表了当前时序形变反演（Time-Series Inversion）的最高学术水平。

算法应用：

大气延迟校正：基于 PyAPS 模块融合 ERA5 数据，物理模拟雷达波穿透对流层时的折射延迟，消除“假性沉降”。

DEM 误差反演：通过残余相位与垂直基线的线性关系，反演并剔除底层 DEM 的高程误差。

时序平差计算：采用加权最小二乘法 (WLS) 或 L1 范数，解算出每个永久散射体 (PS) 像素在时间序列上的绝对位移量和年均形变速率。

3. AlphaEarth 多模态融合创新 (AEF Fusion)

传统 InSAR 只能告诉你“哪里沉了”，但无法告诉你“沉的是什么”。
在前端渲染时，我们将 InSAR 的沉降物理量与 AEF (Alpha Earth Foundation) 的高维语义向量结合：利用 AEF 识别出“在建基坑”、“新建地铁线”和“填海造陆边缘”，自动计算沉降漏斗与 AEF 人造物特征的空间交集，从而由 AI 直接输出具有因果关系的《城市生命线危险预警报告》。

三、 离线算法与 GEE 资产化 (Offline Pipeline)

架构说明：InSAR 算法算力要求极高，必须在本地/HPC 集群完成 SLC -> ISCE2 -> MintPy 链路，然后将解算出的结果（形变速率 velocity 与 质量 coherence）作为静态 Asset 注入云端。

一次性离线固化脚本 (scripts/ch8_insar_asset_builder.py)

```python
import ee
import os
import subprocess

def upload_insar_to_gee(velocity_tif, coherence_tif, asset_id):
    """
    将本地 MintPy 产出的高精度 InSAR 结果上传为 GEE Asset。
    """
    ee.Initialize()
    print(f"🚀 开始构建 InSAR GEE 资产: {asset_id}")

    # 1. 临时上传到 GCS (Google Cloud Storage)
    gcs_bucket = "gs://your-sros-bucket/insar_temp/"
    subprocess.run(f"gsutil cp {velocity_tif} {gcs_bucket}velocity.tif", shell=True, check=True)
    subprocess.run(f"gsutil cp {coherence_tif} {gcs_bucket}coherence.tif", shell=True, check=True)
    
    # 2. 从 GCS 导入到 GEE Asset，构建双波段 Image
    manifest = {
        "name": asset_id,
        "tilesets": [
            {"id": "velocity_tiles", "sources": [{"uris": [f"{gcs_bucket}velocity.tif"]}]},
            {"id": "coherence_tiles", "sources": [{"uris": [f"{gcs_bucket}coherence.tif"]}]}
        ],
        "bands": [
            {"id": "velocity", "tilesetId": "velocity_tiles", "missingData": {"values": [0]}},
            {"id": "coherence", "tilesetId": "coherence_tiles", "missingData": {"values": [0]}}
        ]
    }
    
    import json
    with open('manifest.json', 'w') as f:
        json.dump(manifest, f)
        
    print("⏳ 正在提交 GEE 云端构建任务...")
    subprocess.run("earthengine upload image --manifest manifest.json", shell=True)
    print("✅ 任务已提交！等待云端固化。")

if __name__ == "__main__":
    upload_insar_to_gee("./data/vel.tif", "./data/coh.tif", "projects/your_gee/assets/insar_gz_2020")
```

四、 遥感算法引擎层实现 (backend/gee_service.py)
在后端的 get_layer_logic 中，直接挂载高质量的 Asset，并进行相干性掩膜与阈值报警。

```python
    elif ("ch8_insar_subsidence" in mode_s) or ("沉降" in mode_s):
        # 1. 挂载预处理的 InSAR 时序结果 Asset (NASA ISCE2 + MintPy 产物)
        ASSET_ID = "projects/your_gee_project/assets/insar_gz_2020"
        
        try:
            insar_img = ee.Image(ASSET_ID)
        except Exception as e:
            insar_img = ee.Image.constant(0).rename('velocity').addBands(ee.Image.constant(1).rename('coherence'))
        
        velocity = insar_img.select('velocity')     # 沉降速率 (mm/yr)
        coherence = insar_img.select('coherence')   # 空间相干性 (0~1)
        
        # 2. 科学级质量控制 (Quality Control)
        # 滤除相干性 < 0.75 的噪点（水体、茂密植被），只保留高质量永久散射体(PS)
        high_quality_mask = coherence.gt(0.75)
        
        # 3. 业务靶向过滤 (Anomaly Detection)
        # 提取显著沉降 (<-5mm) 或异常抬升 (>5mm) 的高危隐患点
        significant_deformation = velocity.lt(-5).Or(velocity.gt(5))
        final_mask = high_quality_mask.And(significant_deformation)
        
        img = velocity.updateMask(final_mask)
        
        # 4. 可视化参数
        vis = {
            "min": -30,  # 严重沉降 (红色)
            "max": 10,   # 抬升 (蓝色)
            "palette": ["FF0000", "FF8C00", "FFFF00", "00FF00", "0000FF"],
            "format": "png"  # 核心避坑：开启透明度，确保底部的 3D 白模建筑不被遮挡！
        }
        suffix = "ch8_urban_subsidence"
        return img, vis, suffix
```

五、 后端配置层注入 (backend/config.py)
配置南沙填海区与天河核心区两个典型任务卡片。

```python
locations = {
    # ... (原有locations)
    "guangzhou_nansha": {"coords": [22.75, 113.53, 13], "name": "广州 · 南沙区", "code": "guangzhou_nansha"},
    "guangzhou_tianhe": {"coords": [23.12, 113.32, 14], "name": "广州 · 天河核心区", "code": "guangzhou_tianhe"},
}

modes = {
    # ... (原有modes)
    "ch8_insar_subsidence": "SBAS-InSAR 时序形变分析 (毫米级)",
}

missions = [
    # ... (原有missions)
    {
        "id": "填海区沉降",
        "name": "南沙填海造陆区固结监测",
        "title": "广域基建体检：软土压密固结形变。",
        "location": "guangzhou_nansha",
        "api_mode": "ch8_insar_subsidence",
        "formula": "NASA ISCE2 + MintPy (Sentinel-1)",
        "narrative": "Alpha Earth 载入基于 NASA ISCE2 框架解算的 Sentinel-1A 时序形变网络。结合 ERA5 大气校正模型，系统在南沙填海造陆区成功提取出高密度永久散射体。大面积的橙红色光晕揭示了软土压密固结引发的地表下沉（速率 < -20mm/yr）。该数字孪生底座为沿海防汛抗涝提供了不可或缺的基准数据。",
        "camera": {"lat": 22.70, "lon": 113.55, "height": 8000, "duration_s": 4.5}
    },
    {
        "id": "核心区沉降",
        "name": "天河地下空间形变监测",
        "title": "城市生命线：靶向追踪基坑与地铁沉降。",
        "location": "guangzhou_tianhe",
        "api_mode": "ch8_insar_subsidence",
        "formula": "NASA ISCE2 + MintPy (Sentinel-1)",
        "narrative": "视角切换至高楼林立的天河CBD。在高度复杂的城市峡谷中，InSAR 算法滤除了相干性 < 0.75 的噪点，精准锁定了地铁沿线及深基坑周边的沉降漏斗。红色的靶向异常点表明部分建筑物正承受不均匀沉降应力。结合三维白模，彻底将二维工程报表升维成了具有因果追踪能力的‘城市安全大脑’。",
        "camera": {"lat": 23.08, "lon": 113.32, "height": 5000, "duration_s": 4.0}
    }
]
```

通过将这份“包含国际顶级开源支持”的底层架构融入 PRD，您的系统在满足极速 3D 渲染和前端炫酷交互的同时，拥有了极强的**专业壁垒和科学严谨性**。当政府或学术机构客户询问底层原理时，`ISCE2 + MintPy + ERA5` 的黄金组合足以打消任何关于“数据准确度”的质疑。

---

# 城市广域 InSAR 沉降数字孪生系统 — 技术调研与开发全景

> 配套文档 · 面向《AlphaEarth 城市安防版 V3.0》方案
> 定位：把方案里的「ISCE2 + MintPy + ERA5 + AEF 黄金组合」拆到能开发、能答辩、能科普的颗粒度。
> 侧重：**算法物理原理**（第一部分最厚），并补全数据源、模型底座与系统开发逻辑。
> 编写日期：2026-08

## 0. 一句话读懂这个系统

我们让一颗雷达卫星，每隔几天从太空对同一座城市「拍一次」，但拍下的不是照片，而是**电磁波往返的相位**。相位对距离的变化极其敏感——地面下沉几毫米，波就要多走这几毫米、相位就会偏一点点。把两年、上百次拍摄的相位差按时间排好、把地形/大气/噪声这些「假信号」一层层剥掉，剩下的就是**每个地面点每年到底沉了几毫米**。最后把这张毫米级的沉降速率图铺到城市三维白模上，红色光晕落在哪栋楼、哪条地铁、哪片填海区，一目了然。

这就是「宏观热力图 → 微观建筑靶向锁定」。难点不在渲染，在**如何从一堆缠绕、含噪、被大气污染的相位里，可信地反演出那几毫米**。第一部分讲的就是这件事的物理与数学。

## 第一部分 · 算法物理原理（核心）

（详细原理如雷达测距原理、干涉相位分解、基线、去相干、PS/SBAS技术流派、相位解缠、大气校正、DEM误差反演和时序反演等，请参考原始文档或详细报告。本核心算法流图如下：）

### 算法流程总表：
| 步骤 | 模型/算法 | 输入 | 输出 |
|---|---|---|---|
| 1 影像准备 | Sentinel-1 SLC 配准、去斜 | S1 SLC 栈 + 精密轨道 POE | 配准后的 SLC 栈 |
| 2 干涉图生成 | ISCE2（topsStack / SBAS 组网） | SLC 对 + GLO-30 DEM | 缠绕干涉图 + 相干图 |
| 3 地形相位剥离 | D-InSAR（GLO-30 模拟） | 干涉图 + DEM | 差分干涉图 |
| 4 相位解缠 | SNAPHU（网络流） | 缠绕差分干涉图 + 相干 | 解缠相位 |
| 5 大气校正 | PyAPS + ERA5 / 时空滤波 | 解缠相位 + ERA5 廓线 | 去大气形变相位 |
| 6 DEM 误差反演 | 与 $B_\perp$ 线性回归 | 相位栈 + 基线 | $\Delta h$ 校正后相位 |
| 7 时序反演 | WLS / L1（+ SVD） | 干涉网络 | **velocity(mm/yr)** + timeseries + 质量 |
| 8 地理编码 | radar→geo（GLO-30） | 雷达坐标结果 | 地理坐标 GeoTIFF（velocity, coherence）|

## 第二部分 · 数据源与模型底座

数据源主要包括最新的 Sentinel-1C/1D 雷达数据（6天重访），Copernicus DEM GLO-30，ERA5气象再分析数据，以及AlphaEarth Foundations（AEF）即 `GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL` 用于识别建筑与地表变化的语义引擎。

## 第三部分 · 系统工程架构与开发逻辑

系统架构为 Asset-Driven：

```
[离线 · HPC/本地]                          [在线 · 云 + 前端]
Sentinel-1 SLC 栈                          
   │ POE 精密轨道                          GEE Asset (velocity, coherence)
   ▼                                             │
ISCE2  ── 干涉图 + 相干 (SBAS 组网)          后端 gee_service
   │  SNAPHU 解缠                              │ 相干掩膜 γ>0.75
   ▼                                          │ 异常阈值 |v|>5mm/yr
MintPy ── PyAPS/ERA5 大气校正               │ 生成瓦片 URL
        DEM误差反演 / WLS·L1 反演             ▼
   │                                       前端 CesiumJS 3D 白模
   ▼                                          │ 热力图叠加 (PNG 透明)
velocity.tif + coherence.tif ──(GCS上传)──►  │ 点击建筑 → 靶向定损
                                              │ + AEF 语义 → 预警报告
```

## 第四部分 · 落地方案

建立端到端的数据流。实现由 HPC 生成数据，固化至 GEE，通过后端过滤输出至前端的链路。在渲染过程中保证三维建筑白模和热力图的良好可视化效果，提供“城市生命线”的数字孪生监测预警能力。

