"""
Pytest fixtures for Cesium app testing
"""
import pytest
import os


@pytest.fixture
def mock_gee_user_path():
    """Mock GEE user path for testing"""
    return "users/test_user/aef_demo"


@pytest.fixture
def mock_locations():
    """Mock location data"""
    return {
        "yuhang": {"coords": [30.271092, 119.965127, 13], "name": "杭州 · 余杭"},
        "maowusu": {"coords": [38.85, 109.98, 8], "name": "陕西 · 毛乌素沙地"},
        "zhoukou": {"coords": [33.62, 114.65, 10], "name": "河南 · 周口"},
        "amazon": {"coords": [-11.00, -55.00, 10], "name": "巴西 · 亚马逊"},
        "yancheng": {"coords": [33.38, 120.50, 10], "name": "江苏 · 盐城"},
        "poyang": {"coords": [29.20, 116.20, 10], "name": "江西 · 鄱阳湖"},
    }


@pytest.fixture
def mock_modes():
    """Mock AI mode data"""
    return {
        "ch1_yuhang_faceid": "ch1_yuhang_faceid 城市基因突变 (欧氏距离)",
        "ch2_maowusu_shield": "ch2_maowusu_shield 大国生态护盾 (余弦相似度)",
        "ch3_zhoukou_pulse": "ch3_zhoukou_pulse 粮仓脉搏体检 (特定维度反演)",
        "ch4_amazon_zeroshot": "ch4_amazon_zeroshot 全球通用智能 (零样本聚类)",
        "ch5_coastline_audit": "ch5_coastline_audit 海岸线红线审计 (半监督聚类)",
        "ch6_water_pulse": "ch6_water_pulse 水网脉动监测 (维差分)",
    }


@pytest.fixture(autouse=True)
def set_test_env():
    """Set test environment variables"""
    os.environ["GEE_USER_PATH"] = "users/test_user/aef_demo"
    os.environ["TESTING"] = "1"
    yield
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
