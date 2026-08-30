import pytest
from starlette.testclient import TestClient
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from gee_service import compute_insar_timeseries_profile

@pytest.fixture
def client():
    return TestClient(app)

class TestInsarTimeseriesAPI:
    """测试 InSAR 历史沉降时序位移接口及 AEF 语义诊断"""

    def test_insar_timeseries_nansha_consolidation(self, client):
        """测试南沙填海造陆软土固结沉降中心点"""
        res = client.get("/api/insar/timeseries?lat=22.72&lon=113.53")
        assert res.status_code == 200
        data = res.json()

        assert data["status"] == "success"
        assert data["lat"] == 22.72
        assert data["lon"] == 113.53
        assert "南沙" in data["target_name"]
        assert "软土" in data["aef_semantic"]
        assert data["risk_level"] == "critical"
        assert data["velocity_mm_yr"] < -20.0  # 严重沉降速率
        assert len(data["epochs"]) == 13
        assert data["epochs"][0] == "2022-10-24"
        assert data["epochs"][-1] == "2023-12-30"
        assert len(data["displacements_mm"]) == 13
        # 累积沉降随时间加深
        assert data["displacements_mm"][-1] < data["displacements_mm"][0]
        assert "孔隙水" in data["recommendations"] or "海堤" in data["recommendations"]

    def test_insar_timeseries_tianhe_excavation(self, client):
        """测试天河 CBD 核心区基坑与地下立体空间沉降"""
        res = client.get("/api/insar/timeseries?lat=23.115&lon=113.329")
        assert res.status_code == 200
        data = res.json()

        assert data["status"] == "success"
        assert "天河" in data["target_name"]
        assert "基坑" in data["aef_semantic"] or "人造" in data["aef_semantic"]
        assert data["velocity_mm_yr"] < -10.0
        assert data["risk_level"] in ["warning", "critical"]
        assert len(data["epochs"]) == 13
        assert data["epochs"][0] == "2022-10-24"
        assert data["epochs"][-1] == "2023-12-30"
        assert "地铁" in data["recommendations"] or "基坑" in data["recommendations"]

    def test_insar_timeseries_stable_background(self, client):
        """测试正常稳定地表区域"""
        res = client.get("/api/insar/timeseries?lat=23.40&lon=113.80")
        assert res.status_code == 200
        data = res.json()

        assert data["status"] == "success"
        assert data["risk_level"] == "safe"
        assert -5.0 < data["velocity_mm_yr"] < 5.0
        assert "稳定" in data["risk_label"] or "安全" in data["risk_label"]

    def test_direct_compute_function_output_types(self):
        """测试底层时序反演函数的确定性与数值规范"""
        prof = compute_insar_timeseries_profile(22.72, 113.53)
        assert isinstance(prof, dict)
        assert isinstance(prof["velocity_mm_yr"], float)
        assert isinstance(prof["coherence"], float)
        assert isinstance(prof["epochs"], list)
        assert isinstance(prof["displacements_mm"], list)
        assert all(isinstance(v, (int, float)) for v in prof["displacements_mm"])

    def test_insar_points_api(self, client):
        """测试 InSAR PS 靶向观测点集接口"""
        res = client.get("/api/insar/points?location=guangzhou_nansha")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert len(data["points"]) >= 3
        pt0 = data["points"][0]
        assert "lat" in pt0 and "lon" in pt0
        assert "velocity_mm_yr" in pt0
        assert "name" in pt0
