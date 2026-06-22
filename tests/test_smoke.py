"""
Smoke Tests - 确保关键模块可以导入和基本运行
借鉴 test_app_smoke.py 的测试模式
"""
import importlib
import sys
from pathlib import Path


def test_backend_imports_without_errors():
    """测试：后端模块应该能够正常导入"""
    backend_path = Path(__file__).parent.parent / "backend"
    
    # 添加 backend 到 sys.path
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    # 清除可能存在的缓存模块
    for module in list(sys.modules.keys()):
        if module.startswith("backend.") or module in ["config", "gee_service", "main"]:
            del sys.modules[module]
    
    # 导入关键模块
    try:
        config = importlib.import_module("config")
        assert hasattr(config, "Settings")
        assert hasattr(config, "settings")
    except Exception as e:
        raise AssertionError(f"config 模块导入失败: {e}")
    
    try:
        gee_service = importlib.import_module("gee_service")
        # gee_service 使用函数式编程，检查核心函数
        assert hasattr(gee_service, "get_layer_logic")
        assert hasattr(gee_service, "generate_asset_id")
        assert hasattr(gee_service, "smart_load")
    except Exception as e:
        raise AssertionError(f"gee_service 模块导入失败: {e}")


def test_config_has_required_settings():
    """测试：配置应该包含所有必需的设置"""
    backend_path = Path(__file__).parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    from config import settings
    
    # 必需的配置项（使用小写属性名）
    assert hasattr(settings, "gee_user_path")
    assert hasattr(settings, "locations")
    assert hasattr(settings, "modes")
    
    # locations 应该是字典且包含 V6 标志性事件
    assert isinstance(settings.locations, dict)
    assert "yuhang" in settings.locations
    assert "amazon" in settings.locations
    assert "maowusu" in settings.locations
    assert "zhoukou" in settings.locations
    
    # modes 应该是字典且包含4种模式
    assert isinstance(settings.modes, dict)
    assert len(settings.modes) == 6
    assert all(
        mode in settings.modes
        for mode in [
            "ch1_yuhang_faceid",
            "ch2_maowusu_shield",
            "ch3_zhoukou_pulse",
            "ch4_amazon_zeroshot",
            "ch5_coastline_audit",
            "ch6_water_pulse",
        ]
    )


def test_gee_service_has_core_functions():
    """测试：gee_service 应该有核心函数"""
    backend_path = Path(__file__).parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    import gee_service
    
    # 应该有这些关键函数
    assert hasattr(gee_service, "get_layer_logic")
    assert hasattr(gee_service, "generate_asset_id")
    assert hasattr(gee_service, "smart_load")
    
    # 检查 get_layer_logic 函数签名
    import inspect
    sig = inspect.signature(gee_service.get_layer_logic)
    params = list(sig.parameters.keys())
    assert "mode" in params
    assert "region" in params


def test_main_app_has_required_endpoints():
    """测试：FastAPI 应用应该有所有必需的端点"""
    backend_path = Path(__file__).parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    # 导入 main 模块但不运行服务器
    import main
    
    # 检查 app 实例
    assert hasattr(main, "app")
    
    # 检查路由
    routes = [route.path for route in main.app.routes]
    
    # 必需的端点
    required_endpoints = [
        "/api/locations",
        "/api/modes",
        "/api/layers",
        "/health",
    ]
    
    for endpoint in required_endpoints:
        assert endpoint in routes, f"缺失端点: {endpoint}"


def test_gee_service_functions_are_callable():
    """测试：gee_service 的函数应该可以调用"""
    backend_path = Path(__file__).parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    import gee_service
    
    # 函数应该可调用
    assert callable(gee_service.get_layer_logic)
    assert callable(gee_service.generate_asset_id)
    assert callable(gee_service.smart_load)


def test_mode_names_consistency():
    """测试：模式名称在配置中应该一致"""
    backend_path = Path(__file__).parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    from config import settings
    
    modes = settings.modes
    
    # 每个模式应该有中文名称
    for mode_id, mode_name in modes.items():
        assert isinstance(mode_id, str), f"模式ID应该是字符串: {mode_id}"
        assert isinstance(mode_name, str), f"模式名称应该是字符串: {mode_name}"
        assert len(mode_name) > 0, f"模式名称不应为空: {mode_id}"
        
        # 中文名称应该有汉字
        assert any('\u4e00' <= c <= '\u9fff' for c in mode_name), \
            f"模式名称应该包含中文: {mode_id} -> {mode_name}"


def test_location_data_structure():
    """测试：位置数据结构应该正确"""
    backend_path = Path(__file__).parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    from config import settings
    
    locations = settings.locations
    
    # 每个位置应该有正确的数据结构
    for loc_id, loc_data in locations.items():
        assert "name" in loc_data, f"位置 {loc_id} 缺少 name 字段"
        assert "coords" in loc_data, f"位置 {loc_id} 缺少 coords 字段"
        
        # coords 应该是 [lat, lon, zoom]
        coords = loc_data["coords"]
        assert isinstance(coords, list), f"位置 {loc_id} 的 coords 应该是列表"
        assert len(coords) == 3, f"位置 {loc_id} 的 coords 应该有 3 个元素 [lat, lon, zoom]"
        
        lat, lon, zoom = coords
        assert -90 <= lat <= 90, f"位置 {loc_id} 的纬度超出范围: {lat}"
        assert -180 <= lon <= 180, f"位置 {loc_id} 的经度超出范围: {lon}"
        assert 1 <= zoom <= 20, f"位置 {loc_id} 的缩放级别超出范围: {zoom}"


def test_frontend_exists():
    """测试：前端文件应该存在"""
    frontend_path = Path(__file__).parent.parent / "frontend"
    
    # 检查关键文件
    assert frontend_path.exists(), "frontend 目录不存在"
    assert (frontend_path / "package.json").exists(), "package.json 不存在"
    assert (frontend_path / "index.html").exists(), "index.html 不存在"
    
    # 检查 src 目录
    src_path = frontend_path / "src"
    assert src_path.exists(), "src 目录不存在"
    assert (src_path / "main.js").exists(), "main.js 不存在"
    assert (src_path / "App.vue").exists(), "App.vue 不存在"
    
    # 检查 components
    components_path = src_path / "components"
    assert components_path.exists(), "components 目录不存在"
    assert (components_path / "CesiumViewer.vue").exists(), "CesiumViewer.vue 不存在"
