# BirdVision 智能鸟类识别系统

> 基于深度学习的鸟类识别与知识问答平台，融合 YOLOv11 目标检测与 LLM 大语言模型，提供从图片识别到智能问答的一站式鸟类知识服务。

## 项目简介

BirdVision 是一个面向鸟类爱好者和生态研究者的智能识别平台。用户上传鸟类图片后，系统通过 YOLO 模型进行目标检测，自动匹配数据库中的物种信息，并可通过 LLM 进行深度知识问答，构建"识别 → 了解 → 探索"的完整体验闭环。

### 核心能力

- **智能识别**：三级检测策略，从自定义模型到 LLM 多模态视觉识别，逐级保障识别成功率
- **知识问答**：支持 DeepSeek、小米 MiMo、Ollama 等多种 LLM 后端，识别结果自动注入对话上下文
- **物种百科**：内置 50 种中国常见鸟类数据，含学名、科属、栖息地、保护等级等字段
- **数据统计**：识别记录可视化分析，支持物种分布、趋势趋势等多维统计

## 技术栈

| 层级 | 技术选型 |
|:---|:---|
| **Web 框架** | Flask 3.1 + SQLAlchemy + Jinja2 |
| **目标检测** | Ultralytics YOLOv11（自定义训练 15 种 + 预训练 fallback） |
| **大语言模型** | DeepSeek / 小米 MiMo / Ollama（多 provider 自动 fallback） |
| **前端** | Bootstrap 5.3 + Font Awesome 6 + ECharts 5.1 |
| **数据库** | SQLite（开发） / MySQL（生产可选） |
| **部署** | Gunicorn + Nginx + Systemd（阿里云 ECS） |

## 项目结构

```
BirdVision/
├── project/bird-vision/
│   ├── app/
│   │   ├── __init__.py          # Flask 应用工厂
│   │   ├── models.py             # 数据模型（BirdSpecies / DetectionRecord / ChatRecord）
│   │   ├── init_db.py            # 数据库种子数据（50 种鸟类）
│   │   ├── routes/
│   │   │   ├── main.py           # 页面路由（首页/识别/问答/统计/百科）
│   │   │   └── api.py            # API 路由（12 个端点）
│   │   ├── services/
│   │   │   ├── bird_detector.py  # YOLO 检测服务（三级策略）
│   │   │   └── llm_service.py    # LLM 对话服务（多 provider 适配）
│   │   ├── templates/            # 7 个页面模板
│   │   └── static/uploads/       # 用户上传图片
│   ├── config.py                # 配置模块
│   ├── run.py                   # 应用入口
│   ├── requirements.txt
│   ├── .env.example             # 环境变量模板
│   ├── training/
│   │   ├── yolo/                # YOLO 训练脚本与数据集
│   │   └── llm/                 # LLM 微调脚本与数据
│   ├── models/
│   │   ├── yolo/best.pt        # 训练好的 YOLO 模型
│   │   └── llm/                 # Ollama 模型配置
│   └── docs/
│       └── llm_deploy.md       # LLM 部署指南
└── .gitignore
```

## 快速开始

### 环境要求

- Python 3.10+
- pip
-（可选）NVIDIA GPU，用于本地 Ollama 或模型训练

### 安装步骤

```bash
# 1. 克隆仓库
git clone git@github.com:Dec-snow/BirdVision.git
cd BirdVision/project/bird-vision

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\Activate.ps1     # Windows PowerShell

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY 等配置

# 5. 初始化数据库
python -m app.init_db

# 6. 启动应用
python run.py
```

访问 **http://127.0.0.1:5000** 即可使用。

### 启动自检

应用启动时会自动执行自检，检查 YOLO 模型、LLM 配置、数据库状态：

```
--------------------------------------------------
  BirdVision 启动自检
--------------------------------------------------
  [✓] YOLO 模型: models/yolo/best.pt
  [→] LLM: deepseek (deepseek-chat) - API Key: 已设置
  [✓] 物种数据: 50 条
--------------------------------------------------
```

## 配置说明

编辑 `.env` 文件进行配置（参考 `.env.example`）：

### 基础配置

| 变量 | 说明 | 默认值 |
|:---|:---|:---|
| `SECRET_KEY` | Flask 安全密钥（生产环境必须修改） | 内置默认值 |
| `HOST` | 监听地址 | `127.0.0.1` |
| `PORT` | 监听端口 | `5000` |
| `FLASK_DEBUG` | 调试模式 | `1` |

### LLM 配置

| 变量 | 说明 |
|:---|:---|
| `LLM_PROVIDER` | LLM 提供商：`deepseek` / `mimo` / `ollama` / `openai_compatible` |
| `LLM_API_KEY` | DeepSeek API Key |
| `LLM_CLOUD_MODEL` | DeepSeek 模型名（默认 `deepseek-chat`） |
| `MIMO_API_KEY` | 小米 MiMo API Key |
| `MIMO_MODEL` | MiMo 模型名（默认 `mimo-v2.5`） |
| `LLM_API_URL` | Ollama 服务地址 |
| `LLM_MODEL_NAME` | Ollama 模型名 |

