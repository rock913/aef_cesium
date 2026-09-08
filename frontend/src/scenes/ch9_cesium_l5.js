/**
 * CH9 L5 单体三维图层 · Cesium 集成模块
 * ============================================================
 * 兑现展台海报 P2「L5 单体三维」的承诺，替换掉：
 *   ✗ GeoJSON Polygon extrude 出来的红色平顶方块
 *   ✗ 悬浮在扁平卫星底图上的 2D 热力图 + 三维标签
 *
 * 提供：
 *   1. 电影级打光（暗环境 · 定向光 · 雾 · HDR）
 *   2. 通用古建 glTF 模型加载 + 危险染色 + 呼吸灯
 *   3. 部位锚点绑定（屋脊/檐口/翼角/山墙，来自 *_anchors.json）
 *   4. 屋面风场流线（PolylineCollection 动画）
 *   5. L1→L5 一镜到底镜头编排
 *   6. 图层不可用时的安全跳过（配合 ch9_gee_layer_fix.py）
 */
import * as Cesium from 'cesium'


// ══════════════════════════════════════════════════════════════
// 0. 电影级打光 —— 解决「侧边栏暗黑 vs 地图大白天」的割裂感
// ══════════════════════════════════════════════════════════════
export function applyCinematicLighting(viewer) {
  const scene = viewer.scene;
  const globe = scene.globe;

  // 太阳光照开启，但把时间锁在低角度斜射（黄昏感），而不是正午顶光
  globe.enableLighting = true;
  globe.dynamicAtmosphereLighting = true;
  globe.dynamicAtmosphereLightingFromSun = false;

  // 自定义定向光：低角度 + 冷调，呼应海报的深空底色
  scene.light = new Cesium.DirectionalLight({
    direction: new Cesium.Cartesian3(0.28, -0.52, -0.81),
    color: new Cesium.Color(0.86, 0.92, 1.0),
    intensity: 2.4,
  });

  // 地表基色压暗 —— 无影像区域不再是刺眼的白/蓝
  globe.baseColor = Cesium.Color.fromCssColorString("#0A1520");
  globe.showGroundAtmosphere = true;
  globe.atmosphereBrightnessShift = -0.32;
  globe.atmosphereSaturationShift = 0.12;
  globe.atmosphereHueShift = 0.0;

  // 大气与雾：远处压暗，聚焦当前目标
  scene.skyAtmosphere.brightnessShift = -0.28;
  scene.skyAtmosphere.saturationShift = 0.10;
  scene.fog.enabled = true;
  scene.fog.density = 0.00016;
  scene.fog.screenSpaceErrorFactor = 3.0;

  // HDR + FXAA，金属/瓦面高光更自然
  scene.highDynamicRange = true;
  scene.postProcessStages.fxaa.enabled = true;

  // 关掉默认的白色地球轮廓感
  scene.backgroundColor = Cesium.Color.fromCssColorString("#060E16");
  scene.globe.showSkirts = false;

  return scene;
}

// ══════════════════════════════════════════════════════════════
// 1. 安全添加 GEE 图层 —— 图层不可用就跳过，绝不糊住地球
// ══════════════════════════════════════════════════════════════
const _layerRegistry = new Map();

export function safeAddGeeLayer(viewer, key, layerResponse) {
  removeGeeLayer(viewer, key);

  // ★ 后端返回 available=false 时，什么都不加
  if (!layerResponse || !layerResponse.available || !layerResponse.tileUrl) {
    console.warn(
      `[CH9] 图层「${key}」不可用，已跳过：`,
      layerResponse?.reason, layerResponse?.hint
    );
    return null;
  }

  const provider = new Cesium.UrlTemplateImageryProvider({
    url: layerResponse.tileUrl,
    // GEE 瓦片本身就是带 alpha 的 PNG，被 mask 的像元透明
    // 不要设置 hasAlphaChannel:false，那会把透明通道丢掉
    hasAlphaChannel: true,
    credit: "Google Earth Engine",
  });

  const layer = viewer.imageryLayers.addImageryProvider(provider);
  layer.alpha = layerResponse.recommended_alpha ?? 0.85;
  layer.brightness = 1.05;
  layer.gamma = 0.95;
  _layerRegistry.set(key, layer);
  return layer;
}

export function removeGeeLayer(viewer, key) {
  const old = _layerRegistry.get(key);
  if (old) {
    viewer.imageryLayers.remove(old, true);
    _layerRegistry.delete(key);
  }
}

