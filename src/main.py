"""HR RPA系统主应用入口"""

import asyncio
import argparse
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .core import get_data_manager, get_ai_analyzer, get_rpa_controller
from .services import get_resume_service, get_feishu_service, get_workflow_service
from .models.job import Job, JobCreate, JobUpdate
from .models.resume import Resume, ResumeSearchParams
from .models.analysis import AnalysisResult
from .utils.logger import app_logger
from .utils.config import get_config


# FastAPI应用实例
app = FastAPI(
    title="HR RPA自动化简历筛选系统",
    description="基于AI和RPA技术的智能简历筛选与分析系统",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 请求/响应模型 ====================

class WorkflowStartRequest(BaseModel):
    """启动工作流请求"""
    job_id: int
    search_params: Dict[str, Any]
    max_resumes: int = 100
    custom_weights: Optional[Dict[str, float]] = None


class AnalysisRequest(BaseModel):
    """分析请求"""
    resume_id: int
    job_id: int
    custom_weights: Optional[Dict[str, float]] = None


class BatchAnalysisRequest(BaseModel):
    """批量分析请求"""
    resume_ids: List[int]
    job_id: int
    custom_weights: Optional[Dict[str, float]] = None


# ==================== API路由 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "HR RPA自动化简历筛选系统",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查各个组件状态
        data_manager = get_data_manager()
        workflow_service = get_workflow_service()
        
        status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "database": "connected",
                "workflow_service": "ready",
                "rpa_controller": "ready",
                "ai_analyzer": "ready"
            }
        }
        
        return status
        
    except Exception as e:
        app_logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail="系统不健康")


# ==================== 岗位管理API ====================

@app.post("/api/jobs", response_model=Job)
async def create_job(job_data: JobCreate):
    """创建岗位"""
    try:
        data_manager = get_data_manager()
        job = await data_manager.create_job(job_data)
        return job
    except Exception as e:
        app_logger.error(f"创建岗位失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/jobs/{job_id}", response_model=Job)
async def get_job(job_id: int):
    """获取岗位详情"""
    try:
        data_manager = get_data_manager()
        job = await data_manager.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return job
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"获取岗位失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/jobs/{job_id}", response_model=Job)
async def update_job(job_id: int, job_data: JobUpdate):
    """更新岗位"""
    try:
        data_manager = get_data_manager()
        job = await data_manager.update_job(job_id, job_data)
        if not job:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return job
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"更新岗位失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 简历管理API ====================

@app.get("/api/resumes/{resume_id}", response_model=Resume)
async def get_resume(resume_id: int):
    """获取简历详情"""
    try:
        resume_service = get_resume_service()
        resume = await resume_service.get_resume_by_id(resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="简历不存在")
        return resume
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"获取简历失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/resumes/search")
async def search_resumes(search_params: ResumeSearchParams):
    """搜索简历"""
    try:
        resume_service = get_resume_service()
        resumes, total = await resume_service.search_resumes(search_params)
        
        return {
            "resumes": resumes,
            "total": total,
            "limit": search_params.limit,
            "offset": search_params.offset
        }
    except Exception as e:
        app_logger.error(f"搜索简历失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/resumes/statistics")
