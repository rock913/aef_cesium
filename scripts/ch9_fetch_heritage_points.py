#!/usr/bin/env python3
"""
CH9 古建筑保护 · 真实开放数据管线（路线一 · 零审批）

从以下开放数据源抓取真实古建/遗产点位，写入 `data/ch9_heritage_points.json`：
  - Wikidata SPARQL：
      · 全国重点文物保护单位 (wdt:P1435 wd:Q1188574)  → china / level=national
      · 联合国教科文组织世界遗产 (wdt:P1435 wd:Q9259)   → global / level=world_heritage
  - OpenStreetMap Overpass：
      · 东阳卢宅 / 绍兴越城 / 山西平遥 三个靶场 bbox 的
        historic=* / heritage=* / building=temple|shrine|pagoda → local / level=unknown

产出的 JSON 为「离线缓存」，demo 现场不依赖网络。可随时重跑刷新。

用法： python3 scripts/ch9_fetch_heritage_points.py
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
OVERPASS = "https://overpass-api.de/api/interpreter"

# 三个 CH9 靶场 bbox（south, west, north, east）
LOCAL_BBOX = {
    "dongyang_luzhai": (29.24, 120.20, 29.33, 120.29),
    "shaoxing_yuecheng": (29.95, 120.53, 30.05, 120.63),
    "shanxi_pingyao": (37.15, 112.12, 37.25, 112.23),
}

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ch9_heritage_points.json")

UA = {"User-Agent": "AlphaEarth-CH9-heritage/1.0 (demo sandbox; contact: dev@example.org)"}


def _http_json(url, *, headers=None, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _sparql(query):
    """Run a SPARQL query and return the JSON bindings."""
    url = WIKIDATA_SPARQL + "?" + urllib.parse.urlencode(
        {"query": query, "format": "json"}
    )
    req = urllib.request.Request(url, headers={**UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_wkt_point(wkt):
    """Parse 'Point(120.5 30.0)' → (lon, lat)."""
    if not wkt:
        return None
    inner = wkt.strip()
    if inner.startswith("Point("):
        inner = inner[6:-1]
    parts = inner.split()
    if len(parts) != 2:
        return None
    try:
        lon, lat = float(parts[0]), float(parts[1])
    except ValueError:
        return None
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return None
    return lon, lat


def fetch_guobao():
    """全国重点文物保护单位（国家级）。"""
    items = []
    offset = 0
    while True:
        q = (
            "SELECT ?item ?itemLabel ?coord WHERE {"
            "  ?item wdt:P1435 wd:Q1188574 ; wdt:P625 ?coord ."
            '  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }'
            "} LIMIT 1000 OFFSET %d" % offset
        )
        bindings = _sparql(q)["results"]["bindings"]
        if not bindings:
            break
        for r in bindings:
            pt = _parse_wkt_point(r.get("coord", {}).get("value"))
            if not pt:
                continue
            item_id = r["item"]["value"].rsplit("/", 1)[-1]
            items.append({
                "id": "wd-" + item_id,
                "name": r.get("itemLabel", {}).get("value") or item_id,
                "lon": pt[0],
                "lat": pt[1],
                "type": "guobao",
                "source": "wikidata",
                "level": "national",
            })
        offset += 1000
        if len(bindings) < 1000:
            break
    return items


def fetch_world_heritage():
    """联合国教科文组织世界遗产（全球）。"""
    items = []
    offset = 0
    while True:
        q = (
            "SELECT ?item ?itemLabel ?countryLabel ?coord WHERE {"
            "  ?item wdt:P1435 wd:Q9259 ; wdt:P625 ?coord ."
            "  OPTIONAL { ?item wdt:P17 ?country . }"
            '  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }'
            "} LIMIT 1000 OFFSET %d" % offset
        )
        bindings = _sparql(q)["results"]["bindings"]
        if not bindings:
            break
        for r in bindings:
            pt = _parse_wkt_point(r.get("coord", {}).get("value"))
            if not pt:
                continue
            item_id = r["item"]["value"].rsplit("/", 1)[-1]
            items.append({
                "id": "wd-" + item_id,
                "name": r.get("itemLabel", {}).get("value") or item_id,
                "lon": pt[0],
                "lat": pt[1],
                "type": "world_heritage",
                "source": "wikidata",
                "level": "world_heritage",
                "country": r.get("countryLabel", {}).get("value"),
            })
        offset += 1000
        if len(bindings) < 1000:
            break
    return items


def fetch_osm_local():
    """三个 CH9 靶场的 OSM 历史/遗产/宗教建筑点位。"""
    out = {}
    for loc, (s, w, n, e) in LOCAL_BBOX.items():
        ql = (
            "[out:json][timeout:30];"
            "("
            'node["historic"]({s},{w},{n},{e});way["historic"]({s},{w},{n},{e});'
            'node["heritage"]({s},{w},{n},{e});way["heritage"]({s},{w},{n},{e});'
            'node["building"~"temple|shrine|pagoda"]({s},{w},{n},{e});'
            'way["building"~"temple|shrine|pagoda"]({s},{w},{n},{e});'
            ");out center 500;"
        ).format(s=s, w=w, n=n, e=e)
        headers = {**UA, "Accept": "application/json"}
        data = None
        for attempt in range(3):
            try:
                data = _http_json(OVERPASS, headers=headers, data=urllib.parse.urlencode({"data": ql}).encode())
                break
            except Exception as exc:
                print(f"  ⚠️ OSM {loc} attempt {attempt + 1} failed: {exc}")
                time.sleep(3 * (attempt + 1))
        if data is None:
            out[loc] = []
            continue
        pts = []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            lon = el.get("lon") or (el.get("center", {}) or {}).get("lon")
            lat = el.get("lat") or (el.get("center", {}) or {}).get("lat")
            if lon is None or lat is None:
                continue
            name = tags.get("name") or tags.get("name:zh") or tags.get("historic") or tags.get("heritage") or "未命名"
            htype = tags.get("historic") or tags.get("heritage") or tags.get("building") or "historic"
            pts.append({
                "id": "osm-%s-%s" % (el.get("type"), el.get("id")),
                "name": name,
                "lon": float(lon),
                "lat": float(lat),
                "type": htype,
                "source": "osm",
                "level": "unknown",
            })
        out[loc] = pts
    return out


def main():
    print("🚀 CH9 真实开放数据管线启动")
    guobao = []
    wh = []
    osm = {}
    try:
        guobao = fetch_guobao()
        print(f"  ✅ Wikidata 国保: {len(guobao)}")
    except Exception as e:
        print(f"  ❌ Wikidata 国保 failed: {e}")
    try:
        wh = fetch_world_heritage()
        print(f"  ✅ Wikidata 世界遗产: {len(wh)}")
    except Exception as e:
        print(f"  ❌ Wikidata 世界遗产 failed: {e}")
    try:
        osm = fetch_osm_local()
        print("  ✅ OSM 靶场点位:", {k: len(v) for k, v in osm.items()})
    except Exception as e:
        print(f"  ❌ OSM failed: {e}")

    # WH-China 子集并入 china（世界遗产中文标签）
    wh_china = [w for w in wh if w.get("country") == "中国"]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "wikidata_guobao": len(guobao),
            "wikidata_world_heritage": len(wh),
            "wikidata_world_heritage_china": len(wh_china),
            "osm_local": {k: len(v) for k, v in osm.items()},
        },
        "global": wh,
        "china": guobao + wh_china,
        "local": osm,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"✅ 写入 {OUT_PATH} （global={len(wh)}, china={len(guobao)+len(wh_china)}）")


if __name__ == "__main__":
    sys.exit(main())
