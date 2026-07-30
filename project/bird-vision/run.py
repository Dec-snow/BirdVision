# -*- coding: utf-8 -*-
"""BirdVision 应用入口文件"""

import logging

from app import create_app, db
from app.models import BirdSpecies

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 Flask 应用实例
app = create_app()


@app.shell_context_processor
def make_shell_context():
    """为 Flask shell 注入常用对象，方便调试"""
    return {'db': db, 'BirdSpecies': BirdSpecies}


if __name__ == '__main__':
    # ---- 启动前自检（在应用上下文内） ----
    import os as _os

    with app.app_context():
        # 确保数据库表已创建
        db.create_all()

        print("-" * 50)
        print("  BirdVision 启动自检")
        print("-" * 50)

        # 检查 YOLO 模型
        yolo_path = app.config.get('YOLO_MODEL_PATH', 'models/yolo/best.pt')
        if _os.path.exists(yolo_path):
            print(f"  [✓] YOLO 模型: {yolo_path}")
        else:
            print(f"  [~] YOLO 自定义模型未找到，将使用预训练模型（演示模式）")
            print(f"  [→] 训练自定义模型: python training/yolo/train.py")

        # 检查 LLM 状态
        llm_cfg = app.config.get('_LLM_CONFIG', {})
        provider = llm_cfg.get('provider', 'unknown')
        model = llm_cfg.get('model_name', 'unknown')
        if provider == 'ollama':
            print(f"  [→] LLM: Ollama ({model}) - 请确保已启动 ollama serve")
        else:
            api_key_set = bool(llm_cfg.get('api_key'))
            key_status = '已设置' if api_key_set else '未设置'
            print(f"  [→] LLM: {provider} ({model}) - API Key: {key_status}")

        # 检查数据库
        species_count = BirdSpecies.query.count()
        if species_count > 0:
            print(f"  [✓] 物种数据: {species_count} 条")
        else:
            print(f"  [✗] 物种数据为空，请运行: python -m app.init_db")

        print("-" * 50)

    # 打印启动欢迎信息
    logger.info("=== BirdVision 智能鸟类识别系统 ===")
    logger.info("访问地址: http://127.0.0.1:5000")

    app.run(debug=True, port=5000)