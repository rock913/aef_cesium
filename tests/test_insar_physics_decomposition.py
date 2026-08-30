import pytest
from starlette.testclient import TestClient
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from gee_service import compute_insar_timeseries_profile

@pytest.fixture
def client():
    return TestClient(app)

class TestInsarPhysicsDecomposition:
    """测试 InSAR 物理全要素分解：塑性沉降趋势项、季节性热胀水文弹性项与升降轨 2D 水平位移"""

    def test_nansha_soft_soil_decomposition(self):
        prof = compute_insar_timeseries_profile(22.72, 113.53)
        assert prof["status"] == "success"
        assert "南沙" in prof["target_name"]
        
        # 物理要素分解
        assert "trend_displacements_mm" in prof
        assert "seasonal_elastic_mm" in prof
        assert len(prof["trend_displacements_mm"]) == 13
        assert len(prof["seasonal_elastic_mm"]) == 13
        assert prof["epochs"][0] == "2022-10-24"
        assert prof["epochs"][-1] == "2023-12-30"
        assert prof["elastic_amplitude_mm"] == 3.2

        # 线性叠加一致性：总位移 = 趋势项 + 季节性弹性项
        for t_val, s_val, tot in zip(prof["trend_displacements_mm"], prof["seasonal_elastic_mm"], prof["displacements_mm"]):
            assert abs((t_val + s_val) - tot) < 0.05

        # 升降轨双向融合水平位移 (南沙向外海侧向挤出)
        assert prof["lateral_velocity_mm_yr"] > 0
        assert "侧向流滑" in prof["lateral_displacement_type"] or "挤出" in prof["lateral_displacement_type"]
        assert "抗剪" in prof["lateral_risk_diagnostic"] or "海堤" in prof["lateral_risk_diagnostic"]

    def test_tianhe_excavation_decomposition(self):
        prof = compute_insar_timeseries_profile(23.12, 113.32)
        assert prof["status"] == "success"
        assert "天河" in prof["target_name"]
        assert prof["elastic_amplitude_mm"] == 2.4
        assert len(prof["trend_displacements_mm"]) == 13
        assert prof["epochs"][0] == "2022-10-24"
        assert prof["epochs"][-1] == "2023-12-30"

        # 线性叠加一致性
        for t_val, s_val, tot in zip(prof["trend_displacements_mm"], prof["seasonal_elastic_mm"], prof["displacements_mm"]):
            assert abs((t_val + s_val) - tot) < 0.05

        # 天河向基坑中心向内收敛 (< 0)
        assert prof["lateral_velocity_mm_yr"] < 0
        assert "收敛" in prof["lateral_displacement_type"] or "地连墙" in prof["lateral_displacement_type"]
        assert "管片" in prof["lateral_risk_diagnostic"] or "地连墙" in prof["lateral_risk_diagnostic"]

    def test_api_endpoint_returns_decomposition_fields(self, client):
        res = client.get("/api/insar/timeseries?lat=22.72&lon=113.53")
        assert res.status_code == 200
        data = res.json()
        assert "trend_displacements_mm" in data
        assert "seasonal_elastic_mm" in data
        assert "lateral_velocity_mm_yr" in data
        assert "epoch_velocities_mm_yr" in data
        assert len(data["epoch_velocities_mm_yr"]) == 13
        assert data["epochs"][0] == "2022-10-24"
        assert data["epochs"][-1] == "2023-12-30"
        assert data["rate_threshold_mm_yr"] == -20.0
        assert "cumulative_threshold_mm" in data
        assert data["cumulative_threshold_mm"] < 0
        assert "seasonal_elastic_mm" in data
        assert "vertical_velocity_mm_yr" in data
        assert "lateral_velocity_mm_yr" in data
        assert "lateral_displacement_type" in data
        assert "lateral_risk_diagnostic" in data
        assert "elastic_amplitude_mm" in data
