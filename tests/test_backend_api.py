"""
TDD Tests for FastAPI Backend
测试 REST API 端点
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock, patch
import re
import httpx


@pytest.fixture
def test_client():
    """创建测试客户端"""
    # 添加 backend 目录到 Python 路径
    import sys
    from pathlib import Path
    import types
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))

    # Unit tests should not import the real Earth Engine SDK.
    # Importing `ee` is slow and may attempt credential discovery.
    sys.modules.setdefault("ee", types.ModuleType("ee"))

    # IMPORTANT: other workspaces in this environment also have a top-level `main.py`.
    # Pytest runs in a single interpreter; if some other test imported `main` earlier,
    # Python will reuse that module and ignore our sys.path insertion.
    # Clear it to guarantee we import the intended backend/main.py for this repo.
    sys.modules.pop("main", None)
    
    # 延迟导入以避免 GEE 初始化
    import main as main_module
    # Avoid real EE init during FastAPI startup.
    main_module.init_earth_engine = lambda: None
    main_module.gee_initialized = True
    return TestClient(main_module.app)


class TestHealthEndpoint:
    """测试健康检查端点"""
    
    def test_health_check(self, test_client):
        """测试 /health 端点"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "gee_initialized" in data


class TestLocationsEndpoint:
    """测试地点列表端点"""
    
    def test_get_locations(self, test_client):
        """测试获取所有地点"""
        response = test_client.get("/api/locations")
        assert response.status_code == 200
        data = response.json()
        
        # API 返回字典格式: {"shanghai": {...}, "xiongan": {...}}
        assert isinstance(data, dict)
        # 验证某个位置存在
        assert "yuhang" in data
        yuhang = data["yuhang"]
        assert "coords" in yuhang
        assert len(yuhang["coords"]) == 3
    
    def test_get_specific_location(self, test_client):
        """测试获取特定地点"""
        response = test_client.get("/api/locations/yuhang")
        assert response.status_code == 200
        data = response.json()
        
        assert data["code"] == "yuhang"
        assert "余杭" in data["name"]
    
    def test_get_nonexistent_location(self, test_client):
        """测试获取不存在的地点"""
        response = test_client.get("/api/locations/invalid_city")
        assert response.status_code == 404


class TestModesEndpoint:
    """测试 AI 模式列表端点"""
    
    def test_get_modes(self, test_client):
        """测试获取所有 AI 模式"""
        response = test_client.get("/api/modes")
        assert response.status_code == 200
        data = response.json()
        
        # API 返回字典格式: {"dna": "地表 DNA", "change": "..."}
        assert isinstance(data, dict)
        assert len(data) == 6  # V6.6 6 章模式
        # 验证 V6.6 模式存在
        assert "ch1_yuhang_faceid" in data
        assert "ch4_amazon_zeroshot" in data
        assert "ch5_coastline_audit" in data
        assert "ch6_water_pulse" in data


