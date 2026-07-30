# -*- coding: utf-8 -*-
"""
CUB-200-2011 数据集转 YOLO 格式工具

功能说明：
- 读取 CUB-200-2011 数据集
- 解析 images.txt 和 bounding_boxes.txt
- 将 (x, y, w, h) 绝对坐标转换为 YOLO 归一化格式
  (class_id, x_center, y_center, width, height)
- 按 8:2 比例分割 train/val
- 生成 data.yaml 配置文件
- 输出到 datasets/birds/ 目录
"""

import os
import random
import shutil
from pathlib import Path

import numpy as np


# ===== 可配置参数 =====
# CUB-200-2011 数据集根目录（自动下载后的路径）
CUB_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'datasets', 'cub200')

# YOLO 格式输出目录
YOLO_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'datasets', 'birds')

# 训练集/验证集分割比例
TRAIN_RATIO = 0.8

# 随机种子（确保可复现）
RANDOM_SEED = 42


def read_cub_file(filepath):
    """
    读取 CUB 数据集中的文本文件（空格分隔）
    返回行列表，每行是一个字符串列表
    """
    lines = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line.split())
    return lines


def convert_cub_to_yolo(cub_root=None, output_dir=None):
    """
    将 CUB-200-2011 数据集转换为 YOLO 格式

    参数:
        cub_root: CUB 数据集根目录路径
        output_dir: YOLO 格式输出目录路径

    返回:
        data_yaml_path: 生成的 data.yaml 文件路径
    """
    if cub_root is None:
        cub_root = CUB_ROOT
    if output_dir is None:
        output_dir = YOLO_OUTPUT_DIR

    cub_root = os.path.abspath(cub_root)
    output_dir = os.path.abspath(output_dir)

    print(f"[信息] CUB 数据集路径: {cub_root}")
    print(f"[信息] YOLO 输出路径: {output_dir}")

    # ---- 验证 CUB 数据集目录结构 ----
    images_file = os.path.join(cub_root, 'images.txt')
    boxes_file = os.path.join(cub_root, 'bounding_boxes.txt')
    image_base_dir = os.path.join(cub_root, 'images')

    if not os.path.exists(images_file):
        raise FileNotFoundError(f"未找到 images.txt: {images_file}")
    if not os.path.exists(boxes_file):
        raise FileNotFoundError(f"未找到 bounding_boxes.txt: {boxes_file}")
    if not os.path.exists(image_base_dir):
        raise FileNotFoundError(f"未找到图片目录: {image_base_dir}")

    # ---- 读取标注文件 ----
    print("[信息] 正在读取标注文件...")
    image_info = read_cub_file(images_file)   # 格式: [image_id, image_path]
    box_info = read_cub_file(boxes_file)       # 格式: [image_id, x, y, w, h]

    # 将 bounding_boxes 转为字典，key 为 image_id
    box_dict = {}
    for row in box_info:
        img_id = int(row[0])
        x, y, w, h = float(row[1]), float(row[2]), float(row[3]), float(row[4])
        box_dict[img_id] = (x, y, w, h)

    # ---- 收集所有类别名称 ----
    class_names = set()
    image_records = []  # 存储所有图片记录: (image_id, rel_path, box)

    for row in image_info:
        img_id = int(row[0])
        rel_path = row[1]
        # 从路径中提取类别名（第一级目录名）
        class_name = rel_path.split('/')[0]
        class_names.add(class_name)

        if img_id in box_dict:
            image_records.append((img_id, rel_path, class_name, box_dict[img_id]))
        else:
            print(f"[警告] 图片 {rel_path} (ID={img_id}) 没有对应的边界框标注，已跳过")

    # 排序类别名称，确保 class_id 映射稳定
    sorted_classes = sorted(class_names)
    class_to_id = {name: idx for idx, name in enumerate(sorted_classes)}
    num_classes = len(sorted_classes)

    print(f"[信息] 共发现 {num_classes} 个类别，{len(image_records)} 张有效图片")

    # ---- 创建输出目录结构 ----
    dirs_to_create = [
        os.path.join(output_dir, 'images', 'train'),
        os.path.join(output_dir, 'images', 'val'),
        os.path.join(output_dir, 'labels', 'train'),
        os.path.join(output_dir, 'labels', 'val'),
    ]
    for d in dirs_to_create:
        os.makedirs(d, exist_ok=True)

    # ---- 按 8:2 分割 train/val ----
    random.seed(RANDOM_SEED)
    random.shuffle(image_records)

    split_idx = int(len(image_records) * TRAIN_RATIO)
    train_records = image_records[:split_idx]
    val_records = image_records[split_idx:]

    print(f"[信息] 训练集: {len(train_records)} 张, 验证集: {len(val_records)} 张")

    # ---- 转换并写入 YOLO 格式 ----
    def process_records(records, split_name):
        """
        处理一组图片记录，将图片复制到 YOLO 目录，并生成对应的标签文件

        参数:
            records: 图片记录列表
            split_name: 'train' 或 'val'
        """
        success_count = 0
        for img_id, rel_path, class_name, (bx, by, bw, bh) in records:
            # 源图片路径
            src_img_path = os.path.join(cub_root, 'images', rel_path)
            if not os.path.exists(src_img_path):
                print(f"[警告] 图片文件不存在: {src_img_path}，已跳过")
                continue

            # 目标文件名（用 class_id 前缀避免重名）
            class_id = class_to_id[class_name]
            file_stem = Path(rel_path).stem
            dst_filename = f"{class_id}_{file_stem}.jpg"
            dst_img_path = os.path.join(output_dir, 'images', split_name, dst_filename)

            # 复制图片到目标目录
            shutil.copy2(src_img_path, dst_img_path)

            # 获取图片尺寸，计算归一化坐标
            from PIL import Image
            with Image.open(src_img_path) as img:
                img_w, img_h = img.size

            # 计算 YOLO 归一化坐标
            # CUB 标注的 (x, y, w, h) 是绝对像素坐标
            x_center = (bx + bw / 2.0) / img_w
            y_center = (by + bh / 2.0) / img_h
            norm_w = bw / img_w
            norm_h = bh / img_h

            # 确保坐标在 [0, 1] 范围内
            x_center = max(0.0, min(1.0, x_center))
            y_center = max(0.0, min(1.0, y_center))
            norm_w = max(0.0, min(1.0, norm_w))
            norm_h = max(0.0, min(1.0, norm_h))

            # 写入 YOLO 格式标签文件
            label_filename = f"{class_id}_{file_stem}.txt"
            label_path = os.path.join(output_dir, 'labels', split_name, label_filename)
            with open(label_path, 'w') as f:
                f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}\n")

            success_count += 1

        return success_count

    print("[信息] 正在转换训练集...")
    train_count = process_records(train_records, 'train')
    print(f"[信息] 训练集转换完成: {train_count} 张图片")

    print("[信息] 正在转换验证集...")
    val_count = process_records(val_records, 'val')
    print(f"[信息] 验证集转换完成: {val_count} 张图片")

    # ---- 生成 data.yaml 配置文件 ----
    yaml_path = os.path.join(output_dir, 'data.yaml')
    # 构建 YAML 类别名称列表（单行格式）
    names_str = ", ".join([f"'{name}'" for name in sorted_classes])

    yaml_content = f"""# CUB-200-2011 YOLO 格式数据集配置
# 自动生成，请勿手动修改

# 数据集根目录（相对于本文件的路径）
path: .

# 训练集和验证集图片目录
train: images/train
val: images/val

# 类别数量
nc: {num_classes}

# 类别名称
names: [{names_str}]
"""

    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    print(f"[信息] data.yaml 已生成: {yaml_path}")
    print(f"[完成] 数据集转换完成！共 {train_count + val_count} 张图片")
    print(f"       训练集: {train_count} 张, 验证集: {val_count} 张")
    print(f"       类别数: {num_classes}")

    return yaml_path


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='将 CUB-200-2011 数据集转换为 YOLO 格式')
    parser.add_argument('--cub-root', type=str, default=None,
                        help='CUB-200-2011 数据集根目录路径')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='YOLO 格式输出目录路径')
    parser.add_argument('--seed', type=int, default=RANDOM_SEED,
                        help=f'随机种子（默认: {RANDOM_SEED}）')
    parser.add_argument('--train-ratio', type=float, default=TRAIN_RATIO,
                        help=f'训练集比例（默认: {TRAIN_RATIO}）')
    args = parser.parse_args()

    # 更新全局参数
    if args.seed:
        RANDOM_SEED = args.seed
    if args.train_ratio:
        TRAIN_RATIO = args.train_ratio

    convert_cub_to_yolo(
        cub_root=args.cub_root,
        output_dir=args.output_dir,
    )