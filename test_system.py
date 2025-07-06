#!/usr/bin/env python3
"""HR RPA系统功能测试脚本"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core import get_data_manager, get_ai_analyzer
from src.services import get_resume_service, get_feishu_service
from src.models.job import JobCreate, JobType, JobRequirements, ExperienceLevel, EducationLevel
from src.models.resume import ResumeCreate, ResumeSource, ContactInfo
from src.utils.logger import app_logger
from src.utils.config import get_config


async def test_database_connection():
    """测试数据库连接"""
    print("\n=== 测试数据库连接 ===")
    try:
        data_manager = get_data_manager()
        print("✅ 数据库连接成功")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {str(e)}")
        return False


async def test_job_creation():
    """测试岗位创建"""
    print("\n=== 测试岗位创建 ===")
    try:
        data_manager = get_data_manager()
        
        # 创建测试岗位
        requirements = JobRequirements(
            experience_level=ExperienceLevel.MID_LEVEL,
            education=EducationLevel.BACHELOR,
            required_skills=["Python", "机器学习", "数据分析"],
            preferred_skills=["深度学习", "NLP", "计算机视觉"]
        )
        
        job_data = JobCreate(
            title="AI工程师",
            company="测试科技有限公司",
            location="北京",
            job_type=JobType.FULL_TIME,
            description="负责AI算法开发和优化，参与机器学习项目的设计与实现。",
            responsibilities=[
                "开发和优化机器学习算法",
                "参与AI产品的设计和开发",
                "进行数据分析和模型训练",
                "与团队协作完成项目目标"
            ],
            requirements=requirements,
            created_by="测试系统"
        )
        
        job = await data_manager.create_job(job_data)
        print(f"✅ 岗位创建成功: {job.title} (ID: {job.id})")
        return job
        
    except Exception as e:
        print(f"❌ 岗位创建失败: {str(e)}")
        return None


async def test_resume_creation():
    """测试简历创建"""
    print("\n=== 测试简历创建 ===")
    try:
        resume_service = get_resume_service()
        
        # 创建测试简历
        contact_info = ContactInfo(
            email="zhangsan@example.com",
            phone="13800138000",
            location="北京市朝阳区"
        )
        
        resume_data = ResumeCreate(
            name="张三",
            contact_info=contact_info,
            summary="具有5年Python开发经验的AI工程师，熟悉机器学习和深度学习技术。",
            work_experiences=[
                {
                    "company": "ABC科技公司",
                    "position": "高级AI工程师",
                    "start_date": "2021-01",
                    "end_date": "2024-01",
                    "description": "负责推荐系统算法开发和优化",
                    "responsibilities": ["算法设计", "模型训练", "性能优化"],
                    "achievements": ["提升推荐准确率15%", "优化模型推理速度50%"]
                }
            ],
            education=[
                {
                    "school": "清华大学",
                    "major": "计算机科学与技术",
                    "degree": "硕士",
                    "start_date": "2017-09",
                    "end_date": "2020-07"
                }
            ],
            skills=["Python", "TensorFlow", "PyTorch", "机器学习", "深度学习", "数据分析"],
            languages=["中文(母语)", "英语(流利)"],
            years_of_experience=5,
            current_position="高级AI工程师",
            current_company="ABC科技公司",
            salary_expectation="25-35K",
            source=ResumeSource.MANUAL
        )
        
        resume = await resume_service.create_resume(resume_data)
        print(f"✅ 简历创建成功: {resume.name} (ID: {resume.id})")
        return resume
        
    except Exception as e:
        print(f"❌ 简历创建失败: {str(e)}")
        return None


async def test_ai_analysis(resume, job):
    """测试AI分析"""
    print("\n=== 测试AI分析 ===")
    try:
        if not resume or not job:
            print("❌ 缺少简历或岗位数据，跳过AI分析测试")
            return None
        
        resume_service = get_resume_service()
        
        print(f"开始分析简历: {resume.name} 应聘 {job.title}")
        
        # 注意：这里需要配置有效的SiliconFlow API才能正常工作
        # 如果没有配置API，这个测试会失败
        analysis = await resume_service.analyze_resume(resume.id, job.id)
        
        print(f"✅ AI分析成功:")
        print(f"   综合得分: {analysis.overall_score}")
        print(f"   推荐等级: {analysis.recommendation_level.value}")
        print(f"   分析总结: {analysis.summary[:100]}...")
        
        return analysis
        
    except Exception as e:
        print(f"❌ AI分析失败: {str(e)}")
        print("   提示: 请确保已正确配置SiliconFlow API密钥")
        return None


async def test_feishu_integration(analysis):
    """测试飞书集成"""
    print("\n=== 测试飞书集成 ===")
    try:
        if not analysis:
            print("❌ 缺少分析结果，跳过飞书集成测试")
            return False
        
        feishu_service = get_feishu_service()
        
        # 注意：这里需要配置有效的飞书API才能正常工作
        record_id = await feishu_service.sync_analysis_to_feishu(analysis)
        
        print(f"✅ 飞书同步成功: Record ID {record_id}")
        return True
        
    except Exception as e:
        print(f"❌ 飞书同步失败: {str(e)}")
        print("   提示: 请确保已正确配置飞书API密钥和表格ID")
        return False


async def test_configuration():
    """测试配置"""
    print("\n=== 测试系统配置 ===")
    try:
        config = get_config()
        
        print(f"✅ 配置加载成功:")
        print(f"   数据库路径: {config.database.url}")
        print(f"   SiliconFlow API配置: {'已配置' if config.siliconflow.api_key else '未配置'}")
        print(f"   飞书API配置: {'已配置' if config.feishu.app_id else '未配置'}")
        print(f"   BOSS直聘配置: {'已配置' if config.boss.username else '未配置'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置加载失败: {str(e)}")
        return False


async def main():
    """主测试函数"""
    print("🚀 HR RPA系统功能测试开始")
    print("=" * 50)
    
    # 测试配置
    config_ok = await test_configuration()
    
    # 测试数据库
    db_ok = await test_database_connection()
    
    if not db_ok:
        print("\n❌ 数据库测试失败，无法继续后续测试")
        return
    
    # 测试岗位创建
    job = await test_job_creation()
    
    # 测试简历创建
    resume = await test_resume_creation()
    
    # 测试AI分析（需要API配置）
    analysis = await test_ai_analysis(resume, job)
    
    # 测试飞书集成（需要API配置）
    feishu_ok = await test_feishu_integration(analysis)
    
    # 总结测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    print(f"   配置加载: {'✅' if config_ok else '❌'}")
    print(f"   数据库连接: {'✅' if db_ok else '❌'}")
    print(f"   岗位创建: {'✅' if job else '❌'}")
    print(f"   简历创建: {'✅' if resume else '❌'}")
    print(f"   AI分析: {'✅' if analysis else '❌'}")
    print(f"   飞书同步: {'✅' if feishu_ok else '❌'}")
    
    if job and resume:
        print("\n✅ 核心功能测试通过！")
        print("💡 提示: 如需测试AI分析和飞书同步，请配置相应的API密钥")
    else:
        print("\n❌ 部分核心功能测试失败")
    
    print("\n🎉 测试完成！")


if __name__ == "__main__":
    asyncio.run(main())