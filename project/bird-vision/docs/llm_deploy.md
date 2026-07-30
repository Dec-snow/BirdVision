# LLM 部署指南

本指南介绍如何为 BirdVision 项目配置 LLM 大模型服务，支持以下三种方案：

| 方案 | 提供商 | 说明 |
|------|--------|------|
| A | DeepSeek | 云端 API，无需本地 GPU，性价比高 |
| B | 小米 MiMo | 云端 API，OpenAI 兼容协议 |
| C | Ollama 本地 | 本地运行，无需联网（需要 GPU） |

---

## 方案选择建议

- **新手 / 无 GPU** → 选方案 A（DeepSeek）或 B（小米 MiMo），注册即用
- **有 NVIDIA GPU 且想离线使用** → 选方案 C（Ollama 本地）

---

## 方案 A：使用 DeepSeek API（推荐）

### A1. 获取 API Key
1. 访问 https://platform.deepseek.com
2. 注册账号并登录
3. 进入「API Keys」页面，点击「创建 API Key」
4. 复制生成的 Key（形如 `sk-xxxxxxxx`）

### A2. 配置环境变量

**Windows PowerShell：**
```powershell
$env:LLM_PROVIDER = "deepseek"
$env:LLM_API_KEY = "sk-你的DeepSeek_API_Key"
$env:LLM_CLOUD_MODEL = "deepseek-chat"
```

**Windows CMD：**
```cmd
set LLM_PROVIDER=deepseek
set LLM_API_KEY=sk-你的DeepSeek_API_Key
set LLM_CLOUD_MODEL=deepseek-chat
```

**永久设置（推荐）：**
1. 右键"此电脑" → "属性" → "高级系统设置" → "环境变量"
2. 新建以下用户变量：
   - `LLM_PROVIDER` = `deepseek`
   - `LLM_API_KEY` = `sk-你的API_Key`
   - `LLM_CLOUD_MODEL` = `deepseek-chat`

### A3. 启动测试
```bash
cd bird-vision
python run.py
```
启动日志应显示：`LLM: deepseek (deepseek-chat) - API Key: 已设置`

---

## 方案 B：使用小米 MiMo API

### B1. 获取 API Key
1. 访问小米 MiMo 开放平台获取 API Key
2. MiMo 使用 OpenAI 兼容协议，base_url 为 `https://api.xiaomimimo.com`
3. 在控制台创建 API Key

### B2. 配置环境变量

在 `.env` 文件中设置：
```
LLM_PROVIDER=mimo
MIMO_API_KEY=sk-你的MiMo_API_Key
MIMO_MODEL=mimo-v2.5
```

---

## 方案 C：使用其他 OpenAI 兼容 API

如果你有其他兼容 OpenAI 接口的服务（如 vLLM、LocalAI、OpenRouter 等）：

```powershell
$env:LLM_PROVIDER = "openai_compatible"
$env:LLM_BASE_URL = "https://你的服务地址"
$env:LLM_API_KEY = "sk-你的API_Key"
$env:LLM_CLOUD_MODEL = "模型名称"
```

---

## 方案 D：Ollama 本地部署（备选）

### D1. 安装 Ollama
1. 访问 https://ollama.com 下载 Windows 安装包
2. 安装完成后终端验证：`ollama --version`

### D2. 拉取模型
```bash
# 推荐使用 DeepSeek-R1 8B（约 4.7GB）
ollama pull deepseek-r1:8b

# 或使用较小的模型
ollama pull qwen2.5:7b
```

### D3. 启动服务
```bash
ollama serve
```
默认监听 `http://localhost:11434`

### D4. 配置环境变量（切回 Ollama）
```powershell
$env:LLM_PROVIDER = "ollama"
```

### D5. 验证 API
```bash
curl http://localhost:11434/api/chat -d "{\"model\": \"deepseek-r1:8b\", \"messages\": [{\"role\": \"user\", \"content\": \"介绍丹顶鹤\"}], \"stream\": false}"
```

---

## 附录：LLaMA Factory 微调模型导入 Ollama

如果你已经使用 LLaMA Factory 完成了鸟类专家模型微调：

### 1. 导出并合并 LoRA
```bash
llamafactory-cli export \
  --model_name_or_path /path/to/base-model \
  --adapter_name_or_path models/llm/bird-expert \
  --template default \
  --finetuning_type lora \
  --export_dir models/llm/bird-expert-merged \
  --export_size 2
```

### 2. 转换为 GGUF 格式
```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
python convert_hf_to_gguf.py ../models/llm/bird-expert-merged \
  --outfile ../models/llm/bird-expert.gguf \
  --outtype q4_k_m
```

### 3. 导入 Ollama
创建 `Modelfile`：
```
FROM ./models/llm/bird-expert.gguf
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 1024
SYSTEM "你是一位专业的鸟类生态学专家..."
```

```bash
ollama create bird-expert -f Modelfile
```

### 4. 配置使用
```powershell
$env:LLM_PROVIDER = "ollama"
$env:LLM_MODEL_NAME = "bird-expert"
```

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `LLM 服务连接失败` | Ollama 未启动 | 执行 `ollama serve` |
| `404 Not Found` | 模型未拉取 | `ollama pull deepseek-r1:8b` |
| `401 Unauthorized` | API Key 错误 | 检查 LLM_API_KEY 是否正确 |
| `LLM 响应超时` | 模型太大/网络慢 | 用小模型或增加 timeout |
| DeepSeek 连不上 | 网络问题 | 检查是否能访问 api.deepseek.com |