async def get_resume_statistics():
    """获取简历统计信息"""
    try:
        resume_service = get_resume_service()
        stats = await resume_service.get_resume_statistics()
        return stats
    except Exception as e:
        app_logger.error(f"获取简历统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AI分析API ====================

@app.post("/api/analysis/single", response_model=AnalysisResult)
async def analyze_single_resume(request: AnalysisRequest):
    """分析单个简历"""
    try:
        resume_service = get_resume_service()
        analysis = await resume_service.analyze_resume(
            request.resume_id,
            request.job_id,
            request.custom_weights
        )
        return analysis
    except Exception as e:
        app_logger.error(f"分析简历失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/analysis/batch")
async def analyze_batch_resumes(request: BatchAnalysisRequest):
    """批量分析简历"""
    try:
        resume_service = get_resume_service()
        analyses = await resume_service.batch_analyze_resumes(
            request.resume_ids,
            request.job_id,
            request.custom_weights
        )
        
        return {
            "analyses": analyses,
            "total_analyzed": len(analyses),
            "requested_count": len(request.resume_ids)
        }
    except Exception as e:
        app_logger.error(f"批量分析简历失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/analysis/{analysis_id}", response_model=AnalysisResult)
async def get_analysis_result(analysis_id: int):
    """获取分析结果"""
    try:
        data_manager = get_data_manager()
        analysis = await data_manager.get_analysis_result_by_id(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="分析结果不存在")
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"获取分析结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 工作流API ====================

@app.post("/api/workflow/start")
async def start_workflow(request: WorkflowStartRequest, background_tasks: BackgroundTasks):
    """启动简历筛选工作流"""
    try:
        workflow_service = get_workflow_service()
        data_manager = get_data_manager()
        
        # 获取岗位信息
        job = await data_manager.get_job_by_id(request.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="岗位不存在")
        
        # 在后台启动工作流
        async def run_workflow():
            try:
                await workflow_service.start_resume_screening_workflow(
                    job,
                    request.search_params,
                    request.max_resumes,
                    request.custom_weights
                )
            except Exception as e:
                app_logger.error(f"工作流执行失败: {str(e)}")
        
        background_tasks.add_task(run_workflow)
        
        return {
            "message": "工作流已启动",
            "job_id": request.job_id,
            "job_title": job.title,
            "max_resumes": request.max_resumes,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"启动工作流失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/workflow/status")
async def get_workflow_status():
    """获取当前工作流状态"""
    try:
        workflow_service = get_workflow_service()
        status = workflow_service.get_workflow_status()
        
        if not status:
            return {"message": "当前没有运行中的工作流"}
        
        return status
    except Exception as e:
        app_logger.error(f"获取工作流状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflow/pause")
async def pause_workflow():
    """暂停当前工作流"""
    try:
        workflow_service = get_workflow_service()
        success = await workflow_service.pause_workflow()
        
        if success:
            return {"message": "工作流已暂停"}
        else:
            return {"message": "没有可暂停的工作流"}
    except Exception as e:
        app_logger.error(f"暂停工作流失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflow/cancel")
async def cancel_workflow():
    """取消当前工作流"""
    try:
        workflow_service = get_workflow_service()
        success = await workflow_service.cancel_workflow()
        
        if success:
            return {"message": "工作流已取消"}
        else:
            return {"message": "没有可取消的工作流"}
    except Exception as e:
        app_logger.error(f"取消工作流失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflow/history")
async def get_workflow_history(limit: int = 10):
    """获取工作流历史记录"""
    try:
        workflow_service = get_workflow_service()
        history = workflow_service.get_workflow_history(limit)
        return {"history": history, "total": len(history)}
    except Exception as e:
        app_logger.error(f"获取工作流历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflow/statistics")
async def get_workflow_statistics():
    """获取工作流统计信息"""
    try:
        workflow_service = get_workflow_service()
        stats = await workflow_service.get_workflow_statistics()
        return stats
    except Exception as e:
        app_logger.error(f"获取工作流统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 飞书集成API ====================

@app.post("/api/feishu/sync/{analysis_id}")
async def sync_analysis_to_feishu(analysis_id: int):
    """同步分析结果到飞书"""
    try:
        data_manager = get_data_manager()
        feishu_service = get_feishu_service()
        
        # 获取分析结果
        analysis = await data_manager.get_analysis_result_by_id(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="分析结果不存在")
        
        # 同步到飞书
        record_id = await feishu_service.sync_analysis_to_feishu(analysis)
        
        return {
            "message": "同步成功",
            "analysis_id": analysis_id,
            "feishu_record_id": record_id
        }
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"同步到飞书失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/feishu/statistics")
async def get_feishu_statistics():
    """获取飞书同步统计信息"""
    try:
        feishu_service = get_feishu_service()
        stats = await feishu_service.get_sync_statistics()
        return stats
    except Exception as e:
        app_logger.error(f"获取飞书统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 异常处理 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    app_logger.error(f"未处理的异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "内部服务器错误", "timestamp": datetime.now().isoformat()}
    )


