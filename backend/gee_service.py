"""
GEE Service Layer for Cesium App
提供 Google Earth Engine 的核心计算和缓存管理功能
"""
import ee
import os
from typing import Dict, Tuple, Any


_CH5_CLASSIFIER_CACHE: Any | None = None


def _resolve_ch5_rf_asset_id() -> str:
    """Resolve the GEE Asset ID for the Chapter 5 classifier.

    Priority:
      1) Explicit CH5_RF_ASSET_ID
      2) Derived from GEE_USER_PATH (if configured)
    """

    explicit = str(os.getenv("CH5_RF_ASSET_ID", "")).strip()
    if explicit:
        return explicit

    gee_user_path = str(os.getenv("GEE_USER_PATH", "")).strip()
    if gee_user_path and gee_user_path != "users/default/aef_demo":
        return f"{gee_user_path.rstrip('/')}/classifiers/ch5_coastline_rf_v1"

    return ""


def _get_ch5_classifier() -> Any:
    """Load (and cache) the supervised Chapter 5 classifier from a GEE Asset."""

    global _CH5_CLASSIFIER_CACHE
    if _CH5_CLASSIFIER_CACHE is not None:
        return _CH5_CLASSIFIER_CACHE

    asset_id = _resolve_ch5_rf_asset_id()
    if not asset_id:
        raise ValueError(
            "CH5 RF classifier Asset ID not configured. Set CH5_RF_ASSET_ID, "
            "or set GEE_USER_PATH to a non-default path so the default asset path can be derived."
        )

    _CH5_CLASSIFIER_CACHE = ee.Classifier.load(asset_id)
    return _CH5_CLASSIFIER_CACHE


def _embedding_band_index(a_band: str) -> int:
    """Return embedding band index for an alias like 'A00'..'A63'."""

    name = str(a_band)
    if not (len(name) == 3 and name[0] == "A" and name[1:].isdigit()):
        raise ValueError(f"Invalid embedding band alias: {a_band!r}")
    idx = int(name[1:])
    if idx < 0 or idx > 63:
        raise ValueError(f"Embedding band index out of range: {a_band!r}")
    return idx


def _select_embedding_bands(image: Any, a_bands: list[str], *, rename_to: list[str] | None = None) -> Any:
    """Select embedding dimensions reliably.

    Some GEE datasets expose embedding dimensions with numeric band names ('0'..'63'),
    while our UI/docs use semantic aliases ('A00'..'A63'). Selecting by *index* avoids
    band-name mismatch failures and we then rename to the requested aliases.
    """

    if not a_bands:
        raise ValueError("a_bands must be non-empty")
    indices = [_embedding_band_index(band) for band in a_bands]
    out_names = rename_to if rename_to is not None else a_bands
    return image.select(indices).rename(out_names)


def _pyramid_safe_constant(reference_image: Any, value: int | float) -> Any:
    """Create a constant-valued image that inherits projection/pyramids.

    IMPORTANT: Avoid using ee.Image(constant) as the base for large-area per-pixel
    operations (e.g. .where/.mosaic over 10m data). Constant images have no
    intrinsic pyramid/projection metadata, which can trigger expensive reprojection
    at low zoom levels ("image pyramid collapse").
    """

    # reference_image.multiply(0) preserves scale/projection; add(value) makes it constant.
    return reference_image.multiply(0).add(value)


