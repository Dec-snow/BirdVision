# -*- coding: utf-8 -*-
"""
YOLO 鸟类识别训练脚本

功能说明：
- 使用 ultralytics YOLOv11 预训练模型
- 支持三种数据集来源：
  1. 自动下载 CUB-200-2011 数据集（200种鸟类，约 1.2GB）
  2. 手动放置 YOLO 格式数据集到 datasets/birds/
  3. Roboflow 数据集（需 API Key，见 README）
- 训练完成后将 best.pt 复制到 models/yolo/best.pt
- 支持命令行参数自定义训练配置

使用示例：
  python train.py                          # 检测数据集并训练
  python train.py --download-cub           # 强制下载 CUB-200-2011
  python train.py --epochs 100 --batch 32  # 自定义训练轮数和批量大小
  python train.py --model yolo11s.pt       # 使用更大的模型
  python train.py --data custom.yaml       # 使用自定义数据集配置
"""

import argparse
import os
import shutil
import tarfile
import urllib.request

# ---- 检测 GPU 可用性（延迟导入 torch，避免 Python 3.14 启动慢） ----
def _check_gpu():
    """延迟检测 GPU，避免 import torch 耗时过长"""
    try:
        import torch
        return '0' if torch.cuda.is_available() else 'cpu'
    except Exception:
        return 'cpu'

# 项目根目录（从当前脚本位置向上两级）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# YOLO 格式数据集目录
DATASET_DIR = os.path.join(PROJECT_ROOT, 'datasets', 'birds')

# YOLO 数据集配置文件路径
DATA_YAML = os.path.join(DATASET_DIR, 'data.yaml')

# 模型输出目录
MODEL_OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'models', 'yolo')

# CUB-200-2011 下载 URL
CUB_DOWNLOAD_URL = 'https://www.vision.caltech.edu/visipedia-data/CUB-200-2011/CUB_200_2011.tgz'


def check_yolo_dataset():
    """
    检查 YOLO 格式数据集是否已存在。

    返回:
        bool: 数据集是否完整
    """
    required_paths = [
        os.path.join(DATASET_DIR, 'images', 'train'),
        os.path.join(DATASET_DIR, 'labels', 'train'),
        DATA_YAML,
    ]
    for path in required_paths:
        if not os.path.exists(path):
            return False
        if os.path.isdir(path):
            if not os.listdir(path):
                return False
    return True


def download_and_convert_cub():
    """
    手动下载 CUB-200-2011 数据集并转换为 YOLO 格式。

    不依赖 torchvision，直接使用 urllib 下载 .tgz 文件。
    """
    print("=" * 60)
    print("[信息] 开始下载 CUB-200-2011 数据集...")
    print("[信息] CUB-200-2011: 200种鸟类, 11788张图片, 约1.2GB")
    print("=" * 60)

    # CUB 数据集下载目标路径
    cub_download_dir = os.path.join(PROJECT_ROOT, 'datasets', 'cub200')
    os.makedirs(cub_download_dir, exist_ok=True)

    tgz_path = os.path.join(cub_download_dir, 'CUB_200_2011.tgz')
    cub_extracted_path = os.path.join(cub_download_dir, 'CUB_200_2011')

    # 如果已解压，跳过下载
    if os.path.exists(os.path.join(cub_extracted_path, 'images.txt')):
        print(f"[信息] 数据集已解压: {cub_extracted_path}")
    else:
        # 下载 .tgz 文件（支持断点判断）
        if not os.path.exists(tgz_path):
            print(f"[信息] 下载 URL: {CUB_DOWNLOAD_URL}")
            print(f"[信息] 保存到: {tgz_path}")
            print("[信息] 下载可能需要 10-30 分钟，取决于网络速度...")

            try:
                # 使用 reporthook 显示下载进度
                def reporthook(block_num, block_size, total_size):
                    if block_num % 200 == 0:
                        if total_size > 0:
                            percent = block_num * block_size * 100 / total_size
                            print(f"\r[下载] {percent:.1f}% "
                                  f"({block_num * block_size // 1024 // 1024}MB / "
                                  f"{total_size // 1024 // 1024}MB)", end='', flush=True)
                        else:
                            print(f"\r[下载] {block_num * block_size // 1024 // 1024}MB", end='', flush=True)

                urllib.request.urlretrieve(CUB_DOWNLOAD_URL, tgz_path, reporthook=reporthook)
                print("\n[信息] 下载完成！")
            except Exception as e:
                print(f"\n[错误] 下载失败: {e}")
                print("[提示] 可手动下载: https://www.vision.caltech.edu/visipedia-data/CUB-200-2011/CUB_200_2011.tgz")
                print(f"[提示] 下载后放到: {tgz_path}")
                return
        else:
            print(f"[信息] .tgz 文件已存在，跳过下载: {tgz_path}")

        # 解压 .tgz 文件
        print("[信息] 正在解压数据集...")
        try:
            with tarfile.open(tgz_path, 'r:gz') as tar:
                tar.extractall(path=cub_download_dir)
            print(f"[信息] 解压完成: {cub_extracted_path}")
        except Exception as e:
            print(f"[错误] 解压失败: {e}")
            return

    # 调用格式转换工具
    print("[信息] 开始将 CUB 数据集转换为 YOLO 格式...")
    try:
        from convert_cub_to_yolo import convert_cub_to_yolo
        convert_cub_to_yolo(
            cub_root=cub_extracted_path,
            output_dir=DATASET_DIR,
        )
        print("[信息] 数据集准备完成！")
    except Exception as e:
        print(f"[错误] 格式转换失败: {e}")
        import traceback
        traceback.print_exc()


