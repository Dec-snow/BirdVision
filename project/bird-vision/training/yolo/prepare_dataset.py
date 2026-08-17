#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多类别鸟类检测数据集自动准备工具

对数据库中选定的15种鸟，分别从Unsplash搜索下载图片，
使用YOLO预训练模型自动标注鸟区域，生成YOLO多类别训练数据集。

类别名与数据库 BirdSpecies.name_cn 完全一致。

工作流程：
1. 对每种鸟，从 Unsplash 搜索页面获取图片 URL
2. 下载图片到 datasets/birds/raw/{name_cn}/ 目录
3. 用 YOLO yolo11n.pt 预训练模型检测每张图中的鸟区域（COCO class 14 = bird）
4. 将检测到的鸟区域标注为对应类别ID（0=麻雀, 1=喜鹊, ...）
5. 按 80/20 分割 train/val
6. 生成 data.yaml

使用方式：
  python prepare_dataset.py                  # 下载并准备数据集（每种鸟10张）
  python prepare_dataset.py --count 20       # 每种鸟下载20张
  python prepare_dataset.py --skip-download   # 跳过下载，仅标注已有图片
  python prepare_dataset.py --species 麻雀 喜鹊  # 只处理指定种类

最终生成的数据集结构：
  datasets/birds/
  ├── images/
  │   ├── train/   # 80% 训练图片
  │   └── val/     # 20% 验证图片
  ├── labels/
  │   ├── train/   # 训练标签 (.txt, YOLO格式: class_id x_center y_center width height)
  │   └── val/     # 验证标签 (.txt)
  ├── raw/         # 原始下载图片（按种类分目录）
  └── data.yaml    # YOLO 数据集配置 (nc=15, names=[麻雀, 喜鹊, ...])
