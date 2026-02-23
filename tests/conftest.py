"""
Pytest fixtures for Cesium app testing
"""
import pytest
import os
import sys
import types


def _maybe_install_fast_import_stubs() -> None:
    """Speed up unit tests by stubbing heavyweight optional dependencies.

    Notes:
    - The backend imports `ee` and `llm_service` at module import time.
    - Most tests mock backend functions and don't need real Earth Engine.
    - Integration diagnostics opt-in via RUN_INTEGRATION_TESTS=1.
    """

    # Allow opting out.
    if os.getenv("PYTEST_STUB_EE", "1") not in {"1", "true", "yes", "on"}:
        return
    # If integration tests are enabled, we want the real SDK.
    if os.getenv("RUN_INTEGRATION_TESTS", "0") == "1":
        return

    if "ee" not in sys.modules:
        fake_ee = types.ModuleType("ee")
        # Provide minimal surface used by patch() in tests.
        fake_ee.Geometry = types.SimpleNamespace(
            Point=lambda *a, **k: None,
            Rectangle=lambda *a, **k: None,
        )
        fake_ee.Filter = types.SimpleNamespace(lt=lambda *a, **k: None)
        fake_ee.Reducer = types.SimpleNamespace(min=lambda *a, **k: None, sum=lambda *a, **k: None)
        fake_ee.Clusterer = types.SimpleNamespace(wekaKMeans=lambda *a, **k: None)
        fake_ee.Classifier = types.SimpleNamespace(load=lambda *a, **k: None)
        fake_ee.batch = types.SimpleNamespace(
            Export=types.SimpleNamespace(
                image=types.SimpleNamespace(toAsset=lambda **k: None),
                classifier=types.SimpleNamespace(toAsset=lambda **k: types.SimpleNamespace(start=lambda: None, status=lambda: {"state": "READY"}, id="stub")),
            )
        )
        fake_ee.data = types.SimpleNamespace(getAsset=lambda *a, **k: None, createAsset=lambda *a, **k: None)
        fake_ee.Initialize = lambda *a, **k: None
        fake_ee.ServiceAccountCredentials = lambda *a, **k: None
        fake_ee.ImageCollection = lambda *a, **k: None
        fake_ee.Image = lambda *a, **k: None
        fake_ee.Number = lambda *a, **k: None
        fake_ee.Projection = lambda *a, **k: None
        sys.modules["ee"] = fake_ee

    if "llm_service" not in sys.modules:
        m = types.ModuleType("llm_service")

        async def _noop_async(*_args, **_kwargs):
            return ""

        m.generate_monitoring_brief_openai_compatible = _noop_async
        m.generate_agent_analysis_openai_compatible = _noop_async
        sys.modules["llm_service"] = m


_maybe_install_fast_import_stubs()


@pytest.fixture
def mock_gee_user_path():
    """Mock GEE user path for testing"""
    return "users/test_user/aef_demo"


@pytest.fixture
def mock_locations():
    """Mock location data"""
    return {
           "yuhang": {"coords": [30.26879, 119.92284, 13], "name": "杭州 · 余杭"},
        "maowusu": {"coords": [38.85, 109.98, 8], "name": "陕西 · 毛乌素沙地"},
        "zhoukou": {"coords": [33.62, 114.65, 10], "name": "河南 · 周口"},
        "amazon": {"coords": [-10.04485, -55.42936, 10], "name": "巴西 · 亚马逊"},
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
        "ch5_coastline_audit": "ch5_coastline_audit 海岸线红线审计 (AEF × JRC (Generalized RF))",
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
