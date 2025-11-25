#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
I/O Utilities
文件读写工具函数

提供常用的文件读写功能：
- JSONL格式读写
- TSV格式读写
- YAML配置读取
- 文件验证
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
import yaml


def load_jsonl(
    file_path: Union[str, Path],
    encoding: str = "utf-8",
    max_lines: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    加载JSONL格式文件
    
    Args:
        file_path: JSONL文件路径
        encoding: 文件编码
        max_lines: 最大读取行数（用于调试或采样）
    
    Returns:
        包含所有JSON对象的列表
    
    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON解析错误
    
    Examples:
        >>> data = load_jsonl("data/corpus.jsonl")
        >>> print(f"Loaded {len(data)} records")
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    data = []
    with open(file_path, "r", encoding=encoding) as f:
        for i, line in enumerate(f):
            if max_lines and i >= max_lines:
                break
            
            line = line.strip()
            if not line:
                continue
            
            try:
                obj = json.loads(line)
                data.append(obj)
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping invalid JSON at line {i+1}: {e}")
                continue
    
    return data


def save_jsonl(
    data: List[Dict[str, Any]],
    file_path: Union[str, Path],
    encoding: str = "utf-8",
    ensure_ascii: bool = False
) -> int:
    """
    保存数据为JSONL格式
    
    Args:
        data: 要保存的数据列表
        file_path: 输出文件路径
        encoding: 文件编码
        ensure_ascii: 是否转义非ASCII字符
    
    Returns:
        写入的行数
    
    Examples:
        >>> records = [{"id": 1, "text": "example"}]
        >>> count = save_jsonl(records, "output.jsonl")
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "w", encoding=encoding) as f:
        for obj in data:
            line = json.dumps(obj, ensure_ascii=ensure_ascii)
            f.write(line + "\n")
    
    return len(data)


def load_tsv(
    file_path: Union[str, Path],
    encoding: str = "utf-8",
    delimiter: str = "\t",
    skip_header: bool = False
) -> List[List[str]]:
    """
    加载TSV格式文件
    
    Args:
        file_path: TSV文件路径
        encoding: 文件编码
        delimiter: 分隔符
        skip_header: 是否跳过第一行（表头）
    
    Returns:
        二维列表，每行为一个列表
    
    Examples:
        >>> data = load_tsv("seeds/align_seeds.tsv", skip_header=True)
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    data = []
    with open(file_path, "r", encoding=encoding) as f:
        reader = csv.reader(f, delimiter=delimiter)
        
        if skip_header:
            next(reader, None)
        
        for row in reader:
            data.append(row)
    
    return data


def save_tsv(
    data: List[List[str]],
    file_path: Union[str, Path],
    encoding: str = "utf-8",
    delimiter: str = "\t",
    header: Optional[List[str]] = None
) -> int:
    """
    保存数据为TSV格式
    
    Args:
        data: 要保存的二维列表
        file_path: 输出文件路径
        encoding: 文件编码
        delimiter: 分隔符
        header: 可选的表头行
    
    Returns:
        写入的行数（不含表头）
    
    Examples:
        >>> alignments = [["entity1", "entity2", "0.95"]]
        >>> save_tsv(alignments, "output.tsv", header=["source", "target", "confidence"])
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "w", encoding=encoding, newline='') as f:
        writer = csv.writer(f, delimiter=delimiter)
        
        if header:
            writer.writerow(header)
        
        writer.writerows(data)
    
    return len(data)


def load_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    加载YAML配置文件
    
    Args:
        file_path: YAML文件路径
    
    Returns:
        解析后的配置字典
    
    Examples:
        >>> config = load_yaml("config/kg.yaml")
        >>> print(config["ontology"]["version"])
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config


def save_json(
    data: Union[Dict, List],
    file_path: Union[str, Path],
    encoding: str = "utf-8",
    indent: int = 2,
    ensure_ascii: bool = False
) -> None:
    """
    保存数据为JSON格式（格式化）
    
    Args:
        data: 要保存的数据
        file_path: 输出文件路径
        encoding: 文件编码
        indent: 缩进空格数
        ensure_ascii: 是否转义非ASCII字符
    
    Examples:
        >>> stats = {"total": 100, "accuracy": 0.95}
        >>> save_json(stats, "outputs/statistics.json")
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "w", encoding=encoding) as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)


def load_json(file_path: Union[str, Path], encoding: str = "utf-8") -> Union[Dict, List]:
    """
    加载JSON文件
    
    Args:
        file_path: JSON文件路径
        encoding: 文件编码
    
    Returns:
        解析后的数据
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, "r", encoding=encoding) as f:
        data = json.load(f)
    
    return data


def ensure_dir(dir_path: Union[str, Path]) -> Path:
    """
    确保目录存在，不存在则创建
    
    Args:
        dir_path: 目录路径
    
    Returns:
        Path对象
    """
    dir_path = Path(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def file_exists(file_path: Union[str, Path]) -> bool:
    """
    检查文件是否存在
    
    Args:
        file_path: 文件路径
    
    Returns:
        存在返回True，否则False
    """
    return Path(file_path).exists()


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    获取文件大小（字节）
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件大小（字节）
    """
    return Path(file_path).stat().st_size


def count_lines(file_path: Union[str, Path], encoding: str = "utf-8") -> int:
    """
    统计文件行数
    
    Args:
        file_path: 文件路径
        encoding: 文件编码
    
    Returns:
        行数
    """
    count = 0
    with open(file_path, "r", encoding=encoding) as f:
        for _ in f:
            count += 1
    return count