"""

import argparse
import os
import random
import shutil
import sys
import time
import urllib.request

# ============================================================
# 项目路径
# ============================================================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATASET_DIR = os.path.join(PROJECT_ROOT, 'datasets', 'birds')
RAW_DIR = os.path.join(DATASET_DIR, 'raw')

# ============================================================
# 15种训练鸟类，名称与数据库 BirdSpecies.name_cn 完全一致
# search 字段用于 Unsplash 搜索关键词
# ============================================================
BIRD_SPECIES = [
    {'name_cn': '麻雀',     'search': 'sparrow bird'},
    {'name_cn': '喜鹊',     'search': 'magpie bird'},
    {'name_cn': '白头鹎',   'search': 'bulbul bird'},
    {'name_cn': '翠鸟',     'search': 'kingfisher bird'},
    {'name_cn': '白鹭',     'search': 'egret bird'},
    {'name_cn': '戴胜',     'search': 'hoopoe bird'},
    {'name_cn': '啄木鸟',   'search': 'woodpecker bird'},
    {'name_cn': '红嘴蓝鹊', 'search': 'blue magpie bird'},
    {'name_cn': '画眉',     'search': 'laughingthrush bird'},
    {'name_cn': '鸳鸯',     'search': 'mandarin duck'},
    {'name_cn': '绿头鸭',   'search': 'mallard duck'},
    {'name_cn': '丹顶鹤',   'search': 'red-crowned crane'},
    {'name_cn': '苍鹭',     'search': 'grey heron'},
    {'name_cn': '环颈雉',   'search': 'pheasant bird'},
    {'name_cn': '黄鹂',     'search': 'oriole bird'},
]

# COCO 数据集中 bird 的类别 ID 为 14
COCO_BIRD_CLASS_ID = 14

# 下载置信度阈值（YOLO检测）
CONFIDENCE_THRESHOLD = 0.3

# 训练/验证集分割比例
TRAIN_RATIO = 0.8

# 请求头（模拟浏览器）
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


# ============================================================
# Unsplash 图片搜索与下载
# ============================================================

# 导入硬编码的图片 URL 映射（同目录模块，无论从哪个目录启动脚本均可找到）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from species_urls import SPECIES_IMAGE_URLS
except ImportError:
    SPECIES_IMAGE_URLS = {}


_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')


def _list_images(directory):
    """列出目录下的图片文件（绝对路径），目录不存在时返回空列表。"""
    if not os.path.isdir(directory):
        return []
    return [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(_IMAGE_EXTENSIONS)
    ]


def get_species_urls(name_cn, count=10):
    """
    获取指定鸟种的图片 URL 列表。

    优先从 species_urls.py 的硬编码 URL 获取，
    若不存在则返回空列表。

    Args:
        name_cn: 鸟种中文名
        count: 需要的数量

    Returns:
        list: 图片 URL 列表
    """
    urls = SPECIES_IMAGE_URLS.get(name_cn, [])
    return urls[:count]


def download_image(url, dest_path, timeout=15):
    """
    下载单张图片到指定路径。

    Args:
        url: 图片 URL
        dest_path: 目标文件路径
        timeout: 超时时间（秒）

    Returns:
        bool: 下载是否成功
    """
    try:
        req = urllib.request.Request(url, headers={
            **HEADERS,
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if len(data) < 2000:  # 至少 2KB（过滤掉错误页面或小图标）
                return False
            with open(dest_path, 'wb') as f:
                f.write(data)
            return True
    except Exception:
        return False


def download_species_images(species_info, count=10):
    """
    为单个鸟种搜索并下载图片。

    Args:
        species_info: 鸟种信息字典 {'name_cn': ..., 'search': ...}
        count: 每种鸟需要下载的图片数量

    Returns:
        list: 下载成功的图片路径列表
    """
    name_cn = species_info['name_cn']
    search_query = species_info['search']
    species_raw_dir = os.path.join(RAW_DIR, name_cn)
    os.makedirs(species_raw_dir, exist_ok=True)

    # 检查已有图片数量
    existing_images = _list_images(species_raw_dir)
    if len(existing_images) >= count:
        print(f"    [{name_cn}] 已有 {len(existing_images)} 张图片，跳过下载")
        return existing_images

    print(f"    [{name_cn}] 获取图片 URL...")

    # 获取图片 URL
    urls = get_species_urls(name_cn, count=count + 5)

    if not urls:
        print(f"    [{name_cn}] 未找到图片 URL")
        return existing_images

    # 下载图片
    downloaded = list(existing_images)
    max_index = max(
        (int(os.path.basename(f).split('_')[1].split('.')[0])
         for f in existing_images
         if '_' in os.path.basename(f)),
        default=-1,
    )

    for url in urls:
        if len(downloaded) >= count:
            break

        max_index += 1
        filename = f"{name_cn}_{max_index:03d}.jpg"
        filepath = os.path.join(species_raw_dir, filename)

        # 跳过已存在的文件
        if os.path.exists(filepath) and os.path.getsize(filepath) > 2000:
            downloaded.append(filepath)
            continue

        success = download_image(url, filepath)
        if success:
            downloaded.append(filepath)
            time.sleep(0.3)  # 避免请求过快
        else:
            # 删除空文件/小文件
            if os.path.exists(filepath):
                os.remove(filepath)

    result = _list_images(species_raw_dir)
    print(f"    [{name_cn}] 下载完成: {len(result)} 张图片")
    return result


def download_all_species(species_list, count=10, skip_download=False,
                          only_species=None):
    """
    下载所有鸟种的图片。

    Args:
        species_list: 鸟种列表
        count: 每种鸟下载数量
        skip_download: 是否跳过下载
        only_species: 只处理指定的种类（中文名列表）

    Returns:
        dict: {name_cn: [图片路径列表], ...}
    """
    os.makedirs(RAW_DIR, exist_ok=True)
    species_images = {}

    for i, species in enumerate(species_list):
        name_cn = species['name_cn']

        # 如果指定了只处理某些种类
        if only_species and name_cn not in only_species:
            print(f"  [{i+1}/{len(species_list)}] {name_cn} - 跳过（不在指定列表中）")
            continue

        print(f"  [{i+1}/{len(species_list)}] 处理: {name_cn}")

        if skip_download:
            # 跳过下载，使用已有图片
            images = _list_images(os.path.join(RAW_DIR, name_cn))
            print(f"    [{name_cn}] 已有 {len(images)} 张图片")
        else:
            images = download_species_images(species, count=count)

        species_images[name_cn] = images

    return species_images


# ============================================================
# YOLO 自动标注
# ============================================================

def auto_label_with_yolo(species_images, species_list, dataset_dir):
    """
    使用 YOLO 预训练模型对所有图片进行自动标注。

    将每个鸟种目录下的图片用 yolo11n.pt 检测鸟区域，
    并将检测到的区域标注为对应种类的类别 ID。

    Args:
        species_images: {name_cn: [图片路径列表], ...}
        species_list: 鸟种信息列表
        dataset_dir: 数据集输出目录

    Returns:
        dict: 统计信息
    """
    print("\n" + "=" * 60)
    print("[步骤2] 使用 YOLO 预训练模型自动标注")
    print("=" * 60)

    try:
        from ultralytics import YOLO
    except ImportError:
        print("[错误] ultralytics 未安装，请运行: pip install ultralytics")
        sys.exit(1)

    # 加载预训练模型
    print("[信息] 加载 YOLOv11 预训练模型 (yolo11n.pt)...")
    model = YOLO('yolo11n.pt')

    # 构建类别映射 name_cn -> class_id
    name_to_id = {species['name_cn']: idx for idx, species in enumerate(species_list)}
    nc = len(species_list)

    # 准备输出目录
    train_img_dir = os.path.join(dataset_dir, 'images', 'train')
    val_img_dir = os.path.join(dataset_dir, 'images', 'val')
    train_label_dir = os.path.join(dataset_dir, 'labels', 'train')
    val_label_dir = os.path.join(dataset_dir, 'labels', 'val')

    for d in [train_img_dir, val_img_dir, train_label_dir, val_label_dir]:
        os.makedirs(d, exist_ok=True)

    # 收集所有标注结果
    all_labeled = []  # [{'path': ..., 'labels': [...], 'class_id': ...}, ...]
    stats = {species['name_cn']: {'total': 0, 'labeled': 0} for species in species_list}

    total_images = sum(len(imgs) for imgs in species_images.values())
    processed = 0

    for species in species_list:
        name_cn = species['name_cn']
        class_id = name_to_id[name_cn]
        images = species_images.get(name_cn, [])

        if not images:
            continue

        print(f"\n  [{name_cn}] (类别ID={class_id}) 处理 {len(images)} 张图片...")

        for img_path in images:
            processed += 1
            stats[name_cn]['total'] += 1

            try:
                results = model(img_path, verbose=False)

                for result in results:
                    boxes = result.boxes
                    img_w = result.orig_shape[1]
                    img_h = result.orig_shape[0]

                    bird_boxes = []
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        if cls_id == COCO_BIRD_CLASS_ID:
                            conf = float(box.conf[0])
                            if conf >= CONFIDENCE_THRESHOLD:
                                x1, y1, x2, y2 = box.xyxy[0].tolist()
                                bird_boxes.append((x1, y1, x2, y2, conf))

                    if bird_boxes:
                        # 转换为 YOLO 格式标签
                        label_lines = []
                        for x1, y1, x2, y2, conf in bird_boxes:
                            x_center = (x1 + x2) / 2.0 / img_w
                            y_center = (y1 + y2) / 2.0 / img_h
                            width = (x2 - x1) / img_w
                            height = (y2 - y1) / img_h

                            # 确保值在 [0, 1] 范围内
                            x_center = max(0.0, min(1.0, x_center))
                            y_center = max(0.0, min(1.0, y_center))
                            width = max(0.0, min(1.0, width))
                            height = max(0.0, min(1.0, height))

                            label_lines.append(
                                f"{class_id} {x_center:.6f} {y_center:.6f} "
                                f"{width:.6f} {height:.6f}"
                            )

                        if label_lines:
                            all_labeled.append({
                                'path': img_path,
                                'labels': label_lines,
                                'class_id': class_id,
                                'name_cn': name_cn,
                            })
                            stats[name_cn]['labeled'] += 1

            except Exception as e:
                print(f"      [错误] 标注失败 {os.path.basename(img_path)}: {e}")

            # 进度提示
            if processed % 20 == 0:
                print(f"    [进度] {processed}/{total_images} 张已处理, "
                      f"已标注 {len(all_labeled)} 张包含鸟类")

    print(f"\n[信息] 自动标注完成: 共处理 {total_images} 张图片, "
          f"{len(all_labeled)} 张包含鸟类检测框")

    if not all_labeled:
        print("[错误] 未检测到任何鸟类，数据集生成失败")
        print("[提示] 请检查图片是否包含清晰的鸟类个体")
        return stats

    # 打印各物种标注统计
    print("\n  各物种标注统计:")
    for species in species_list:
        name_cn = species['name_cn']
        s = stats[name_cn]
        print(f"    {name_cn:8s} (ID={name_to_id[name_cn]:2d}): "
              f"{s['labeled']:3d}/{s['total']:3d} 张")

    # 按 80/20 比例划分训练集/验证集
    random.seed(42)
    random.shuffle(all_labeled)
    split_idx = int(len(all_labeled) * TRAIN_RATIO)
    train_items = all_labeled[:split_idx]
    val_items = all_labeled[split_idx:]

    print(f"\n[信息] 训练集/验证集划分: {len(train_items)} 张 / {len(val_items)} 张 "
          f"(比例 {TRAIN_RATIO:.0%}/{1-TRAIN_RATIO:.0%})")

    # 复制图片和标签到对应目录
    _copy_dataset_items(train_items, train_img_dir, train_label_dir)
    _copy_dataset_items(val_items, val_img_dir, val_label_dir)

    # 生成 data.yaml
    _generate_data_yaml(dataset_dir, species_list, nc)

    return stats


def _copy_dataset_items(items, img_dir, label_dir):
    """
    将标注好的图片和标签复制到目标目录。
    """
    for item in items:
        basename = os.path.basename(item['path'])
        name_without_ext = os.path.splitext(basename)[0]

        # 确保文件名唯一（避免不同物种的同名文件冲突）
        # 使用 {name_cn}_{original_name} 格式
        unique_name = f"{item['name_cn']}_{name_without_ext}"
        unique_img_name = f"{unique_name}.jpg"
        unique_label_name = f"{unique_name}.txt"

        # 复制图片
        dst_img = os.path.join(img_dir, unique_img_name)
        shutil.copy2(item['path'], dst_img)

        # 保存标签
        label_path = os.path.join(label_dir, unique_label_name)
        with open(label_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(item['labels']))


def _generate_data_yaml(dataset_dir, species_list, nc):
    """
    生成 data.yaml 配置文件。

    类别名与数据库 BirdSpecies.name_cn 完全一致。
    """
    names_list = '\n'.join(f'  {i}: {species["name_cn"]}'
                          for i, species in enumerate(species_list))

    yaml_content = f"""# Bird Detection Dataset (multi-class, auto-labeled)
