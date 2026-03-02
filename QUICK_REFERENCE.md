# AlphaEarth Cesium 快速参考

## 🚀 快速启动

```bash
# 首次使用：配置环境变量
cd /path/to/alphaearth/cesium_app
./setup_env.sh  # 交互式配置

# 或手动创建 .env
cp .env.example .env
vim .env

# 启动服务
./start.sh
```

访问: `http://127.0.0.1:8404`

## ⚙️ 环境配置

### 快速配置（推荐）
```bash
./setup_env.sh  # 交互式配置向导
```

### 手动配置
```bash
# 1. 复制配置模板
cp .env.example .env

# 2. 编辑 .env 文件
vim .env

# 3. 最少配置（必需）
GEE_USER_PATH=users/your_username/aef_demo
```

### 配置文件位置
- 配置文件: `cesium_app/.env`
- 示例配置: `cesium_app/.env.example`
- 自动加载: 启动脚本会自动读取 .env

## 🎯 常用命令

### 启动服务
```bash
# 一键启动（推荐）
./start.sh

# 分别启动
./run_backend.sh    # 后端 (8405)
./run_frontend.sh   # 前端 (8404)
```

### CH5（盐城）V8.1 分类器导出（GEE Tasks）

导出脚本：`backend/ch5_rf_export.py`（提交任务，不等待完成）。

```bash
# 设置资产路径（二选一）
export CH5_RF_ASSET_ID=users/<your_username>/aef_demo/classifiers/ch5_coastline_rf_v1
# 或：export GEE_USER_PATH=users/<your_username>/aef_demo

python backend/ch5_rf_export.py --check
python backend/ch5_rf_export.py --ensure
```

任务描述名：`Export_Coastline_RF_V8_1`（GEE Code Editor → Tasks 面板查看）。

## 🧯 线上部署：避免 502（运维/保活问题）

如果你看到 `GET /__cesium/.../*.css 502 (Bad Gateway)` 或者连 `/` 首页都 502，这说明 **8404/8406 端口背后的上游进程不存在/不可达**（nginx upstream 断了、node/uvicorn 进程挂了、端口映射错了、OOM 杀进程等）。

两种稳定方案：

### 方案 A（最省心）：单进程服务（FastAPI 托管前端 dist + /api）

- 命令：`./run_prod_single.sh`
- 访问：`http://<server-ip>:8406/`
- 特点：不依赖 Vite dev/preview；`/__cesium/*` 静态资源由 FastAPI 直接返回，避免“上游丢失导致全站 502”。

### 方案 B：nginx 静态托管 + 反代 /api

- 构建前端：在 `frontend/` 下执行 `npm run build`，把 `frontend/dist` 拷贝到服务器目录（例如 `/opt/oneearth/frontend/dist`）
- nginx 示例配置：参考 `frontend/nginx.prod.conf`（Docker 版）或 `deploy/nginx/` 下的生产配置模板
- 特点：静态资源完全不依赖任何上游进程；只有 `/api/*` 走反代到后端（8407）。

### systemd 保活（可选但推荐）

- 单进程 unit：`deploy/systemd/oneearth-v6-single.service`
- 仅后端 unit：`deploy/systemd/oneearth-v6-backend.service`

### 停止服务
```bash
# 如果使用 start.sh
Ctrl+C

# 手动停止
kill $(cat logs/backend.pid logs/frontend.pid)
```

### 运行测试
```bash
cd /path/to/alphaearth
pytest cesium_app/tests/ -v
```

### 查看日志
```bash
tail -f logs/backend.log
tail -f logs/frontend.log
```

## ⚙️ 环境配置

### 快速配置（推荐）
```bash
./setup_env.sh  # 交互式配置向导
```

### 手动配置
```bash
# 1. 复制配置模板
cp .env.example .env

# 2. 编辑 .env 文件
vim .env

# 3. 最少配置（必需）
GEE_USER_PATH=users/your_username/aef_demo
```

### 配置文件位置
- 配置文件: `cesium_app/.env`
- 示例配置: `cesium_app/.env.example`
- 自动加载: 启动脚本会自动读取 .env

### 完整配置项
```bash
# GEE 配置
GEE_USER_PATH=users/your_username/aef_demo
EE_SERVICE_ACCOUNT=xxx@yyy.iam.gserviceaccount.com  # 可选
EE_PRIVATE_KEY_FILE=/path/to/key.json              # 可选

# 服务器配置
API_HOST=127.0.0.1
API_PORT=8405
FRONTEND_PORT=8404

# Cesium 配置
VITE_CESIUM_TOKEN=your_token  # 可选

# LLM 配置（可选，用于 /api/report；未配置则模板回退）
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=your_dashscope_api_key
LLM_MODEL=qwen-plus
LLM_TIMEOUT_S=12
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=512

# 开发配置
TESTING=0
LOG_LEVEL=INFO
```

