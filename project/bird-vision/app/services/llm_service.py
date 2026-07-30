# -*- coding: utf-8 -*-
"""LLM 对话服务（支持 Ollama / DeepSeek / MIMO / 任意 OpenAI 兼容 API）"""

import base64
import json
import logging
import os
import re

import requests

from app import db
from app.models import ChatRecord

logger = logging.getLogger(__name__)

# 提供商显示名称映射（供前端展示和 system_prompt 身份注入使用）
PROVIDER_LABELS = {
    'deepseek': 'DeepSeek',
    'mimo': '小米 MiMo',
    'ollama': 'Ollama 本地',
    'openai_compatible': '自定义 API',
}

# ===== 【最高优先级·身份强制锚点】 =====
# 放在 system_prompt 的最开头，让模型第一时间看到自己是谁。
# 明确声明：身份类问题 优先级高于 "鸟类专家" 的话题过滤规则，
# 避免出现"用户问你是什么模型，模型却说'我只回答鸟类问题'"的情况。
_IDENTITY_RULE_PREFIX = (
    "【关于你自身身份的·最高优先级回答规则】\n"
    "以下规则优先级高于任何话题边界或角色设定。只要用户询问任何关于你自身的问题，"
    "(包括但不限于：你是什么模型 / 你是哪家公司的 / 你是 DeepSeek 吗 / "
    "你是 MiMo 吗 / 你用的什么 API / 你接的什么模型 / 你叫什么 / 你是大模型吗)，"
    "你必须首先、明确、如实地用下面信息回答，绝对不能编造，也不能回避：\n"
    "  - 服务名称（API 提供商）：{provider_label}\n"
    "  - 模型名称：{model_name}\n"
    "标准回答模板（可在此基础上扩展，但必须包含这些关键信息）：\n"
    "我是通过 {provider_label} 的 {model_name} 模型为您提供服务的鸟类知识专家助手。\n"
    "重要：\n"
    "- 如果用户问『你是 DeepSeek 吗』，只有当服务名称等于 DeepSeek 时才能回答是，"
    "否则必须回答否并说出真实的服务名称与模型名称。\n"
    "- 如果用户问『你是 MiMo 吗』，只有当服务名称等于 小米 MiMo 时才能回答是，"
    "否则必须回答否并说出真实的服务名称与模型名称。\n"
    "- 如果用户问『你是本地模型 / Ollama 吗』，只有当服务名称等于 Ollama 本地时才能回答是，"
    "否则必须回答否并说出真实的服务名称与模型名称。\n"
    "- 绝对不要声称自己是与上述信息不一致的任何品牌、公司或模型，"
    "比如在使用 小米 MiMo 时不要说自己基于 DeepSeek，反之亦然。\n"
    "- 身份类问题不需要执行『鸟类话题过滤』，直接按上述要求回答，然后再引导到鸟类话题即可。\n\n"
)

# 鸟类专家角色描述（身份锚点之后才追加）
_BIRD_EXPERT_CORE = (
    "【你的角色：资深鸟类生态学专家】\n"
    "除了上述身份问题按最高优先级回答之外，对于其他问题，你是一位资深的鸟类生态学专家，"
    "拥有丰富的鸟类分类学、行为学和生态保护知识。"
    "请用专业但通俗易懂的语言回答用户关于鸟类的各种问题，包括但不限于："
    "鸟类识别特征、栖息地与分布、生活习性、迁徙规律、保护现状等。"
    "如果问题与鸟类无关（且不属于身份类问题），请礼貌地引导用户回到鸟类话题。"
)


# ===== 物种上下文注入（知识问答模块串联识别结果） =====
# 当 detect 页面识别出物种后，跳转到 /chat?context=...，后端用下面格式拼进 system prompt：
_SPECIES_CONTEXT_TEMPLATE = (
    "\n\n【本次对话的上下文·基于最近一次鸟类识别结果】\n"
    "用户刚刚通过图片识别出了一种鸟类，请你接下来的回答**始终围绕并优先引用以下物种信息**。\n"
    "如果用户问『它分布在哪里』『如何保护它』『它吃什么』等省略主语的问题，默认主语就是下面『物种名称』里列出的鸟类，不要让用户再重复提问名称。\n"
    "对于该物种的所有问题，先尝试引用『数据库信息』回答；如果数据库信息不足，再结合你专业的鸟类生态学知识补充；不要与数据库已有的信息矛盾（比如科属、保护等级）。\n"
    "【物种名称】：{species_name}\n"
    "{db_info_block}"
    "========================\n"
)