# 多类别鸟类检测数据集 - 类别名与数据库 BirdSpecies.name_cn 完全一致
#
# 自动生成工具: prepare_dataset.py
# 类别数量: {nc}
# 标注方式: YOLO yolo11n.pt 预训练模型自动标注

path: .
# ↑ 可移植写法：使用相对路径（以 data.yaml 所在目录为根），
#   兼容 Windows 本地 / DSW Linux / 远端 GPU 服务器等所有环境
train: images/train
val: images/val

# 类别数量
nc: {nc}

# 类别名称（与数据库 BirdSpecies.name_cn 一致）
names:
{names_list}
"""

    yaml_path = os.path.join(dataset_dir, 'data.yaml')
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    print(f"\n[信息] data.yaml 已生成: {yaml_path}")
    print(f"  路径: {dataset_dir.replace(os.sep, '/')}")
    print(f"  类别数: {nc}")
    print(f"  类别名: {[s['name_cn'] for s in species_list]}")


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='多类别鸟类检测数据集自动准备工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
支持的鸟种 ({len(BIRD_SPECIES)} 种，与数据库 BirdSpecies.name_cn 一致）:
{chr(10).join(f'  {i+1:2d}. {s["name_cn"]} (搜索: "{s["search"]}")' for i, s in enumerate(BIRD_SPECIES))}

示例:
  python prepare_dataset.py                    # 每种鸟下载10张
  python prepare_dataset.py --count 20         # 每种鸟下载20张
  python prepare_dataset.py --skip-download     # 跳过下载，仅标注已有图片
  python prepare_dataset.py --species 麻雀 喜鹊  # 只处理指定种类
  python prepare_dataset.py --confidence 0.4   # 设置检测置信度阈值
""",
    )
    parser.add_argument('--count', type=int, default=10,
                        help='每种鸟下载的图片数量（默认: 10）')
    parser.add_argument('--skip-download', action='store_true',
                        help='跳过下载，仅使用已有图片进行标注')
    parser.add_argument('--species', nargs='+', default=None,
                        help='只处理指定的鸟种（中文名，空格分隔）')
    parser.add_argument('--confidence', type=float, default=0.3,
                        help='YOLO 检测置信度阈值（默认: 0.3）')
    parser.add_argument('--train-ratio', type=float, default=0.8,
                        help='训练集比例（默认: 0.8）')

    args = parser.parse_args()

    # 应用全局参数
    global CONFIDENCE_THRESHOLD, TRAIN_RATIO
    CONFIDENCE_THRESHOLD = args.confidence
    TRAIN_RATIO = args.train_ratio

    # 确定要处理的鸟种
    if args.species:
        target_species = [s for s in BIRD_SPECIES if s['name_cn'] in args.species]
        if not target_species:
            print(f"[错误] 指定的种类不在列表中: {args.species}")
            print(f"[提示] 可选种类: {[s['name_cn'] for s in BIRD_SPECIES]}")
            sys.exit(1)
        print(f"[信息] 仅处理指定种类: {[s['name_cn'] for s in target_species]}")
    else:
        target_species = BIRD_SPECIES

    print("=" * 60)
    print("  多类别鸟类检测数据集自动准备工具")
    print(f"  鸟种数量: {len(target_species)}")
    print(f"  每种下载: {args.count} 张（--skip-download 时跳过）")
    print(f"  置信度阈值: {CONFIDENCE_THRESHOLD}")
    print(f"  训练/验证比例: {TRAIN_RATIO:.0%}/{1-TRAIN_RATIO:.0%}")
    print("=" * 60)

    # 步骤1: 下载图片
    print(f"\n[步骤1] 下载鸟类图片（Unsplash）")
    species_images = download_all_species(
        target_species,
        count=args.count,
        skip_download=args.skip_download,
        only_species=args.species,
    )

    total_downloaded = sum(len(imgs) for imgs in species_images.values())
    print(f"\n[信息] 图片准备完成: {total_downloaded} 张图片 "
          f"({len(species_images)} 种鸟)")

    if total_downloaded == 0:
        print("\n[错误] 没有可用的图片，请先运行不带 --skip-download 的命令")
        sys.exit(1)

    # 步骤2: YOLO 自动标注
    stats = auto_label_with_yolo(species_images, target_species, DATASET_DIR)

    # 最终统计
    total_labeled = sum(s['labeled'] for s in stats.values())
    print("\n" + "=" * 60)
    if total_labeled > 0:
        print("[完成] 数据集生成成功！")
        print(f"  数据集目录: {DATASET_DIR}")
        print(f"  配置文件: {os.path.join(DATASET_DIR, 'data.yaml')}")
        print(f"\n  可以运行以下命令开始训练:")
        print(f"    python {os.path.join(os.path.dirname(__file__), 'train.py')}")
    else:
        print("[失败] 数据集生成失败，未检测到鸟类")
        print("[提示] 请尝试:")
        print("  1. 增加 --count 参数获取更多图片")
        print("  2. 降低 --confidence 阈值")
        print("  3. 检查网络连接，确保 Unsplash 可访问")
    print("=" * 60)


if __name__ == '__main__':
    main()