def compute_zonal_stats(
    image: Any,
    region: Any,
    *,
    scale: int = 30,
    max_pixels: int = int(1e9),
    masked_as_anomaly: bool = True,
) -> Dict[str, Any]:
    """Compute simple zonal statistics for a layer.

    This is intended to power V5 HUD metrics (replace mockStats) with real cloud
    results via Earth Engine `reduceRegion`.

    Returns numbers in km^2 and percent.
    """

    # Total area of the analysis geometry (pixel-based so it matches mask behavior)
    pixel_area = ee.Image.pixelArea().rename(["area"])
    total_area_m2 = pixel_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region,
        scale=scale,
        maxPixels=max_pixels,
    ).get("area")

    anomaly_area_m2 = None
    if masked_as_anomaly:
        # Treat masked-in pixels as anomaly; our mode logic typically sets mask for "interesting" areas.
        anomaly_area_m2 = pixel_area.updateMask(image.mask()).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=region,
            scale=scale,
            maxPixels=max_pixels,
        ).get("area")

    # Convert to client-side numbers
    total_m2 = ee.Number(total_area_m2).getInfo() if total_area_m2 is not None else 0.0
    total_km2 = float(total_m2) / 1e6 if total_m2 else 0.0

    anomaly_km2 = None
    anomaly_pct = None
    if anomaly_area_m2 is not None and total_m2:
        a_m2 = float(ee.Number(anomaly_area_m2).getInfo())
        anomaly_km2 = a_m2 / 1e6
        anomaly_pct = (a_m2 / float(total_m2)) * 100.0

    return {
        "total_area_km2": total_km2,
        "anomaly_area_km2": anomaly_km2,
        "anomaly_pct": anomaly_pct,
        "scale_m": scale,
    }


