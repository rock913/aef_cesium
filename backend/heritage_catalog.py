"""
CH9 古建筑天地一体预防性保护 · 单体档案目录（演示沙箱轨，纯 Python，不依赖 GEE）

数据真实性口径（对齐 PRD §10 双轨机制）：
- 真实：`data/` 物料（FEA 风载荷云图、病害标注照片与多边形）与五层档案结构本身。
- 仿真：InSAR 形变五指标、风载薄弱点、AEF 候选概率均为确定性演示数据，
  明确以 `data_track: "demo_sandbox"` 角标，输出为相对风险排序而非结构安全鉴定。
"""

# data/ 真实物料文件名（由 /api/heritage/assets/{filename} 提供同源访问）
DISEASE_IMAGE = "072500002AAaa.jpg"
DISEASE_ANNOTATION = "072500002AAaa.json"
FEA_PANORAMA = "FEA云图_全景.png"
FEA_WEAKPOINTS = "FEA云图_薄弱点标注.png"

import json
from pathlib import Path

_POINTS_CACHE = None


def _load_points_json():
    """加载真实开放数据点位缓存（data/ch9_heritage_points.json）。"""
    global _POINTS_CACHE
    if _POINTS_CACHE is not None:
        return _POINTS_CACHE
    candidates = [
        Path("/app/data/ch9_heritage_points.json"),
        Path("/mnt/data/hyf/aef_cesium/data/ch9_heritage_points.json"),
        Path("data/ch9_heritage_points.json"),
    ]
    for p in candidates:
        if p.exists():
            try:
                _POINTS_CACHE = json.loads(p.read_text(encoding="utf-8"))
                return _POINTS_CACHE
            except Exception:
                pass
    return None


def heritage_points(scope: str = "china", location: str = None):
    """返回真实开放数据点位（scope: global|china|local）。

    - global: 联合国教科文组织世界遗产（Wikidata）
    - china:  全国重点文物保护单位（Wikidata）+ 世界遗产（中国）
    - local:  三个 CH9 靶场的 OSM historic/heritage/temple 点位
    """
    data = _load_points_json()
    if not data:
        return {"status": "success", "scope": scope, "count": 0,
                "points": [], "sources": {}, "data_track": "real_open_data"}

    if scope == "global":
        points = data.get("global", [])
    elif scope == "local":
        points = data.get("local", {}).get(location or "", [])
    else:
        points = data.get("china", [])

    return {
        "status": "success",
        "scope": scope,
        "location": location,
        "count": len(points),
        "points": points,
        "sources": data.get("sources", {}),
        "generated_at": data.get("generated_at"),
        "data_track": "real_open_data",
    }

_DISCLAIMER = (
    "LOS 向相对形变；输出为相对风险排序，非结构安全鉴定结论。"
    "形变/风载/AEF 候选为演示仿真数据，真实值需由实际管线回填。"
)

_L3_COMMON = {
    "source": "Sentinel-1 SBAS-InSAR",
    "stack": "2023-01 ~ 2026-08",
    "direction": "LOS",
    "note": "相对参考点；非绝对垂直沉降",
    "data_track": "demo_sandbox",
}


def _l3(v_max, v_diff, beta_ratio, angular_distortion, risk_score, risk_level,
         temporal_cluster, ps_count=0, coherence_mean=0.0, skew=0.0):
    return {
        **_L3_COMMON,
        "ps_count": ps_count,
        "coherence_mean": coherence_mean,
        "v_max_mm_yr": v_max,
        "v_diff_mm_yr": v_diff,
        "angular_distortion": angular_distortion,
        "beta_ratio": beta_ratio,
        "skew": skew,
        "temporal_cluster": temporal_cluster,
        "risk_score": risk_score,
        "risk_level": risk_level,
    }


def _l4(ledger_id, defect_type, rule, polygons):
    return {
        "source": "古建病害视觉语义数据集",
        "model": {"name": "YOLO + 文润VLM", "accuracy": 0.87, "latency_s": 2.0},
        "ledger_id": ledger_id,
        "image": DISEASE_IMAGE,
        "annotation": DISEASE_ANNOTATION,
        "surveys": [
            {
                "date": "2025-08-21",
                "part": "木构架",
                "defects": [
                    {
                        "type": defect_type,
                        "rule": rule,
                        "level": "Ⅱ",
                        "polygons": polygons,
                    }
                ],
            }
        ],
    }


