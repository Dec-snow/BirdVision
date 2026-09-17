# -*- coding: utf-8 -*-
"""API 路由蓝图"""

import logging
import os
from datetime import datetime, timedelta
from urllib.parse import quote

from flask import Blueprint, current_app, jsonify, request

from app import db
from app.models import BirdSpecies, ChatRecord, DetectionRecord
from app.services.bird_detector import BirdDetector
from app.services.llm_service import LLMService, PROVIDER_LABELS
from config import Config

logger = logging.getLogger(__name__)

# 创建 API 蓝图，统一添加 /api 前缀
api_bp = Blueprint('api', __name__, url_prefix='/api')

# ---- 输入校验限制 ----
MAX_MESSAGE_LENGTH = 2000           # 单条消息最大长度（字符）
MAX_HISTORY_ITEMS = 20              # 对话历史最大条数
MAX_HISTORY_CONTENT_LENGTH = 2000   # 历史消息单条最大长度（字符）
_ALLOWED_HISTORY_ROLES = ('user', 'assistant')

# LLM provider fallback 固定优先级（项目约束：deepseek → mimo → ollama）
_FIXED_PROVIDER_PRIORITY = ['deepseek', 'mimo', 'ollama']


# --------------------------------------------------
# 通用辅助函数
# --------------------------------------------------

