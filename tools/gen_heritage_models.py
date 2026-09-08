#!/usr/bin/env python3
"""
CH9 古建筑通用 3D 模型生成器
------------------------------------------------------------------
参数化生成中式传统建筑 glTF/GLB 模型，用于 Cesium L5 单体三维图层。
相比网上下载的随机模型，优势：
  · 无版权风险（本脚本原创生成）
  · 可绑定部位锚点（屋脊/檐口/翼角/山墙/柱脚），标签精确挂载
  · 多边形数可控（每个模型 < 20k 三角面，Cesium 流畅）
  · 可按「基本型 + 变体」批量派生，对应风载荷知识库的 40+ 基本型

坐标约定：建模用 Z-up（建筑惯例），导出 GLB 时由 trimesh 转 Y-up（glTF 规范）
单位：米
"""
import json
import os
import numpy as np
import trimesh

OUT = os.path.dirname(os.path.abspath(__file__))

# ── 配色（与展台海报同一套语义色）─────────────────────────
COL = {
    "platform": [196, 190, 178, 255],   # 台基 · 石灰白
    "wall":     [222, 216, 204, 255],   # 墙体 · 粉白
    "column":   [122, 58,  42,  255],   # 柱 · 朱红木色
    "beam":     [140, 76,  50,  255],   # 梁枋
    "roof":     [ 74, 82,  90,  255],   # 瓦面 · 青灰
    "ridge":    [ 48, 54,  60,  255],   # 正脊 · 深灰
    "door":     [104, 62,  44,  255],   # 门窗
}


def mat(name, rgba):
    return trimesh.visual.material.PBRMaterial(
        name=name,
        baseColorFactor=[c / 255.0 for c in rgba],
        metallicFactor=0.0,
        roughnessFactor=0.82,
    )


def box(cx, cy, z0, z1, sx, sy, rgba, name):
    m = trimesh.creation.box(extents=[sx, sy, z1 - z0])
    m.apply_translation([cx, cy, (z0 + z1) / 2])
    m.visual = trimesh.visual.TextureVisuals(material=mat(name, rgba))
    return m


def cyl(cx, cy, z0, z1, r, rgba, name, sections=10):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sections)
    m.apply_translation([cx, cy, (z0 + z1) / 2])
    m.visual = trimesh.visual.TextureVisuals(material=mat(name, rgba))
    return m