# 病害标注多边形（像素坐标，取自 data/072500002AAaa.json 真实标注）
_DEFECT_POLYGONS = [
    [[1890, 1756], [3448, 629], [3448, 922], [2025, 1921]],
    [[0, 79], [2353, 882], [2246, 986], [0, 251]],
]
_DEFECT_TYPE = "木构件开裂"
_DEFECT_RULE = "木材表面出现可见裂缝（劈裂、贯穿性裂缝、纵向劈开、榫头断裂），裂缝深度和宽度可辨识"


def _l5(basic_type_id, weak_points, material_correction=True):
    return {
        "source": "风载荷结构响应知识库（预计算）",
        "basic_type_id": basic_type_id,
        "variant_id": f"{basic_type_id}-V1",
        "wind_levels": [9, 13],
        "fea_panorama": FEA_PANORAMA,
        "fea_weakpoints": FEA_WEAKPOINTS,
        "weak_points": weak_points,
        "material_correction": {
            "applied": material_correction,
            "source": "L4_defect",
            "note": "依据实测病害等级下调构件强度参数",
        },
    }


BUILDINGS = {
    # ═══════════ 绍兴越城（CH9-B 形变体检）═══════════
    "SX-YC-ZP-08": {
        "building_id": "SX-YC-ZP-08",
        "name": "恒济台门",
        "admin": {"province": "浙江", "city": "绍兴", "district": "越城区"},
        "protection_level": "市保（待核定）",
        "era": "清",
        "structure": "砖木混合 · 多进院落 · 共用山墙",
        "centroid": [120.5810, 30.0023],
        "location": "shaoxing_yuecheng",
        "layers": {
            "L1_satellite": {"source": "三体计算星座", "resolution_m": 0.3, "acquired": "2026-09-XX", "data_track": "待接入"},
            "L2_semantic": {"source": "AEF Satellite Embedding V1", "dim": 64, "year": 2024, "label": "明清木构聚落", "confidence": 0.92},
            "L3_deformation": _l3(-12.3, 4.8, "1/280", 0.003571, 17, "unstable", "accelerating", ps_count=14, coherence_mean=0.82),
            "L4_defect": _l4("ZP-08", _DEFECT_TYPE, _DEFECT_RULE, _DEFECT_POLYGONS),
            "L5_structural": _l5("JH-TM-03", [
                {"part": "屋脊", "rank": 1, "level": "severe"},
                {"part": "檐口", "rank": 2, "level": "moderate"},
                {"part": "翼角", "rank": 3, "level": "moderate"},
                {"part": "山墙", "rank": 4, "level": "minor"},
            ]),
        },
        "fusion": {
            "coupled_risk_level": "Ⅲ（优先处置）",
            "evidence_chain": [
                "L3 角变形 1/280 超过 1/300 关注线",
                "L4 同期记录墙体竖向开裂 Ⅱ 级 → 与形变互证",
                "L5 风载工况下屋脊为一级薄弱点 → 风险等级上调",
            ],
            "recommendation": "优先安排现场核查，复核基础差异沉降与墙体开裂关联",
        },
    },
    "SX-YC-LX-01": {
        "building_id": "SX-YC-LX-01",
        "name": "鲁迅故里 · 三味书屋",
        "admin": {"province": "浙江", "city": "绍兴", "district": "越城区"},
        "protection_level": "国保",
        "era": "清",
        "structure": "砖木混合",
        "centroid": [120.5760, 30.0060],
        "location": "shaoxing_yuecheng",
        "layers": {
            "L1_satellite": {"source": "三体计算星座", "resolution_m": 0.3, "acquired": "2026-09-XX", "data_track": "待接入"},
            "L2_semantic": {"source": "AEF Satellite Embedding V1", "dim": 64, "year": 2024, "label": "江南台门聚落", "confidence": 0.88},
            "L3_deformation": _l3(-7.8, 3.1, "1/520", 0.001923, 12, "moderate", "linear", ps_count=11, coherence_mean=0.80),
            "L4_defect": _l4("LX-01", _DEFECT_TYPE, _DEFECT_RULE, _DEFECT_POLYGONS),
            "L5_structural": _l5("JH-TM-01", [
                {"part": "檐口", "rank": 1, "level": "moderate"},
                {"part": "屋脊", "rank": 2, "level": "minor"},
            ]),
        },
        "fusion": {
            "coupled_risk_level": "Ⅱ（建议核查）",
            "evidence_chain": [
                "L3 最大沉降速率 -7.8 mm/yr，接近关注区间",
                "L4 病害台账存在木构件开裂记录",
            ],
            "recommendation": "纳入年度体检重点清单，加密一轮形变复测",
        },
    },
    "SX-YC-GH-02": {
        "building_id": "SX-YC-GH-02",
        "name": "大运河遗产点 · 八字桥",
        "admin": {"province": "浙江", "city": "绍兴", "district": "越城区"},
        "protection_level": "国保（大运河）",
        "era": "南宋",
        "structure": "石构桥梁",
        "centroid": [120.5860, 29.9980],
        "location": "shaoxing_yuecheng",
        "layers": {
            "L1_satellite": {"source": "三体计算星座", "resolution_m": 0.3, "acquired": "2026-09-XX", "data_track": "待接入"},
            "L2_semantic": {"source": "AEF Satellite Embedding V1", "dim": 64, "year": 2024, "label": "河网石构遗产", "confidence": 0.85},
            "L3_deformation": _l3(-5.1, 2.2, "1/720", 0.001389, 10, "moderate", "linear", ps_count=9, coherence_mean=0.78),
            "L4_defect": _l4("GH-02", _DEFECT_TYPE, _DEFECT_RULE, _DEFECT_POLYGONS),
            "L5_structural": _l5("JH-Q-01", [
                {"part": "桥台", "rank": 1, "level": "moderate"},
                {"part": "拱券", "rank": 2, "level": "minor"},
            ]),
        },
        "fusion": {
            "coupled_risk_level": "Ⅱ（建议核查）",
            "evidence_chain": ["L3 沿河水位波动引起的差异沉降需关注", "L4 桥台出现细微裂缝记录"],
            "recommendation": "关注河网水位季节波动对桥台基础的长期影响",
        },
    },
    "SX-YC-SM-03": {
        "building_id": "SX-YC-SM-03",
        "name": "书圣故里 · 戒珠寺",
        "admin": {"province": "浙江", "city": "绍兴", "district": "越城区"},
        "protection_level": "省保",
        "era": "明",
        "structure": "砖木混合",
        "centroid": [120.5720, 29.9960],
        "location": "shaoxing_yuecheng",
        "layers": {
            "L1_satellite": {"source": "三体计算星座", "resolution_m": 0.3, "acquired": "2026-09-XX", "data_track": "待接入"},
            "L2_semantic": {"source": "AEF Satellite Embedding V1", "dim": 64, "year": 2024, "label": "江南寺观聚落", "confidence": 0.82},
            "L3_deformation": _l3(-3.4, 1.5, "1/1050", 0.000952, 7, "stable", "converging", ps_count=8, coherence_mean=0.79),
            "L4_defect": _l4("SM-03", _DEFECT_TYPE, _DEFECT_RULE, _DEFECT_POLYGONS),
            "L5_structural": _l5("JH-TM-02", [
                {"part": "翼角", "rank": 1, "level": "minor"},
            ]),
        },
        "fusion": {
            "coupled_risk_level": "Ⅰ（常规监测）",
            "evidence_chain": ["L3 角变形处于稳定线内", "L4 病害等级为 Ⅱ 级但无加速迹象"],
            "recommendation": "维持年度常规遥感监测与季度巡查",
        },
    },
    "SX-YC-CJ-04": {
        "building_id": "SX-YC-CJ-04",
        "name": "仓桥直街 · 台门院落",
        "admin": {"province": "浙江", "city": "绍兴", "district": "越城区"},
        "protection_level": "未定级",
        "era": "清",
        "structure": "砖木混合 · 多进院落",
        "centroid": [120.5900, 30.0080],
        "location": "shaoxing_yuecheng",
        "layers": {
            "L1_satellite": {"source": "三体计算星座", "resolution_m": 0.3, "acquired": "2026-09-XX", "data_track": "待接入"},
            "L2_semantic": {"source": "AEF Satellite Embedding V1", "dim": 64, "year": 2024, "label": "江南台门聚落", "confidence": 0.80},
            "L3_deformation": _l3(-2.1, 0.9, "1/1600", 0.000625, 6, "stable", "linear", ps_count=6, coherence_mean=0.77),
            "L4_defect": _l4("CJ-04", _DEFECT_TYPE, _DEFECT_RULE, _DEFECT_POLYGONS),
            "L5_structural": _l5("JH-TM-02", [
                {"part": "山墙", "rank": 1, "level": "minor"},
            ]),
        },
        "fusion": {
            "coupled_risk_level": "Ⅰ（常规监测）",
            "evidence_chain": ["L3 形变微弱", "L4 无显著病害记录"],
            "recommendation": "纳入普查台账，维持常规巡查",
        },
    },
    "SX-YC-WM-07": {
        "building_id": "SX-YC-WM-07",
        "name": "王阳明故居",
        "admin": {"province": "浙江", "city": "绍兴", "district": "越城区"},
        "protection_level": "省保",
        "era": "明",
        "structure": "砖木混合",
        "centroid": [120.5670, 30.0110],
        "location": "shaoxing_yuecheng",
        "layers": {
            "L1_satellite": {"source": "三体计算星座", "resolution_m": 0.3, "acquired": "2026-09-XX", "data_track": "待接入"},
            "L2_semantic": {"source": "AEF Satellite Embedding V1", "dim": 64, "year": 2024, "label": "江南宅第聚落", "confidence": 0.86},
            "L3_deformation": _l3(0.8, 1.1, "1/2400", 0.000417, 5, "stable", "seasonal", ps_count=10, coherence_mean=0.84),
            "L4_defect": _l4("WM-07", _DEFECT_TYPE, _DEFECT_RULE, _DEFECT_POLYGONS),
            "L5_structural": _l5("JH-TM-01", [
                {"part": "屋脊", "rank": 1, "level": "minor"},
            ]),
        },
        "fusion": {
            "coupled_risk_level": "Ⅰ（常规监测）",
            "evidence_chain": ["L3 为稳定硬地参考区，轻微季节性弹性波动", "L4 无加速病害"],
            "recommendation": "作为越城区稳定参考点，维持季度巡查",
        },
    },

    # ═══════════ 东阳卢宅（CH9-A 风载靶场）═══════════
    "JH-DY-LZ-001": {
        "building_id": "JH-DY-LZ-001",
        "name": "卢宅建筑群",
        "admin": {"province": "浙江", "city": "金华东阳", "district": "东阳"},
        "protection_level": "国保",
        "era": "明 · 清",
        "structure": "木构 · 抬梁式/穿斗式混合 · 硬山/歇山 · 小青瓦",
        "centroid": [120.2410, 29.2832],
        "location": "dongyang_luzhai",
        "layers": {
            "L1_satellite": {"source": "三体计算星座", "resolution_m": 0.3, "acquired": "2026-09-XX", "data_track": "待接入"},
            "L2_semantic": {"source": "AEF Satellite Embedding V1", "dim": 64, "year": 2024, "label": "江南木构建筑群", "confidence": 0.90},
            "L3_deformation": _l3(-0.6, 0.5, "1/4800", 0.000208, 5, "stable", "linear", ps_count=12, coherence_mean=0.85),
            "L4_defect": _l4("LZ-001", _DEFECT_TYPE, _DEFECT_RULE, _DEFECT_POLYGONS),
            "L5_structural": _l5("JH-MC-07", [
                {"part": "屋脊", "rank": 1, "level": "severe"},
                {"part": "檐口", "rank": 2, "level": "severe"},
                {"part": "翼角", "rank": 3, "level": "moderate"},
                {"part": "山墙", "rank": 4, "level": "moderate"},
            ]),
        },
        "fusion": {
            "coupled_risk_level": "Ⅲ（优先处置）",
            "evidence_chain": [
                "台风过境 48h 窗口内屋脊/檐口为一级风吸薄弱点",
                "L4 材质劣化参数下调屋面构件抗风强度",
                "L3 基础稳定，风险主要来自地上风载而非形变",
            ],
            "recommendation": "灾前加固屋面瓦件与翼角，重点巡查屋脊/檐口负压区",
        },
    },
    "JH-DY-LZ-002": {
        "building_id": "JH-DY-LZ-002",
        "name": "肃雍堂",
        "admin": {"province": "浙江", "city": "金华东阳", "district": "东阳"},
        "protection_level": "国保",
        "era": "明",
        "structure": "木构 · 抬梁式 · 歇山 · 小青瓦",
        "centroid": [120.2440, 29.2810],
        "location": "dongyang_luzhai",
        "layers": {
            "L1_satellite": {"source": "三体计算星座", "resolution_m": 0.3, "acquired": "2026-09-24", "data_track": "待接入"},
            "L2_semantic": {"source": "AEF Satellite Embedding V1", "dim": 64, "year": 2024, "label": "江南木构建筑群", "confidence": 0.89},
            "L3_deformation": _l3(-0.5, 0.4, "1/5200", 0.000192, 5, "stable", "linear", ps_count=10, coherence_mean=0.86),
            "L4_defect": _l4("LZ-002", _DEFECT_TYPE, _DEFECT_RULE, _DEFECT_POLYGONS),
            "L5_structural": _l5("JH-MC-06", [
                {"part": "檐口", "rank": 1, "level": "severe"},
                {"part": "翼角", "rank": 2, "level": "moderate"},
                {"part": "屋脊", "rank": 3, "level": "moderate"},
            ]),
        },
        "fusion": {
            "coupled_risk_level": "Ⅱ（重点核查）",
            "evidence_chain": ["檐口为一级风吸薄弱点", "基础稳定，无显著形变放大"],
            "recommendation": "灾前重点核查檐口瓦件与翼角起翘部位",
        },
    },

    # ═══════════ 山西平遥（CH9-C 跨省泛化候选）═══════════
    "PY-CAND-001": {
        "building_id": "PY-CAND-001",
        "name": "平遥古城东郊 · 候选古建聚落 A",
        "admin": {"province": "山西", "city": "晋中", "district": "平遥"},
        "protection_level": "未定级（候选线索）",
        "era": "待核实",
        "structure": "砖木（待核实）",
        "centroid": [112.1750, 37.2010],
        "location": "shanxi_pingyao",
        "is_candidate": True,
        "layers": {
            "L1_satellite": {"source": "三体计算星座", "resolution_m": 0.3, "acquired": "2026-09-XX", "data_track": "待接入"},
            "L2_semantic": {"source": "AEF Satellite Embedding V1", "dim": 64, "year": 2024, "label": "晋中砖木聚落", "confidence": 0.91},
            "L3_deformation": _l3(-1.2, 0.8, "1/2900", 0.000345, 6, "stable", "linear", ps_count=7, coherence_mean=0.80),
            "L4_defect": None,
            "L5_structural": None,
        },
        "fusion": {
            "coupled_risk_level": "候选线索（待实地核实）",
            "evidence_chain": ["AEF 语义嵌入与浙江古建正样本高相似", "名录之外的新候选聚落"],
            "recommendation": "转文物部门实地核实，不作为认定结论",
        },
    },
    "PY-CAND-002": {
        "building_id": "PY-CAND-002",
        "name": "平遥古城南郊 · 候选古建聚落 B",
        "admin": {"province": "山西", "city": "晋中", "district": "平遥"},
        "protection_level": "未定级（候选线索）",
        "era": "待核实",
        "structure": "砖木（待核实）",
        "centroid": [112.1600, 37.2060],
        "location": "shanxi_pingyao",
        "is_candidate": True,
        "layers": {
            "L1_satellite": {"source": "三体计算星座", "resolution_m": 0.3, "acquired": "2026-09-XX", "data_track": "待接入"},
            "L2_semantic": {"source": "AEF Satellite Embedding V1", "dim": 64, "year": 2024, "label": "晋中砖木聚落", "confidence": 0.84},
            "L3_deformation": _l3(-0.9, 0.6, "1/3100", 0.000323, 5, "stable", "linear", ps_count=6, coherence_mean=0.79),
            "L4_defect": None,
            "L5_structural": None,
        },
        "fusion": {
            "coupled_risk_level": "候选线索（待实地核实）",
            "evidence_chain": ["AEF 语义嵌入高相似候选", "需排除新建仿古建筑误报"],
            "recommendation": "转文物部门实地核实，重点排除仿古建筑",
        },
    },
    "PY-CAND-003": {
        "building_id": "PY-CAND-003",
        "name": "平遥古城西北 · 候选古建聚落 C",
        "admin": {"province": "山西", "city": "晋中", "district": "平遥"},
        "protection_level": "未定级（候选线索）",
        "era": "待核实",
        "structure": "砖木（待核实）",
        "centroid": [112.1880, 37.1950],
        "location": "shanxi_pingyao",
        "is_candidate": True,
        "layers": {
            "L1_satellite": {"source": "三体计算星座", "resolution_m": 0.3, "acquired": "2026-09-XX", "data_track": "待接入"},
            "L2_semantic": {"source": "AEF Satellite Embedding V1", "dim": 64, "year": 2024, "label": "晋中砖木聚落", "confidence": 0.78},
            "L3_deformation": _l3(-1.0, 0.7, "1/3000", 0.000333, 6, "stable", "linear", ps_count=5, coherence_mean=0.78),
            "L4_defect": None,
            "L5_structural": None,
        },
        "fusion": {
            "coupled_risk_level": "候选线索（待实地核实）",
            "evidence_chain": ["AEF 语义嵌入中等相似候选"],
            "recommendation": "转文物部门实地核实",
        },
    },
}