def _coerce_int(value):
    """安全转换为 int，失败返回 None。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sanitize_history(history):
    """校验并清理对话历史，返回安全的历史消息列表。"""
    if not isinstance(history, list):
        return []
    sanitized = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get('role')
        content = item.get('content')
        if role not in _ALLOWED_HISTORY_ROLES or not isinstance(content, str):
            continue
        content = content.strip()
        if not content:
            continue
        sanitized.append({'role': role, 'content': content[:MAX_HISTORY_CONTENT_LENGTH]})
    return sanitized[-MAX_HISTORY_ITEMS:]


def _build_provider_try_order(preferred, provider_ids):
    """
    构建 provider 尝试顺序：用户指定 > 固定优先级 > 其余可用。
    """
    try_order = []
    if preferred and preferred in provider_ids:
        try_order.append(preferred)
    for pid in _FIXED_PROVIDER_PRIORITY:
        if pid in provider_ids and pid not in try_order:
            try_order.append(pid)
    for pid in provider_ids:
        if pid not in try_order:
            try_order.append(pid)
    return try_order


def _resolve_species_context(species_id, species_name, species_info=None):
    """
    根据物种 ID / 名称解析物种信息（识别结果 → 问答串联）。

    返回 (sp, species_name, species_info)，sp 为 BirdSpecies 实例或 None。
    """
    sp = None
    sid = _coerce_int(species_id)
    if sid:
        sp = db.session.get(BirdSpecies, sid)
        if sp:
            species_info = sp.to_dict()
            species_name = species_info.get('name_cn') or species_info.get('name_en') or species_name
    if not sp and species_name:
        sp = _resolve_species_from_name(species_name)
        if sp:
            species_info = sp.to_dict()
            species_name = species_info.get('name_cn') or species_info.get('name_en') or species_name
    return sp, species_name, species_info


# --------------------------------------------------
# 鸟类识别接口
# --------------------------------------------------

@api_bp.route('/detect', methods=['POST'])
def detect_bird():
    """
    接收上传图片，执行鸟类检测并返回结果。

    三级识别策略：
    1. 自定义 YOLO 模型（15 种本地鸟类）
    2. YOLO 预训练模型 bird 类检测（确保能检测到鸟）
    3. LLM 视觉识别（识别具体物种，不受类别限制）

    请求：multipart/form-data，字段名 image
    返回：JSON {success, species, confidence, image_url, species_info}
    """
    file = request.files.get('image')
    if not file or not file.filename:
        return jsonify({'success': False, 'message': '未收到图片文件'}), 400

    if not BirdDetector.is_allowed_image(file.filename):
        return jsonify({
            'success': False,
            'message': '不支持的图片格式，仅支持 jpg/jpeg/png/webp/bmp/gif',
        }), 400

    try:
        # 初始化检测器并保存上传文件，得到相对路径
        detector = BirdDetector(current_app.config['YOLO_MODEL_PATH'])
        image_rel_path = detector.preprocess_image(file)
    except ValueError as e:
        logger.warning("上传文件校验失败: %s", e)
        return jsonify({'success': False, 'message': str(e)}), 400

    # 拼接绝对路径用于推理
    image_abs_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'],
        os.path.basename(image_rel_path),
    )

    if detector.model is None:
        return jsonify({
            'success': False,
            'message': 'YOLO 模型加载失败，请检查 ultralytics 是否安装',
        }), 200

    try:
        # 第一级 + 第二级：YOLO 检测（自定义模型 → 预训练 bird 类）
        detections = detector.detect(image_abs_path)

        best = None
        used_llm = False

        if detections:
            best = max(detections, key=lambda d: d['confidence'])
            # 如果是未知鸟类，或置信度低于阈值，尝试第三级 LLM 视觉识别
            if (best.get('is_unknown') or best['class_name'] == '未知鸟类'
                    or best['confidence'] < 0.5):  # 置信度低于50%时也用LLM确认
                logger.info("YOLO 无法确定具体物种（置信度 %.2f%%），尝试 LLM 视觉识别...",
                            best['confidence'] * 100)
                llm_best = _build_llm_detection(image_abs_path, best.get('bbox', [0, 0, 0, 0]))
                if llm_best:
                    best = llm_best
                    used_llm = True
        else:
            # YOLO 完全没检测到，也尝试一下 LLM 视觉识别
            logger.info("YOLO 未检测到鸟类，尝试 LLM 视觉识别...")
            llm_best = _build_llm_detection(image_abs_path, [0, 0, 0, 0])
            if llm_best:
                best = llm_best
                used_llm = True

        if not best:
            return jsonify({
                'success': False,
                'message': '未检测到鸟类，请确保图片中包含清晰的鸟类主体',
            }), 200

        # 保存识别记录
        record = DetectionRecord(
            image_path=image_rel_path,
            species_name=best['class_name'],
            confidence=best['confidence'],
            user_ip=request.remote_addr,
        )
        db.session.add(record)
        db.session.commit()

        # 查询物种详细信息（匹配 bird_species 表，优先中文名、再英文名、再别名）
        species_info = detector.get_species_info(best['class_name'])
        species_id = None
        if isinstance(species_info, dict):
            species_id = species_info.get('id')
        if not species_id:
            # detector 未匹配到 bird_species 时，再走别名字典/模糊匹配兜底
            sp = _resolve_species_from_name(best['class_name'])
            if sp:
                species_info = sp.to_dict()
                species_id = sp.id

        logger.info("识别成功: %s, 置信度: %.2f%%, IP: %s, 方式: %s",
                    best['class_name'], best['confidence'] * 100,
                    request.remote_addr, 'LLM视觉' if used_llm else 'YOLO')

        return jsonify({
            'success': True,
            'species': best['class_name'],
            'confidence': best['confidence'],
            'image_url': image_rel_path,
            'species_info': species_info,
            'species_id': species_id,
            'record_id': record.id,
            'used_llm': used_llm,
            # 供前端串联知识问答页面使用（URL 编码，避免特殊字符破坏链接）
            'qa_link': f'/chat?context={quote(best["class_name"])}'
                       + (f'&species_id={species_id}' if species_id else ''),
        })
    except Exception:
        db.session.rollback()
        logger.exception("鸟类识别接口异常")
        return jsonify({'success': False, 'message': '服务器处理异常，请稍后重试'}), 500


def _try_llm_identify(image_path):
    """
    尝试使用 LLM 视觉模型识别鸟类。

    遍历所有可用的 LLM provider，优先尝试支持视觉识别的 MiMo。
    """
    providers = Config.list_available_providers()
    provider_ids = [p['id'] for p in providers]

    # 优先尝试 mimo（经验证支持视觉识别）
    if 'mimo' in provider_ids:
        provider_ids.remove('mimo')
        provider_ids.insert(0, 'mimo')

    for pid in provider_ids:
        try:
            llm_cfg = Config.get_llm_config(provider=pid)
            llm = LLMService(**llm_cfg)
            result = llm.identify_bird(image_path)
            if result and result.get('success'):
                return result
        except Exception as e:
            logger.warning("LLM 视觉识别尝试失败 (provider=%s): %s", pid, e)
            continue

    return None


def _build_llm_detection(image_path, fallback_bbox):
    """尝试 LLM 视觉识别；成功且确认是鸟时返回检测结果 dict，否则返回 None。"""
    llm_result = _try_llm_identify(image_path)
    if not (llm_result and llm_result.get('success') and llm_result.get('is_bird')):
        return None
    logger.info("LLM 视觉识别成功: %s (置信度 %.2f%%)",
                llm_result['species_name'], llm_result['confidence'] * 100)
    return {
        'class_name': llm_result['species_name'],
        'confidence': llm_result['confidence'],
        'bbox': fallback_bbox,
    }


# ============================================================
# 物种名称解析（英→中、别名匹配）
# 用于把 YOLO / CUB 的英文类别名映射到 bird_species 表中
# ============================================================

# CUB-200-2011 常见物种别名 -> bird_species.name_cn / name_en 模糊匹配兜底
# 这里只列出高概率命中的别名，其余通过模糊查询兜底
_CUB_SPECIES_ALIASES = {
    'Eagle Owl': '雕鸮',
    'Eurasian Eagle-Owl': '雕鸮',
    '雕鸮': '雕鸮',
    'Bubo bubo': '雕鸮',
    '白鹭': '白鹭',
    'Little Egret': '白鹭',
    'Egretta garzetta': '白鹭',
    'Peacock': '孔雀',
    'Common Peafowl': '孔雀',
    'Pavo cristatus': '孔雀',
    'Swan': '天鹅',
    'Whooper Swan': '天鹅',
    'Cygnus cygnus': '天鹅',
    'Mandarin Duck': '鸳鸯',
    'Aix galericulata': '鸳鸯',
    'Parrot': '鹦鹉',
    'Red-crowned Crane': '丹顶鹤',
    'Grus japonensis': '丹顶鹤',
}


def _resolve_species_from_name(name):
    """
    根据任意字符串（中文名、英文名、学名、CUB 英文名、别名）查找 BirdSpecies 记录。

    返回 BirdSpecies 或 None。
    """
    if not name:
        return None
    name = str(name).strip()
    if not name:
        return None

    # 0) 先看别名表
    alias_hit = _CUB_SPECIES_ALIASES.get(name) or _CUB_SPECIES_ALIASES.get(name.replace('_', ' '))
    if alias_hit and alias_hit != name:
        q = (BirdSpecies.query
             .filter((BirdSpecies.name_cn == alias_hit) | (BirdSpecies.name_en == alias_hit))
             .first())
        if q:
            return q

    # 1) 精确匹配 name_cn
    sp = BirdSpecies.query.filter_by(name_cn=name).first()
    if sp:
        return sp

    # 2) 精确匹配 name_en
    sp = BirdSpecies.query.filter_by(name_en=name).first()
    if sp:
        return sp
    sp = BirdSpecies.query.filter_by(name_en=name.replace('_', ' ')).first()
    if sp:
        return sp

    # 3) 模糊匹配：CUB 的英文通常是 "Admiralty Bird" 等，匹配首尾 or 子串
    norm = name.replace('_', ' ').lower()
    for field in ('name_en', 'name_cn'):
        col = getattr(BirdSpecies, field)
        try:
            like = BirdSpecies.query.filter(col.ilike(f'%{name}%')).first()
            if like:
                return like
        except Exception:
            logger.debug("ilike 模糊匹配不可用 (field=%s)", field, exc_info=True)

    # 4) 别名表反向：如果别名表的 value 是中文，key 可能是英文，遍历匹配
    for en, cn in _CUB_SPECIES_ALIASES.items():
        if en.lower() == norm or cn == name:
            sp = BirdSpecies.query.filter_by(name_cn=cn).first()
            if sp:
                return sp

    return None


# ============================================================
# 物种知识问答快捷接口（基于识别结果串联）
# ============================================================

@api_bp.route('/species/<int:species_id>/qa', methods=['POST'])
@api_bp.route('/species/qa', methods=['POST'])
def species_qa(species_id=None):
    """
    基于识别结果的鸟类知识问答快捷接口。

    两种调用方式：
      1) /api/species/<species_id>/qa   —— 只传物种 ID
      2) /api/species/qa + body {species_id:.., context_name:.., species_name:..}

    请求 body：
        message:           str  用户问题（必填）
        species_id:        int  可选（已包含在 URL 时可不传）
        species_name:      str  可选，中文名/英文名
        species_info:      dict 可选，物种详情（为省查库可直接来自上一次 /api/detect 响应）
        history:           list 可选，{role,content} 列表

    返回：
        {success, reply, provider, model, species_info?}
    """
    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({'success': False, 'message': '请输入问题'}), 400
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({'success': False, 'message': f'问题过长（最多 {MAX_MESSAGE_LENGTH} 字）'}), 400

    # 物种解析： species_id 优先，否则 species_name 匹配
    species_info = data.get('species_info')
    species_name = data.get('species_name') or data.get('context_name') or ''
    sp, species_name, species_info = _resolve_species_context(
        species_id or data.get('species_id'), species_name, species_info
    )

    # 没拿到 species_info 但有 species_name：构造最小上下文
    species_context = {
        'species_name': species_name or '该鸟类',
        'species_id': sp.id if sp else None,
        'species_info': species_info,
    }

    history = _sanitize_history(data.get('history'))
    provider_id = data.get('provider')

    # 构建 provider 尝试顺序：用户指定的优先，失败后按固定优先级 fallback
    available = Config.list_available_providers()
    available_ids = [p['id'] for p in available]
    try_order = _build_provider_try_order(provider_id, available_ids)

    fallback_from = None
    fallback_from_label = None
    result = None

    for i, pid in enumerate(try_order):
        try:
            llm_cfg = Config.get_llm_config(provider=pid)
            llm = LLMService(**llm_cfg)
            result = llm.chat(message, history=history, species_context=species_context)
        except ValueError as e:
            return jsonify({'success': False, 'message': str(e)}), 400
        except Exception:
            logger.exception("物种问答调用失败 provider=%s", pid)
            result = {'success': False, 'reply': 'AI 服务异常，请稍后重试', 'error_type': 'server'}

        if result.get('success'):
            if i > 0:
                fallback_from = provider_id
                fallback_from_label = PROVIDER_LABELS.get(provider_id, provider_id)
            break

    if result is None:
        result = {'success': False, 'reply': 'AI 服务异常，请稍后重试', 'error_type': 'server'}

    actual_provider = result.get('provider', provider_id)
    provider_label = PROVIDER_LABELS.get(actual_provider, actual_provider)

    resp = {
        'success': result['success'],
        'reply': result['reply'],
        'provider': actual_provider,
        'provider_label': provider_label,
        'model': result.get('model'),
    }
    if fallback_from:
        resp['fallback'] = True
        resp['fallback_from'] = fallback_from
        resp['fallback_from_label'] = fallback_from_label
    if not result['success']:
        resp['error_type'] = result.get('error_type')
    # 把解析到的 species 信息一起回传，方便前端展示
    if species_name:
        resp['species_name'] = species_name
    if species_info:
        resp['species_info'] = species_info

    return jsonify(resp), 200


@api_bp.route('/detect/history', methods=['GET'])
def detection_history():
    """
    获取最近 20 条识别记录。

    返回：JSON {records: list}
    """
    records = (
        DetectionRecord.query
        .order_by(DetectionRecord.created_at.desc())
        .limit(20)
        .all()
    )
    return jsonify({'records': [r.to_dict() for r in records]})


@api_bp.route('/detect/history/<int:record_id>', methods=['DELETE'])
def delete_detection_record(record_id):
    """
    删除单条识别记录，同时从数据库移除，统计页面数据将同步更新。

    返回：JSON {success: bool, message: str}
    """
    record = db.session.get(DetectionRecord, record_id)
    if not record:
        return jsonify({'success': False, 'message': '记录不存在'}), 404

    try:
        db.session.delete(record)
        db.session.commit()
        logger.info('删除识别记录: id=%d, species=%s', record_id, record.species_name)
        return jsonify({'success': True, 'message': '已删除'})
    except Exception:
        db.session.rollback()
        logger.exception('删除识别记录失败: id=%d', record_id)
        return jsonify({'success': False, 'message': '删除失败'}), 500


@api_bp.route('/detect/history/clear', methods=['DELETE'])
def clear_detection_history():
    """
    清空所有识别记录，统计页面数据将同步更新。

    返回：JSON {success: bool, message: str, deleted_count: int}
    """
    try:
        count = DetectionRecord.query.count()
        DetectionRecord.query.delete()
        db.session.commit()
        logger.info('清空识别记录: 共删除 %d 条', count)
        return jsonify({'success': True, 'message': f'已清空 {count} 条记录', 'deleted_count': count})
    except Exception:
        db.session.rollback()
        logger.exception('清空识别记录失败')
        return jsonify({'success': False, 'message': '清空失败'}), 500


# --------------------------------------------------
# LLM 对话接口
# --------------------------------------------------

@api_bp.route('/llm/providers', methods=['GET'])
def llm_providers():
    """
    返回当前可用的 LLM 提供商列表。

    返回：JSON {providers: [{id, label, model}], default: str}
    """
    providers = Config.list_available_providers()
    return jsonify({
        'providers': providers,
        'default': Config.LLM_PROVIDER,
    })


@api_bp.route('/llm/health', methods=['GET'])
def llm_health():
    """
    健康检查：检测指定 provider 的 API Key 和服务是否可用。

    不指定 provider 时，按顺序检测所有可用 provider，返回首个可用的。
    指定 provider 时，单独检测该 provider。

    查询参数：
        provider: str (可选) ollama | deepseek | mimo

    返回：JSON {
        'provider': str,          # 检测的 provider
        'ok': bool,               # 是否可用
        'error_type': str|None,   # auth/not_found/connection/timeout/...
        'message': str,           # 用户友好的中文说明
        'all_statuses': list      # 所有已检测 provider 的状态列表
    }
    """
    preferred = request.args.get('provider')

    available = Config.list_available_providers()
    provider_ids = [p['id'] for p in available]

    if not provider_ids:
        return jsonify({
            'provider': 'none',
            'ok': False,
            'error_type': 'not_configured',
            'message': '没有可用的 AI 模型，请先配置 API Key 或安装 Ollama。',
            'all_statuses': [],
        })

    # 确定要检测的顺序
    if preferred and preferred in provider_ids:
        check_order = [preferred]
    else:
        check_order = provider_ids

    all_statuses = []
    first_ok = None

    for pid in check_order:
        try:
            llm_cfg = Config.get_llm_config(provider=pid)
            llm = LLMService(**llm_cfg)
            st = llm.check_connection()
            status = {
                'provider': pid,
                'label': llm_cfg.get('label', PROVIDER_LABELS.get(pid, pid)),
                'ok': st['ok'],
                'error_type': st['error_type'],
                'message': st['message'],
            }
        except Exception as e:
            logger.error("健康检查异常 provider=%s: %s", pid, e)
            status = {
                'provider': pid,
                'label': PROVIDER_LABELS.get(pid, pid),
                'ok': False,
                'error_type': 'unknown',
                'message': f'{PROVIDER_LABELS.get(pid, pid)} 检测异常：{str(e)}',
            }
        all_statuses.append(status)
        if status['ok'] and first_ok is None:
            first_ok = status

    # 选一个作为整体状态
    if preferred:
        main = all_statuses[0]
    else:
        main = first_ok or all_statuses[0]

    return jsonify({
        'provider': main['provider'],
        'ok': main['ok'],
        'error_type': main['error_type'],
        'message': main['message'],
        'all_statuses': all_statuses,
    })


def _chat_error_payload(reply, error_type='bad_request'):
    """构造 /api/chat 的统一错误响应体。"""
    return {
        'reply': reply,
        'provider': 'none',
        'provider_label': '',
        'model': '',
        'fallback': False,
        'fallback_from': None,
        'fallback_from_label': None,
        'success': False,
        'error_type': error_type,
        'species_name': None,
        'species_id': None,
    }


@api_bp.route('/chat', methods=['POST'])
def chat_reply():
    """
    接收用户消息，调用 LLM 返回回复。

    支持自动 fallback：当前 provider 返回服务错误时，
    自动尝试下一个已配置的 provider（deepseek → mimo → ollama）。

    【识别结果串联】请求体中新增可选字段：
        species_id:        int  bird_species.id（推荐，最可靠）
        species_name:      str  中文名/英文名/CUB别名（例如 "雕鸮" / "Eagle Owl"）
        species_context:   str  简写版，等价于 species_name
        species_info:      dict 可选，直接传上一次 /api/detect 返回的 species_info

    请求：JSON {message, history, provider, species_id?, species_name?, species_info?}
    返回：JSON {
        'reply': str,
        'provider': str,
        'provider_label': str,
        'model': str,
        'fallback': bool,
        'fallback_from': str|None,
        'fallback_from_label': str|None,
        'success': bool,
        'error_type': str|None,
        'species_name': str|None,   # 实际解析到的物种名
        'species_id':   int|None,   # 实际匹配到的 ID
    }
    """
    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify(_chat_error_payload('请输入有效的消息内容')), 400
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify(_chat_error_payload(f'消息过长（最多 {MAX_MESSAGE_LENGTH} 字）')), 400

    history = _sanitize_history(data.get('history'))
    preferred = data.get('provider')

    # ===== 物种上下文解析（识别 → 问答串联）=====
    species_name = (
        data.get('species_name')
        or data.get('species_context')
        or data.get('context_name')
        or data.get('context')
        or ''
    )
    species_info = data.get('species_info')
    sp_obj, species_name, species_info = _resolve_species_context(
        data.get('species_id') or data.get('sid'), species_name, species_info
    )

    species_context = None
    if species_name or species_info:
        species_context = {
            'species_name': species_name or '该鸟类',
            'species_id': sp_obj.id if sp_obj else None,
            'species_info': species_info,
        }
    resolved_species_id = sp_obj.id if sp_obj else None
    resolved_species_name = species_name or None

    available = Config.list_available_providers()
    provider_ids = [p['id'] for p in available]
    try_order = _build_provider_try_order(preferred, provider_ids)

    if not try_order:
        return jsonify({
            'reply': '没有可用的 AI 模型，请先配置 API Key 或安装 Ollama。',
            'provider': 'none',
            'provider_label': '',
            'model': '',
            'fallback': False,
            'fallback_from': None,
            'fallback_from_label': None,
            'success': False,
            'error_type': 'not_configured',
            'species_name': resolved_species_name,
            'species_id': resolved_species_id,
        }), 200

    first_provider = try_order[0]
    first_label = PROVIDER_LABELS.get(first_provider, first_provider)

    last_error_reply = ''
    last_error_type = None
    last_provider = ''
    last_model = ''

    for prov in try_order:
        try:
            llm_cfg = Config.get_llm_config(provider=prov)
            llm = LLMService(**llm_cfg)
            result = llm.chat(message, history=history, species_context=species_context)

            # result 是结构化 dict，直接判断 success 字段
            if result.get('success'):
                is_fallback = prov != first_provider
                resp_data = {
                    'reply': result['reply'],
                    'provider': prov,
                    'provider_label': llm_cfg.get('label', PROVIDER_LABELS.get(prov, prov)),
                    'model': result.get('model', llm_cfg['model_name']),
                    'fallback': is_fallback,
                    # 发生 fallback 时用单独字段告知，不拼接到 reply 正文（由前端独立展示）
                    'fallback_from': first_provider if is_fallback else None,
                    'fallback_from_label': first_label if is_fallback else None,
                    'success': True,
                    'error_type': None,
                    'species_name': resolved_species_name,
                    'species_id': resolved_species_id,
                }
                return jsonify(resp_data)

            # 这次 provider 返回服务错误，记录并继续下一个
            last_error_reply = result.get('reply', 'AI 服务暂时不可用。')
            last_error_type = result.get('error_type')
            last_provider = prov
            last_model = result.get('model', llm_cfg.get('model_name', ''))
            logger.warning(
                "Provider %s 返回服务错误 (type=%s): %s",
                prov, last_error_type, last_error_reply,
            )

        except Exception:
            logger.exception("Provider %s 调用异常", prov)
            last_error_reply = 'AI 服务连接异常，请检查网络后重试。'
            last_error_type = 'exception'
            last_provider = prov
            continue

    # ===== 所有 provider 都失败 =====
    # 根据最后一次的错误类型，给一个汇总的用户友好提示
    if last_error_type == 'auth':
        summary_msg = (
            '当前配置的所有 AI 模型均认证失败（API Key 可能已过期或未配置）。\n'
            '请检查 .env 文件中的 LLM_API_KEY / MIMO_API_KEY 是否正确，或切换到 Ollama 本地模型。'
        )
    elif last_error_type == 'not_found':
        summary_msg = (
            '当前配置的所有 AI 模型均不可用：云端模型不存在或本地 Ollama 未拉取模型。\n'
            '请检查 .env 中的模型名称，或执行 `ollama pull bird-expert:latest`。'
        )
    elif last_error_type == 'connection':
        summary_msg = (
            '无法连接到任何 AI 服务：请检查网络连接，或确认 Ollama 是否已启动（`ollama serve`）。'
        )
    elif last_error_type == 'timeout':
        summary_msg = '所有 AI 服务响应都超时，请稍后重试。'
    elif last_error_type == 'rate_limit':
        summary_msg = '所有 AI 服务均触发频率限制，请稍后再试。'
    else:
        summary_msg = (
            last_error_reply
            or '所有 AI 模型均不可用，请检查网络或配置后重试。'
        )

    return jsonify({
        'reply': summary_msg,
        'provider': last_provider or first_provider,
        'provider_label': PROVIDER_LABELS.get(
            last_provider or first_provider, last_provider or first_provider
        ),
        'model': last_model,
        'fallback': len(try_order) > 1,  # 尝试了多个就算发生过多重 fallback
        'fallback_from': first_provider if len(try_order) > 1 else None,
        'fallback_from_label': first_label if len(try_order) > 1 else None,
        'success': False,
        'error_type': last_error_type or 'unknown',
        'species_name': resolved_species_name,
        'species_id': resolved_species_id,
    }), 200


# --------------------------------------------------
# 统计接口
# --------------------------------------------------

@api_bp.route('/stats/overview', methods=['GET'])
def stats_overview():
    """
    获取系统概览统计数据。

    返回：JSON {total_detections, total_species, total_chats, today_detections}
    """
    total_detections = DetectionRecord.query.count()
    total_species = db.session.query(
        db.func.count(db.func.distinct(DetectionRecord.species_name))
    ).scalar() or 0
    total_chats = ChatRecord.query.count()

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_detections = DetectionRecord.query.filter(
        DetectionRecord.created_at >= today_start
    ).count()
    today_chats = ChatRecord.query.filter(
        ChatRecord.created_at >= today_start
    ).count()

    return jsonify({
        'total_detections': total_detections,
        'total_species': total_species,
        'total_chats': total_chats,
        'today_detections': today_detections,
        'today_chats': today_chats,
    })


@api_bp.route('/stats/species_distribution', methods=['GET'])
def species_distribution():
    """
    按物种统计识别次数。

    返回：JSON {names: list, counts: list}
    """
    rows = (
        db.session.query(
            DetectionRecord.species_name,
            db.func.count(DetectionRecord.id),
        )
        .group_by(DetectionRecord.species_name)
        .order_by(db.func.count(DetectionRecord.id).desc())
        .all()
    )
    return jsonify({
        'names': [r[0] for r in rows],
        'counts': [r[1] for r in rows],
    })


@api_bp.route('/stats/daily_trend', methods=['GET'])
def daily_trend():
    """
    获取最近 7 天每日识别数量。

    返回：JSON {dates: list, counts: list}
    """
    seven_days_ago = datetime.now() - timedelta(days=7)

    rows = (
        db.session.query(
            db.func.date(DetectionRecord.created_at),
            db.func.count(DetectionRecord.id),
        )
        .filter(DetectionRecord.created_at >= seven_days_ago)
        .group_by(db.func.date(DetectionRecord.created_at))
        .order_by(db.func.date(DetectionRecord.created_at))
        .all()
    )

    # 构建日期->数量的映射，并补齐缺失日期（count=0），确保折线图始终有7个数据点
    date_count_map = {str(r[0]): r[1] for r in rows}
    all_dates = []
    all_counts = []
    for i in range(7):
        day = (datetime.now() - timedelta(days=6 - i)).strftime('%Y-%m-%d')
        all_dates.append(day)
        all_counts.append(date_count_map.get(day, 0))

    return jsonify({'dates': all_dates, 'counts': all_counts})


# --------------------------------------------------
# 物种百科接口
# --------------------------------------------------

@api_bp.route('/species', methods=['GET'])
def species_list():
    """
    获取所有鸟类物种列表。

    返回：JSON {species: list}
    """
    species = BirdSpecies.query.order_by(BirdSpecies.id).all()
    return jsonify({'species': [s.to_dict() for s in species]})


@api_bp.route('/species/<int:bird_id>', methods=['GET'])
def species_detail(bird_id):
    """
    根据 ID 获取单个物种详情。

    返回：JSON {success, species: dict} 或 404
    """
    species = db.session.get(BirdSpecies, bird_id)
    if not species:
        return jsonify({'success': False, 'message': '物种不存在'}), 404
    return jsonify({'success': True, 'species': species.to_dict()})
