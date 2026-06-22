"""
API 端到端集成测试
验证所有 AI 模式在实际环境中的工作情况
"""
import requests
import time
import pytest
import os


BASE_URL = "http://127.0.0.1:8503"
BASE_URL = "http://127.0.0.1:8505"


def _integration_enabled() -> bool:
    return os.getenv("RUN_INTEGRATION_TESTS", "0") == "1"


pytestmark = pytest.mark.skipif(
    not _integration_enabled(),
    reason="Integration tests are disabled by default (set RUN_INTEGRATION_TESTS=1)",
)


def wait_for_backend(timeout=10):
    """等待后端服务启动"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"{BASE_URL}/api/modes", timeout=2)
            if response.status_code == 200:
                return True
        except:
            time.sleep(0.5)
    return False


@pytest.fixture(scope="module", autouse=True)
def ensure_backend_running():
    """确保后端服务运行"""
    if not wait_for_backend():
        pytest.skip("后端服务未运行，跳过集成测试")


def test_modes_endpoint():
    """测试模式列表端点"""
    response = requests.get(f"{BASE_URL}/api/modes")
    assert response.status_code == 200
    
    data = response.json()
    # API 现在返回字典: {"dna": "地表 DNA (语义视图)", ...}
    assert isinstance(data, dict)
    assert len(data) >= 6

    # V6.6 chapter mode keys should exist
    assert "ch1_yuhang_faceid" in data
    assert "ch2_maowusu_shield" in data
    assert "ch3_zhoukou_pulse" in data
    assert "ch4_amazon_zeroshot" in data
    assert "ch5_coastline_audit" in data
    assert "ch6_water_pulse" in data


def test_locations_endpoint():
    """测试位置列表端点"""
    response = requests.get(f"{BASE_URL}/api/locations")
    assert response.status_code == 200
    
    data = response.json()
    # API 现在返回字典: {"xiongan": {...}, ...}
    assert isinstance(data, dict)
    assert len(data) > 0

    # 验证余杭位置存在
    assert "yuhang" in data
    assert len(data["yuhang"]["coords"]) == 3


@pytest.mark.parametrize("mode,location", [
    ("ch1_yuhang_faceid", "yuhang"),
    ("ch2_maowusu_shield", "maowusu"),
    ("ch3_zhoukou_pulse", "zhoukou"),
    ("ch4_amazon_zeroshot", "amazon"),
    ("ch5_coastline_audit", "yancheng"),
    ("ch6_water_pulse", "poyang"),
])
def test_ai_mode_layers(mode, location):
    """测试所有 AI 模式的图层生成"""
    response = requests.get(
        f"{BASE_URL}/api/layers",
        params={"mode": mode, "location": location},
        timeout=30  # GEE 计算可能需要时间
    )
    
    # 断言响应成功
    assert response.status_code == 200, f"{mode} 模式返回错误: {response.status_code}"
    
    data = response.json()
    
    # 验证返回数据结构
    assert "tile_url" in data, f"{mode} 模式缺少 tile_url"
    assert "mode" in data
    assert data["mode"] == mode
    assert "bounds" in data  # 边界框
    assert "location" in data  # 位置信息
    
    # 验证 tile_url 格式
    # tile_url 可能是 GEE 上游地址，也可能是后端同源代理地址
    assert data["tile_url"].startswith("http")
    assert "{x}" in data["tile_url"]
    assert ("{y}" in data["tile_url"]) or ("{reverseY}" in data["tile_url"])
    assert "{z}" in data["tile_url"]


def test_dna_mode_specific():
    """专门测试第一章（余杭）模式"""
    response = requests.get(
        f"{BASE_URL}/api/layers",
        params={"mode": "ch1_yuhang_faceid", "location": "yuhang"},
        timeout=30
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # DNA 模式应该返回 RGB 可视化
    assert "tile_url" in data
    assert data["mode"] == "ch1_yuhang_faceid"


def test_change_mode_specific():
    """专门测试变化雷达模式"""
    response = requests.get(
        f"{BASE_URL}/api/layers",
        params={"mode": "change", "location": "xiongan"},
        timeout=30
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # 变化雷达应该计算 2019-2024 差异
    assert "tile_url" in data
    assert data["mode"] == "change"


def test_intensity_mode_specific():
    """专门测试建设强度模式"""
    response = requests.get(
        f"{BASE_URL}/api/layers",
        params={"mode": "intensity", "location": "xiongan"},
        timeout=30
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "tile_url" in data
    assert data["mode"] == "intensity"


def test_eco_mode_specific():
    """专门测试生态韧性模式"""
    response = requests.get(
        f"{BASE_URL}/api/layers",
        params={"mode": "eco", "location": "xiongan"},
        timeout=30
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "tile_url" in data
    assert data["mode"] == "eco"


def test_invalid_mode():
    """测试无效模式的错误处理"""
    response = requests.get(
        f"{BASE_URL}/api/layers",
        params={"mode": "invalid", "location": "xiongan"}
    )
    
    assert response.status_code == 400


def test_invalid_location():
    """测试无效位置的错误处理"""
    response = requests.get(
        f"{BASE_URL}/api/layers",
        params={"mode": "dna", "location": "invalid"}
    )
    
    assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