# ══════════════════════════════════════════════════════════════
# 屋顶：参数化中式曲面（举折 + 翼角起翘 + 出翘）
# ══════════════════════════════════════════════════════════════
def chinese_roof(W, D, z_eave, z_ridge, ridge_frac=0.55,
                 overhang=1.1, curve_p=0.62,
                 corner_lift=0.85, corner_flare=0.55,
                 nu=14, nv=22, hip=True):
    """
    W: 面阔(x)  D: 进深(y)  z_eave: 檐口高  z_ridge: 正脊高
    ridge_frac: 正脊长度占面阔比例（歇山/庑殿 < 1；硬山 = 1）
    curve_p: 举折指数 <1 → 近脊陡、近檐缓（中式屋面特征）
    corner_lift/flare: 翼角起翘高度 / 外飘量
    """
    hw, hd = W / 2.0, D / 2.0
    rw = hw * ridge_frac                       # 正脊半长
    ex, ey = hw + overhang, hd + overhang      # 檐口外沿

    def surf(u, v, sign_y):
        """u∈[0,1] 脊→檐；v∈[-1,1] 沿面阔"""
        # 沿面阔方向：脊端点随 u 从 ±rw 张开到 ±ex
        x_ridge = rw * v
        x_eave = ex * v
        x = x_ridge + (x_eave - x_ridge) * u
        # 进深方向
        y = sign_y * (0.0 + (ey - 0.0) * u)
        # 高度：举折曲线
        z = z_ridge - (z_ridge - z_eave) * (u ** curve_p)
        # 翼角：仅在两端 |v|>0.62 区间抬升与外飘，随 u² 增长
        t = max(0.0, (abs(v) - 0.62) / 0.38)
        k = (t ** 2) * (u ** 2)
        z += corner_lift * k
        x += np.sign(v) * corner_flare * k
        y += sign_y * corner_flare * k * 0.6
        return [x, y, z]

    verts, faces = [], []

    def add_patch(sign_y):
        nonlocal verts, faces
        base = len(verts)
        for i in range(nu + 1):
            for j in range(nv + 1):
                u = i / nu
                v = -1 + 2 * j / nv
                verts.append(surf(u, v, sign_y))
        for i in range(nu):
            for j in range(nv):
                a = base + i * (nv + 1) + j
                b = a + 1
                c = a + (nv + 1)
                d = c + 1
                if sign_y > 0:
                    faces += [[a, c, b], [b, c, d]]
                else:
                    faces += [[a, b, c], [b, d, c]]
        return base

    add_patch(+1)
    add_patch(-1)

    if hip:
        # 歇山/庑殿：两山面的坡（山花下的撒头）
        for sx in (+1, -1):
            base = len(verts)
            for i in range(nu + 1):
                for j in range(nv // 2 + 1):
                    u = i / nu
                    w = -1 + 2 * j / (nv // 2)          # 沿进深
                    x_r = sx * rw
                    x_e = sx * ex
                    x = x_r + (x_e - x_r) * u
                    y = w * (0.0 + (ey - 0.0) * u)
                    z = z_ridge - (z_ridge - z_eave) * (u ** curve_p)
                    t = 1.0
                    k = (t ** 2) * (u ** 2) * (abs(w) ** 2)
                    z += corner_lift * k * 0.9
                    verts.append([x, y, z])
            n2 = nv // 2
            for i in range(nu):
                for j in range(n2):
                    a = base + i * (n2 + 1) + j
                    b = a + 1
                    c = a + (n2 + 1)
                    d = c + 1
                    if sx > 0:
                        faces += [[a, b, c], [b, d, c]]
                    else:
                        faces += [[a, c, b], [b, c, d]]

    m = trimesh.Trimesh(vertices=np.array(verts, float),
                        faces=np.array(faces, int), process=False)
    m.visual = trimesh.visual.TextureVisuals(material=mat("roof", COL["roof"]))
    return m


def ridge_beam(W, z_ridge, ridge_frac=0.55, up=0.30):
    """正脊：略带上翘的细长体 + 两端鸱吻"""
    rw = W / 2.0 * ridge_frac
    n = 16
    pts = []
    for i in range(n + 1):
        t = -1 + 2 * i / n
        x = rw * t * 1.04
        z = z_ridge + 0.16 + up * (t ** 4)
        pts.append([x, z])
    verts, faces = [], []
    half = 0.16
    for i, (x, z) in enumerate(pts):
        verts += [[x, -half, z - 0.16], [x, half, z - 0.16],
                  [x, half, z + 0.16], [x, -half, z + 0.16]]
    for i in range(n):
        a = i * 4
        b = (i + 1) * 4
        for k in range(4):
            k2 = (k + 1) % 4
            faces += [[a + k, b + k, a + k2], [a + k2, b + k, b + k2]]
    m = trimesh.Trimesh(vertices=np.array(verts, float),
                        faces=np.array(faces, int), process=False)
    m.visual = trimesh.visual.TextureVisuals(material=mat("ridge", COL["ridge"]))
    parts = [m]
    for sx in (+1, -1):
        w = box(sx * rw * 1.06, 0, z_ridge + 0.16 + up, z_ridge + 0.16 + up + 0.55,
                0.34, 0.30, COL["ridge"], "ridge")
        parts.append(w)
    return parts


# ══════════════════════════════════════════════════════════════
# 单体：中式厅堂（歇山顶）
# ══════════════════════════════════════════════════════════════
def build_hall(W=16.0, D=10.0, name="hall", ox=0.0, oy=0.0,
               h_platform=0.55, h_column=4.2, h_eave=4.9, h_ridge=8.2,
               bays=5, ridge_frac=0.55, hip=True, overhang=1.1):
    parts, anchors = [], {}

    parts.append(box(ox, oy, 0, h_platform * 0.72, W + 1.5, D + 1.5, COL["platform"], "platform"))
    parts.append(box(ox, oy, h_platform * 0.72, h_platform, W + 0.9, D + 0.9,
                     COL["platform"], "platform"))

    z0 = h_platform
    parts.append(box(ox, oy, z0, z0 + h_column * 0.90, W - 2.6, D - 2.2, COL["wall"], "wall"))

    xs = np.linspace(-W / 2 + 0.9, W / 2 - 0.9, bays + 1)
    ys = [-D / 2 + 0.7, D / 2 - 0.7]
    for x in xs:
        for y in ys:
            parts.append(cyl(ox + x, oy + y, z0, z0 + h_column, 0.30, COL["column"], "column"))

    parts.append(box(ox, oy, z0 + h_column, z0 + h_column + 0.42,
                     W - 0.4, D - 0.4, COL["beam"], "beam"))

    for x in xs[1:-1]:
        parts.append(box(ox + x, oy - D / 2 + 0.68, z0, z0 + h_column * 0.78,
                         (W / bays) * 0.62, 0.14, COL["door"], "door"))

    roof = chinese_roof(W, D, h_eave + z0, h_ridge + z0,
                        ridge_frac=ridge_frac, overhang=overhang, hip=hip)
    roof.apply_translation([ox, oy, 0])
    parts.append(roof)

    for r in ridge_beam(W, h_ridge + z0, ridge_frac):
        r.apply_translation([ox, oy, 0])
        parts.append(r)

    rw = W / 2 * ridge_frac
    ex, ey = W / 2 + overhang, D / 2 + overhang
    anchors[f"{name}_屋脊"] = [ox, oy, h_ridge + z0 + 0.5]
    anchors[f"{name}_檐口"] = [ox, oy - ey, h_eave + z0]
    anchors[f"{name}_翼角_东南"] = [ox + ex + 0.5, oy - ey - 0.3, h_eave + z0 + 0.85]
    anchors[f"{name}_翼角_西南"] = [ox - ex - 0.5, oy - ey - 0.3, h_eave + z0 + 0.85]
    anchors[f"{name}_翼角_东北"] = [ox + ex + 0.5, oy + ey + 0.3, h_eave + z0 + 0.85]
    anchors[f"{name}_翼角_西北"] = [ox - ex - 0.5, oy + ey + 0.3, h_eave + z0 + 0.85]
    anchors[f"{name}_山墙_东"] = [ox + W / 2, oy, z0 + h_column * 0.6]
    anchors[f"{name}_山墙_西"] = [ox - W / 2, oy, z0 + h_column * 0.6]
    anchors[f"{name}_柱脚"] = [ox, oy, z0]
    anchors[f"{name}_台基"] = [ox, oy, h_platform]
    return parts, anchors


def wall_ring(W, D, h=2.6, t=0.45, ox=0.0, oy=0.0, gap_front=6.0):
    """院墙（南面留门洞）"""
    p = []
    p.append(box(ox, oy + D / 2, 0, h, W, t, COL["wall"], "wall"))
    for sx in (+1, -1):
        p.append(box(ox + sx * W / 2, oy, 0, h, t, D, COL["wall"], "wall"))
    seg = (W - gap_front) / 2
    for sx in (+1, -1):
        p.append(box(ox + sx * (gap_front / 2 + seg / 2), oy - D / 2, 0, h, seg, t,
                     COL["wall"], "wall"))
    return p


def export(parts, anchors, fname, title):
    scene = trimesh.Scene()
    for i, m in enumerate(parts):
        scene.add_geometry(m, node_name=f"part_{i:03d}")
    path = os.path.join(OUT, fname)
    scene.export(path)
    tris = sum(len(m.faces) for m in parts)
    b = scene.bounds
    size = (b[1] - b[0]).round(2).tolist()
    meta = {
        "file": fname,
        "title": title,
        "triangles": int(tris),
        "size_m": {"x_面阔": size[0], "y_进深": size[1], "z_总高": size[2]},
        "up_axis_modeling": "Z-up (建模)",
        "up_axis_gltf": "Y-up (glTF 规范, trimesh 自动转换)",
        "origin": "模型中心位于台基中心；Cesium 定位时用建筑几何中心经纬度",
        "anchors_local_m": {k: [round(x, 2) for x in v] for k, v in anchors.items()},
    }
    with open(os.path.join(OUT, fname.replace(".glb", "_anchors.json")), "w",
              encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"✅ {fname:36s} tris={tris:6d}  size={size}")
    return meta


# ══════════════════════════════════════════════════════════════
metas = []

# ① 通用厅堂（歇山顶）· 单体展示用
p, a = build_hall(W=16, D=10, name="厅堂")
metas.append(export(p, a, "heritage_hall_xieshan.glb", "通用中式厅堂 · 歇山顶"))

# ② 台门 / 三合院 · 恒济台门（绍兴形制：门楼 + 正厅 + 两厢 + 院墙）
p, a = [], {}
h, aa = build_hall(W=14, D=9, name="正厅", oy=6.5, h_ridge=7.6, ridge_frac=0.62)
p += h; a.update(aa)
for sx, tag in ((+1, "东厢"), (-1, "西厢")):
    h, aa = build_hall(W=8, D=6.5, name=tag, ox=sx * 9.5, oy=-1.0,
                       h_column=3.4, h_eave=4.0, h_ridge=6.0, bays=3,
                       ridge_frac=1.0, hip=False, overhang=0.85)
    p += h; a.update(aa)
h, aa = build_hall(W=9, D=5, name="门楼", oy=-9.5, h_column=3.6, h_eave=4.2,
                   h_ridge=6.6, bays=3, ridge_frac=0.60)
p += h; a.update(aa)
p += wall_ring(28, 26, h=2.8, oy=-1.0, gap_front=9.5)
metas.append(export(p, a, "heritage_taimen_courtyard.glb",
                    "台门 / 三合院 · 门楼+正厅+两厢+院墙（恒济台门形制）"))

# ③ 多进院落建筑群 · 卢宅形制（三进 + 廊）
p, a = [], {}
for i, (yy, w, d, hr, tag) in enumerate([
        (22.0, 20, 12, 9.4, "第一进"),
        (2.0, 18, 11, 8.8, "第二进"),
        (-18.0, 15, 9, 7.8, "第三进")]):
    h, aa = build_hall(W=w, D=d, name=tag, oy=yy, h_ridge=hr,
                       ridge_frac=0.55, bays=7 if i == 0 else 5)
    p += h; a.update(aa)
for sx in (+1, -1):
    for yy in (12.0, -8.0):
        h, aa = build_hall(W=6, D=8, name=f"廊{'东' if sx>0 else '西'}{int(yy)}",
                           ox=sx * 14.0, oy=yy, h_column=3.0, h_eave=3.6,
                           h_ridge=5.2, bays=2, ridge_frac=1.0, hip=False,
                           overhang=0.8)
        p += h; a.update(aa)
p += wall_ring(44, 62, h=3.2, oy=2.0, gap_front=12.0)
metas.append(export(p, a, "heritage_complex_multicourt.glb",
                    "多进院落建筑群 · 三进+厢廊（卢宅形制）"))

with open(os.path.join(OUT, "MODELS_MANIFEST.json"), "w", encoding="utf-8") as f:
    json.dump({"generator": "CH9 parametric heritage model generator",
               "license": "本脚本生成，无第三方版权",
               "models": metas}, f, ensure_ascii=False, indent=2)
print("\n📦 MODELS_MANIFEST.json 已写出")