def get_layer_logic(mode: str, region: Any) -> Tuple[Any, Dict, str]:
    """
    定义核心计算逻辑 (纯数学算子)
    
    Args:
        mode: AI 场景模式 (如 "地表 DNA (语义视图)")
        region: ee.Geometry 对象，表示监测区域
    
    Returns:
        (ee.Image, 视觉参数, Asset名称后缀)
    """
    emb_col = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
    mode_s = str(mode or "")

    # Use a moderately-sized embedding subset for robust performance.
    # The dataset is 64-D (A00..A63); using a subset keeps cloud costs bounded.
    emb_bands = [f"A{idx:02d}" for idx in range(0, 16)]

    # Core fix: Earth Engine stores imagery in large tiles; using .first() may return just
    # the first intersecting source tile, rendering as a single square. Use
    # filterBounds(region).mosaic() to stitch all intersecting pieces into one image.
    # NOTE: Restore the original wider time window for visual consistency with the previous version.
    filtered_col = emb_col.filterBounds(region).filterDate("2023-01-01", "2025-01-01")

    # --- V6 modes ---
    if ("ch1_yuhang_faceid" in mode_s) or ("城市基因突变" in mode_s) or ("欧氏距离" in mode_s):
        # Chapter 1: Euclidean distance between 2017 and 2024 embedding vectors.
        emb17 = _select_embedding_bands(
            emb_col.filterDate("2017-01-01", "2017-12-31").filterBounds(region).mosaic(),
            emb_bands,
        )
        emb24 = _select_embedding_bands(
            emb_col.filterDate("2024-01-01", "2024-12-31").filterBounds(region).mosaic(),
            emb_bands,
        )
        dist = emb17.subtract(emb24).pow(2).reduce(ee.Reducer.sum()).sqrt()
        img = dist.updateMask(dist.gt(0.16))
        vis = {"min": 0.16, "max": 0.45, "palette": ["330000", "FF0000", "FFAA00", "FFFFFF"]}
        suffix = "ch1_faceid"

    elif ("ch2_maowusu_shield" in mode_s) or ("大国生态护盾" in mode_s) or ("余弦相似度" in mode_s):
        # Chapter 2: Cosine similarity (direction-only) to reduce seasonal amplitude noise.
        emb19 = _select_embedding_bands(
            emb_col.filterDate("2019-01-01", "2019-12-31").filterBounds(region).mosaic(),
            emb_bands,
        )
        emb24 = _select_embedding_bands(
            emb_col.filterDate("2024-01-01", "2024-12-31").filterBounds(region).mosaic(),
            emb_bands,
        )

        dot = emb19.multiply(emb24).reduce(ee.Reducer.sum())
        n19 = emb19.pow(2).reduce(ee.Reducer.sum()).sqrt()
        n24 = emb24.pow(2).reduce(ee.Reducer.sum()).sqrt()
        cosine = dot.divide(n19.multiply(n24))

        # Turn similarity into a "risk" score.
        risk = ee.Image(1).subtract(cosine)
        img = risk.updateMask(risk.gt(0.06))
        vis = {'min': 0.06, 'max': 0.22, 'palette': ['00110A', '00AA66', 'FFCC00', 'FF3300']}
        suffix = "ch2_shield"

    elif ("ch3_zhoukou_pulse" in mode_s) or ("粮仓脉搏" in mode_s) or ("特定维度反演" in mode_s):
        # Chapter 3: Specific dimension inversion/extraction (interpretable intensity field).
        # Restore legacy visualization: unitScale + threshold in the normalized domain.
        img = _select_embedding_bands(filtered_col.mosaic(), ["A02"], rename_to=["pulse"]).unitScale(-0.2, 0.2)
        img = img.updateMask(img.gt(0.55))
        vis = {"min": 0.55, "max": 0.9, "palette": ["001018", "00A3FF", "00F5FF", "FFFFFF"]}
        suffix = "ch3_pulse"

    elif ("ch5_coastline_audit" in mode_s) or ("海岸线" in mode_s) or ("红线审计" in mode_s):
        # Chapter 5: Coastline redline audit (supervised, assetized RF classifier).
        # Semantic binding:
        #   0: water (blue)
        #   1: natural mudflat (gold)
        #   2: reclaimed/artificial hardening (red)
        #   3: inland background (transparent/masked)
        base_img = _select_embedding_bands(filtered_col.mosaic(), emb_bands)

        # STRICT: production requires the supervised classifier asset to be configured and loadable.
        try:
            classifier = _get_ch5_classifier()
        except Exception as e:
            raise ValueError(f"CH5 RF classifier asset is not configured/ready: {e}") from e

        try:
            img = base_img.classify(classifier)
        except Exception as e:
            raise RuntimeError(f"CH5 RF classifier failed to run classify(): {e}") from e

        # Hide background pixels (class 3) to avoid semantic overflow over inland areas.
        try:
            img = img.updateMask(img.neq(3))
        except Exception as e:
            raise RuntimeError(f"CH5 RF classifier failed to apply background mask: {e}") from e

        suffix = "ch5_audit_supervised"

        vis = {
            "min": 0,
            "max": 2,
            "palette": ["1A365D", "F6C431", "E23D28"],
        }

    elif ("ch6_water_pulse" in mode_s) or ("水网脉动" in mode_s) or ("维差分" in mode_s):
        # Chapter 6: Poyang water pulse (dimension delta between years).
        water_2022 = (
            emb_col.filterDate("2022-01-01", "2022-12-31").filterBounds(region).mosaic()
        )
        water_2022 = _select_embedding_bands(water_2022, ["A02"])
        water_2024 = (
            emb_col.filterDate("2024-01-01", "2024-12-31").filterBounds(region).mosaic()
        )
        water_2024 = _select_embedding_bands(water_2024, ["A02"])
        diff = water_2024.subtract(water_2022)
        diff = diff.updateMask(diff.abs().gt(0.10))
        img = diff
        vis = {
            "min": -0.20,
            "max": 0.20,
            "palette": ["1E4AFF", "000000", "FF5A36"],
        }
        suffix = "ch6_water"

    elif ("ch4_amazon_zeroshot" in mode_s) or ("零样本" in mode_s):
        # Chapter 4: Zero-shot KMeans clustering.
        # Critical guard: use a bounded training region to avoid GEE timeouts.
        # (Do NOT train on the full viewport.)
        training_region = ee.Geometry.Rectangle([-56.5, -12.5, -53.5, -9.5])

        base = _select_embedding_bands(filtered_col.mosaic(), [f"A{idx:02d}" for idx in range(0, 8)])
        training = base.sample(
            region=training_region,
            scale=60,
            numPixels=5000,
            seed=13,
            geometries=False,
        )
        clusterer = ee.Clusterer.wekaKMeans(6).train(training)
        clustered = base.cluster(clusterer)
        img = clustered.randomVisualizer()
        # randomVisualizer already returns RGB, but force RGB output for robustness.
        vis = {'forceRgbOutput': True}
        suffix = "ch4_zeroshot"

    else:
        raise ValueError(f"Unknown mode: {mode}")
    
    # 🔧 修复：不裁剪图像到region，保持全球范围
    # 原因：clip()后的小范围图像在某些zoom level下可能没有瓦片
    # Cesium会根据视口自动加载需要的瓦片范围
    # 注意：tile 渲染阶段不再使用 filterBounds；空间裁剪由 EE tile engine 按需处理。
    return img, vis, suffix