// ══════════════════════════════════════════════════════════════
// 2. 古建 3D 模型加载
// ══════════════════════════════════════════════════════════════
const MODEL_LIBRARY = {
  hall:      "/assets/models/heritage_hall_xieshan.glb",        // 通用厅堂 · 歇山顶
  taimen:    "/assets/models/heritage_taimen_courtyard.glb",    // 台门 / 三合院
  complex:   "/assets/models/heritage_complex_multicourt.glb",  // 多进院落建筑群
};

const RISK_COLOR = {
  stable:            Cesium.Color.fromCssColorString("#5DAE8B"),
  moderate:          Cesium.Color.fromCssColorString("#C89A3C"),
  unstable:          Cesium.Color.fromCssColorString("#C85F45"),
  critical:          Cesium.Color.fromCssColorString("#B03A2E"),
  data_insufficient: Cesium.Color.fromCssColorString("#5F7885"),
};

/**
 * @param {Object} o
 * @param {number[]} o.position   [lon, lat, height]
 * @param {string}   o.modelKey   hall | taimen | complex
 * @param {number}   o.heading    建筑朝向（度，正南为 180）
 * @param {number}   o.scale      缩放，使模型覆盖真实轮廓
 * @param {string}   o.riskLevel  stable|moderate|unstable|critical|data_insufficient
 * @param {boolean}  o.breathing  是否呼吸灯
 */
export function addHeritageModel(viewer, o) {
  const [lon, lat, h = 0] = o.position;
  const position = Cesium.Cartesian3.fromDegrees(lon, lat, h);
  const hpr = new Cesium.HeadingPitchRoll(
    Cesium.Math.toRadians(o.heading ?? 180), 0, 0);
  const orientation = Cesium.Transforms.headingPitchRollQuaternion(position, hpr);

  const base = RISK_COLOR[o.riskLevel] ?? RISK_COLOR.stable;

  // 呼吸灯：用 CallbackProperty 让 alpha 随时间脉动
  const colorProp = o.breathing
    ? new Cesium.CallbackProperty(() => {
        const t = performance.now() / 1000;
        const a = 0.42 + 0.30 * (0.5 + 0.5 * Math.sin(t * 2.0));
        return base.withAlpha(a);
      }, false)
    : base.withAlpha(0.72);

  const entity = viewer.entities.add({
    id: `ch9_model_${o.buildingId}`,
    name: o.name ?? "古建单体",
    position,
    orientation,
    model: {
      uri: MODEL_LIBRARY[o.modelKey ?? "hall"],
      scale: o.scale ?? 1.0,
      minimumPixelSize: 96,
      maximumScale: 400,
      // MIX：保留瓦面/木柱的原始材质纹理，同时叠加风险色
      // 若用 REPLACE 会变回「纯色方块」，务必用 MIX
      color: colorProp,
      colorBlendMode: Cesium.ColorBlendMode.MIX,
      colorBlendAmount: o.blendAmount ?? 0.55,
      silhouetteColor: base,
      silhouetteSize: o.riskLevel === "unstable" || o.riskLevel === "critical" ? 2.0 : 0.0,
      shadows: Cesium.ShadowMode.ENABLED,
      lightColor: new Cesium.Cartesian3(1.25, 1.30, 1.38), // 冷调补光，配合暗环境
    },
  });

  return entity;
}

// ══════════════════════════════════════════════════════════════
// 3. 部位锚点绑定 —— 标签挂到模型真实部位，不再悬空
// ══════════════════════════════════════════════════════════════
/**
 * anchors 来自模型同名的 *_anchors.json（模型局部坐标，米，Z-up）
 * 本函数把局部坐标转成世界坐标后挂标签。
 */
