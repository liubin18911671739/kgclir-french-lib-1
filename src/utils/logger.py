#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging Utilities
日志系统

提供统一的日志配置和管理。
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from loguru import logger


def get_logger(name: str = "kgclir") -> logging.Logger:
    """
    获取标准logger实例
    
    Args:
        name: logger名称
    
    Returns:
        Logger对象
    """
    return logging.getLogger(name)


def setup_logging(
    log_file: Optional[str] = None,
    level: str = "INFO",
    format_string: Optional[str] = None
) -> None:
    """
    配置日志系统
    
    Args:
        log_file: 日志文件路径（None表示仅控制台输出）
        level: 日志级别 (DEBUG|INFO|WARNING|ERROR)
        format_string: 自定义格式字符串
    
    Examples:
        >>> setup_logging("logs/app.log", level="DEBUG")
    """
    # 移除默认handler
    logger.remove()
    
    # 日志格式
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    # 控制台输出
    logger.add(
        sys.stderr,
        format=format_string,
        level=level,
        colorize=True
    )
    
    # 文件输出
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format=format_string,
            level=level,
            rotation="100 MB",  # 日志轮转
            retention="30 days",  # 保留30天
            compression="zip"  # 压缩旧日志
        )
    
    logger.info(f"Logging initialized. Level: {level}")


# 设置默认日志配置
setup_logging(level="INFO")