def get_mode_vis_and_suffix(mode: str) -> Tuple[Dict, str]:
    """Return (vis_params, suffix) for a V6 mode without running heavy EE operations.

    This is used to avoid expensive `get_layer_logic()` computation when an exported
    Asset already exists.
    """
    mode_s = str(mode or "")

    if ("ch1_yuhang_faceid" in mode_s) or ("城市基因突变" in mode_s) or ("欧氏距离" in mode_s):
        return (
            {
                "min": 0.16,
                "max": 0.45,
                "palette": ["330000", "FF0000", "FFAA00", "FFFFFF"],
                # Preserve alpha for masked pixels when stacking in Cesium.
                "format": "png",
            },
            "ch1_faceid",
        )
    if ("ch2_maowusu_shield" in mode_s) or ("大国生态护盾" in mode_s) or ("余弦相似度" in mode_s):
        return (
            {
                "min": 0.06,
                "max": 0.22,
                "palette": ["00110A", "00AA66", "FFCC00", "FF3300"],
                "format": "png",
            },
            "ch2_shield",
        )
    if ("ch3_zhoukou_pulse" in mode_s) or ("粮仓脉搏" in mode_s) or ("特定维度反演" in mode_s):
        return (
            {
                "min": 0.55,
                "max": 0.9,
                "palette": ["001018", "00A3FF", "00F5FF", "FFFFFF"],
                "format": "png",
            },
            "ch3_pulse",
        )
    if ("ch4_amazon_zeroshot" in mode_s) or ("零样本" in mode_s):
        return ({"forceRgbOutput": True, "format": "png"}, "ch4_zeroshot")
    if ("ch5_coastline_audit" in mode_s) or ("海岸线" in mode_s) or ("红线审计" in mode_s):
        return (
            {
                "min": 0,
                "max": 2,
                "palette": ["0B1B36", "E23D28", "F6C431"],
                "format": "png",
            },
            "ch5_audit",
        )
    if ("ch6_water_pulse" in mode_s) or ("水网脉动" in mode_s) or ("维差分" in mode_s):
        return (
            {
                "min": -0.20,
                "max": 0.20,
                "palette": ["1E4AFF", "000000", "FF5A36"],
                "format": "png",
            },
            "ch6_water",
        )

    raise ValueError(f"Unknown mode: {mode}")


def generate_asset_id(loc_code: str, suffix: str, gee_user_path: str) -> str:
    """
    生成 Asset ID
    
    Args:
        loc_code: 地点代码 (如 "shanghai")
        suffix: 场景后缀 (如 "change")
        gee_user_path: GEE 用户路径 (如 "users/xxx/aef_demo")
    
    Returns:
        完整的 Asset ID
    """
    return f"{gee_user_path}/{loc_code}_{suffix}"


