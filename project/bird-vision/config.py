# -*- coding: utf-8 -*-
"""Flask 应用配置模块"""

import os

# 项目根目录（本文件所在目录的绝对路径）
basedir = os.path.abspath(os.path.dirname(__file__))

# ---- 加载 .env 文件（优先级：环境变量 > .env 文件 > 默认值） ----
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(basedir, '.env')
    if os.path.exists(_env_path):
        load_dotenv(_env_path, override=True)
        # override=True 确保每次启动都从 .env 重新加载，避免旧值残留
except ImportError:
    # python-dotenv 未安装时静默跳过，仍可使用系统环境变量
    pass

# 打印当前 LLM 配置来源（方便排查）
_env_source = os.path.join(basedir, '.env')
if os.path.exists(_env_source):
    print(f"[配置] 已加载 .env 文件: {_env_source}")
else:
    print(f"[配置] 未找到 .env 文件，使用系统环境变量或默认值")
    print(f"[配置] 可复制 .env.example → .env 并填入你的 API Key")


class Config:
    """Flask 核心配置类"""

    # 密钥，用于 session 签名等安全场景
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bird-vision-2026-summer')

    # SQLite 数据库路径
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'birdvision.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 上传文件存储目录
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')

    # YOLO 模型权重文件路径
    YOLO_MODEL_PATH = os.path.join(basedir, 'models', 'yolo', 'best.pt')

    # ================================================================
    # LLM 配置（支持 Ollama / DeepSeek / 小米MiMo / 任意 OpenAI 兼容 API）
    # ================================================================
    # 默认提供商，可选: ollama | deepseek | mimo | openai_compatible
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'deepseek')

    # Ollama 专用
    LLM_API_URL = os.environ.get('LLM_API_URL', 'http://localhost:11434/api/chat')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'bird-expert')  # 微调后的鸟类专家模型
    LLM_BIRD_MODEL = os.environ.get('LLM_BIRD_MODEL', 'bird-expert')  # 微调后的鸟类专家模型

    # DeepSeek 专用
    LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
    LLM_CLOUD_MODEL = os.environ.get('LLM_CLOUD_MODEL', 'deepseek-chat')

    # 小米 MiMo 专用（OpenAI 兼容协议，base_url: https://api.xiaomimimo.com/v1）
    MIMO_API_KEY = os.environ.get('MIMO_API_KEY', '')
    MIMO_MODEL = os.environ.get('MIMO_MODEL', 'mimo-v2.5')

    # 自定义 OpenAI 兼容接口
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', '')

    # 上传文件大小上限：16 MB
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # ----------------------------------------------------------------
    # 各 Provider 的预设配置
    # ----------------------------------------------------------------
    _PROVIDER_PRESETS = {
        'deepseek': {
            'base_url': 'https://api.deepseek.com',
            'model': os.environ.get('LLM_CLOUD_MODEL', 'deepseek-chat'),
            'api_key': os.environ.get('LLM_API_KEY', ''),
        },
        'mimo': {
            'base_url': 'https://api.xiaomimimo.com',
            'model': os.environ.get('MIMO_MODEL', 'mimo-v2.5'),
            'api_key': os.environ.get('MIMO_API_KEY', ''),
        },
        'ollama': {
            'base_url': None,  # Ollama 用自己的 /api/chat 端点
            'model': os.environ.get('LLM_MODEL_NAME', 'qwen2.5:7b'),
            'api_key': '',
        },
    }

    # provider 显示名称映射
    _PROVIDER_LABELS = {
        'deepseek': 'DeepSeek',
        'mimo': '小米 MiMo',
        'ollama': 'Ollama 本地',
    }

    @classmethod
    def get_llm_config(cls, provider=None):
        """
        返回指定 provider 的 LLM 配置字典。

        Args:
            provider: ollama | deepseek | mimo | openai_compatible
                      为 None 时使用 LLM_PROVIDER 默认值

        Returns:
            dict: {api_url, model_name, api_key, provider, label}
        """
        if provider is None:
            provider = cls.LLM_PROVIDER
        provider = provider.lower()

        # ----- Ollama 协议 -----
        if provider == 'ollama':
            return {
                'api_url': cls.LLM_API_URL,
                'model_name': cls.LLM_MODEL_NAME,
                'api_key': None,
                'provider': 'ollama',
                'label': cls._PROVIDER_LABELS.get('ollama', 'Ollama'),
            }

        # ----- OpenAI 兼容协议 -----
        preset = cls._PROVIDER_PRESETS.get(provider, {})

        if provider == 'openai_compatible':
            if not cls.LLM_BASE_URL:
                raise ValueError(
                    'LLM_PROVIDER=openai_compatible 时必须设置 LLM_BASE_URL 环境变量'
                )
            return {
                'api_url': cls.LLM_BASE_URL.rstrip('/') + '/v1/chat/completions',
                'model_name': cls.LLM_CLOUD_MODEL,
                'api_key': cls.LLM_API_KEY,
                'provider': 'openai_compatible',
                'label': '自定义 API',
            }

        # deepseek / mimo
        base_url = (cls.LLM_BASE_URL or preset.get('base_url', '')).rstrip('/')
        return {
            'api_url': base_url + '/v1/chat/completions',
            'model_name': preset.get('model', ''),
            'api_key': preset.get('api_key', ''),
            'provider': provider,
            'label': cls._PROVIDER_LABELS.get(provider, provider),
        }

    @classmethod
    def list_available_providers(cls):
        """
        列出当前已配置 API Key 的可用提供商，供前端下拉框使用。

        Returns:
            list[dict]: [{id, label, model}]
        """
        available = []
        for pid, preset in cls._PROVIDER_PRESETS.items():
            if pid == 'ollama':
                # Ollama 不需要 Key，始终可用
                available.append({
                    'id': 'ollama',
                    'label': cls._PROVIDER_LABELS.get('ollama', 'Ollama'),
                    'model': preset['model'],
                })
            elif preset.get('api_key'):
                available.append({
                    'id': pid,
                    'label': cls._PROVIDER_LABELS.get(pid, pid),
                    'model': preset['model'],
                })
        return available
