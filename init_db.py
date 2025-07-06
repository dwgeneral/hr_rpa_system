#!/usr/bin/env python3
"""数据库初始化脚本"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.data_manager import get_data_manager
from src.utils.logger import app_logger
from src.utils.config import get_config


def main():
    """初始化数据库"""
    try:
        print("🚀 开始初始化数据库...")
        
        # 获取配置
        config = get_config()
        db_path = config.database.url.replace("sqlite:///", "")
        
        print(f"📍 数据库路径: {db_path}")
        
        # 确保数据库目录存在
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 数据库目录: {db_dir}")
        
        # 初始化数据管理器（会自动创建表）
        data_manager = get_data_manager()
        
        print("✅ 数据库初始化完成！")
        print("\n📊 数据库表结构:")
        print("   - jobs (岗位表)")
        print("   - resumes (简历表)")
        print("   - candidates (候选人表)")
        print("   - analysis_results (分析结果表)")
        
        print("\n🎉 初始化成功！现在可以运行系统了。")
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {str(e)}")
        app_logger.error(f"数据库初始化失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()