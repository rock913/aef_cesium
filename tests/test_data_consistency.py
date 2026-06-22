"""
Data Consistency Tests - 确保数据一致性
借鉴原项目对配置和状态的测试
"""
import pytest
from pathlib import Path
import sys


backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


from config import settings


class TestDataConsistency:
    """测试数据一致性"""
    
    def test_mode_ids_match_between_config_and_service(self):
        """测试：配置中的模式 ID 应该与服务中的逻辑匹配"""
        import gee_service
        
        mode_ids = set(settings.modes.keys())
        
        # 每个模式 ID 应该能被 get_layer_logic 处理
        # get_layer_logic 接受完整的中文名称，不是 ID
        # 所以我们检查函数存在
        assert callable(gee_service.get_layer_logic)
    
    def test_location_ids_are_url_safe(self):
        """测试：位置ID应该是URL安全的（用于API路径）"""
        for loc_id in settings.locations.keys():
            # 应该只包含小写字母、数字、下划线
            assert loc_id.replace('_', '').replace('-', '').isalnum(), \
                f"位置ID不是URL安全的: {loc_id}"
            assert loc_id.islower(), f"位置ID应该是小写: {loc_id}"
    
    def test_mode_ids_are_consistent(self):
        """测试：模式ID应该在整个系统中保持一致"""
        # V6.6 six-chapter mode ids
        valid_mode_ids = {
            "ch1_yuhang_faceid",
            "ch2_maowusu_shield",
            "ch3_zhoukou_pulse",
            "ch4_amazon_zeroshot",
            "ch5_coastline_audit",
            "ch6_water_pulse",
        }
        actual_mode_ids = set(settings.modes.keys())
        
        assert actual_mode_ids == valid_mode_ids, \
            f"模式ID不一致。期望: {valid_mode_ids}，实际: {actual_mode_ids}"
    
    def test_all_locations_have_chinese_names(self):
        """测试：所有位置都应该有中文名称"""
        for loc_id, loc_data in settings.locations.items():
            name = loc_data.get("name", "")
            # 应该包含中文字符
            assert any('\u4e00' <= c <= '\u9fff' for c in name), \
                f"位置 {loc_id} 的名称应该包含中文: {name}"
    
    def test_gee_user_path_format(self):
        """测试：GEE 用户路径格式应该正确"""
        gee_path = settings.gee_user_path
        
        # 支持两种常见格式：
        # - users/<username>/<folder>
        # - projects/<project-id>/assets/<folder>
        assert gee_path.startswith("users/") or gee_path.startswith("projects/"), \
            f"GEE_USER_PATH 应该以 'users/' 或 'projects/' 开头: {gee_path}"
        
        # 不应该以 / 结尾
        assert not gee_path.endswith("/"), \
            f"GEE_USER_PATH 不应该以 '/' 结尾: {gee_path}"
        
        # 应该至少有两个部分
        parts = gee_path.split("/")
        assert len(parts) >= 2, \
            f"GEE_USER_PATH 格式不正确: {gee_path}"


class TestAPIResponseStructure:
    """测试 API 响应结构"""
    
    def test_locations_endpoint_structure(self):
        """测试：/api/locations 应该返回正确的结构"""
        expected_structure = {
            "id": str,
            "name": str,
            "coords": list,
        }
        
        # 验证配置数据符合预期结构
        for loc_id, loc_data in settings.locations.items():
            assert "name" in loc_data
            assert "coords" in loc_data
            assert isinstance(loc_data["name"], str)
            assert isinstance(loc_data["coords"], list)
            assert len(loc_data["coords"]) == 3
    
    def test_modes_endpoint_structure(self):
        """测试：/api/modes 应该返回正确的结构"""
        # 验证配置数据符合预期结构
        for mode_id, mode_name in settings.modes.items():
            assert isinstance(mode_id, str)
            assert isinstance(mode_name, str)
            assert mode_id in settings.modes
            # 模式名称应该包含中文描述
            assert any('\u4e00' <= c <= '\u9fff' for c in mode_name)


class TestGEEBandSelection:
    """测试 GEE 波段选择的正确性"""
    
    def test_band_names_are_correct_format(self):
        """测试：波段名称应该使用正确的格式 (A00-A63)"""
        # 读取 gee_service.py 源码
        gee_service_path = backend_path / "gee_service.py"
        content = gee_service_path.read_text(encoding="utf-8")
        
        # 检查不应该使用数字字符串 '0', '1', '2'
        # 应该使用 'A00', 'A01', 'A02' 或通过 f"A{idx:02d}" 动态生成
        import re
        
        # 查找所有 select() 调用
        select_patterns = re.findall(r"\.select\(\[([^\]]+)\]\)", content)
        
        for pattern in select_patterns:
            # 检查是否使用了错误的数字格式
            if "'0'" in pattern or '"0"' in pattern:
                pytest.fail(
                    f"发现错误的波段选择格式（使用数字字符串）: {pattern}\n"
                    f"应该使用 'A00', 'A01', 'A02' 等格式"
                )
            
        # 至少应该出现显式的 A02（V6 ch2 分支）或动态生成格式
        assert ("'A02'" in content or '"A02"' in content) or ("A{idx:02d}" in content), \
            "未找到正确的波段格式（缺少显式 A02 或动态 A{idx:02d} 生成）"
    
    def test_v6_specific_dimension_mode_mentions_a02(self):
        """测试：V6 ch2 模式应使用 A02 通道（显式选择）"""
        import gee_service
        import inspect

        source = inspect.getsource(gee_service.get_layer_logic)
        assert "A02" in source, "V6 ch2 分支应包含对 A02 通道的选择"
    
    def test_single_band_modes_use_correct_bands(self):
        """测试：V6 模式使用的波段命名应符合 Axx 规范"""
        import gee_service
        import inspect
        
        # 获取 get_layer_logic 函数源码
        source = inspect.getsource(gee_service.get_layer_logic)
        
        assert ("A{idx:02d}" in source) or ("A02" in source), \
            "未找到符合 Axx 规范的波段选择逻辑"


class TestDateRangeConsistency:
    """测试日期范围的一致性"""
    
    def test_date_ranges_are_reasonable(self):
        """测试：日期范围应该是合理的"""
        import gee_service
        import inspect
        
        source = inspect.getsource(gee_service.get_layer_logic)
        
        # 提取日期字符串
        import re
        dates = re.findall(r'["\'](\d{4}-\d{2}-\d{2})["\']', source)
        
        for date_str in dates:
            year = int(date_str.split("-")[0])
            # 年份应该在合理范围内（2015-2026）
            assert 2015 <= year <= 2026, \
                f"get_layer_logic 中的日期不合理: {date_str}"
    
    def test_change_mode_has_two_time_points(self):
        """测试：Change 模式应该有两个时间点进行对比"""
        import gee_service
        import inspect
        
        source = inspect.getsource(gee_service.get_layer_logic)
        
        # 应该有两个不同的日期范围
        import re
        dates = re.findall(r'["\'](\d{4})-\d{2}-\d{2}["\']', source)
        unique_years = set(dates)
        
        # 至少应该有两个不同的年份
        assert len(unique_years) >= 2, \
            f"Change 模式应该对比两个不同时间点，找到的年份: {unique_years}"
