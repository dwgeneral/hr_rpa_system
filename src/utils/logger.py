"""日志工具模块"""

import sys
from pathlib import Path
from loguru import logger
from .config import get_settings

settings = get_settings()


def setup_logger():
    """配置日志系统"""
    # 移除默认处理器
    logger.remove()
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 控制台输出格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 文件输出格式
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        format=console_format,
        level=settings.app.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # 添加文件处理器 - 所有日志
    logger.add(
        log_dir / "app.log",
        format=file_format,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # 添加错误日志文件
    logger.add(
        log_dir / "error.log",
        format=file_format,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # 添加RPA操作日志
    logger.add(
        log_dir / "rpa.log",
        format=file_format,
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        filter=lambda record: "rpa" in record["name"].lower() or "selenium" in record["name"].lower()
    )
    
    # 添加AI分析日志
    logger.add(
        log_dir / "ai_analysis.log",
        format=file_format,
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        filter=lambda record: "ai" in record["name"].lower() or "siliconflow" in record["name"].lower()
    )
    
    return logger


def get_logger(name: str = None):
    """获取日志记录器"""
    if name:
        return logger.bind(name=name)
    return logger


# 初始化日志系统
setup_logger()

# 导出常用的日志记录器
app_logger = get_logger("app")
rpa_logger = get_logger("rpa")
ai_logger = get_logger("ai")
api_logger = get_logger("api")