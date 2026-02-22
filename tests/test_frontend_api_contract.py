"""
前端API数据契约测试

验证后端API返回的数据格式是否符合前端期望，确保前后端数据契约一致。

这些测试专注于验证:
1. API返回的数据结构（dict vs list）
2. 数据字段的类型和格式
3. 前端能够正确解析和使用的数据格式
"""

import pytest
import sys
import types
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


@pytest.fixture
def client():
    """创建测试客户端"""
    # 添加 backend 目录到 Python 路径
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))

    # Keep unit tests offline/fast: stub out the heavy Earth Engine SDK.
    if "ee" not in sys.modules:
        fake_ee = types.ModuleType("ee")
        fake_ee.Geometry = types.SimpleNamespace(Point=lambda *a, **k: None)
        sys.modules["ee"] = fake_ee

    # Ensure we import the intended backend/main.py module.
    sys.modules.pop("main", None)
    
    # 延迟导入以避免 GEE 初始化
    import main as main_module

    # Avoid real EE init during FastAPI startup.
    main_module.init_earth_engine = lambda: None
    
    # 模拟 GEE 已初始化
    main_module.gee_initialized = True
    
    return TestClient(main_module.app)


@pytest.fixture(autouse=True)
def mock_layers_dependencies(client):
    """避免契约测试触发真实 Earth Engine 计算。

    这些测试关注的是前后端数据结构契约，而不是 GEE 本身可用性。
    """
    mock_viewport = Mock()
    mock_image = Mock()

    # Depend on `client` fixture so backend_path is on sys.path and `main` is imported.
    with (
        patch("main.ee.Geometry.Point") as mock_point,
        patch("main.smart_load") as mock_smart_load,
        patch("main.get_tile_url") as mock_get_tile,
    ):
        mock_point.return_value.buffer.return_value = mock_viewport
        mock_smart_load.return_value = (
            mock_image,
            {"min": 0, "max": 1},
            "cached",
            True,
            "asset_id",
            mock_image,
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/tiles/{z}/{x}/{y}"
        yield


class TestModesAPIContract:
    """测试 /api/modes 数据契约"""
    
    def test_modes_returns_dict_format(self, client):
        """测试 modes 返回字典格式而非数组
        
        前端期望:
        - HudPanel.vue 使用 v-for="(name, key) in modes"
        - 期望 key 是 mode ID (如 "dna")，name 是字符串 (如 "地表 DNA")
        - getModeName(name) 调用 name.split(' ') 需要 name 是字符串
        
        错误场景:
        - 如果返回数组 [{"id": "dna", "name": "..."}]
        - key 会是索引 0, 1, 2...
        - name 会是对象，导致 split() 失败
        """
        response = client.get("/api/modes")
        assert response.status_code == 200
        
        data = response.json()
        
        # ❌ 当前返回: [{"id": "dna", "name": "..."}]
        # ✅ 应该返回: {"dna": "地表 DNA (语义视图)", ...}
        assert isinstance(data, dict), \
            f"modes 应该返回 dict 而不是 {type(data).__name__}"
        
        # 验证至少包含6个AI模式 (V6.6)
        assert len(data) >= 6, "应该至少有6个AI模式"
        
        # 验证必须包含的模式
        required_modes = [
            "ch1_yuhang_faceid",
            "ch2_maowusu_shield",
            "ch3_zhoukou_pulse",
            "ch4_amazon_zeroshot",
            "ch5_coastline_audit",
            "ch6_water_pulse",
        ]
        for mode_id in required_modes:
            assert mode_id in data, f"缺少必需的模式: {mode_id}"
            assert isinstance(data[mode_id], str), \
                f"模式名称应该是字符串，实际是: {type(data[mode_id])}"
    
    def test_mode_names_are_splittable_strings(self, client):
        """测试模式名称可以被 split() 处理
        
        前端代码: getModeName(fullName) { return fullName.split(' ')[0] }
        需要确保返回的值是字符串且可以被 split
        """
        response = client.get("/api/modes")
        data = response.json()
        
        # 验证每个模式名称都是可分割的字符串
        for mode_id, mode_name in data.items():
            try:
                parts = mode_name.split(' ')
                assert len(parts) >= 1, f"{mode_id} 的名称无法分割"
            except AttributeError as e:
                pytest.fail(f"模式 {mode_id} 的名称 {mode_name} 不是字符串: {e}")
    
    def test_mode_keys_match_valid_ids(self, client):
        """测试模式的键名符合预期的ID格式"""
        response = client.get("/api/modes")
        data = response.json()
        
        valid_mode_ids = {
            "ch1_yuhang_faceid",
            "ch2_maowusu_shield",
            "ch3_zhoukou_pulse",
            "ch4_amazon_zeroshot",
            "ch5_coastline_audit",
            "ch6_water_pulse",
        }
        
        for mode_id in data.keys():
            assert mode_id in valid_mode_ids, \
                f"未知的模式ID: {mode_id}，有效ID: {valid_mode_ids}"


class TestLocationsAPIContract:
    """测试 /api/locations 数据契约"""
    
    def test_locations_returns_dict_format(self, client):
        """测试 locations 返回字典格式而非数组
        
        前端期望:
        - HudPanel.vue 使用 <option :value="key">
        - 期望 key 是 location ID (如 "xiongan")
        - 如果是数组，key 会是索引，导致 API 调用失败
        
        错误场景:
        - Backend 返回: [{"id": "xiongan", ...}]
        - Frontend v-for 的 key = 0
        - 用户选择后发送: GET /api/layers?location=0
        - Backend 报错: 400 Bad Request (无效的 location)
        """
        response = client.get("/api/locations")
        assert response.status_code == 200
        
        data = response.json()
        
        # ❌ 当前返回: [{"id": "xiongan", "name": "...", ...}]
        # ✅ 应该返回: {"xiongan": {"name": "...", ...}}
        assert isinstance(data, dict), \
            f"locations 应该返回 dict 而不是 {type(data).__name__}"
        
        # 验证至少有一个地点
        assert len(data) > 0, "应该至少有一个监测地点"
    
    def test_location_structure_is_correct(self, client):
        """测试每个地点的数据结构符合前端期望"""
        response = client.get("/api/locations")
        data = response.json()
        
        # 验证至少有 yuhang
        assert "yuhang" in data, "应该包含余杭地点"
        
        yuhang = data["yuhang"]
        
        # 前端需要的字段
        assert "name" in yuhang, "地点应该有 name 字段"
        assert "coords" in yuhang, "地点应该有 coords 字段"
        assert "bounds" in yuhang, "地点应该有 bounds 字段用于 Cesium 视口"
        
        # 验证 coords 格式: [lat, lon, zoom]
        assert isinstance(yuhang["coords"], list), "coords 应该是数组"
        assert len(yuhang["coords"]) == 3, "coords 应该有3个元素: [lat, lon, zoom]"
        
        # 验证 bounds 格式
        bounds = yuhang["bounds"]
        required_bounds = ["west", "south", "east", "north"]
        for key in required_bounds:
            assert key in bounds, f"bounds 应该包含 {key}"
            assert isinstance(bounds[key], (int, float)), \
                f"bounds.{key} 应该是数字"
    
    def test_location_keys_are_valid_identifiers(self, client):
        """测试地点ID是有效的标识符（用于URL参数）"""
        response = client.get("/api/locations")
        data = response.json()
        
        import re
        valid_id_pattern = re.compile(r'^[a-z][a-z0-9_]*$')
        
        for location_id in data.keys():
            assert valid_id_pattern.match(location_id), \
                f"地点ID '{location_id}' 应该是小写字母和下划线组成"


class TestCacheExportAPIContract:
    """测试 /api/cache/export 数据契约"""
    
    def test_cache_export_accepts_mode_as_string(self, client):
        """测试缓存导出接受 mode 字符串参数
        
        错误场景:
        - Frontend: modes.value = {"dna": {"id": "dna", "name": "..."}}
        - Frontend 发送: {mode: modes.value["dna"]} → 发送对象
        - Backend 期望: {mode: "dna"} → 期望字符串
        - 结果: 422 Unprocessable Entity
        
        正确做法:
        - Frontend 应该发送: {mode: selectedMode.value}
        - 直接发送 mode ID 字符串
        """
        response = client.post("/api/cache/export", json={
            "mode": "ch2_maowusu_shield",  # ✅ 字符串，不是对象
            "location": "maowusu"
        })
        
        # 应该接受请求（200/202）或返回业务错误（400/500）
        # 但不应该是 422 (参数格式错误)
        assert response.status_code != 422, \
            "mode 字符串参数应该被接受，不应该返回 422"
        
        # 如果返回错误，应该是有意义的业务错误
        if response.status_code >= 400:
            error_data = response.json()
            assert "detail" in error_data, "错误响应应该包含 detail 字段"
    
    def test_cache_export_validates_mode_values(self, client):
        """测试缓存导出验证 mode 参数的有效性"""
        response = client.post("/api/cache/export", json={
            "mode": "invalid_mode",
            "location": "maowusu"
        })
        
        # 应该返回 400 (业务验证失败) 而不是 500 或 422
        assert response.status_code == 400, \
            "无效的 mode 应该返回 400 Bad Request"
    
    def test_cache_export_validates_location_values(self, client):
        """测试缓存导出验证 location 参数的有效性"""
        response = client.post("/api/cache/export", json={
            "mode": "ch2_maowusu_shield",
            "location": "invalid_location"
        })
        
        # 应该返回 400 (业务验证失败)
        assert response.status_code == 400, \
            "无效的 location 应该返回 400 Bad Request"


class TestLayerAPIContract:
    """测试 /api/layers 数据契约"""
    
    def test_layer_api_accepts_string_parameters(self, client):
        """测试图层API接受字符串参数
        
        确保前端发送的参数格式被正确接受
        """
        response = client.get("/api/layers", params={
            "mode": "ch1_yuhang_faceid",  # 字符串
            "location": "yuhang"  # 字符串（不是索引 0）
        })
        
        assert response.status_code == 200, \
            "有效的字符串参数应该被接受"

        data = response.json()
        assert "render_hints" in data, "layers 响应应包含可选 render_hints（用于前端渲染调优）"
        assert isinstance(data["render_hints"], dict)
        assert "ai_opacity" in data["render_hints"], "render_hints 应包含 ai_opacity"
        opacity = data["render_hints"]["ai_opacity"]
        assert isinstance(opacity, (int, float))
        assert 0.0 <= float(opacity) <= 1.0
    
    def test_layer_api_rejects_numeric_location(self, client):
        """测试图层API拒绝数字location参数
        
        当前端错误发送索引时应该报错
        """
        response = client.get("/api/layers", params={
            "mode": "ch1_yuhang_faceid",
            "location": "0"  # 错误：数组索引
        })
        
        # 应该返回 400 表示无效参数
        assert response.status_code == 400, \
            "数字location应该被拒绝，返回 400"


class TestHealthAPIContract:
    """测试健康检查API契约"""
    
    def test_health_returns_consistent_format(self, client):
        """测试健康检查返回一致的格式"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data, "健康检查应该包含 status 字段"
        assert data["status"] == "healthy", \
            "健康状态应该是 'healthy' (前端可能依赖此值)"


# ============================================================================
# 集成测试：模拟前端完整流程
# ============================================================================

class TestFrontendWorkflow:
    """测试前端完整工作流程的数据契约"""
    
    def test_complete_frontend_initialization_flow(self, client):
        """测试前端初始化流程
        
        模拟 App.vue onMounted 流程:
        1. 获取 locations
        2. 获取 modes
        3. 使用默认值加载图层
        """
        # 步骤1: 获取locations
        loc_response = client.get("/api/locations")
        assert loc_response.status_code == 200
        locations = loc_response.json()
        assert isinstance(locations, dict), "locations应该是dict"
        
        # 步骤2: 获取modes
        mode_response = client.get("/api/modes")
        assert mode_response.status_code == 200
        modes = mode_response.json()
        assert isinstance(modes, dict), "modes应该是dict"
        
        # 步骤3: 使用第一个location和mode加载图层
        first_location = list(locations.keys())[0]
        first_mode = list(modes.keys())[0]
        
        layer_response = client.get("/api/layers", params={
            "mode": first_mode,
            "location": first_location
        })
        assert layer_response.status_code == 200, \
            f"使用有效参数 mode={first_mode}, location={first_location} 应该成功"
    
    def test_location_change_workflow(self, client):
        """测试用户切换地点的工作流程
        
        模拟用户在HudPanel选择新地点:
        1. 获取locations列表
        2. 用户选择 (从select的value属性)
        3. 发送新的图层请求
        """
        # 获取locations
        loc_response = client.get("/api/locations")
        locations = loc_response.json()
        
        # 模拟用户选择：value应该是location ID而不是索引
        selected_location_id = "yuhang"  # ✅ 正确：使用ID
        # selected_location_id = "0"  # ❌ 错误：使用索引
        
        assert selected_location_id in locations, \
            "选中的location ID应该存在于locations中"
        
        # 发送请求
        layer_response = client.get("/api/layers", params={
            "mode": "ch1_yuhang_faceid",
            "location": selected_location_id
        })
        
        assert layer_response.status_code == 200, \
            f"使用location ID '{selected_location_id}' 应该成功"
    
    def test_mode_change_workflow(self, client):
        """测试用户切换模式的工作流程"""
        # 获取modes
        mode_response = client.get("/api/modes")
        modes = mode_response.json()
        
        # 模拟用户选择模式
        selected_mode_id = "ch3_zhoukou_pulse"
        
        assert selected_mode_id in modes, \
            "选中的mode ID应该存在于modes中"
        
        # 验证mode值是字符串（可以被前端直接使用）
        mode_name = modes[selected_mode_id]
        assert isinstance(mode_name, str), \
            f"mode值应该是字符串，实际是 {type(mode_name)}"
        
        # 发送图层请求
        layer_response = client.get("/api/layers", params={
            "mode": selected_mode_id,
            "location": "yuhang"
        })
        
        assert layer_response.status_code == 200
    
    def test_cache_export_workflow(self, client):
        """测试用户导出缓存的工作流程
        
        前端代码: 
        await apiService.exportCache(
            selectedMode.value,  # ✅ 应该直接传mode ID
            selectedLocation.value
        )
        """
        selected_mode = "ch2_maowusu_shield"  # ✅ 字符串ID
        selected_location = "maowusu"
        
        response = client.post("/api/cache/export", json={
            "mode": selected_mode,
            "location": selected_location
        })
        
        # 应该成功或返回明确的业务错误
        assert response.status_code != 422, \
            "正确的参数格式不应该返回 422"