export function bindAnchorLabels(viewer, o) {
  const [lon, lat, h = 0] = o.position;
  const origin = Cesium.Cartesian3.fromDegrees(lon, lat, h);
  const enuFrame = Cesium.Transforms.eastNorthUpToFixedFrame(origin);
  const headingRad = Cesium.Math.toRadians(o.heading ?? 180);
  const scale = o.scale ?? 1.0;
  const entities = [];

  for (const item of o.anchorItems) {
    // item: { key: "正厅_屋脊", label: "屋脊", value: "-3.697 kPa",
    //         level: "severe|moderate|watch" }
    const local = o.anchors[item.key];
    if (!local) { console.warn("[CH9] 锚点缺失:", item.key); continue; }

    // 局部 Z-up (x=面阔, y=进深, z=高) → ENU (east, north, up)，先按 heading 旋转
    const [lx, ly, lz] = local.map((v) => v * scale);
    const cos = Math.cos(headingRad), sin = Math.sin(headingRad);
    const east = lx * cos + ly * sin;
    const north = -lx * sin + ly * cos;
    const offset = new Cesium.Cartesian3(east, north, lz);
    const world = Cesium.Matrix4.multiplyByPoint(
      enuFrame, offset, new Cesium.Cartesian3());

    const color = {
      severe:   Cesium.Color.fromCssColorString("#B03A2E"),
      moderate: Cesium.Color.fromCssColorString("#C89A3C"),
      watch:    Cesium.Color.fromCssColorString("#2E9CB8"),
    }[item.level ?? "watch"];

    entities.push(viewer.entities.add({
      id: `ch9_anchor_${o.buildingId}_${item.key}`,
      position: world,
      point: {
        pixelSize: 9,
        color,
        outlineColor: Cesium.Color.WHITE.withAlpha(0.85),
        outlineWidth: 1.5,
        disableDepthTestDistance: 0,   // ★ 参与深度测试，被屋顶遮挡时自然隐藏
      },
      label: {
        text: `${item.label}  ${item.value}`,
        font: "600 14px 'Microsoft YaHei', sans-serif",
        fillColor: Cesium.Color.WHITE,
        backgroundColor: Cesium.Color.fromCssColorString("#13242FCC"),
        showBackground: true,
        backgroundPadding: new Cesium.Cartesian2(9, 6),
        pixelOffset: new Cesium.Cartesian2(0, -26),
        horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        scaleByDistance: new Cesium.NearFarScalar(120, 1.0, 900, 0.55),
        translucencyByDistance: new Cesium.NearFarScalar(600, 1.0, 1600, 0.0),
        disableDepthTestDistance: Number.POSITIVE_INFINITY, // 文字始终可读
      },
      // 从锚点向下引一根短线到屋面，视觉上「钉」在部位上
      polyline: item.leader === false ? undefined : {
        positions: [world, Cesium.Matrix4.multiplyByPoint(
          enuFrame, new Cesium.Cartesian3(east, north, Math.max(0, lz - 2.2)),
          new Cesium.Cartesian3())],
        width: 1.6,
        material: color.withAlpha(0.75),
      },
    }));
  }
  return entities;
}

// ══════════════════════════════════════════════════════════════
// 4. 屋面风场流线 —— 替代物理上错误的「地面 2D 热力图」
// ══════════════════════════════════════════════════════════════
/**
 * 风压作用在屋顶上，地面的红色热力图在物理逻辑上是错的。
 * 这里在屋面上方画一组随时间流动的青蓝色流线，呼应侧边栏的 FEA 云图。
 */
export function addWindStreamlines(viewer, o) {
  const [lon, lat] = o.position;
  const origin = Cesium.Cartesian3.fromDegrees(lon, lat, 0);
  const enu = Cesium.Transforms.eastNorthUpToFixedFrame(origin);

  const dirRad = Cesium.Math.toRadians(o.windDirectionDeg ?? 120); // 气象风向：风的来向
  const ux = Math.sin(dirRad + Math.PI);  // 转成风的去向
  const uy = Math.cos(dirRad + Math.PI);

  const span = o.span ?? 42;          // 流线长度（米）
  const nLines = o.lines ?? 9;
  const height = o.height ?? 12;      // 屋面上方高度
  const speed = o.speed ?? 0.55;      // 流动速度

  const entities = [];
  for (let i = 0; i < nLines; i++) {
    const lateral = (i - (nLines - 1) / 2) * (o.spacing ?? 4.2);
    // 侧向偏移方向 = 风向的法向
    const px = -uy * lateral;
    const py = ux * lateral;
    const zJitter = height + Math.sin(i * 1.7) * 1.6;

    const positions = new Cesium.CallbackProperty(() => {
      const t = (performance.now() / 1000) * speed;
      const phase = ((t + i * 0.35) % 1.0);
      const pts = [];
      const segs = 16;
      for (let s = 0; s <= segs; s++) {
        const f = s / segs;
        // 沿风向推进，起点随 phase 循环滚动
        const d = -span / 2 + span * ((f * 0.42 + phase) % 1.0);
        // 屋面拱起：中间略抬高，模拟气流爬坡
        const bump = Math.cos((d / span) * Math.PI) * 1.8;
        pts.push(Cesium.Matrix4.multiplyByPoint(
          enu,
          new Cesium.Cartesian3(px + ux * d, py + uy * d, zJitter + bump),
          new Cesium.Cartesian3()));
      }
      return pts;
    }, false);

    entities.push(viewer.entities.add({
      id: `ch9_wind_${o.buildingId}_${i}`,
      polyline: {
        positions,
        width: 2.2,
        material: new Cesium.PolylineGlowMaterialProperty({
          glowPower: 0.28,
          taperPower: 0.55,
          color: Cesium.Color.fromCssColorString("#2E9CB8").withAlpha(0.85),
        }),
        arcType: Cesium.ArcType.NONE,
      },
    }));
  }
  return entities;
}