def list_buildings():
    """返回全部建筑（按目录顺序）。"""
    return list(BUILDINGS.values())


def get_buildings(location: str):
    """返回指定地点的建筑清单摘要（不含五层全量字段）。"""
    items = []
    for b in BUILDINGS.values():
        if b.get("location") != location:
            continue
        l3 = b.get("layers", {}).get("L3_deformation") or {}
        fusion = b.get("fusion", {}) or {}
        items.append({
            "building_id": b["building_id"],
            "name": b["name"],
            "centroid": b["centroid"],
            "protection_level": b.get("protection_level", ""),
            "risk_level": l3.get("risk_level", "data_insufficient"),
            "coupled_risk_level": fusion.get("coupled_risk_level", ""),
            "is_candidate": bool(b.get("is_candidate", False)),
        })
    return items


def get_building(building_id: str):
    """返回单体五层档案全量；不存在返回 None。"""
    b = BUILDINGS.get(building_id)
    if not b:
        return None
    out = dict(b)
    out["disclaimer"] = _DISCLAIMER
    out["data_track"] = "demo_sandbox"
    return out


# 用于 /api/heritage/wind_assessment 的确定性查表（按基本型）
_WIND_LOOKUP = {
    "JH-MC-07": {
        "dominant_direction_deg": 120,
        "max_wind_level": 12,
        "weak_components": [
            {"part": "屋脊", "rank": 1, "level": "severe", "cumulative_probability": 0.72},
            {"part": "檐口", "rank": 2, "level": "severe", "cumulative_probability": 0.66},
            {"part": "翼角", "rank": 3, "level": "moderate", "cumulative_probability": 0.48},
            {"part": "山墙", "rank": 4, "level": "moderate", "cumulative_probability": 0.37},
        ],
        "pre_disaster_checklist": [
            "加固屋面瓦件与望板连接",
            "复核翼角起翘部位灰浆约束",
            "清理檐口天沟防止积水增重",
        ],
        "measures": ["灾前 24h 加密巡查屋脊/檐口", "对高危瓦件做临时压重或拆移"],
    },
    "JH-MC-06": {
        "dominant_direction_deg": 120,
        "max_wind_level": 12,
        "weak_components": [
            {"part": "檐口", "rank": 1, "level": "severe", "cumulative_probability": 0.64},
            {"part": "翼角", "rank": 2, "level": "moderate", "cumulative_probability": 0.45},
            {"part": "屋脊", "rank": 3, "level": "moderate", "cumulative_probability": 0.39},
        ],
        "pre_disaster_checklist": [
            "核查檐口瓦件与翼角起翘部位",
            "加固屋面边缘部位",
        ],
        "measures": ["灾前重点巡查檐口/翼角", "对松动瓦件做临时加固"],
    },
}