class LLMService:
    """
    统一的 LLM 对话服务，自动适配 Ollama / OpenAI 兼容接口。

    使用方式：
        # 方式1：从 Flask config 自动读取
        llm = LLMService.from_app_config(current_app.config)

        # 方式2：手动指定
        llm = LLMService(
            api_url='https://api.deepseek.com/v1/chat/completions',
            model_name='deepseek-chat',
            api_key='sk-xxx',
            provider='deepseek',
        )

    Ollama 协议                          OpenAI 兼容协议
    ────────────                        ──────────────────
    POST /api/chat                      POST /v1/chat/completions
    {"model":"x","messages":[...]}      {"model":"x","messages":[...]}
                                        + Authorization: Bearer <key>
    """

    def __init__(self, api_url, model_name, api_key=None, provider='ollama', **kwargs):
        """
        初始化 LLM 服务。

        Args:
            api_url:   完整的 API 端点地址
            model_name: 模型名称
            api_key:   API Key（OpenAI 兼容接口必填）
            provider:  ollama | deepseek | mimo | openai_compatible
            **kwargs:  忽略额外字段（如 label）以兼容 Config.get_llm_config()
        """
        self.api_url = api_url
        self.model_name = model_name
        self.api_key = api_key
        self.provider = provider

    # ----------------------------------------------------------------
    # 工厂方法
    # ----------------------------------------------------------------

    @classmethod
    def from_app_config(cls, app_config):
        """
        从 Flask 应用配置创建 LLMService 实例。

        优先使用 Config.get_llm_config() 整合配置，
        如果 config 对象没有该方法则回退到手动读取键值。
        """
        try:
            llm_config = app_config['_LLM_CONFIG']
        except KeyError:
            from config import Config
            llm_config = Config.get_llm_config()

        return cls(**llm_config)

    # ----------------------------------------------------------------
    # 物种上下文（识别结果 → 知识问答串联）
    # ----------------------------------------------------------------

    @staticmethod
    def _build_species_context_prompt(system_prompt, species_context):
        """把识别出的物种信息拼接到 system prompt，用于知识问答模块串联。

        Args:
            system_prompt:  已组装好的 system prompt（身份锚点 + 鸟类专家）
            species_context: str | dict。
                - str: 直接当物种名
                - dict: {species_name, species_id?, species_info?}
        """
        if not species_context:
            return system_prompt

        # 兼容字符串或 dict
        if isinstance(species_context, str):
            species_name = species_context.strip()
            species_info = None
        elif isinstance(species_context, dict):
            species_name = (
                species_context.get('species_name')
                or species_context.get('name_cn')
                or species_context.get('name_en')
                or ''
            ).strip()
            species_info = (
                species_context.get('species_info')
                or species_context
            )
        else:
            return system_prompt

        if not species_name:
            return system_prompt

        # 组装数据库信息块（如果有）
        db_lines = []
        if species_info and isinstance(species_info, dict):
            mapping = [
                ('info_family',   ['科属', 'family', '科']),
                ('info_habitat',  ['栖息地', 'habitat']),
                ('info_status',   ['保护状态', '保护等级', 'conservation_status']),
                ('info_sci',      ['学名', 'scientific_name']),
                ('info_en',       ['英文名', 'name_en']),
                ('info_desc',     ['简介', 'description', '描述']),
            ]
            for key_cn, keys in mapping:
                val = ''
                for k in keys:
                    v = species_info.get(k)
                    if v and str(v).strip() and str(v).strip() != '——':
                        val = str(v).strip()
                        break
                if val:
                    for k in keys[:3]:
                        pass
                    label = keys[0]
                    db_lines.append(f'【数据库·{label}】：{val}')

        db_block = ''
        if db_lines:
            db_block = '【数据库信息（高优先级，不要与之矛盾）】：\n' + '\n'.join(db_lines) + '\n'

        context_block = _SPECIES_CONTEXT_TEMPLATE.format(
            species_name=species_name,
            db_info_block=db_block
        )
        return (system_prompt or '') + context_block

    # ----------------------------------------------------------------
    # 对话核心
    # ----------------------------------------------------------------

    def chat(self, message, history=None, system_prompt=None, species_context=None):
        """
        调用 LLM 进行对话。

        Args:
            message:         用户当前消息文本
            history:         对话历史列表，每项 {role, content}
            system_prompt: 系统提示词，默认使用鸟类专家角色 + 动态身份注入
            species_context: 可选，鸟类识别上下文（用于识别结果）。
                             支持传 dict: {
                                'species_name': str (必填，中文名或英文名),
                                'species_id': int|None (BirdSpecies ID，
                                'species_info': dict|None (bird_species.to_dict())
                             也支持只传字符串：str (只表示物种名称）

        Returns:
            dict: {
                'success': bool,        # True 表示拿到有效回复，False 表示服务错误
                'reply': str,           # 模型回复或用户友好的错误消息
                'error_type': str|None, # connection / timeout / auth / not_found / rate_limit / server / unknown
                'provider': str,        # 实际使用的 provider
                'model': str,           # 实际使用的模型名
            }
        """
        # 取当前模型的显示名（用于身份注入、健康提示、前端展示回显）
        provider_label = PROVIDER_LABELS.get(self.provider, self.provider)

        # 未指定 system_prompt 时：先写身份强制锚点（最高优先级，放最前面），再写鸟类专家规则
        # （解决：MiMo 说自己是 DeepSeek，以及"身份问题被当作非鸟类话题过滤"两个问题）
        if system_prompt is None:
            system_prompt = (
                _IDENTITY_RULE_PREFIX.format(
                    provider_label=provider_label,
                    model_name=self.model_name,
                )
                + _BIRD_EXPERT_CORE
            )

        # ===== 物种上下文注入（串联识别结果 → 知识问答）=====
        if species_context:
            system_prompt = self._build_species_context_prompt(
                system_prompt, species_context
            )

        # 构建消息列表
        messages = [{'role': 'system', 'content': system_prompt}]
        if history:
            for item in history:
                if 'role' in item and 'content' in item:
                    messages.append({
                        'role': item['role'],
                        'content': item['content'],
                    })
        messages.append({'role': 'user', 'content': message})

        # 根据 provider 选择请求方式
        if self.provider == 'ollama':
            result = self._call_ollama(messages)
        else:
            result = self._call_openai_compatible(messages)

        # 成功才持久化对话记录（避免把错误消息存进去）
        if result.get('success'):
            self._save_record(message, result['reply'])

        # 补充 provider / model 信息，方便上层使用
        result.setdefault('provider', self.provider)
        result.setdefault('model', self.model_name)
        return result

    # ----------------------------------------------------------------
    # 连接性 / API Key 检测（用于页面初始化时的健康检查）
    # ----------------------------------------------------------------

    def check_connection(self):
        """
        快速检测当前 LLM 配置是否可用（API Key 是否有效 / 服务是否在线）。

        原理：用极短的 prompt 发起一次轻量请求，看 HTTP 状态码。
        不依赖模型输出内容，只用于判断 401/404/连接失败 等情况。

        Returns:
            dict: {
                'ok': bool,
                'error_type': str|None,
                'message': str,        # 用户友好的中文说明
            }
        """
        # 极短的消息，降低请求开销
        probe_messages = [
            {'role': 'system', 'content': '你是一个助手。'},
            {'role': 'user', 'content': 'hi'},
        ]

        if self.provider == 'ollama':
            raw = self._call_ollama(probe_messages, _probe=True)
        else:
            raw = self._call_openai_compatible(probe_messages, _probe=True)

        if raw.get('success'):
            return {
                'ok': True,
                'error_type': None,
                'message': f'{PROVIDER_LABELS.get(self.provider, self.provider)} 连接正常',
            }

        label = PROVIDER_LABELS.get(self.provider, self.provider)
        msg = raw.get('reply', '连接失败')
        # 把错误信息打磨得更友好、更具体
        error_type = raw.get('error_type')
        if error_type == 'auth':
            user_msg = f'{label} 的 API Key 无效或已过期，请前往配置文件检查并更新。'
        elif error_type == 'not_found':
            if self.provider == 'ollama':
                user_msg = f'{label} 未找到模型「{self.model_name}」，请先执行 `ollama pull {self.model_name}`。'
            else:
                user_msg = f'{label} 未找到模型「{self.model_name}」，请检查 API 地址和模型名称。'
        elif error_type == 'connection':
            if self.provider == 'ollama':
                user_msg = f'无法连接到 {label}，请确认 Ollama 已启动（`ollama serve`）并正在监听 {self.api_url}。'
            else:
                user_msg = f'无法连接到 {label}，请检查网络连接或 API 地址是否正确。'
        elif error_type == 'timeout':
            user_msg = f'{label} 响应超时，请稍后重试。'
        elif error_type == 'rate_limit':
            user_msg = f'{label} 请求过于频繁（429），请稍后再试。'
        elif error_type == 'server':
            user_msg = f'{label} 服务端暂时不可用（5xx），请稍后重试。'
        else:
            user_msg = f'{label} 不可用：{msg}'

        return {
            'ok': False,
            'error_type': error_type,
            'message': user_msg,
        }

    # ----------------------------------------------------------------
    # Ollama 协议
    # ----------------------------------------------------------------

    def _call_ollama(self, messages, _probe=False):
        """调用 Ollama /api/chat 端点

        Args:
            messages: 消息列表
            _probe:   是否是连接探测（探测时超时更短，输出更简洁）

        Returns:
            dict: {success, reply, error_type}
        """
        timeout = 10 if _probe else 120
        payload = {
            'model': self.model_name,
            'messages': messages,
            'stream': False,
        }
        try:
            resp = requests.post(self.api_url, json=payload, timeout=timeout)
            resp.raise_for_status()
            content = resp.json().get('message', {}).get('content', '')
            if not content:
                return {'success': False, 'reply': '服务暂时无法回复。', 'error_type': 'unknown'}
            return {'success': True, 'reply': content, 'error_type': None}
        except requests.ConnectionError:
            logger.warning("Ollama 连接失败: %s", self.api_url)
            return {
                'success': False,
                'reply': '本地 LLM 服务未启动，请安装 Ollama 并运行 `ollama serve` 后重试。',
                'error_type': 'connection',
            }
        except requests.Timeout:
            logger.warning("Ollama 请求超时: %s", self.api_url)
            return {
                'success': False,
                'reply': 'AI 回复时间较长，请稍后再试。',
                'error_type': 'timeout',
            }
        except requests.HTTPError as e:
            status = e.response.status_code if e.response else 0
            if status == 404:
                return {
                    'success': False,
                    'reply': '本地 LLM 服务未找到，请确认 Ollama 已启动且模型已拉取。',
                    'error_type': 'not_found',
                }
            if status >= 500:
                return {
                    'success': False,
                    'reply': 'AI 服务端暂时不可用，请稍后重试。',
                    'error_type': 'server',
                }
            logger.error("Ollama HTTP 错误 [%s]: %s", status, e)
            return {
                'success': False,
                'reply': 'AI 服务暂时不可用，请稍后重试。',
                'error_type': 'unknown',
            }
        except requests.RequestException as e:
            logger.error("Ollama 请求异常: %s", e)
            return {
                'success': False,
                'reply': 'AI 服务连接异常，请检查网络后重试。',
                'error_type': 'connection',
            }

    # ----------------------------------------------------------------
    # OpenAI 兼容协议（DeepSeek / MIMO / 其它）
    # ----------------------------------------------------------------

    def _call_openai_compatible(self, messages, _probe=False):
        """调用 OpenAI 兼容的 /v1/chat/completions 端点（DeepSeek / MiMo 等）

        Args:
            messages: 消息列表
            _probe:   是否是连接探测（探测时 max_tokens 更小，超时更短）

        Returns:
            dict: {success, reply, error_type}
        """
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        timeout = 15 if _probe else 120
        payload = {
            'model': self.model_name,
            'messages': messages,
            'stream': False,
            'temperature': 0.7,
            'max_tokens': 16 if _probe else 4096,
        }

        try:
            resp = requests.post(
                self.api_url, json=payload, headers=headers, timeout=timeout
            )
        except requests.ConnectionError:
            logger.warning("%s 连接失败: %s", self.provider, self.api_url)
            return {
                'success': False,
                'reply': 'AI 服务暂时不可用，请检查网络连接后重试。',
                'error_type': 'connection',
            }
        except requests.Timeout:
            logger.warning("%s 请求超时: %s", self.provider, self.api_url)
            return {
                'success': False,
                'reply': 'AI 回复时间较长，请稍后再试。',
                'error_type': 'timeout',
            }
        except requests.RequestException as e:
            logger.error("%s 请求异常: %s", self.provider, e)
            return {
                'success': False,
                'reply': 'AI 服务连接异常，请检查网络后重试。',
                'error_type': 'connection',
            }

        # 非 200 状态码处理
        if resp.status_code != 200:
            logger.error("%s HTTP %d: %s", self.provider, resp.status_code, resp.text[:500])
            if resp.status_code == 401:
                return {
                    'success': False,
                    'reply': 'AI 服务认证失败，API Key 可能已过期，请检查配置。',
                    'error_type': 'auth',
                }
            elif resp.status_code == 404:
                return {
                    'success': False,
                    'reply': 'AI 服务未找到，请确认 API 地址和模型名称是否正确。',
                    'error_type': 'not_found',
                }
            elif resp.status_code == 429:
                return {
                    'success': False,
                    'reply': 'AI 服务请求过于频繁，请稍后再试。',
                    'error_type': 'rate_limit',
                }
            elif resp.status_code >= 500:
                return {
                    'success': False,
                    'reply': 'AI 服务端暂时不可用，请稍后重试。',
                    'error_type': 'server',
                }
            else:
                return {
                    'success': False,
                    'reply': 'AI 服务暂时不可用，请稍后重试。',
                    'error_type': 'unknown',
                }

        try:
            data = resp.json()
        except ValueError:
            logger.error("%s 返回非 JSON 响应: %s", self.provider, resp.text[:300])
            return {
                'success': False,
                'reply': 'AI 服务返回格式异常，请稍后重试。',
                'error_type': 'unknown',
            }

        # 兼容推理模型：content 可能为空，需回退到 reasoning_content
        message_obj = data.get('choices', [{}])[0].get('message', {})
        content = message_obj.get('content', '')
        if not content:
            content = message_obj.get('reasoning_content', '')

        if not content:
            return {'success': False, 'reply': '服务暂时无法回复。', 'error_type': 'unknown'}

        return {'success': True, 'reply': content, 'error_type': None}

    # ----------------------------------------------------------------
    # 鸟类视觉识别
    # ----------------------------------------------------------------

    def identify_bird(self, image_path, known_species=None):
        """
        使用多模态 LLM 识别图片中的鸟类物种。

        Args:
            image_path: 图片文件的绝对路径
            known_species: 已知的物种列表（可选），用于约束识别范围

        Returns:
            dict: {
                'success': bool,
                'is_bird': bool,
                'species_name': str,      # 中文物种名
                'confidence': float,     # 置信度 0-1
                'description': str,       # 识别依据描述
            }
        """
        # 构建提示词
        if known_species and len(known_species) > 0:
            species_list = '、'.join(known_species)
            prompt = (
                '请仔细观察这张图片，识别其中的鸟类。'
                f'请从以下鸟类中选择最匹配的一种：{species_list}。'
                '请严格按照以下 JSON 格式回复（用 markdown 代码块包裹也可以）：\n'
                '{\n'
                '  "is_bird": true/false,\n'
                '  "species_name": "中文物种名",\n'
                '  "confidence": 0.95,\n'
                '  "description": "识别依据，比如羽毛特征、体型、喙的形状等"\n'
                '}\n'
                '如果图片中没有鸟类，is_bird 设为 false。'
            )
        else:
            prompt = (
                '请仔细观察这张图片，识别其中的鸟类。'
                '请给出你认为最准确的鸟类物种名称（中文名）。'
                '请严格按照以下 JSON 格式回复（用 markdown 代码块包裹也可以）：\n'
                '{\n'
                '  "is_bird": true/false,\n'
                '  "species_name": "中文物种名",\n'
                '  "confidence": 0.95,\n'
                '  "description": "识别依据，比如羽毛特征、体型、喙的形状等"\n'
                '}\n'
                '如果图片中没有鸟类，is_bird 设为 false。'
            )

        # 读取并编码图片
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            logger.error("读取图片失败: %s", e)
            return {'success': False, 'error': '图片读取失败'}

        # 尝试使用视觉模型
        result = self._call_vision_model(prompt, image_data)
        return result

    def _call_vision_model(self, prompt, image_base64):
        """
        调用多模态模型进行图像识别。

        尝试顺序：MiMo（经验证支持视觉）→ DeepSeek → 其他
        """
        vision_attempts = []

        # MiMo 经验证支持视觉，优先尝试
        try:
            from config import Config
            mimo_cfg = Config.get_llm_config(provider='mimo')
            if mimo_cfg.get('api_key'):
                vision_attempts.append({
                    'api_url': mimo_cfg['api_url'],
                    'model': mimo_cfg['model_name'],
                    'api_key': mimo_cfg['api_key'],
                    'provider': 'mimo',
                })
        except Exception:
            pass

        # 当前 provider 是 mimo 的话也加进去
        if self.provider == 'mimo' and self.api_key:
            # 如果已经加了就跳过
            already_has_mimo = any(a.get('provider') == 'mimo' for a in vision_attempts)
            if not already_has_mimo:
                vision_attempts.insert(0, {
                    'api_url': self.api_url,
                    'model': self.model_name,
                    'api_key': self.api_key,
                    'provider': 'mimo',
                })

        # 尝试 DeepSeek
        try:
            from config import Config
            ds_cfg = Config.get_llm_config(provider='deepseek')
            if ds_cfg.get('api_key'):
                vision_attempts.append({
                    'api_url': ds_cfg['api_url'],
                    'model': 'deepseek-v4-flash',  # 尝试 v4 支持视觉
                    'api_key': ds_cfg['api_key'],
                    'provider': 'deepseek',
                })
        except Exception:
            pass

        # 如果都没有，用当前的
        if not vision_attempts and self.api_key:
            vision_attempts.append({
                'api_url': self.api_url,
                'model': self.model_name,
                'api_key': self.api_key,
                'provider': self.provider,
            })

        for attempt in vision_attempts:
            try:
                result = self._call_openai_vision(
                    api_url=attempt['api_url'],
                    model=attempt['model'],
                    api_key=attempt['api_key'],
                    prompt=prompt,
                    image_base64=image_base64,
                )
                if result and result.get('success') and result.get('is_bird'):
                    logger.info("视觉识别成功 (provider=%s): %s",
                                attempt['provider'], result.get('species_name'))
                    return result
                elif result and result.get('success'):
                    # 成功调用了但说不是鸟，也返回
                    return result
            except Exception as e:
                logger.warning("视觉识别尝试失败 (provider=%s): %s",
                               attempt['provider'], e)
                continue

        logger.warning("所有视觉识别尝试均失败")
        return {'success': False, 'error': '视觉识别服务不可用'}

    def _call_openai_vision(self, api_url, model, api_key, prompt, image_base64):
        """调用 OpenAI 兼容的多模态接口"""
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        payload = {
            'model': model,
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/jpeg;base64,{image_base64}'
                            }
                        }
                    ]
                }
            ],
            'stream': False,
            'max_tokens': 1024,
            'temperature': 0.1,
        }

        try:
            resp = requests.post(api_url, json=payload, headers=headers, timeout=60)
        except requests.RequestException as e:
            logger.error("视觉模型请求异常: %s", e)
            return {'success': False, 'error': str(e)}

        if resp.status_code != 200:
            logger.error("视觉模型 HTTP %d: %s", resp.status_code, resp.text[:300])
            return {'success': False, 'error': f'HTTP {resp.status_code}'}

        try:
            data = resp.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            return self._parse_vision_result(content)
        except Exception as e:
            logger.error("解析视觉模型响应失败: %s", e)
            return {'success': False, 'error': '响应解析失败'}

    def _parse_vision_result(self, content):
        """解析 LLM 返回的 JSON 识别结果"""
        # 尝试直接解析 JSON
        try:
            data = json.loads(content)
            return self._extract_bird_info(data)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown 代码块中提取 JSON
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)```', content, re.DOTALL | re.IGNORECASE)
        if json_match:
            try:
                data = json.loads(json_match.group(1).strip())
                return self._extract_bird_info(data)
            except json.JSONDecodeError:
                pass

        # 尝试提取第一个完整的 JSON 对象（用大括号匹配）
        brace_count = 0
        start_idx = -1
        for i, ch in enumerate(content):
            if ch == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif ch == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx >= 0:
                    json_str = content[start_idx:i+1]
                    try:
                        data = json.loads(json_str)
                        return self._extract_bird_info(data)
                    except json.JSONDecodeError:
                        pass
                    start_idx = -1

        # 最后兜底：尝试从文本中提取物种名
        logger.warning("无法解析视觉识别结果为 JSON，原始内容前200字: %s", content[:200])
        return {
            'success': False,
            'error': '结果格式解析失败',
            'raw_content': content,
        }

    def _extract_bird_info(self, data):
        """从字典数据中提取鸟类识别信息，兼容多种字段名"""
        # 标准字段
        is_bird = data.get('is_bird', None)
        species_name = data.get('species_name', '')
        confidence = data.get('confidence', None)
        description = data.get('description', '')

        # 如果 is_bird 没有，尝试从 bird_identification 等嵌套结构中提取
        if is_bird is None and not species_name:
            bird_info = data.get('bird_identification', {})
            if isinstance(bird_info, dict):
                species_name = bird_info.get('common_name', '') or bird_info.get('name', '')
                if not species_name:
                    species_name = bird_info.get('species', '')
                description = bird_info.get('identification_features', [])
                if isinstance(description, list):
                    description = '、'.join(description)
                elif not isinstance(description, str):
                    description = str(description)

            # 如果有 bird 相关字段，认为是鸟
            if species_name or bird_info:
                is_bird = True

        # 如果 is_bird 还是 None，根据有没有 species_name 判断
        if is_bird is None:
            is_bird = bool(species_name)

        # 置信度处理
        if confidence is None:
            confidence = 0.8  # 默认给一个较高的置信度，因为 LLM 识别一般较准
        elif isinstance(confidence, str):
            # 如果是百分比字符串
            confidence = confidence.replace('%', '').strip()
            try:
                confidence = float(confidence)
                if confidence > 1:
                    confidence = confidence / 100
            except ValueError:
                confidence = 0.8
        elif confidence > 1:
            confidence = confidence / 100

        # 清理物种名：去掉括号里的内容，取第一个名字
        if species_name:
            # 取括号前的主名
            species_name = re.split(r'[（(]', species_name)[0].strip()
            # 去掉"又称"、"也叫"等
            species_name = re.split(r'[，,、]', species_name)[0].strip()

        return {
            'success': True,
            'is_bird': bool(is_bird),
            'species_name': species_name,
            'confidence': float(confidence),
            'description': description,
        }

    # ----------------------------------------------------------------
    # 对话记录
    # ----------------------------------------------------------------

    def _save_record(self, question, answer):
        """将对话记录持久化到数据库。"""
        try:
            record = ChatRecord(
                question=question,
                answer=answer,
                model_name=f'{self.provider}:{self.model_name}',
            )
            db.session.add(record)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("保存对话记录失败")