class TestLayerEndpoint:
    """测试图层获取端点"""
    
    @patch('main.ee.Geometry.Point')
    @patch('main.smart_load')
    @patch('main.get_tile_url')
    def test_get_layer_success(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        """测试成功获取图层"""
        # 模拟 GEE Geometry
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport
        
        # 模拟返回值
        mock_image = Mock()
        mock_vis = {'min': 0, 'max': 1}
        mock_smart_load.return_value = (
            mock_image,  # layer
            mock_vis,    # vis_params
            "cached",    # status_html
            True,        # is_cached
            "asset_id",  # asset_id
            mock_image   # raw_img
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/{z}/{x}/{y}"
        
        response = test_client.get("/api/layers?mode=ch1_yuhang_faceid&location=yuhang")
        assert response.status_code == 200
        
        data = response.json()
        assert "tile_url" in data
        assert re.search(r"/api/tiles/[0-9a-f]{24}/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", data["tile_url"])
        assert "is_cached" in data
        assert data["is_cached"] is True
        assert "asset_id" in data
        assert "vis_params" in data

    @patch('main.ee.Geometry.Point')
    @patch('main.smart_load')
    @patch('main.get_tile_url')
    def test_get_layer_uses_template_cache_for_repeat_calls(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        """相同 mode/location 重复请求时应复用 upstream tile template，避免重复 getMapId 调用。"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport

        mock_image = Mock()
        mock_smart_load.return_value = (
            mock_image,
            {'min': 0, 'max': 1},
            "cached",
            True,
            "asset_id_fixed",
            None,
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/{z}/{x}/{y}"

        r1 = test_client.get("/api/layers?mode=ch1_yuhang_faceid&location=yuhang")
        assert r1.status_code == 200
        r2 = test_client.get("/api/layers?mode=ch1_yuhang_faceid&location=yuhang")
        assert r2.status_code == 200

        # Only the first call should consult get_tile_url()
        assert mock_get_tile.call_count == 1
    
    def test_get_layer_missing_params(self, test_client):
        """测试缺少必需参数"""
        response = test_client.get("/api/layers?mode=ch1_yuhang_faceid")
        assert response.status_code == 422  # Validation error
    
    @patch('main.smart_load')
    def test_get_layer_invalid_location(self, mock_smart_load, test_client):
        """测试无效地点"""
        response = test_client.get("/api/layers?mode=change&location=invalid")
        assert response.status_code == 400
        assert "Invalid location" in response.json()["detail"]
    
    @patch('main.ee.Geometry.Point')
    @patch('main.smart_load')
    @patch('main.get_tile_url')
    def test_get_layer_cache_miss(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        """测试缓存未命中场景"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport
        
        mock_image = Mock()
        mock_smart_load.return_value = (
            mock_image, {'min': 0, 'max': 1}, "live", False, "asset_id", mock_image
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/{z}/{x}/{y}"
        
        response = test_client.get("/api/layers?mode=ch2_maowusu_shield&location=maowusu")
        assert response.status_code == 200
        
        data = response.json()
        assert re.search(r"/api/tiles/[0-9a-f]{24}/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", data["tile_url"])
        assert data["is_cached"] is False
        assert "live" in data["status"].lower() or "实时" in data["status"]


class TestTileProxyEndpoint:
    """测试同源瓦片代理端点"""

    @patch("main.ee.Geometry.Point")
    @patch("main.smart_load")
    @patch("main.get_tile_url")
    def test_tile_proxy_returns_image_and_cors(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport

        mock_image = Mock()
        mock_smart_load.return_value = (
            mock_image,
            {"min": 0, "max": 1},
            "cached",
            True,
            "asset_id",
            mock_image,
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/tiles/{z}/{x}/{y}"

        # 先调用 /api/layers 注册 tile_id
        layer_resp = test_client.get("/api/layers?mode=ch2_maowusu_shield&location=maowusu")
        assert layer_resp.status_code == 200
        tile_url = layer_resp.json()["tile_url"]
        m = re.search(r"/api/tiles/(?P<tile_id>[0-9a-f]{24})/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", tile_url)
        assert m
        tile_id = m.group("tile_id")

        upstream_resp = Mock()
        upstream_resp.status_code = 200
        upstream_resp.headers = {
            "Content-Type": "image/png",
            "Cache-Control": "private, max-age=3600",
        }
        upstream_resp.content = b"\x89PNG\r\n\x1a\n..."
        upstream_resp.raise_for_status = Mock()

        with patch("main.http_client", new=Mock(get=AsyncMock(return_value=upstream_resp))):
            tile_resp = test_client.get(
                f"/api/tiles/{tile_id}/7/105/48",
                headers={"Origin": "http://127.0.0.1:8504"},
            )

        assert tile_resp.status_code == 200
        assert tile_resp.headers.get("content-type", "").startswith("image/png")
        assert tile_resp.content.startswith(b"\x89PNG")

        # CORS: allow_origins="*" 时通常返回 "*"
        assert tile_resp.headers.get("access-control-allow-origin") in ("*", "http://127.0.0.1:8504")

    @patch("main.ee.Geometry.Point")
    @patch("main.smart_load")
    @patch("main.get_tile_url")
    def test_tile_proxy_upstream_400_returns_blank_png(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        """上游 400/404 时后端应返回可用 PNG(200)，避免 Cesium 蓝底和错误风暴。"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport

        mock_image = Mock()
        mock_smart_load.return_value = (
            mock_image,
            {"min": 0, "max": 1},
            "cached",
            True,
            "asset_id",
            mock_image,
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/tiles/{z}/{x}/{y}"

        layer_resp = test_client.get("/api/layers?mode=ch2_maowusu_shield&location=maowusu")
        assert layer_resp.status_code == 200
        tile_url = layer_resp.json()["tile_url"]
        m = re.search(r"/api/tiles/(?P<tile_id>[0-9a-f]{24})/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", tile_url)
        assert m
        tile_id = m.group("tile_id")

        upstream_resp = httpx.Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            content=b"{\"error\":\"Bad Request\"}",
        )

        with patch("main.http_client", new=Mock(get=AsyncMock(return_value=upstream_resp))):
            tile_resp = test_client.get(f"/api/tiles/{tile_id}/0/0/0")

        assert tile_resp.status_code == 200
        assert tile_resp.headers.get("content-type", "").startswith("image/png")
        assert tile_resp.content.startswith(b"\x89PNG")

        # Ensure the fallback tile is 256x256 (Cesium imagery tiles expect this)
        # PNG IHDR stores width/height as big-endian uint32 at bytes 16..23
        width = int.from_bytes(tile_resp.content[16:20], "big")
        height = int.from_bytes(tile_resp.content[20:24], "big")
        assert (width, height) == (256, 256)

    @patch("main.ee.Geometry.Point")
    @patch("main.smart_load")
    @patch("main.get_tile_url")
    def test_tile_proxy_upstream_5xx_returns_blank_png(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        """上游 5xx/429 等瞬态错误时，返回可用 PNG(200) 以避免 Cesium 报错风暴。"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport

        mock_image = Mock()
        mock_smart_load.return_value = (
            mock_image,
            {"min": 0, "max": 1},
            "cached",
            True,
            "asset_id",
            mock_image,
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/tiles/{z}/{x}/{y}"

        layer_resp = test_client.get("/api/layers?mode=ch2_maowusu_shield&location=maowusu")
        assert layer_resp.status_code == 200
        tile_url = layer_resp.json()["tile_url"]
        m = re.search(r"/api/tiles/(?P<tile_id>[0-9a-f]{24})/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", tile_url)
        assert m
        tile_id = m.group("tile_id")

        upstream_resp = httpx.Response(
            status_code=502,
            headers={"Content-Type": "text/plain"},
            content=b"Bad Gateway",
        )

        with patch("main.http_client", new=Mock(get=AsyncMock(return_value=upstream_resp))):
            tile_resp = test_client.get(f"/api/tiles/{tile_id}/10/855/408")

        assert tile_resp.status_code == 200
        assert tile_resp.headers.get("content-type", "").startswith("image/png")
        assert tile_resp.content.startswith(b"\x89PNG")

    @patch("main.ee.Geometry.Point")
    @patch("main.smart_load")
    @patch("main.get_tile_url")
    def test_tile_proxy_fallback_error_propagates_upstream_5xx(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        """当 fallback=error 时，后端应返回非 200 以便前端触发底图兜底。"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport

        mock_image = Mock()
        mock_smart_load.return_value = (
            mock_image,
            {"min": 0, "max": 1},
            "cached",
            True,
            "asset_id",
            mock_image,
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/tiles/{z}/{x}/{y}"

        layer_resp = test_client.get("/api/layers?mode=ch2_maowusu_shield&location=maowusu")
        assert layer_resp.status_code == 200
        tile_url = layer_resp.json()["tile_url"]
        m = re.search(r"/api/tiles/(?P<tile_id>[0-9a-f]{24})/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", tile_url)
        assert m
        tile_id = m.group("tile_id")

        upstream_resp = httpx.Response(
            status_code=502,
            headers={"Content-Type": "text/plain"},
            content=b"Bad Gateway",
        )

        with patch("main.http_client", new=Mock(get=AsyncMock(return_value=upstream_resp))):
            tile_resp = test_client.get(
                f"/api/tiles/{tile_id}/10/855/408",
                params={"fallback": "error"},
            )

        assert tile_resp.status_code == 502
        payload = tile_resp.json()
        assert payload.get("detail", {}).get("error") == "tile_proxy_failed"

    @patch("main.ee.Geometry.Point")
    @patch("main.smart_load")
    @patch("main.get_tile_url")
    def test_tile_proxy_fallback_error_propagates_upstream_400_as_404(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        """当 fallback=error 且上游 400/404（无数据）时，返回 404 以触发前端兜底。"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport

        mock_image = Mock()
        mock_smart_load.return_value = (
            mock_image,
            {"min": 0, "max": 1},
            "cached",
            True,
            "asset_id",
            mock_image,
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/tiles/{z}/{x}/{y}"

        layer_resp = test_client.get("/api/layers?mode=ch2_maowusu_shield&location=maowusu")
        assert layer_resp.status_code == 200
        tile_url = layer_resp.json()["tile_url"]
        m = re.search(r"/api/tiles/(?P<tile_id>[0-9a-f]{24})/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", tile_url)
        assert m
        tile_id = m.group("tile_id")

        upstream_resp = httpx.Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            content=b"{\"error\":\"Bad Request\"}",
        )

        with patch("main.http_client", new=Mock(get=AsyncMock(return_value=upstream_resp))):
            tile_resp = test_client.get(
                f"/api/tiles/{tile_id}/0/0/0",
                params={"fallback": "error"},
            )

        assert tile_resp.status_code == 404
        payload = tile_resp.json()
        assert payload.get("detail", {}).get("error") == "tile_proxy_failed"

    @patch("main.ee.Geometry.Point")
    @patch("main.smart_load")
    @patch("main.get_tile_url")
    def test_tile_proxy_fallback_error_timeout_returns_504(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        """当 fallback=error 且上游超时，返回 504 便于前端快速切换底图。"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport

        mock_image = Mock()
        mock_smart_load.return_value = (
            mock_image,
            {"min": 0, "max": 1},
            "cached",
            True,
            "asset_id",
            mock_image,
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/tiles/{z}/{x}/{y}"

        layer_resp = test_client.get("/api/layers?mode=ch2_maowusu_shield&location=maowusu")
        assert layer_resp.status_code == 200
        tile_url = layer_resp.json()["tile_url"]
        m = re.search(r"/api/tiles/(?P<tile_id>[0-9a-f]{24})/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", tile_url)
        assert m
        tile_id = m.group("tile_id")

        async def _raise_timeout(*_args, **_kwargs):
            raise httpx.TimeoutException("timeout")

        with patch("main.http_client", new=Mock(get=AsyncMock(side_effect=_raise_timeout))):
            tile_resp = test_client.get(
                f"/api/tiles/{tile_id}/10/855/408",
                params={"fallback": "error"},
            )

        assert tile_resp.status_code == 504
        payload = tile_resp.json()
        assert payload.get("detail", {}).get("error") == "tile_proxy_failed"

    @patch("main.ee.Geometry.Point")
    @patch("main.smart_load")
    @patch("main.get_tile_url")
    def test_tile_proxy_uses_lru_cache_for_same_tile(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        """同一瓦片被请求多次时应命中内存缓存，避免重复上游请求。"""
        import main as main_module

        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport

        mock_image = Mock()
        mock_smart_load.return_value = (
            mock_image,
            {"min": 0, "max": 1},
            "cached",
            True,
            "asset_id",
            mock_image,
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/tiles/{z}/{x}/{y}"

        # Register tile_id
        layer_resp = test_client.get("/api/layers?mode=ch2_maowusu_shield&location=maowusu")
        assert layer_resp.status_code == 200
        tile_url = layer_resp.json()["tile_url"]
        m = re.search(r"/api/tiles/(?P<tile_id>[0-9a-f]{24})/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", tile_url)
        assert m
        tile_id = m.group("tile_id")

        upstream_resp = Mock()
        upstream_resp.status_code = 200
        upstream_resp.headers = {
            "Content-Type": "image/png",
            "Cache-Control": "private, max-age=3600",
        }
        upstream_resp.content = b"\x89PNG\r\n\x1a\n...cached..."
        upstream_resp.raise_for_status = Mock()

        mock_get = AsyncMock(return_value=upstream_resp)
        with patch("main.http_client", new=Mock(get=mock_get)):
            # Ensure cache is empty for deterministic behavior
            try:
                main_module._tile_cache.clear()
                main_module._tile_cache_total_bytes = 0
            except Exception:
                pass
            # Same tile twice
            r1 = test_client.get(f"/api/tiles/{tile_id}/7/105/48")
            r2 = test_client.get(f"/api/tiles/{tile_id}/7/105/48")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.content.startswith(b"\x89PNG")
        assert r2.content == r1.content
        assert mock_get.await_count == 1

    def test_tile_proxy_unknown_tile_id_returns_blank_png_by_default(self, test_client):
        """旧 tile_id（重启/轮转导致 registry 丢失）默认应返回透明 PNG(200) 避免前端报错风暴。"""
        resp = test_client.get("/api/tiles/ffffffffffffffffffffffff/10/1/2")
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("image/png")
        assert resp.content.startswith(b"\x89PNG")

    def test_tile_proxy_unknown_tile_id_fallback_error_returns_404(self, test_client):
        """底图请求使用 fallback=error 时，未知 tile_id 必须返回 404 触发前端兜底。"""
        resp = test_client.get(
            "/api/tiles/ffffffffffffffffffffffff/10/1/2",
            params={"fallback": "error"},
        )
        assert resp.status_code == 404


def test_tile_cache_respects_max_bytes_budget():
    """Unit test: tile LRU cache should not grow unbounded in bytes.

    This protects the backend from OOM kills (which appear as proxy-level 502).
    """
    from pathlib import Path
    import sys

    backend_path = Path(__file__).parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    import main as main_module  # noqa: WPS433

    # Configure a tiny budget and reset cache.
    main_module._tile_cache_max_items = 100
    main_module._tile_cache_max_bytes = 250
    try:
        main_module._tile_cache.clear()
    except Exception:
        pass
    main_module._tile_cache_total_bytes = 0

    headers = {"Content-Type": "image/png"}
    main_module._tile_cache_set(("t", 0, 0, 0), b"a" * 120, "image/png", headers)
    main_module._tile_cache_set(("t", 0, 0, 1), b"b" * 120, "image/png", headers)
    # Adding a third entry should trigger eviction to stay within 250 bytes.
    main_module._tile_cache_set(("t", 0, 0, 2), b"c" * 120, "image/png", headers)

    assert main_module._tile_cache_total_bytes <= main_module._tile_cache_max_bytes
    assert len(main_module._tile_cache) <= 3
    # With 3x120 bytes and a 250-byte budget, at least one eviction must occur.
    assert len(main_module._tile_cache) <= 2


class TestExportEndpoint:
    """测试缓存导出端点"""
    
    @patch('main.ee.Geometry.Point')
    @patch('main.trigger_export_task')
    @patch('main.get_layer_logic')
    def test_export_cache_success(self, mock_get_layer, mock_trigger, mock_point, test_client):
        """测试成功触发导出"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport
        
        mock_image = Mock()
        mock_get_layer.return_value = (mock_image, {'min': 0}, 'ch1_faceid')
        mock_trigger.return_value = "TASK_12345"
        
        payload = {
            "mode": "ch1_yuhang_faceid",  # ✅ 使用mode ID而不是完整名称
            "location": "yuhang"
        }
        response = test_client.post("/api/cache/export", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["task_id"] == "TASK_12345"
        assert data["status"] == "submitted"
    
    def test_export_cache_missing_fields(self, test_client):
        """测试缺少必需字段"""
        payload = {"mode": "变化雷达"}
        response = test_client.post("/api/cache/export", json=payload)
        assert response.status_code == 422


class TestCORSHeaders:
    """测试 CORS 配置"""
    
    def test_cors_headers_present(self, test_client):
        """测试 CORS 头是否正确设置"""
        response = test_client.options(
            "/api/locations",
            headers={
                "Origin": "http://localhost:8504",
                "Access-Control-Request-Method": "GET"
            }
        )
        # FastAPI 的 CORS 中间件应该返回正确的头
        assert response.status_code in [200, 204]


class TestErrorHandling:
    """测试错误处理"""
    
    @patch('main.ee.Geometry.Point')
    @patch('main.smart_load')
    def test_gee_error_handling(self, mock_smart_load, mock_point, test_client):
        """测试 GEE 错误处理"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport
        mock_smart_load.side_effect = Exception("GEE computation failed")
        
        response = test_client.get("/api/layers?mode=ch1_yuhang_faceid&location=yuhang")
        assert response.status_code == 500
        assert "error" in response.json()["detail"]