## 🎮 功能快捷键

### HUD 面板操作
- 选择场景: 点击 🧬 🏗️ ⚠️ 🌿 按钮
- 切换城市: 下拉选择器
- 缓存导出: 点击"📥 为下次演示缓存结果"

### Cesium 地球控制
- 旋转: 左键拖动
- 缩放: 滚轮
- 倾斜: 中键拖动 或 Ctrl+左键拖动
- 平移: 右键拖动

## 📊 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/locations` | GET | 获取所有地点 |
| `/api/modes` | GET | 获取 AI 模式 |
| `/api/missions` | GET | 获取 V5 Missions（任务驱动演示主线） |
| `/api/layers` | GET | 获取图层 URL |
| `/api/stats` | POST | 动态统计（reduceRegion，替换 mockStats） |
| `/api/report` | POST | 生成《区域空间监测简报》（模板/LLM） |
| `/api/cache/export` | POST | 触发缓存导出 |

API 文档: `http://127.0.0.1:8405/docs`

## 🧪 测试统计

- ✅ 单元测试: 11/11 通过
- ✅ API 测试: 13/13 通过
- ✅ 总计: 24/24 通过
- ✅ 覆盖率: > 80%

## 🔧 故障排查

### 问题: 后端报错 "GEE not initialized"
```bash
# 解决方案 1: 检查 .env 配置
cat .env  # 确认 GEE_USER_PATH 已设置

# 解决方案 2: GEE 授权
earthengine authenticate --quiet --auth_mode=notebook
```

### 问题: CH5 导出任务失败："The class band must be integer typed"

这是 `stratifiedSample` 的典型约束，V8.1 脚本已将 `classBand` 强制转为整型；若仍失败，通常是你运行的不是仓库当前脚本版本，或任务引用了旧代码。

### 问题: 环境变量未生效
```bash
# 检查 .env 文件是否存在
ls -la .env

# 手动加载测试
source <(cat .env | grep -v '^#' | sed 's/^/export /')
echo $GEE_USER_PATH

# 重新配置
./setup_env.sh
```

### 问题: 前端无法连接后端
```bash
# 检查后端是否运行
curl http://127.0.0.1:8503/health

# 查看后端日志
tail -f logs/backend.log
```

### 问题: Cesium 地球不显示
```
1. 检查浏览器是否支持 WebGL
2. 检查 Cesium Token 是否配置
3. 检查网络是否能访问 Cesium Ion
```

### 问题: 图层加载慢
```
1. 使用缓存机制（点击缓存按钮）
2. 检查 GEE API 配额是否用尽
3. 考虑使用服务账号
```

### 集成测试（可选）

部分测试会真实访问本机后端与 GEE（需要服务已启动、且已完成 GEE 授权）。默认跳过。

```bash
RUN_INTEGRATION_TESTS=1 pytest -q
```

## 📁 重要文件路径

```
cesium_app/
├── backend/
│   └── main.py              # API 入口
├── frontend/
│   └── src/
│       ├── App.vue          # 主应用
│       └── components/      # Vue 组件
├── tests/                   # 测试文件
├── logs/                    # 运行日志
├── start.sh                 # 一键启动
└── README.md               # 完整文档
```

## 🎬 演示检查清单

演示前 15 分钟:
- [ ] 启动服务: `./start.sh`
- [ ] 检查后端: 访问 `/health`
- [ ] 检查前端: 打开浏览器
- [ ] 测试场景切换
- [ ] 测试地点飞行
- [ ] 准备演讲稿

演示话术要点:
1. 开场: "行星级空间智能底座"
2. 演示: "从太空俯瞰地球"
3. 切换: "AI 实时监测地表变化"
4. 揭示: "数据来自 Google，存在断供风险"
5. 呼吁: "建设中国版 AEF 的必要性"

## 📞 技术支持

- 文档: `README.md`
- 对比分析: `COMPARISON.md`
- 开发总结: `DEVELOPMENT_SUMMARY.md`
- API 文档: `http://127.0.0.1:8503/docs`

---

**版本**: v1.0  
**更新**: 2026-02-19  
**打印此卡片随身携带** 📄
