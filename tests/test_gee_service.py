"""TDD Unit Tests for GEE Service Layer (V6)

These tests are mock-based and validate:
- Mode dispatch in get_layer_logic for the V6 four chapters
- smart_load cache-hit/miss behavior
- Zero-shot KMeans (ch4) uses a bounded training_region to avoid timeouts
- Coastline audit (ch5) prefers supervised assetized classifier (RF)

We import backend modules via sys.path injection so the tests work in this repo
layout (backend/*.py are not packaged as a pip module).
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def gee_service_module():
    backend_path = Path(__file__).parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    import gee_service  # type: ignore

    return gee_service


class TestLayerLogicV6:
    def test_get_layer_logic_ch1_euclidean_distance(self, gee_service_module):
        mode = "ch1_yuhang_faceid 城市基因突变 (欧氏距离)"
        mock_region = Mock()

        with patch.object(gee_service_module, "ee") as mock_ee:
            mock_collection = Mock()
            mock_img_2017 = Mock()
            mock_img_2024 = Mock()
            mock_selected_2017 = Mock()
            mock_selected_2024 = Mock()
            mock_dist = Mock()
            mock_masked = Mock()

            mock_ee.ImageCollection.return_value = mock_collection

            def filter_date_side_effect(start, end):
                mock_filter = Mock()
                mock_filtered = Mock()
                mock_filter.filterBounds.return_value = mock_filtered
                if "2017" in start:
                    mock_filtered.mosaic.return_value = mock_img_2017
                else:
                    mock_filtered.mosaic.return_value = mock_img_2024
                return mock_filter

            mock_collection.filterDate.side_effect = filter_date_side_effect

            # Implementation selects embedding bands by index then renames to Axx aliases.
            mock_img_2017.select.return_value.rename.return_value = mock_selected_2017
            mock_img_2024.select.return_value.rename.return_value = mock_selected_2024

            mock_selected_2017.subtract.return_value.pow.return_value.reduce.return_value.sqrt.return_value = mock_dist
            mock_dist.gt.return_value = Mock()
            mock_dist.updateMask.return_value = mock_masked

            result_image, vis_params, suffix = gee_service_module.get_layer_logic(mode, mock_region)

            assert suffix == "ch1_faceid"
            assert "palette" in vis_params
            assert result_image is mock_masked

    def test_get_layer_logic_ch2_cosine_similarity(self, gee_service_module):
        mode = "ch2_maowusu_shield 大国生态护盾 (余弦相似度)"
        mock_region = Mock()

        with patch.object(gee_service_module, "ee") as mock_ee:
            mock_collection = Mock()
            mock_img_a = Mock()
            mock_img_b = Mock()
            mock_dot = Mock()
            mock_n19 = Mock()
            mock_n24 = Mock()
            mock_risk = Mock()

            mock_ee.ImageCollection.return_value = mock_collection

            def filter_date_side_effect(start, end):
                mock_filter = Mock()
                mock_filtered = Mock()
                mock_filter.filterBounds.return_value = mock_filtered
                if "2019" in start:
                    mock_filtered.mosaic.return_value = mock_img_a
                else:
                    mock_filtered.mosaic.return_value = mock_img_b
                return mock_filter

            mock_collection.filterDate.side_effect = filter_date_side_effect

            mock_img_a.select.return_value.rename.return_value = mock_img_a
            mock_img_b.select.return_value.rename.return_value = mock_img_b

            # dot = emb19.multiply(emb24).reduce(sum)
            mock_img_a.multiply.return_value = mock_dot
            mock_dot.reduce.return_value = mock_dot

            # n19 = emb19.pow(2).reduce(sum).sqrt()
            mock_img_a.pow.return_value = mock_n19
            mock_n19.reduce.return_value = mock_n19
            mock_n19.sqrt.return_value = mock_n19

            # n24 = emb24.pow(2).reduce(sum).sqrt()
            mock_img_b.pow.return_value = mock_n24
            mock_n24.reduce.return_value = mock_n24
            mock_n24.sqrt.return_value = mock_n24

            # cosine = dot.divide(n19.multiply(n24))
            mock_n19.multiply.return_value = mock_n19
            mock_dot.divide.return_value = Mock()  # cosine

            # risk = ee.Image(1).subtract(cosine)
            mock_ee.Image.return_value.subtract.return_value = mock_risk
            mock_risk.updateMask.return_value = mock_risk
            mock_risk.gt.return_value = Mock()

            result_image, vis_params, suffix = gee_service_module.get_layer_logic(mode, mock_region)

            assert suffix == "ch2_shield"
            assert "palette" in vis_params
            assert result_image is mock_risk

    def test_get_layer_logic_ch3_specific_dimension(self, gee_service_module):
        mode = "ch3_zhoukou_pulse 粮仓脉搏体检 (特定维度反演)"
        mock_region = Mock()

        with patch.object(gee_service_module, "ee") as mock_ee:
            mock_collection = Mock()
            mock_mosaic = Mock()
            mock_filtered = Mock()
            mock_pulse = Mock()
            mock_scaled = Mock()
            mock_masked = Mock()

            mock_ee.ImageCollection.return_value = mock_collection
            mock_collection.filterBounds.return_value.filterDate.return_value = mock_filtered
            mock_filtered.mosaic.return_value = mock_mosaic

            # pulse band selection (legacy: unitScale + threshold in normalized domain)
            mock_mosaic.select.return_value.rename.return_value = mock_pulse
            mock_pulse.unitScale.return_value = mock_scaled
            mock_scaled.gt.return_value = Mock()
            mock_scaled.updateMask.return_value = mock_masked

            result_image, vis_params, suffix = gee_service_module.get_layer_logic(mode, mock_region)

            assert suffix == "ch3_pulse"
            assert vis_params.get("min") is not None
            assert result_image is mock_masked

    def test_get_layer_logic_ch4_kmeans_uses_training_region(self, gee_service_module):
        mode = "ch4_amazon_zeroshot 全球通用智能 (零样本聚类)"
        mock_region = Mock()

        with patch.object(gee_service_module, "ee") as mock_ee:
            mock_collection = Mock()
            mock_mosaic = Mock()
            mock_filtered = Mock()
            mock_geom = Mock()
            mock_base = Mock()

            mock_ee.ImageCollection.return_value = mock_collection
            mock_collection.filterBounds.return_value.filterDate.return_value = mock_filtered
            mock_filtered.mosaic.return_value = mock_mosaic

            # base = filtered_col.mosaic().select([...indices...]).rename([...Axx...])
            mock_mosaic.select.return_value.rename.return_value = mock_base

            mock_ee.Geometry.Rectangle.return_value = mock_geom

            mock_sample_fc = Mock()
            mock_base.sample.return_value = mock_sample_fc

            mock_clusterer = Mock()
            mock_ee.Clusterer.wekaKMeans.return_value = mock_clusterer
            mock_clusterer.train.return_value = mock_clusterer

            mock_clustered = Mock()
            mock_visualized = Mock()
            mock_base.cluster.return_value = mock_clustered
            mock_clustered.randomVisualizer.return_value = mock_visualized

            result_image, vis_params, suffix = gee_service_module.get_layer_logic(mode, mock_region)

            assert suffix == "ch4_zeroshot"
            assert result_image is mock_visualized
            assert vis_params.get("forceRgbOutput") is True

            mock_base.sample.assert_called()
            kwargs = mock_base.sample.call_args.kwargs
            assert "region" in kwargs
            assert kwargs["region"] is mock_geom

    def test_get_layer_logic_ch5_coastline_audit_supervised_classifier_asset(self, gee_service_module, monkeypatch):
        mode = "ch5_coastline_audit 海岸线红线审计 (RF资产化)"
        mock_region = Mock()

        monkeypatch.setenv("CH5_RF_ASSET_ID", "users/test/classifiers/ch5_coastline_rf_v1")
        gee_service_module._CH5_CLASSIFIER_CACHE = None

        with patch.object(gee_service_module, "ee") as mock_ee:
            mock_embedding_collection = Mock()
            mock_filtered = Mock()
            mock_mosaic = Mock()
            mock_selected = Mock()
            mock_base_img = Mock()
            mock_classifier = Mock()
            mock_classified = Mock()
            mock_mask = Mock()
            mock_masked = Mock()

            mock_ee.ImageCollection.return_value = mock_embedding_collection
            mock_embedding_collection.filterBounds.return_value.filterDate.return_value = mock_filtered
            mock_filtered.mosaic.return_value = mock_mosaic

            # base_img = _select_embedding_bands(mosaic, emb_bands)
            mock_mosaic.select.return_value.rename.return_value = mock_base_img

            # classifier = ee.Classifier.load(asset_id)
            mock_ee.Classifier.load.return_value = mock_classifier
            mock_base_img.classify.return_value = mock_classified

            # background masking: img.updateMask(img.neq(3))
            mock_classified.neq.return_value = mock_mask
            mock_classified.updateMask.return_value = mock_masked

            result_image, vis_params, suffix = gee_service_module.get_layer_logic(mode, mock_region)

            assert suffix == "ch5_audit_supervised"
            assert vis_params.get("min") == 0
            assert vis_params.get("max") == 2
            assert isinstance(vis_params.get("palette"), list)
            assert len(vis_params["palette"]) == 3
            assert result_image is mock_masked

            mock_ee.Classifier.load.assert_called_once()
            mock_base_img.classify.assert_called_once_with(mock_classifier)
            mock_classified.neq.assert_called_once_with(3)
            mock_classified.updateMask.assert_called_once_with(mock_mask)

    def test_get_layer_logic_ch5_requires_asset_id(self, gee_service_module, monkeypatch):
        mode = "ch5_coastline_audit 海岸线红线审计 (RF资产化)"
        mock_region = Mock()

        # Strict behavior: without an asset id configured, we must fail fast.
        monkeypatch.delenv("CH5_RF_ASSET_ID", raising=False)
        monkeypatch.setenv("GEE_USER_PATH", "users/default/aef_demo")
        gee_service_module._CH5_CLASSIFIER_CACHE = None

        with patch.object(gee_service_module, "ee") as mock_ee:
            mock_collection = Mock()
            mock_filtered = Mock()
            mock_mosaic = Mock()
            mock_base_img = Mock()

            mock_ee.ImageCollection.return_value = mock_collection
            mock_collection.filterBounds.return_value.filterDate.return_value = mock_filtered
            mock_filtered.mosaic.return_value = mock_mosaic

            mock_mosaic.select.return_value.rename.return_value = mock_base_img

            with pytest.raises(ValueError):
                gee_service_module.get_layer_logic(mode, mock_region)

    def test_get_layer_logic_ch5_requires_asset_id(self, gee_service_module, monkeypatch):
        """CH5 must fail fast if the supervised classifier asset is not configured."""

        mode = "ch5_coastline_audit 海岸线红线审计 (RF资产化)"
        mock_region = Mock()

        monkeypatch.delenv("CH5_RF_ASSET_ID", raising=False)
        monkeypatch.setenv("GEE_USER_PATH", "users/default/aef_demo")
        gee_service_module._CH5_CLASSIFIER_CACHE = None

        with patch.object(gee_service_module, "ee") as mock_ee:
            mock_embedding_collection = Mock()
            mock_filtered = Mock()
            mock_mosaic = Mock()
            mock_base_img = Mock()

            mock_ee.ImageCollection.return_value = mock_embedding_collection
            mock_embedding_collection.filterBounds.return_value.filterDate.return_value = mock_filtered
            mock_filtered.mosaic.return_value = mock_mosaic
            mock_mosaic.select.return_value.rename.return_value = mock_base_img

            with pytest.raises(ValueError):
                gee_service_module.get_layer_logic(mode, mock_region)

    def test_get_layer_logic_ch6_water_pulse_year_diff(self, gee_service_module):
        mode = "ch6_water_pulse 水网脉动监测 (维差分)"
        mock_region = Mock()

        with patch.object(gee_service_module, "ee") as mock_ee:
            mock_collection = Mock()
            mock_ee.ImageCollection.return_value = mock_collection

            # Two mosaics for different year ranges
            mock_mosaic_2022 = Mock()
            mock_mosaic_2024 = Mock()

            def filter_date_side_effect(start, end):
                mock_filter = Mock()
                mock_filtered = Mock()
                mock_filter.filterBounds.return_value = mock_filtered
                if "2022" in start:
                    mock_filtered.mosaic.return_value = mock_mosaic_2022
                else:
                    mock_filtered.mosaic.return_value = mock_mosaic_2024
                return mock_filter

            mock_collection.filterDate.side_effect = filter_date_side_effect

            mock_sel_2022 = Mock()
            mock_sel_2024 = Mock()
            mock_mosaic_2022.select.return_value.rename.return_value = mock_sel_2022
            mock_mosaic_2024.select.return_value.rename.return_value = mock_sel_2024

            mock_diff = Mock()
            mock_sel_2024.subtract.return_value = mock_diff
            mock_diff.updateMask.return_value = mock_diff
            mock_diff.abs.return_value.gt.return_value = Mock()

            result_image, vis_params, suffix = gee_service_module.get_layer_logic(mode, mock_region)

            assert suffix == "ch6_water"
            assert "palette" in vis_params
            assert result_image is mock_diff


class TestSmartLoad:
    def test_smart_load_cache_hit(self, gee_service_module, mock_gee_user_path):
        mode = "ch1_yuhang_faceid 城市基因突变 (欧氏距离)"
        mock_region = Mock()
        loc_code = "yuhang"

        with patch.object(gee_service_module, "ee") as mock_ee:
            mock_ee.data.getAsset.return_value = {"type": "Image"}
            mock_ee.Image.return_value = Mock()

            with patch.object(gee_service_module, "get_layer_logic") as mock_get_layer:
                layer, vis, status, is_cached, asset_id, raw_img = gee_service_module.smart_load(
                    mode, mock_region, loc_code, mock_gee_user_path
                )

                assert is_cached is True
                assert asset_id == f"{mock_gee_user_path}/yuhang_ch1_faceid"
                assert layer is mock_ee.Image.return_value
                assert raw_img is None
                # Cache-hit should avoid expensive computation
                mock_get_layer.assert_not_called()

    def test_smart_load_cache_miss(self, gee_service_module, mock_gee_user_path):
        mode = "ch2_maowusu_shield 大国生态护盾 (余弦相似度)"
        mock_region = Mock()
        loc_code = "maowusu"

        with patch.object(gee_service_module, "ee") as mock_ee:
            mock_ee.data.getAsset.side_effect = Exception("Asset not found")

            with patch.object(gee_service_module, "get_layer_logic") as mock_get_layer:
                mock_img = Mock()
                mock_get_layer.return_value = (mock_img, {"min": 0}, "ch2_shield")

                layer, vis, status, is_cached, asset_id, raw_img = gee_service_module.smart_load(
                    mode, mock_region, loc_code, mock_gee_user_path
                )

                assert is_cached is False
                assert layer is mock_img
                assert raw_img is mock_img
                mock_get_layer.assert_called_once()


class TestTileURLGeneration:
    def test_get_tile_url_success(self, gee_service_module):
        mock_image = Mock()
        vis_params = {"min": 0, "max": 1, "palette": ["000000", "FFFFFF"]}

        mock_map_id = {"tile_fetcher": Mock(url_format="https://earthengine.googleapis.com/v1/{z}/{x}/{y}")}
        mock_image.getMapId.return_value = mock_map_id

        url = gee_service_module.get_tile_url(mock_image, vis_params)

        assert "earthengine.googleapis.com" in url
        assert "{z}" in url and "{x}" in url and "{y}" in url


class TestExportTask:
    def test_trigger_export_task_calls_to_asset_and_starts(self, gee_service_module):
        mock_image = Mock()
        mock_region = Mock()
        description = "export_test"
        asset_id = "users/test/assets/yuhang_ch1_faceid"

        with patch.object(gee_service_module, "ee") as mock_ee:
            mock_task = Mock()
            mock_task.id = "TASK_001"
            mock_ee.batch.Export.image.toAsset.return_value = mock_task

            task_id = gee_service_module.trigger_export_task(mock_image, description, asset_id, mock_region)

            assert task_id == "TASK_001"
            mock_ee.batch.Export.image.toAsset.assert_called_once()
            call_kwargs = mock_ee.batch.Export.image.toAsset.call_args.kwargs
            assert call_kwargs["image"] is mock_image
            assert call_kwargs["description"] == description
            assert call_kwargs["assetId"] == asset_id
            assert call_kwargs["region"] is mock_region
            mock_task.start.assert_called_once()
