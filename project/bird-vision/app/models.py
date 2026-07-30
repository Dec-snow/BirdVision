# -*- coding: utf-8 -*-
"""SQLAlchemy 数据模型定义"""

from datetime import datetime

from app import db


class BirdSpecies(db.Model):
    """鸟类物种信息表"""

    __tablename__ = 'bird_species'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name_cn = db.Column(db.String(50), nullable=False, comment='中文名')
    name_en = db.Column(db.String(100), comment='英文名')
    scientific_name = db.Column(db.String(100), comment='学名')
    family = db.Column(db.String(50), comment='科')
    description = db.Column(db.Text, comment='描述')
    habitat = db.Column(db.String(200), comment='栖息地')
    conservation_status = db.Column(db.String(20), comment='保护等级')

    def to_dict(self):
        """将模型实例转换为字典"""
        return {
            'id': self.id,
            'name_cn': self.name_cn,
            'name_en': self.name_en,
            'scientific_name': self.scientific_name,
            'family': self.family,
            'description': self.description,
            'habitat': self.habitat,
            'conservation_status': self.conservation_status,
        }

    def __repr__(self):
        return f'<BirdSpecies {self.name_cn}>'


class DetectionRecord(db.Model):
    """鸟类识别记录表"""

    __tablename__ = 'detection_record'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    image_path = db.Column(db.String(256), nullable=False, comment='图片存储路径')
    species_name = db.Column(db.String(100), nullable=False, comment='识别出的物种名称')
    confidence = db.Column(db.Float, nullable=False, comment='置信度')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='识别时间')
    user_ip = db.Column(db.String(45), comment='用户 IP 地址')

    def to_dict(self):
        """将模型实例转换为字典"""
        return {
            'id': self.id,
            'image_path': self.image_path,
            'species_name': self.species_name,
            'confidence': self.confidence,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'user_ip': self.user_ip,
        }

    def __repr__(self):
        date_str = self.created_at.strftime('%Y-%m-%d') if self.created_at else 'unknown'
        return f'<DetectionRecord {self.species_name} {date_str}>'


class ChatRecord(db.Model):
    """LLM 对话记录表"""

    __tablename__ = 'chat_record'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.Text, nullable=False, comment='用户提问')
    answer = db.Column(db.Text, nullable=False, comment='模型回复')
    model_name = db.Column(db.String(50), comment='使用的模型名称')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='对话时间')

    def to_dict(self):
        """将模型实例转换为字典"""
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'model_name': self.model_name,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }

    def __repr__(self):
        return f'<ChatRecord {self.model_name or "unknown"}>'