// ══════════════════════════════════════════════════════════════
// 5. L1 → L5 一镜到底镜头编排
// ══════════════════════════════════════════════════════════════
export const LAYER_LEVELS = {
  L1_GLOBAL:   { height: 20_000_000, pitch: -90 },
  L2_NATION:   { height:  4_200_000, pitch: -75 },
  L3_TRANSIT:  { height:    900_000, pitch: -60 },
  L4_REGION:   { height:     14_000, pitch: -48 },
  L5_BUILDING: { height:        620, pitch: -32 },  // ★ 绝不用 -90，垂直俯视会丧失 3D 感
};

export async function flyToLevel(viewer, level, target, opts = {}) {
  const cfg = LAYER_LEVELS[level];
  return new Promise((resolve) => {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        target.lon, target.lat, opts.height ?? cfg.height),
      orientation: {
        heading: Cesium.Math.toRadians(opts.heading ?? target.heading ?? 20),
        pitch: Cesium.Math.toRadians(opts.pitch ?? cfg.pitch),
        roll: 0,
      },
      duration: opts.duration ?? 4.0,
      easingFunction: Cesium.EasingFunction.QUADRATIC_IN_OUT,
      complete: resolve,
    });
  });
}

/**
 * 完整下潜剧本：宏观聚合点 → 区域影像+GEE → 单体三维
 */
export async function playDrilldown(viewer, ctx) {
  const { target, clusterDS, geeLayers, building } = ctx;

  // ── L1/L2：保留聚合点，环境压暗
  applyCinematicLighting(viewer);
  if (clusterDS) clusterDS.show = true;
  await flyToLevel(viewer, "L2_NATION", target, { duration: 2.6 });

  // ── L3：过境轨迹（如有）
  await flyToLevel(viewer, "L3_TRANSIT", target, { duration: 2.4 });

  // ── L4：区域影像 + GEE 图层（安全添加）
  await flyToLevel(viewer, "L4_REGION", target, { duration: 3.2, pitch: -48 });
  for (const [key, resp] of Object.entries(geeLayers ?? {})) {
    safeAddGeeLayer(viewer, key, resp);
  }

  // ── L5：隐藏宏观聚合点，显现单体三维
  if (clusterDS) clusterDS.show = false;
  await flyToLevel(viewer, "L5_BUILDING", target, { duration: 3.0, pitch: -32 });

  if (building) {
    addHeritageModel(viewer, building);
    if (building.anchors && building.anchorItems) {
      bindAnchorLabels(viewer, building);
    }
    if (building.wind) {
      addWindStreamlines(viewer, { ...building, ...building.wind });
    }
  }
}

// ══════════════════════════════════════════════════════════════
// 6. 场景清理
// ══════════════════════════════════════════════════════════════
export function clearCh9Scene(viewer) {
  const ids = [];
  viewer.entities.values.forEach((e) => {
    if (typeof e.id === "string" && e.id.startsWith("ch9_")) ids.push(e.id);
  });
  ids.forEach((id) => viewer.entities.removeById(id));
  for (const key of Array.from(_layerRegistry.keys())) removeGeeLayer(viewer, key);
}

// ══════════════════════════════════════════════════════════════
// 7. 使用示例
// ══════════════════════════════════════════════════════════════
/*
import anchors from "/assets/models/heritage_taimen_courtyard_anchors.json";

await playDrilldown(viewer, {
  target: { lon: 120.58108, lat: 30.00220, heading: 18 },
  clusterDS: heritagePointsDataSource,
  geeLayers: {
    deformation: await fetch("/api/layer?mode=ch9_heritage_deformation&location=shaoxing_yuecheng").then(r=>r.json()),
  },
  building: {
    buildingId: "SX-YC-ZP-08",
    name: "恒济台门",
    position: [120.58108, 30.00220, 0],
    modelKey: "taimen",
    heading: 18,
    scale: 1.0,
    riskLevel: "unstable",
    breathing: true,
    anchors: anchors.anchors_local_m,
    anchorItems: [
      { key: "正厅_屋脊",     label: "屋脊", value: "−3.70 kPa", level: "severe" },
      { key: "正厅_翼角_东南", label: "翼角", value: "−2.85 kPa", level: "moderate" },
      { key: "正厅_山墙_东",   label: "山墙", value: "+1.42 kPa", level: "watch" },
    ],
    // 风场（CH9-A 东阳卢宅场景才开）
    // wind: { windDirectionDeg: 120, span: 46, lines: 9, height: 13 },
  },
});
*/
