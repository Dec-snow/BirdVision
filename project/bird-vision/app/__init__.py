# -*- coding: utf-8 -*-
"""Flask 应用工厂模块"""

import logging
import os

from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

# 配置基础日志（run.py 已配置格式时此处为 no-op）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化 SQLAlchemy 扩展（延迟绑定到应用实例）
db = SQLAlchemy()


def create_app():
    """创建并配置 Flask 应用实例"""
    from config import Config

    app = Flask(__name__)

    # 加载配置
    app.config.from_object(Config)

    # 确保 JSON 响应中中文不转义（Flask 2.3+ 使用 app.json，JSON_AS_ASCII 已废弃）
    app.json.ensure_ascii = False

    # 初始化扩展
    db.init_app(app)

    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 缓存 LLM 配置（避免每次 API 请求都重新计算）
    app.config['_LLM_CONFIG'] = Config.get_llm_config()
    llm_cfg = app.config['_LLM_CONFIG']
    logger.info("LLM 配置: provider=%s, model=%s, url=%s",
                llm_cfg['provider'], llm_cfg['model_name'], llm_cfg['api_url'])

    # 注册蓝图
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # 注册上下文处理器：向所有模板注入 active_page 变量
    @app.context_processor
    def inject_active_page():
        return dict(active_page='home')

    # 统一错误处理：API 路径返回 JSON，页面路径返回 HTML
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api'):
            return jsonify({'success': False, 'message': '请求的资源不存在'}), 404
        return render_template(
            'error.html', error_code=404, error_title='页面不存在',
            error_message='您访问的页面不存在或已被移除。'
        ), 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.error("服务器内部错误: %s", e, exc_info=True)
        if request.path.startswith('/api'):
            return jsonify({'success': False, 'message': '服务器内部错误，请稍后重试'}), 500
        return render_template(
            'error.html', error_code=500, error_title='服务器内部错误',
            error_message='服务器开小差了，请稍后重试。'
        ), 500

    @app.errorhandler(413)
    def request_too_large(e):
        if request.path.startswith('/api'):
            return jsonify({'success': False, 'message': '上传文件过大，最大支持 16MB'}), 413
        return render_template(
            'error.html', error_code=413, error_title='文件过大',
            error_message='上传的文件超过大小限制（最大 16MB）。'
        ), 413

    return app
