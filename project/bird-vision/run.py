# -*- coding: utf-8 -*-
"""BirdVision 应用入口文件"""

import logging
import os

# 配置日志格式（需在导入 app 之前，避免被 app 内 basicConfig 抢先配置）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

from app import create_app, db  # noqa: E402
from app.models import BirdSpecies  # noqa: E402

# 创建 Flask 应用实例
app = create_app()


@app.shell_context_processor
def make_shell_context():
    """为 Flask shell 注入常用对象，方便调试"""
    return {'db': db, 'BirdSpecies': BirdSpecies}


def startup_self_check():
    """启动前自检：检查 YOLO 模型、LLM 配置与数据库状态。"""
    with app.app_context():
        # 确保数据库表已创建
        db.create_all()

        logger.info("-" * 50)
        logger.info("  BirdVision 启动自检")
        logger.info("-" * 50)

        # 检查 YOLO 模型
        yolo_path = app.config.get('YOLO_MODEL_PATH', 'models/yolo/best.pt')
        if os.path.exists(yolo_path):
            logger.info("  [✓] YOLO 模型: %s", yolo_path)
        else:
            logger.info("  [~] YOLO 自定义模型未找到，将使用预训练模型（演示模式）")
            logger.info("  [→] 训练自定义模型: python training/yolo/train.py")

        # 检查 LLM 状态
        llm_cfg = app.config.get('_LLM_CONFIG', {})
        provider = llm_cfg.get('provider', 'unknown')
        model = llm_cfg.get('model_name', 'unknown')
        if provider == 'ollama':
            logger.info("  [→] LLM: Ollama (%s) - 请确保已启动 ollama serve", model)
        else:
            api_key_set = bool(llm_cfg.get('api_key'))
            key_status = '已设置' if api_key_set else '未设置'
            logger.info("  [→] LLM: %s (%s) - API Key: %s", provider, model, key_status)

        # 检查数据库
        species_count = BirdSpecies.query.count()
        if species_count > 0:
            logger.info("  [✓] 物种数据: %s 条", species_count)
        else:
            logger.info("  [✗] 物种数据为空，请运行: python -m app.init_db")

        logger.info("-" * 50)


if __name__ == '__main__':
    try:
        startup_self_check()
    except Exception:
        logger.exception("启动自检失败，请检查运行环境")
        raise SystemExit(1)

    # 开发服务器配置（环境变量可覆盖，默认与原行为一致）
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', '1').strip().lower() in ('1', 'true', 'yes', 'on')

    logger.info("=== BirdVision 智能鸟类识别系统 ===")
    logger.info("访问地址: http://%s:%s", host, port)

    app.run(debug=debug, port=port, host=host)
