"""API Correctness Tests - 测试 API 返回的正确性

注意：本文件中的测试会真实访问本机后端服务 (127.0.0.1:8503)，并可能触发真实 GEE 计算。
因此它们属于“集成/端到端测试”，默认应跳过，避免在纯单元测试/TDD 阶段阻塞开发。

运行方式：
    RUN_INTEGRATION_TESTS=1 pytest -q tests/test_api_correctness.py
"""
import pytest
import requests
import time
import os
from pathlib import Path
import sys


backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


BASE_URL = "http://127.0.0.1:8505"


def _integration_enabled() -> bool:
    return os.getenv("RUN_INTEGRATION_TESTS", "0") == "1"


def _backend_available() -> bool:
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=1)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _integration_enabled(),
    reason="Integration tests are disabled by default (set RUN_INTEGRATION_TESTS=1)",
)


@pytest.fixture(autouse=True)
def _skip_if_backend_down():
    if not _backend_available():
        pytest.skip("Backend is not running on 127.0.0.1:8505")


class TestAPIEndpoints:
    """测试 API 端点"""
    
    def test_health_endpoint_responds_quickly(self):
        """测试：健康检查端点应该快速响应"""
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed < 1.0, f"健康检查应该在 1 秒内响应，实际: {elapsed:.2f}s"
        
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_locations_endpoint_returns_all_locations(self):
        """测试：locations 端点应该返回所有位置"""
        response = requests.get(f"{BASE_URL}/api/locations", timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        
        # 🔧 修复：现在返回的是字典而不是列表
        # 格式: {"xiongan": {...}, "shanghai": {...}, ...}
        assert isinstance(data, dict), f"应该返回字典，实际: {type(data)}"
        
        # 应该至少有几个位置
        assert len(data) >= 3, f"应该至少有 3 个位置，实际: {len(data)}"
        
        # 每个位置都应该有正确的结构
        for location_code, location in data.items():
            assert "coords" in location, f"位置 {location_code} 应该有 coords"
            assert "name" in location
            assert "coords" in location
            
            # coords 应该是 [lat, lon, zoom]
            assert len(location["coords"]) == 3
            
            # 验证数据类型
            lat, lon, zoom = location["coords"]
            assert isinstance(lat, (int, float))
            assert isinstance(lon, (int, float))
            assert isinstance(zoom, int)
    
    def test_modes_endpoint_returns_all_modes(self):
        """测试：modes 端点应该返回所有模式"""
        response = requests.get(f"{BASE_URL}/api/modes", timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        
        # 应该是字典: {"dna": "地表 DNA", ...}
        assert isinstance(data, dict)
        
        # 应该有4个模式
        assert len(data) >= 6, f"应该至少有6个模式，实际: {len(data)}"

        # 验证必须包含的模式ID
        required_modes = [
            "ch1_yuhang_faceid",
            "ch2_maowusu_shield",
            "ch3_zhoukou_pulse",
            "ch4_amazon_zeroshot",
            "ch5_coastline_audit",
            "ch6_water_pulse",
        ]
        for mode_id in required_modes:
            assert mode_id in data, f"缺少模式: {mode_id}"
            # 名称应该包含中文
            assert any('\u4e00' <= c <= '\u9fff' for c in data[mode_id])
    
    def test_layers_endpoint_validates_parameters(self):
        """测试：layers 端点应该验证参数"""
        # 缺少 mode 参数
        response = requests.get(
            f"{BASE_URL}/api/layers",
            params={"location": "xiongan"},
            timeout=10
        )
        assert response.status_code == 422  # Validation error
        
        # 缺少 location 参数
        response = requests.get(
            f"{BASE_URL}/api/layers",
            params={"mode": "dna"},
            timeout=10
        )
        assert response.status_code == 422  # Validation error
        
        # 无效的 mode
        response = requests.get(
            f"{BASE_URL}/api/layers",
            params={"mode": "invalid", "location": "xiongan"},
            timeout=10
        )
        assert response.status_code == 400  # Bad request
        
        # 无效的 location
        response = requests.get(
            f"{BASE_URL}/api/layers",
            params={"mode": "dna", "location": "invalid"},
            timeout=10
        )
        assert response.status_code == 400  # Bad request


class TestLayersEndpoint:
    """测试 layers 端点的详细行为"""
    
    @pytest.mark.parametrize(
        "mode",
        [
            "ch1_yuhang_faceid",
            "ch2_maowusu_shield",
            "ch3_zhoukou_pulse",
            "ch4_amazon_zeroshot",
            "ch5_coastline_audit",
            "ch6_water_pulse",
        ],
    )
    def test_all_modes_return_valid_data(self, mode):
        """测试：所有模式都应该返回有效数据"""
        response = requests.get(
            f"{BASE_URL}/api/layers",
            params={"mode": mode, "location": "yuhang"},
            timeout=30
        )
        
        assert response.status_code == 200, \
            f"{mode} 模式返回错误状态码: {response.status_code}\n响应: {response.text}"
        
        data = response.json()
        
        # 应该有必需的字段
        assert "tile_url" in data, f"{mode} 模式缺少 tile_url"
        assert "bounds" in data, f"{mode} 模式缺少 bounds"
        assert "mode" in data, f"{mode} 模式缺少 mode"
        
        # mode 应该匹配请求的模式
        assert data["mode"] == mode, \
            f"返回的模式 ({data['mode']}) 不匹配请求的模式 ({mode})"
        
        # tile_url 应该是有效的 URL
        assert data["tile_url"].startswith("http"), \
            f"{mode} 模式的 tile_url 不是有效的 HTTP URL"
        
        # bounds 应该是 4 个数字的列表
        assert len(data["bounds"]) == 4, \
            f"{mode} 模式的 bounds 应该有 4 个元素"
        
        for bound in data["bounds"]:
            assert isinstance(bound, (int, float)), \
                f"{mode} 模式的 bounds 应该是数字"
    
    def test_different_locations_return_different_bounds(self):
        """测试：不同位置应该返回不同的边界"""
        locations = ["yuhang", "amazon"]
        bounds_list = []
        
        for location in locations:
            response = requests.get(
                f"{BASE_URL}/api/layers",
                params={"mode": "ch2_talatan_carbon", "location": location},
                timeout=30
            )
            
            assert response.status_code == 200
            data = response.json()
            bounds_list.append(tuple(data["bounds"]))
        
        # 不同位置的 bounds 应该不同
        assert bounds_list[0] != bounds_list[1], \
            "不同位置应该有不同的边界"
    
    def test_tile_url_contains_required_parameters(self):
        """测试：tile URL 应该包含必需的参数"""
        response = requests.get(
            f"{BASE_URL}/api/layers",
            params={"mode": "ch2_talatan_carbon", "location": "yuhang"},
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        tile_url = data["tile_url"]
        
        # tile_url 可能是 GEE 上游地址，也可能是后端同源代理地址
        assert tile_url.startswith("http"), "tile_url 应该是 HTTP URL"
        
        # 应该包含 {x}, {z}，以及 {y} 或 {reverseY} 占位符
        assert "{z}" in tile_url and "{x}" in tile_url
        assert ("{y}" in tile_url) or ("{reverseY}" in tile_url)


class TestPerformance:
    """测试性能相关的问题"""
    
    def test_concurrent_requests_dont_crash(self):
        """测试：并发请求不应该导致崩溃"""
        import concurrent.futures
        
        def make_request(mode):
            try:
                response = requests.get(
                    f"{BASE_URL}/api/layers",
                    params={"mode": mode, "location": "yuhang"},
                    timeout=30
                )
                return response.status_code == 200
            except Exception as e:
                print(f"Request failed: {e}")
                return False
        
        # 并发发送 4 个请求（每个模式一个）
        modes = [
            "ch1_yuhang_faceid",
            "ch2_talatan_carbon",
            "ch3_aral_rescue",
            "ch4_amazon_zeroshot",
        ]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(make_request, modes))
        
        # 所有请求都应该成功
        assert all(results), f"并发请求失败，成功: {sum(results)}/{len(results)}"
    
    def test_response_time_is_acceptable(self):
        """测试：响应时间应该在可接受范围内"""
        # 第一次请求可能较慢（GEE 计算）
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/layers",
            params={"mode": "change", "location": "xiongan"},
            timeout=60
        )
        first_request_time = time.time() - start_time
        
        assert response.status_code == 200
        
        # 第一次请求应该在 60 秒内完成
        assert first_request_time < 60, \
            f"首次请求耗时过长: {first_request_time:.2f}s"
        
        print(f"首次请求耗时: {first_request_time:.2f}s")


class TestErrorHandling:
    """测试错误处理"""
    
    def test_invalid_mode_returns_clear_error(self):
        """测试：无效的模式应该返回清晰的错误"""
        response = requests.get(
            f"{BASE_URL}/api/layers",
            params={"mode": "invalid_mode", "location": "xiongan"},
            timeout=10
        )
        
        assert response.status_code == 400
        data = response.json()
        
        # 应该有 detail 字段说明错误
        assert "detail" in data
        assert "mode" in data["detail"].lower() or "模式" in data["detail"]
    
    def test_invalid_location_returns_clear_error(self):
        """测试：无效的位置应该返回清晰的错误"""
        response = requests.get(
            f"{BASE_URL}/api/layers",
            params={"mode": "dna", "location": "invalid_location"},
            timeout=10
        )
        
        assert response.status_code == 400
        data = response.json()
        
        # 应该有 detail 字段说明错误
        assert "detail" in data
        assert "location" in data["detail"].lower() or "位置" in data["detail"]
