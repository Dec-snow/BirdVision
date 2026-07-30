# -*- coding: utf-8 -*-
"""Flask 应用工厂模块"""

import logging
import os

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy

# 配置基础日志
logging.basicConfig(level=logging.INFO)

# 初始化 SQLAlchemy 扩展（延迟绑定到应用实例）
db = SQLAlchemy()


def create_app():
    """创建并配置 Flask 应用实例"""
    app = Flask(__name__)

    # 加载配置
    from config import Config
    app.config.from_object(Config)

    # 确保 JSON 响应中中文不转义
    app.config['JSON_AS_ASCII'] = False

    # 初始化扩展
    db.init_app(app)

    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 缓存 LLM 配置（避免每次 API 请求都重新计算）
    from config import Config as AppConfig
    app.config['_LLM_CONFIG'] = AppConfig.get_llm_config()
    logger = logging.getLogger(__name__)
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

    # 404 错误处理
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'success': False, 'message': '请求的资源不存在'}), 404

    # 500 错误处理
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'success': False, 'message': '服务器内部错误，请稍后重试'}), 500

    return app