def wind_assessment(building_ids, typhoon=None):
    """确定性风载研判（演示沙箱轨），返回 PRD §8.3 结构。"""
    typhoon = typhoon or {}
    results = []
    for bid in building_ids:
        b = BUILDINGS.get(bid)
        if not b:
            results.append({"building_id": bid, "error": "unknown_building"})
            continue
        l5 = b.get("layers", {}).get("L5_structural") or {}
        key = l5.get("basic_type_id", "JH-MC-07")
        lookup = _WIND_LOOKUP.get(key, _WIND_LOOKUP["JH-MC-07"])
        results.append({
            "building_id": bid,
            "name": b["name"],
            "risk_level": "Ⅲ" if any(w["level"] == "severe" for w in lookup["weak_components"]) else "Ⅱ",
            "dominant_direction_deg": lookup["dominant_direction_deg"],
            "max_wind_level": lookup["max_wind_level"],
            "weak_components": lookup["weak_components"],
            "pre_disaster_checklist": lookup["pre_disaster_checklist"],
            "measures": lookup["measures"],
        })
    return {
        "assessment_id": "CH9-WIND-DEMO",
        "typhoon": typhoon,
        "window": {"start": "T-72h", "end": "T-0h"},
        "buildings": results,
        "review": {"required": True, "reviewer_role": "古建院专家"},
        "disclaimer": _DISCLAIMER,
        "data_track": "demo_sandbox",
    }


