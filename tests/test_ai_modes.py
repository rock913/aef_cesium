"""V6 AI mode dispatch tests.

This file used to validate V5 modes (dna/change/intensity/eco). In V6 the
backend exposes four chapter modes (ch1..ch4). Here we keep tests lightweight:
we stub out the `ee` module so no real Earth Engine calls are required.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def gee_service_module():
    backend_path = Path(__file__).parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    import gee_service  # type: ignore

    return gee_service


def _make_ee_stub() -> MagicMock:
    ee_stub = MagicMock()

    # Core namespaces used by get_layer_logic
    ee_stub.ImageCollection.return_value = MagicMock()
    ee_stub.Image.return_value = MagicMock()
    ee_stub.Geometry.Rectangle.return_value = MagicMock()
    ee_stub.Clusterer.wekaKMeans.return_value.train.return_value = MagicMock()
    ee_stub.Reducer.sum.return_value = MagicMock()
    ee_stub.Classifier.load.return_value = MagicMock()

    return ee_stub


@pytest.mark.parametrize(
    ("mode", "expected_suffix"),
    [
        ("ch1_yuhang_faceid 城市基因突变 (欧氏距离)", "ch1_faceid"),
        ("ch2_maowusu_shield 大国生态护盾 (余弦相似度)", "ch2_shield"),
        ("ch3_zhoukou_pulse 粮仓脉搏体检 (特定维度反演)", "ch3_pulse"),
        ("ch4_amazon_zeroshot 全球通用智能 (零样本聚类)", "ch4_zeroshot"),
        ("ch5_coastline_audit 海岸线红线审计 (K-Means KD(16-Dim))", "ch5_audit_kd"),
        ("ch6_water_pulse 水网脉动监测 (维差分)", "ch6_water"),
    ],
)
def test_v6_modes_dispatch_without_error(gee_service_module, mode: str, expected_suffix: str):
    ee_stub = _make_ee_stub()
    mock_region = MagicMock()

    if "ch5_coastline_audit" in mode:
        # Force supervised path (otherwise gee_service will fall back).
        import os

        os.environ["CH5_RF_ASSET_ID"] = "users/test/classifiers/ch5_coastline_rf_v1"
        os.environ["CH5_INLAND_CLASS_ID"] = "4"
        gee_service_module._CH5_CLASSIFIER_CACHE = None

    with patch.object(gee_service_module, "ee", ee_stub):
        _img, vis, suffix = gee_service_module.get_layer_logic(mode, mock_region)

    assert isinstance(vis, dict)
    assert suffix == expected_suffix


def test_unknown_mode_raises_value_error(gee_service_module):
    ee_stub = _make_ee_stub()
    mock_region = MagicMock()

    with patch.object(gee_service_module, "ee", ee_stub):
        with pytest.raises(ValueError):
            gee_service_module.get_layer_logic("unknown-mode", mock_region)
