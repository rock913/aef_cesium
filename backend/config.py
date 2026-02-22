"""Configuration for Cesium Backend (V6.6).

V6 goals:
- Avoid conflict with V5 deployment by defaulting to frontend 8504 / backend 8505.
- Replace V5 mission registry with a chapter-based global narrative registry.
"""
import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# 加载 .env 文件（从 cesium_app 根目录）
# 使用绝对路径确保无论工作目录在哪都能正确找到
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ 已加载环境变量: {env_path}")
else:
    print(f"⚠️  未找到 .env 文件: {env_path}，使用默认配置")


class Settings(BaseModel):
    """Application settings"""
    
    # GEE Configuration
    gee_user_path: str = os.getenv("GEE_USER_PATH", "users/default/aef_demo")
    ee_service_account: str = os.getenv("EE_SERVICE_ACCOUNT", "")
    ee_private_key_file: str = os.getenv("EE_PRIVATE_KEY_FILE", "")
    
    # Server Configuration
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8505"))

    # LLM (OpenAI compatible)
    # DashScope compatible-mode example:
    #   LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
    #   LLM_API_KEY=...
    #   LLM_MODEL=qwen-plus
    llm_base_url: str = os.getenv(
        "LLM_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "qwen-plus")
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "12"))
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "512"))

    # Map viewport buffer (meters)
    # Used for backend-side filterBounds region when generating AI layers.
    viewport_buffer_m: int = int(os.getenv("VIEWPORT_BUFFER_M", "150000"))

    # Per-mode viewport buffer overrides (meters).
    # Smaller buffers reduce Earth Engine compute latency and tile generation cost.
    # These defaults target the V6 main-case narrative; override globally via VIEWPORT_BUFFER_M if needed.
    viewport_buffer_m_by_mode: dict = {
        "ch1_yuhang_faceid": 60000,
        "ch2_maowusu_shield": 120000,
        "ch3_zhoukou_pulse": 90000,
        "ch4_amazon_zeroshot": 150000,
        "ch5_coastline_audit": 120000,
        "ch6_water_pulse": 90000,
    }

    def get_viewport_buffer_m_for_mode(self, mode_id: str | None) -> int:
        if not mode_id:
            return int(self.viewport_buffer_m)
        return int(self.viewport_buffer_m_by_mode.get(mode_id, self.viewport_buffer_m))
    
    # CORS Configuration (dev defaults)
    cors_origins: list = [
        "http://localhost:8504",
        "http://127.0.0.1:8504",
    ]
    
    # V6.6 标志性事件坐标库
    locations: dict = {
        # 主案例 1：余杭（以之江实验室为中心坐标）
        "yuhang": {"coords": [30.26879, 119.92284, 13], "name": "杭州 · 余杭", "code": "yuhang"},
        # 主案例 2：毛乌素（生态护盾）
        "maowusu": {"coords": [38.85, 109.98, 8], "name": "陕西 · 毛乌素", "code": "maowusu"},
        # 主案例 3：周口（粮仓脉搏）
        "zhoukou": {"coords": [33.62, 114.65, 10], "name": "河南 · 周口", "code": "zhoukou"},
        # 主案例 4：亚马逊（全球共识）
        "amazon": {"coords": [-10.04485, -55.42936, 10], "name": "巴西 · 亚马逊", "code": "amazon"},
        # 主案例 5：盐城（海岸线红线）
        "yancheng": {"coords": [33.38, 120.50, 10], "name": "江苏 · 盐城", "code": "yancheng"},
        # 主案例 6：鄱阳湖（水网脉动）
        "poyang": {"coords": [29.20, 116.20, 10], "name": "江西 · 鄱阳湖", "code": "poyang"},
    }
     
    # V6.6 高级算法模式注册
    modes: dict = {
        "ch1_yuhang_faceid": "ch1_yuhang_faceid 城市基因突变 (欧氏距离)",
        "ch2_maowusu_shield": "ch2_maowusu_shield 大国生态护盾 (余弦相似度)",
        "ch3_zhoukou_pulse": "ch3_zhoukou_pulse 粮仓脉搏体检 (特定维度反演)",
        "ch4_amazon_zeroshot": "ch4_amazon_zeroshot 全球通用智能 (零样本聚类)",
        "ch5_coastline_audit": "ch5_coastline_audit 海岸线红线审计 (零样本超平面映射)",
        "ch6_water_pulse": "ch6_water_pulse 水网脉动监测 (维差分)",
    }

    # V6 mission registry (ordered)
    # NOTE: Keep this list order stable; front-end uses it as the default narrative sequence.
    missions: list = [
        {
            "id": "ch1_yuhang",
            "name": "觉醒",
            "title": "杭州余杭 · 未来科技城崛起 (2017-2024)",
            "location": "yuhang",
            "api_mode": "ch1_yuhang_faceid",
            "formula": "EuclideanDistance(V_2017, V_2024)",
            "narrative": "中国数字经济的心脏地带，7年间从城郊荒地变为高新产业矩阵。AEF 以欧氏距离锁定大尺度‘基因重写’，作为客观的城建审计证据锚点。",
            "camera": {"lat": 30.26879, "lon": 119.92284, "height": 16000, "duration_s": 3.8},
        },
        {
            "id": "ch2_maowusu",
            "name": "护盾",
            "title": "陕西毛乌素沙地 · 消失的沙漠 (2019-2024)",
            "location": "maowusu",
            "api_mode": "ch2_maowusu_shield",
            "formula": "CosineSimilarity(V_2019, V_2024)",
            "narrative": "联合国认可的治沙奇迹。传统遥感在秋冬仍呈枯黄，易被质疑‘伪绿化’；AEF 以余弦相似度只看语义方向，证明即使在冬季土地‘骨骼’已转为固沙林。",
            "camera": {"lat": 38.60, "lon": 109.60, "height": 70000, "duration_s": 3.9},
        },
        {
            "id": "ch3_zhoukou",
            "name": "脉搏",
            "title": "河南周口 · 农田内涝与胁迫监测 (2019-2024)",
            "location": "zhoukou",
            "api_mode": "ch3_zhoukou_pulse",
            "formula": "InverseSpecificDimension(A02)",
            "narrative": "光学影像看着仍是绿油油麦田，但 AEF 特定维度（如 A02）可‘透视’深层生命力：识别因积水/胁迫导致的根系缺氧、倒伏等风险网格，提前发出预警。",
            "camera": {"lat": 33.63, "lon": 114.65, "height": 70000, "duration_s": 4.0},
        },
        {
            "id": "ch4_amazon",
            "name": "共识",
            "title": "巴西亚马逊 · 毁林前线的“鱼骨” (马托格罗索州)",
            "location": "amazon",
            "api_mode": "ch4_amazon_zeroshot",
            "formula": "ZeroShotKMeans(k=6)",
            "narrative": "不给 AI 任何南美地理先验，直接一键聚类：自动切分‘原始林/新生砍伐区/河流’等结构单元，证明 Alpha Earth Foundation 具备全球即插即用的通用智能能力。",
            "camera": {"lat": -10.04485, "lon": -55.42936, "height": 90000, "duration_s": 4.0},
        },
        {
            "id": "ch5_yancheng",
            "name": "红线",
            "title": "江苏盐城 · 海岸线红线审计 (2023-2024)",
            "location": "yancheng",
            "api_mode": "ch5_coastline_audit",
            "formula": "ZeroShotHyperplane(A00,A02) + PriorityMosaic",
            "narrative": "弃用 KMeans 以消除跨区域标签漂移：用 A00(人造物) 与 A02(水/湿度) 的固定阈值超平面规则，稳定区分建筑硬化带/水体/滩涂，并以优先级合成让建筑压制水体假信号；为红线核查提供可迁移的审计底图。",
            "camera": {"lat": 33.38, "lon": 120.50, "height": 95000, "duration_s": 4.0},
        },
        {
            "id": "ch6_poyang",
            "name": "脉动",
            "title": "江西鄱阳湖 · 水网脉动与湿地变化 (2022 vs 2024)",
            "location": "poyang",
            "api_mode": "ch6_water_pulse",
            "formula": "ΔA02(2024-2022) with |Δ|>0.10",
            "narrative": "以 A02 维度跨年差分突出水体/湿地相关语义变化，捕捉枯丰水位变化与水网连通性波动，为生态水文协同治理提供量化线索。",
            "camera": {"lat": 29.20, "lon": 116.20, "height": 95000, "duration_s": 4.0},
        },
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