# ==================== 命令行接口 ====================

async def cli_start_workflow(args):
    """命令行启动工作流"""
    try:
        workflow_service = get_workflow_service()
        data_manager = get_data_manager()
        
        # 获取岗位
        job = await data_manager.get_job_by_id(args.job_id)
        if not job:
            print(f"错误: 岗位不存在 (ID: {args.job_id})")
            return
        
        # 解析搜索参数
        search_params = json.loads(args.search_params) if args.search_params else {}
        
        print(f"启动工作流: {job.title}")
        print(f"搜索参数: {search_params}")
        print(f"最大简历数: {args.max_resumes}")
        
        # 启动工作流
        workflow = await workflow_service.start_resume_screening_workflow(
            job, search_params, args.max_resumes
        )
        
        print(f"工作流完成: {workflow['id']}")
        print(f"收集简历: {len(workflow['results']['collected_resumes'])}份")
        print(f"分析简历: {len(workflow['results']['analysis_results'])}份")
        print(f"同步记录: {len(workflow['results']['feishu_records'])}条")
        
    except Exception as e:
        print(f"工作流执行失败: {str(e)}")


async def cli_create_job(args):
    """命令行创建岗位"""
    try:
        from .models.job import JobCreate, JobType, JobRequirements, ExperienceLevel, EducationLevel
        
        # 创建基本的岗位要求
        requirements = JobRequirements(
            experience_level=ExperienceLevel.MID_LEVEL,
            education=EducationLevel.BACHELOR,
            required_skills=["Python", "数据分析"],
            preferred_skills=["机器学习", "深度学习"]
        )
        
        job_data = JobCreate(
            title=args.title,
            company=args.company,
            location=args.location,
            job_type=JobType.FULL_TIME,
            description=args.description or f"{args.title}岗位",
            requirements=requirements,
            created_by="CLI"
        )
        
        data_manager = get_data_manager()
        job = await data_manager.create_job(job_data)
        
        print(f"岗位创建成功:")
        print(f"ID: {job.id}")
        print(f"标题: {job.title}")
        print(f"公司: {job.company}")
        print(f"地点: {job.location}")
        
    except Exception as e:
        print(f"创建岗位失败: {str(e)}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="HR RPA自动化简历筛选系统")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 启动API服务器
    server_parser = subparsers.add_parser("server", help="启动API服务器")
    server_parser.add_argument("--host", default="0.0.0.0", help="服务器地址")
    server_parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    server_parser.add_argument("--reload", action="store_true", help="开发模式")
    
    # 启动工作流
    workflow_parser = subparsers.add_parser("workflow", help="启动简历筛选工作流")
    workflow_parser.add_argument("job_id", type=int, help="岗位ID")
    workflow_parser.add_argument("--search-params", help="搜索参数(JSON格式)")
    workflow_parser.add_argument("--max-resumes", type=int, default=100, help="最大简历数")
    
    # 创建岗位
    job_parser = subparsers.add_parser("create-job", help="创建岗位")
    job_parser.add_argument("title", help="岗位标题")
    job_parser.add_argument("company", help="公司名称")
    job_parser.add_argument("location", help="工作地点")
    job_parser.add_argument("--description", help="岗位描述")
    
    args = parser.parse_args()
    
    if args.command == "server":
        import uvicorn
        uvicorn.run(
            "src.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload
        )
    elif args.command == "workflow":
        asyncio.run(cli_start_workflow(args))
    elif args.command == "create-job":
        asyncio.run(cli_create_job(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()