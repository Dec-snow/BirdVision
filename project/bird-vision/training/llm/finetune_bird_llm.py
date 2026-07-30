# -*- coding: utf-8 -*-
"""
鸟类知识 LLM 微调脚本
基于 LLaMA Factory 框架，使用 LoRA 方法微调

使用步骤:
1. 安装依赖: pip install "transformers>=4.34.0" "datasets>=2.14.0" peft accelerate torch
2. 安装 llama-factory: pip install llama-factory
3. 运行脚本: python finetune_bird_llm.py
"""

import os
import sys

def create_dataset():
    """创建鸟类知识微调数据集"""
    print("=" * 60)
    print("创建鸟类知识微调数据集")
    print("=" * 60)
    
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # 读取已有的 QA 数据
    qa_file = os.path.join(data_dir, 'bird_knowledge_qa.json')
    if os.path.exists(qa_file):
        import json
        with open(qa_file, 'r', encoding='utf-8') as f:
            qa_data = json.load(f)
        
        # 转换为 LLaMA Factory 需要的格式
        train_data = []
        for item in qa_data:
            train_data.append({
                'instruction': item['instruction'],
                'input': item.get('input', ''),
                'output': item['output'],
            })
        
        # 划分训练集和验证集 (90%/10%)
        split_idx = int(len(train_data) * 0.9)
        train_split = train_data[:split_idx]
        val_split = train_data[split_idx:]
        
        # 保存为 JSONL 格式 (LLaMA Factory 支持)
        train_file = os.path.join(data_dir, 'bird_knowledge_train.jsonl')
        val_file = os.path.join(data_dir, 'bird_knowledge_val.jsonl')
        
        with open(train_file, 'w', encoding='utf-8') as f:
            for item in train_split:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        with open(val_file, 'w', encoding='utf-8') as f:
            for item in val_split:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"训练集: {len(train_split)} 条, 验证集: {len(val_split)} 条")
        print(f"保存到: {train_file}")
        print(f"保存到: {val_file}")
        
        return train_file, val_file
    else:
        print(f"未找到 QA 数据文件: {qa_file}")
        return None, None

def create_config(train_file, val_file):
    """创建 LLaMA Factory 配置文件"""
    config_content = f"""### Model
model_name_or_path: qwen2.5:7b
adapter_name_or_path:
model_base:
model_type: qwen2
template: qwen
quantization_bit: 4
quantization_type: bitsandbytes

### Method
stage: sft
do_train: true
do_eval: true
finetuning_type: lora
lora_rank: 8
lora_alpha: 16
lora_dropout: 0.05
lora_target: all

### Dataset
dataset: bird_knowledge
dataset_dir: {os.path.dirname(train_file)}
train_file: {os.path.basename(train_file)}
val_file: {os.path.basename(val_file)}
cutoff_len: 2048
max_samples: 200
overwrite_output_dir: true

### Output
output_dir: ../../models/llm/bird-expert
logging_dir: ../../models/llm/bird-expert/logs
save_steps: 50
save_total_limit: 3
load_best_model_at_end: true

### Train
per_device_train_batch_size: 2
per_device_eval_batch_size: 2
gradient_accumulation_steps: 4
learning_rate: 5.0e-5
num_train_epochs: 3
max_grad_norm: 1.0
warmup_ratio: 0.1
lr_scheduler_type: cosine

### Eval
eval_strategy: steps
eval_steps: 20
val_size: 0.1

### Logging
logging_steps: 10
report_to: tensorboard

### Misc
seed: 42
fp16: true
"""
    config_path = os.path.join(os.path.dirname(__file__), 'finetune_config.yaml')
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print(f"配置文件已保存: {config_path}")
    return config_path

def run_finetune(config_path):
    """运行微调"""
    print("\n" + "=" * 60)
    print("开始微调训练")
    print("=" * 60)
    
    try:
        from llama_factory.cli import main
        sys.argv = ['llama_factory', 'train', config_path]
        main()
        print("微调完成!")
    except ImportError:
        print("请先安装 llama-factory: pip install llama-factory")
        print("或者直接使用命令: llamafactory-cli train " + config_path)

def convert_to_ollama():
    """将微调后的模型转换为 Ollama 格式"""
    print("\n" + "=" * 60)
    print("转换为 Ollama 格式")
    print("=" * 60)
    
    adapter_path = os.path.join(os.path.dirname(__file__), '../../models/llm/bird-expert')
    ollama_dir = os.path.join(os.path.dirname(__file__), '../../models/llm/bird-expert-ollama')
    os.makedirs(ollama_dir, exist_ok=True)
    
    # 创建 Ollama Modelfile
    modelfile_content = f"""FROM qwen2.5:7b

# 加载微调的 LoRA 适配器
ADAPTER {adapter_path}

# 设置系统提示词，让模型成为鸟类专家
SYSTEM
你是一位专业的鸟类学家和自然保护专家。请用中文回答关于鸟类的问题，包括鸟类识别、生态习性、分类学、保护现状、观鸟技巧等。回答要准确、专业但易懂，引用权威资料。如果问题超出鸟类知识范围，请礼貌地说明。
"""
    
    modelfile_path = os.path.join(ollama_dir, 'Modelfile')
    with open(modelfile_path, 'w', encoding='utf-8') as f:
        f.write(modelfile_content)
    
    print(f"Modelfile 已创建: {modelfile_path}")
    print(f"\n请在终端运行以下命令创建 Ollama 模型:")
    print(f"  cd {ollama_dir}")
    print(f"  ollama create bird-expert -f Modelfile")
    print(f"\n创建成功后，运行:")
    print(f"  ollama run bird-expert")
    print(f"\n或者通过 API 调用:")
    print(f"  curl http://localhost:11434/api/chat -d '{{\"model\": \"bird-expert\", \"messages\": [{{\"role\": \"user\", \"content\": \"丹顶鹤有什么特征？\"}}]}}'")
    
    return modelfile_path

if __name__ == '__main__':
    # 1. 创建数据集
    train_file, val_file = create_dataset()
    if not train_file:
        sys.exit(1)
    
    # 2. 创建配置
    config_path = create_config(train_file, val_file)
    
    # 3. 运行微调 (可选，需要 GPU)
    # run_finetune(config_path)
    
    # 4. 创建 Ollama 转换脚本
    convert_to_ollama()
    
    print("\n" + "=" * 60)
    print("准备完成!")
    print("=" * 60)
    print("\n下一步操作:")
    print("1. 安装 llama-factory: pip install llama-factory")
    print("2. 运行微调: llamafactory-cli train " + config_path)
    print("3. 转换为 Ollama: ollama create bird-expert -f " + os.path.join(os.path.dirname(__file__), '../../models/llm/bird-expert-ollama/Modelfile'))
    print("4. 使用模型: ollama run bird-expert")