def print_dataset_guide():
    """打印手动准备数据集的指南。"""
    print("\n" + "=" * 60)
    print("[数据集准备指南]")
    print("=" * 60)
    print("""
方式一：自动准备数据集（推荐）
  python training/yolo/prepare_dataset.py
  从 Unsplash 下载鸟类图片，用 YOLO 预训练模型自动标注，生成 YOLO 格式数据集

方式二：自动下载 CUB-200-2011
  python train.py --download-cub
  CUB-200-2011 包含 200 种鸟类，11788 张图片，自动转换为 YOLO 格式

方式三：手动放置 YOLO 格式数据集
  1. 从 Roboflow (https://universe.roboflow.com) 搜索 "bird detection"
  2. 下载数据集，选择 YOLOv11 格式
  3. 解压到 datasets/birds/ 目录，确保结构如下：
     datasets/birds/
     ├── images/
     │   ├── train/    # 训练图片
     │   └── val/      # 验证图片
     ├── labels/
     │   ├── train/    # 训练标签 (.txt)
     │   └── val/      # 验证标签 (.txt)
     └── data.yaml     # 数据集配置文件

方式四：自定义数据集
  1. 使用 LabelImg 或 Roboflow 标注你的鸟类图片
  2. 按 YOLO 格式组织目录结构
  3. 创建 data.yaml 配置文件
  4. 运行: python train.py --data your_data.yaml
""")