def smart_load(
    mode: str, 
    region: Any, 
    loc_code: str,
    gee_user_path: str
) -> Tuple[Any, Dict, str, bool, str, Any]:
    """
    智能加载：先查 Asset，无则计算
    
    Args:
        mode: AI 场景模式
        region: 监测区域
        loc_code: 地点代码
        gee_user_path: GEE 用户路径
    
    Returns:
        (图层, 视觉参数, 状态HTML, 是否缓存命中, Asset ID, 原始计算图层)
    """
    # 1) Derive metadata without heavy EE work.
    #    This lets us check for an existing exported Asset first.
    vis_params, suffix = get_mode_vis_and_suffix(mode)

    # 2) Build Asset ID
    asset_id = generate_asset_id(loc_code, suffix, gee_user_path)
    
    status_html = ""
    final_layer = None
    is_cached = False
    raw_img = None
    
    try:
        # 尝试加载 Asset
        ee.data.getAsset(asset_id)  # 如果不存在会抛异常
        final_layer = ee.Image(asset_id)
        status_html = "<span class='status-badge status-cached'>🚀 极速缓存 (Asset)</span>"
        is_cached = True
    except Exception:
        # Asset 不存在，使用实时计算（可能较慢）
        computed_img, _computed_vis, _computed_suffix = get_layer_logic(mode, region)
        raw_img = computed_img
        final_layer = computed_img
        status_html = "<span class='status-badge status-live'>⚡ 实时计算 (Cloud)</span>"
        is_cached = False

    return final_layer, vis_params, status_html, is_cached, asset_id, raw_img


def get_tile_url(image: Any, vis_params: Dict) -> str:
    """
    获取 GEE 图层的 Tile URL
    
    Args:
        image: ee.Image 对象
        vis_params: 可视化参数
    
    Returns:
        XYZ Tile URL (包含 {z}/{x}/{y} 占位符)
    """
    # 🔧 Fix: Force PNG tiles to preserve transparency.
    #
    # Symptom (frontend): semi-transparent white overlay when stacking AI layers.
    # Root cause: upstream GEE tile responses can default to JPEG, which has no alpha
    # channel. When an ee.Image has masked pixels, JPEG encoding turns the background
    # into a solid color (often white). Cesium then blends that "white background" at
    # the imagery layer alpha, showing as a white haze.
    #
    # For EE map tiles, `format='png'` keeps alpha from the image mask.
    vis = dict(vis_params or {})
    fmt = str(vis.get("format") or "").strip().lower()
    # Default to PNG when not specified. Do NOT override an explicit JPEG choice
    # (e.g. for true-color Sentinel-2 where alpha is unnecessary).
    if fmt == "":
        vis["format"] = "png"

    # 无需重投影，直接生成MapID即可获得有效的瓦片
    map_id = image.getMapId(vis)
    tile_url = map_id['tile_fetcher'].url_format
    return tile_url


def trigger_export_task(
    image: Any,
    description: str,
    asset_id: str,
    region: Any,
    scale: int = 10,
    max_pixels: int = int(1e9)
) -> str:
    """
    触发 GEE 后台导出任务
    
    Args:
        image: 要导出的 ee.Image
        description: 任务描述
        asset_id: 目标 Asset ID
        region: 导出区域
        scale: 分辨率 (米)
        max_pixels: 最大像素数
    
    Returns:
        任务 ID
    """
    task = ee.batch.Export.image.toAsset(
        image=image,
        description=description,
        assetId=asset_id,
        region=region,
        scale=scale,
        maxPixels=max_pixels
    )
    task.start()
    return task.id


def init_earth_engine():
    """
    初始化 Earth Engine
    优先使用服务账号，回退到交互式认证
    """
    try:
        # 尝试服务账号认证
        service_account = os.getenv('EE_SERVICE_ACCOUNT')
        key_file = os.getenv('EE_PRIVATE_KEY_FILE')
        
        if service_account and key_file:
            credentials = ee.ServiceAccountCredentials(service_account, key_file)
            ee.Initialize(credentials)
            print(f"✅ GEE initialized with service account: {service_account}")
        else:
            # 交互式认证
            ee.Initialize()
            print("✅ GEE initialized with user credentials")
    except Exception as e:
        print(f"❌ GEE initialization failed: {e}")
        raise

