# -*- coding: utf-8 -*-
"""YOLO 鸟类检测服务"""

import logging
import os
import random
import uuid

from flask import current_app

from app.models import BirdSpecies

logger = logging.getLogger(__name__)


class BirdDetector:
    """基于 YOLOv11 的鸟类目标检测服务（两级检测策略）

    检测流程：
    1. 先用自定义多类别模型（best.pt）尝试识别具体物种
    2. 若无结果，再用 YOLO 预训练模型（yolo11n.pt）检测 COCO bird 类
    3. 确保"有鸟就一定能被检测到"，未匹配到具体品种时返回"未知鸟类"
    """

    # COCO 数据集中 "bird" 类别的 ID
    COCO_BIRD_CLASS_ID = 14

    def __init__(self, model_path):
        """
        初始化检测器，加载 YOLO 模型。

        同时加载自定义模型和预训练模型，实现两级 fallback。

        Args:
            model_path: 自定义模型权重文件路径 (.pt)
        """
        self.custom_model_path = model_path
        self.custom_model = None
        self.pretrained_model = None
        self.is_custom_available = False

        try:
            from ultralytics import YOLO
        except ImportError:
            logger.error("ultralytics 未安装，识别功能不可用")
            return

        # 1. 加载自定义模型（识别具体鸟种）
        if os.path.exists(model_path):
            try:
                self.custom_model = YOLO(model_path)
                self.is_custom_available = True
                logger.info("自定义模型加载成功: %s", model_path)
                logger.info("自定义模型类别: %s", self.custom_model.names)
            except Exception as e:
                logger.error("自定义模型加载失败: %s", e)

        # 2. 加载预训练模型（检测是否有鸟，作为 fallback）
        try:
            self.pretrained_model = YOLO('yolo11n.pt')
            logger.info("YOLO 预训练模型加载成功（用于 bird 类检测 fallback）")
        except Exception as e:
            logger.error("预训练模型加载失败: %s", e)

    @property
    def model(self):
        """兼容旧接口：优先返回自定义模型，否则返回预训练模型"""
        return self.custom_model or self.pretrained_model

    def detect(self, image_source, conf=0.2):
        """
        对输入图像执行鸟类检测（两级策略）。

        Args:
            image_source: 图片文件路径（str）或 numpy 数组（BGR 格式）
            conf: 置信度阈值，默认 0.2

        Returns:
            list[dict]: 检测结果列表，每项包含
                {class_name: str, confidence: float, bbox: list[int], is_unknown: bool}
        """
        # 第一级：自定义模型检测（识别具体物种）
        if self.is_custom_available and self.custom_model:
            detections = self._run_inference(
                self.custom_model, image_source,
                conf_threshold=conf,
                filter_bird_only=False
            )
            if detections:
                logger.info("自定义模型检测到 %d 个目标", len(detections))
                return detections
            logger.info("自定义模型未检测到目标，尝试预训练模型 bird 类检测...")

        # 第二级：预训练模型 bird 类检测（兜底，确保有鸟就能检测到）
        if self.pretrained_model:
            detections = self._run_inference(
                self.pretrained_model, image_source,
                conf_threshold=0.15,  # 预训练模型阈值稍低
                filter_bird_only=True
            )
            if detections:
                # bird 类无法区分品种，映射为"未知鸟类"
                for det in detections:
                    det['class_name'] = self._pick_most_likely_species()
                    det['is_unknown'] = True
                logger.info("预训练模型检测到鸟类（%d 个），使用 fallback 物种", len(detections))
                return detections
            logger.info("预训练模型也未检测到鸟类")

        return []

    def _run_inference(self, model, image_source, conf_threshold=None, filter_bird_only=False):
        """
        使用指定模型执行推理。

        Args:
            model: YOLO 模型实例
            image_source: 图片路径或 numpy 数组
            conf_threshold: 置信度阈值
            filter_bird_only: 是否只保留 bird 类（用于预训练模型）

        Returns:
            list[dict]: 检测结果列表
        """
        try:
            infer_kwargs = {}
            if conf_threshold is not None:
                infer_kwargs['conf'] = conf_threshold
            results = model(image_source, **infer_kwargs)
            detections = []

            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                for box in boxes:
                    cls_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    bbox = box.xyxy[0].tolist()
                    bbox = [int(round(v)) for v in bbox]

                    # 预训练模型时只保留 bird 类
                    if filter_bird_only and cls_id != self.COCO_BIRD_CLASS_ID:
                        continue

                    class_name = model.names.get(cls_id, f"class_{cls_id}")
                    detections.append({
                        'class_name': class_name,
                        'confidence': round(confidence, 4),
                        'bbox': bbox,
                        'is_unknown': False,
                    })

            return detections
        except Exception as e:
            logger.error("模型推理异常: %s", e, exc_info=True)
            return []

    def _pick_most_likely_species(self):
        """当无法确定具体物种时，从数据库返回"未知鸟类"

        注意：不再随机分配，避免误导用户。
        """
        return '未知鸟类'

    def _pick_random_species(self):
        """从数据库随机选取一个鸟类名称（保留旧接口兼容）"""
        species = BirdSpecies.query.all()
        if species:
            picked = random.choice(species)
            return picked.name_cn
        return '未知鸟类'

    def preprocess_image(self, file_storage):
        """
        保存上传文件到 UPLOAD_FOLDER。

        Args:
            file_storage: Flask 的 FileStorage 对象

        Returns:
            str: 保存后的相对路径（相对于 static 目录）

        Raises:
            ValueError: 文件大小超过限制时抛出
        """
        max_size = current_app.config.get('MAX_CONTENT_LENGTH')
        if max_size and file_storage.content_length and file_storage.content_length > max_size:
            logger.warning("上传文件大小 %d 字节，超过限制 %d 字节",
                           file_storage.content_length, max_size)
            raise ValueError(f"文件大小超过限制（最大 {max_size // 1024 // 1024}MB）")

        ext = os.path.splitext(file_storage.filename)[1] or '.jpg'
        filename = str(uuid.uuid4().hex) + ext

        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)

        save_path = os.path.join(upload_folder, filename)
        file_storage.save(save_path)

        return f'uploads/{filename}'

    def get_species_info(self, species_name):
        """
        根据物种名称查询数据库获取详细信息。

        Args:
            species_name: 物种名称（中文名或英文名）

        Returns:
            dict or None: 物种信息字典，未找到则返回 None
        """
        if species_name == '未知鸟类':
            return {
                'name_cn': '未知鸟类',
                'name_en': 'Unknown Bird',
                'scientific_name': 'Aves sp.',
                'family': '——',
                'habitat': '——',
                'conservation_status': '——',
                'description': '已检测到鸟类，但无法确定具体物种。建议上传更清晰的鸟类图片，或在物种百科中浏览常见鸟类。',
            }

        species = BirdSpecies.query.filter(
            (BirdSpecies.name_cn == species_name)
            | (BirdSpecies.name_en == species_name)
        ).first()

        if species:
            return species.to_dict()

        fuzzy_result = BirdSpecies.query.filter(
            BirdSpecies.name_cn.like(f'%{species_name}%')
        ).first()

        if fuzzy_result:
            logger.info("精确匹配无结果，模糊匹配命中: %s -> %s", species_name, fuzzy_result.name_cn)
            return fuzzy_result.to_dict()

        return None