def train_yolo(epochs=50, batch=16, imgsz=416, data_path=None, model_name='yolo11n.pt'):
    """
    执行 YOLO 模型训练。

    参数:
        epochs: 训练轮数
        batch: 批量大小
        imgsz: 输入图像尺寸
        data_path: data.yaml 文件路径
        model_name: 预训练模型名称或路径
    """
    device = _check_gpu()

    if data_path is None:
        data_path = DATA_YAML

    print("=" * 60)
    print("[信息] YOLO 鸟类识别模型训练")
    print("=" * 60)
    print(f"  模型:       {model_name}")
    print(f"  数据集配置: {data_path}")
    print(f"  训练轮数:   {epochs}")
    print(f"  批量大小:   {batch}")
    print(f"  图像尺寸:   {imgsz}")
    print(f"  设备:       {device}")
    print("=" * 60)

    # 导入 ultralytics（延迟导入，减少启动时间）
    from ultralytics import YOLO

    # 加载预训练模型
    print(f"[信息] 正在加载模型: {model_name}")
    model = YOLO(model_name)

    # 确保模型输出目录存在
    os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)

    # 定义训练输出目录
    train_output_dir = os.path.join(PROJECT_ROOT, 'runs', 'detect', 'bird_train')
    print(f"[信息] 训练输出目录: {train_output_dir}")

    # 开始训练
    print("[信息] 开始训练...")
    results = model.train(
        data=data_path,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=os.path.join(PROJECT_ROOT, 'runs', 'detect'),
        name='bird_train',
        exist_ok=True,
        patience=10,
        save=True,
        save_period=-1,
        pretrained=True,
        optimizer='auto',
        verbose=True,
        seed=42,
        deterministic=True,
        workers=4,
    )

    # ---- 训练完成后处理 ----
    print("\n" + "=" * 60)
    print("[信息] 训练完成！")
    print("=" * 60)

    # 打印训练结果指标
    print("\n[结果] 训练指标:")
    if hasattr(results, 'results_dict'):
        metrics = results.results_dict
        print(f"  mAP50:   {metrics.get('metrics/mAP50(B)', 'N/A')}")
        print(f"  mAP50-95: {metrics.get('metrics/mAP50-95(B)', 'N/A')}")
        print(f"  Precision: {metrics.get('metrics/precision(B)', 'N/A')}")
        print(f"  Recall:    {metrics.get('metrics/recall(B)', 'N/A')}")

    # 将 best.pt 复制到 models/yolo/best.pt
    best_pt_source = os.path.join(train_output_dir, 'weights', 'best.pt')
    best_pt_target = os.path.join(MODEL_OUTPUT_DIR, 'best.pt')

    if os.path.exists(best_pt_source):
        os.makedirs(os.path.dirname(best_pt_target), exist_ok=True)
        shutil.copy2(best_pt_source, best_pt_target)
        print(f"\n[信息] 最佳模型已复制到: {best_pt_target}")
    else:
        print(f"\n[警告] 未找到 best.pt: {best_pt_source}")
        last_pt_source = os.path.join(train_output_dir, 'weights', 'last.pt')
        if os.path.exists(last_pt_source):
            shutil.copy2(last_pt_source, best_pt_target)
            print(f"[信息] 使用 last.pt 作为替代，已复制到: {best_pt_target}")

    return results


def main():
    """主函数：解析参数并执行训练流程"""
    parser = argparse.ArgumentParser(
        description='YOLO 鸟类识别模型训练脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--epochs', type=int, default=50,
                        help='训练轮数（默认: 50）')
    parser.add_argument('--batch', type=int, default=16,
                        help='批量大小（默认: 16）')
    parser.add_argument('--imgsz', type=int, default=416,
                        help='输入图像尺寸（默认: 416）')
    parser.add_argument('--data', type=str, default=None,
                        help='data.yaml 文件路径（默认: 自动检测）')
    parser.add_argument('--model', type=str, default='yolo11n.pt',
                        help='预训练模型名称或路径（默认: yolo11n.pt）')
    parser.add_argument('--download-cub', action='store_true',
                        help='强制下载 CUB-200-2011 数据集')

    args = parser.parse_args()

    # 步骤一：检查或下载数据集
    if args.download_cub:
        print("[信息] 用户指定下载 CUB-200-2011 数据集")
        download_and_convert_cub()
    elif not check_yolo_dataset():
        print("[警告] 未检测到 YOLO 格式数据集")
        print_dataset_guide()

        # 尝试自动下载 CUB-200-2011
        response = input("\n是否自动下载 CUB-200-2011 数据集？(y/n): ").strip().lower()
        if response == 'y':
            download_and_convert_cub()
        else:
            print("[信息] 请手动准备数据集后重新运行此脚本")
            return

    # 步骤二：确认 data.yaml 存在
    data_path = args.data if args.data else DATA_YAML
    if not os.path.exists(data_path):
        print(f"[错误] 数据集配置文件不存在: {data_path}")
        print("[错误] 请先准备数据集")
        return

    # 步骤三：开始训练
    train_yolo(
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        data_path=data_path,
        model_name=args.model,
    )


if __name__ == '__main__':
    main()
