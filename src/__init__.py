"""HR RPA自动化简历筛选系统"""

__version__ = "1.0.0"
__author__ = "HR RPA Team"
__description__ = "基于AI和RPA技术的智能简历筛选与分析系统"

# 导出主要组件
from .core import get_ai_analyzer, get_rpa_controller, get_data_manager
from .services import get_resume_service, get_feishu_service, get_workflow_service
from .integrations import get_siliconflow_api, get_feishu_api, get_boss_rpa
from .utils.config import get_config
from .utils.logger import app_logger

__all__ = [
    "get_ai_analyzer",
    "get_rpa_controller",
    "get_data_manager",
    "get_resume_service",
    "get_feishu_service",
    "get_workflow_service",
    "get_siliconflow_api",
    "get_feishu_api",
    "get_boss_rpa",
    "get_config",
    "app_logger",
]