详见 [LLM 部署指南](project/bird-vision/docs/llm_deploy.md)。

## 功能页面

| 页面 | 路径 | 说明 |
|:---|:---|:---|
| 首页 | `/` | 项目介绍与功能导航 |
| 鸟类识别 | `/detect` | 上传图片，AI 自动识别鸟类物种 |
| 知识问答 | `/chat` | 与 LLM 对话，深入了解鸟类知识 |
| 数据统计 | `/stats` | 识别数据可视化分析 |
| 物种百科 | `/species` | 50 种鸟类物种信息浏览 |

## API 文档

所有 API 以 `/api` 为前缀。

### 鸟类识别

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| POST | `/api/detect` | 上传图片执行识别 |
| GET | `/api/detect/history` | 获取识别历史（最近 20 条） |
| DELETE | `/api/detect/history/<id>` | 删除单条记录 |
| DELETE | `/api/detect/history/clear` | 清空所有记录 |

### 知识问答

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| POST | `/api/chat` | LLM 对话 |
| POST | `/api/species/<id>/qa` | 基于识别结果的物种问答 |
| GET | `/api/llm/providers` | 获取可用 LLM 列表 |
| GET | `/api/llm/health` | LLM 健康检查 |

### 统计与百科

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/api/stats/overview` | 概览统计 |
| GET | `/api/stats/species_distribution` | 物种分布 |
| GET | `/api/stats/daily_trend` | 每日趋势 |
| GET | `/api/species` | 物种列表 |
| GET | `/api/species/<id>` | 物种详情 |

## 识别策略

BirdVision 采用三级 fallback 检测策略，最大化识别成功率：

```
上传图片
  │
  ├─ ① 自定义 YOLO 模型 (best.pt)
  │    识别 15 种中国常见鸟类（置信度 ≥ 0.2）
  │    ✗ 未检测到
  │
  ├─ ② 预训练 YOLO (yolo11n.pt)
  │    检测 COCO "bird" 类别（通用鸟类检测）
  │    ✗ 未检测到
  │
  └─ ③ LLM 多模态视觉识别
       发送图片至 MiMo/DeepSeek 视觉模型
       返回物种名称 + 置信度
```

## 模型训练

### YOLO 检测模型训练

```bash
cd training/yolo

# 自动准备数据集（从 Unsplash 下载图片 + YOLO 自动标注）
python prepare_dataset.py

# 开始训练
python train.py
```

训练参数：epochs=50, batch=16, imgsz=416，输出至 `runs/detect/bird_train/`。

### LLM 微调

```bash
cd training/llm

# 使用 LLaMA Factory + LoRA 微调
python finetune_bird_llm.py
```

基于 Qwen2.5-7B，LoRA rank=8，4bit 量化，训练数据为鸟类知识问答对。

## 生产部署

### Gunicorn + Systemd 部署

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动服务
gunicorn --workers 2 --threads 2 --timeout 120 \
  --bind 127.0.0.1:5000 run:app
```

Nginx 反向代理配置：

```nginx
server {
    listen 80;
    server_name project.example.com;

    client_max_body_size 16m;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /opt/BirdVision/project/bird-vision/app/static/;
    }
}
```

Systemd 服务配置：

```ini
[Unit]
Description=BirdVision Flask Application
After=network.target

[Service]
User=root
WorkingDirectory=/opt/BirdVision/project/bird-vision
EnvironmentFile=/opt/BirdVision/project/bird-vision/.env
ExecStart=/opt/BirdVision/project/bird-vision/venv/bin/gunicorn \
    --workers 2 --threads 2 --timeout 120 \
    --bind 127.0.0.1:5000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## 数据库

### 数据模型

| 表名 | 说明 |
|:---|:---|
| `bird_species` | 鸟类物种信息（中文名/英文名/学名/科/描述/栖息地/保护等级） |
| `detection_record` | 识别记录（图片路径/物种名/置信度/时间/IP） |
| `chat_record` | 对话记录（问题/回答/模型名/时间） |

### 初始化

```bash
# 初始化数据库（插入 50 种鸟类种子数据）
python -m app.init_db
```

> 注意：若数据库已有数据，`init_db` 会跳过种子数据插入。

## 依赖列表

```
flask>=3.1.1
flask-sqlalchemy>=3.1.1
sqlalchemy>=2.0.30
ultralytics>=8.3.0
opencv-python>=4.10.0.84
requests>=2.32.3
Pillow>=11.2.1
Werkzeug>=3.1.3
python-dotenv>=1.0.0
```

## License

MIT License