# 风载场景（CH9-A 卢宅）：确定性风场流线 + FEA 薄弱点锚标
_PART_OFFSET = {
    "屋脊": (0.0, 0.0005, 24.0),    # (dlon, dlat, height_m)
    "檐口": (0.0007, -0.0002, 12.0),
    "翼角": (-0.0005, 0.0005, 18.0),
    "山墙": (0.0, -0.0005, 14.0),
}
_PRESSURE_BY_RANK = {1: -3.697, 2: -2.415, 3: -1.986, 4: -1.204}


def wind_scene(location: str):
    """返回 CH9-A 卢宅风载场景的确定性风场流线与 FEA 薄弱点锚标（演示沙箱轨）。"""
    if location != "dongyang_luzhai":
        return {"trails": [], "anchors": []}

    trails = [
        {"id": "trail-1", "points": [[120.2360, 29.2850, 70], [120.2470, 29.2828, 70]], "speed": 5.0},
        {"id": "trail-2", "points": [[120.2355, 29.2842, 55], [120.2465, 29.2820, 55]], "speed": 4.2},
        {"id": "trail-3", "points": [[120.2362, 29.2834, 40], [120.2472, 29.2812, 40]], "speed": 3.6},
        {"id": "trail-4", "points": [[120.2368, 29.2826, 26], [120.2478, 29.2804, 26]], "speed": 3.0},
    ]

    anchors = []
    for bid in ("JH-DY-LZ-001", "JH-DY-LZ-002"):
        b = BUILDINGS.get(bid)
        if not b:
            continue
        l5 = b.get("layers", {}).get("L5_structural") or {}
        for wp in l5.get("weak_points", []):
            part = wp.get("part", "")
            dlon, dlat, h = _PART_OFFSET.get(part, (0.0, 0.0003, 16.0))
            lon = b["centroid"][0] + dlon
            lat = b["centroid"][1] + dlat
            pressure = _PRESSURE_BY_RANK.get(wp.get("rank"), -2.0)
            note = ("极易掀揭" if wp.get("level") == "severe"
                    else ("风吸薄弱" if wp.get("level") == "moderate" else "一般关注"))
            anchors.append({
                "building_id": bid,
                "part": part,
                "lon": round(lon, 6),
                "lat": round(lat, 6),
                "height": h,
                "pressure_kpa": pressure,
                "level": wp.get("level"),
                "note": note,
            })

    return {"trails": trails, "anchors": anchors}
