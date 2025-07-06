"""工作流服务"""

import asyncio
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime
from enum import Enum

from ..core.rpa_controller import get_rpa_controller
from ..core.ai_analyzer import get_ai_analyzer
from ..core.data_manager import get_data_manager
from .resume_service import get_resume_service
from .feishu_service import get_feishu_service
from ..models.resume import Resume, ResumeCreate
from ..models.job import Job
from ..models.analysis import AnalysisResult
from ..utils.logger import app_logger
from ..utils.config import get_config


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStep(Enum):
    """工作流步骤"""
    INIT = "init"
    RPA_COLLECTION = "rpa_collection"
    AI_ANALYSIS = "ai_analysis"
    FEISHU_SYNC = "feishu_sync"
    COMPLETED = "completed"


class WorkflowService:
    """工作流服务"""
    
    def __init__(self):
        self.rpa_controller = get_rpa_controller()
        self.ai_analyzer = get_ai_analyzer()
        self.data_manager = get_data_manager()
        self.resume_service = get_resume_service()
        self.feishu_service = get_feishu_service()
        self.config = get_config()
        
        # 工作流状态
        self.current_workflow = None
        self.workflow_history = []
        
        # 回调函数
        self.callbacks = {
            "on_step_start": [],
            "on_step_complete": [],
            "on_workflow_complete": [],
            "on_error": [],
            "on_progress_update": []
        }
    
    def add_callback(self, event: str, callback: Callable):
        """添加回调函数"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    async def _trigger_callback(self, event: str, *args, **kwargs):
        """触发回调函数"""
        for callback in self.callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                app_logger.error(f"回调函数执行失败: {event} - {str(e)}")
    
    async def start_resume_screening_workflow(self, job: Job, search_params: Dict[str, Any], max_resumes: int = 100, custom_weights: Optional[Dict] = None) -> Dict[str, Any]:
        """启动简历筛选工作流"""
        try:
            if self.current_workflow and self.current_workflow["status"] == WorkflowStatus.RUNNING:
                raise ValueError("已有工作流正在运行中")
            
            # 初始化工作流
            workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.current_workflow = {
                "id": workflow_id,
                "job": job,
                "search_params": search_params,
                "max_resumes": max_resumes,
                "custom_weights": custom_weights,
                "status": WorkflowStatus.RUNNING,
                "current_step": WorkflowStep.INIT,
                "start_time": datetime.now(),
                "progress": {
                    "total_steps": 4,
                    "completed_steps": 0,
                    "current_step_progress": 0,
                    "collected_resumes": 0,
                    "analyzed_resumes": 0,
                    "synced_records": 0
                },
                "results": {
                    "collected_resumes": [],
                    "analysis_results": [],
                    "feishu_records": []
                },
                "errors": []
            }
            
            app_logger.info(f"启动简历筛选工作流: {workflow_id} - 岗位: {job.title}")
            
            await self._trigger_callback("on_step_start", WorkflowStep.INIT, self.current_workflow)
            
            # 执行工作流步骤
            try:
                # 步骤1: RPA简历收集
                await self._execute_rpa_collection_step()
                
                # 步骤2: AI分析
                await self._execute_ai_analysis_step()
                
                # 步骤3: 飞书同步
                await self._execute_feishu_sync_step()
                
                # 完成工作流
                await self._complete_workflow()
                
            except Exception as e:
                await self._handle_workflow_error(e)
                raise
            
            return self.current_workflow
            
        except Exception as e:
            app_logger.error(f"启动工作流失败: {str(e)}")
            raise
    
    async def _execute_rpa_collection_step(self):
        """执行RPA简历收集步骤"""
        try:
            self.current_workflow["current_step"] = WorkflowStep.RPA_COLLECTION
            await self._trigger_callback("on_step_start", WorkflowStep.RPA_COLLECTION, self.current_workflow)
            
            app_logger.info("开始RPA简历收集步骤")
            
            # 设置RPA回调
            async def on_resume_found(resume: Resume):
                self.current_workflow["progress"]["collected_resumes"] += 1
                self.current_workflow["results"]["collected_resumes"].append(resume)
                await self._trigger_callback("on_progress_update", self.current_workflow)
            
            self.rpa_controller.add_callback("on_resume_found", on_resume_found)
            
            # 执行RPA收集
            collected_resumes = await self.rpa_controller.start_resume_collection(
                self.current_workflow["job"],
                self.current_workflow["search_params"],
                self.current_workflow["max_resumes"]
            )
            
            # 保存简历到数据库
            saved_resumes = []
            for resume in collected_resumes:
                try:
                    # 检查是否已存在
                    existing = await self.resume_service.get_resume_by_source(
                        resume.source, resume.source_id
                    )
                    
                    if existing:
                        saved_resumes.append(existing)
                    else:
                        # 创建新简历
                        resume_create = ResumeCreate(**resume.dict(exclude={"id", "created_at", "updated_at"}))
                        saved_resume = await self.resume_service.create_resume(resume_create)
                        saved_resumes.append(saved_resume)
                        
                except Exception as e:
                    app_logger.error(f"保存简历失败: {resume.name} - {str(e)}")
                    self.current_workflow["errors"].append(f"保存简历失败: {resume.name} - {str(e)}")
            
            self.current_workflow["results"]["collected_resumes"] = saved_resumes
            self.current_workflow["progress"]["completed_steps"] += 1
            
            app_logger.info(f"RPA简历收集完成: 收集{len(saved_resumes)}份简历")
            
            await self._trigger_callback("on_step_complete", WorkflowStep.RPA_COLLECTION, self.current_workflow)
            
        except Exception as e:
            app_logger.error(f"RPA简历收集步骤失败: {str(e)}")
            raise
    
    async def _execute_ai_analysis_step(self):
        """执行AI分析步骤"""
        try:
            self.current_workflow["current_step"] = WorkflowStep.AI_ANALYSIS
            await self._trigger_callback("on_step_start", WorkflowStep.AI_ANALYSIS, self.current_workflow)
            
            app_logger.info("开始AI分析步骤")
            
            collected_resumes = self.current_workflow["results"]["collected_resumes"]
            
            if not collected_resumes:
                app_logger.warning("没有收集到简历，跳过AI分析步骤")
                self.current_workflow["progress"]["completed_steps"] += 1
                return
            
            # 批量分析简历
            resume_ids = [resume.id for resume in collected_resumes]
            
            analysis_results = await self.resume_service.batch_analyze_resumes(
                resume_ids,
                self.current_workflow["job"].id,
                self.current_workflow["custom_weights"]
            )
            
            self.current_workflow["results"]["analysis_results"] = analysis_results
            self.current_workflow["progress"]["analyzed_resumes"] = len(analysis_results)
            self.current_workflow["progress"]["completed_steps"] += 1
            
            app_logger.info(f"AI分析完成: 分析{len(analysis_results)}份简历")
            
            await self._trigger_callback("on_step_complete", WorkflowStep.AI_ANALYSIS, self.current_workflow)
            
        except Exception as e:
            app_logger.error(f"AI分析步骤失败: {str(e)}")
            raise
    
    async def _execute_feishu_sync_step(self):
        """执行飞书同步步骤"""
        try:
            self.current_workflow["current_step"] = WorkflowStep.FEISHU_SYNC
            await self._trigger_callback("on_step_start", WorkflowStep.FEISHU_SYNC, self.current_workflow)
            
            app_logger.info("开始飞书同步步骤")
            
            analysis_results = self.current_workflow["results"]["analysis_results"]
            
            if not analysis_results:
                app_logger.warning("没有分析结果，跳过飞书同步步骤")
                self.current_workflow["progress"]["completed_steps"] += 1
                return
            
            # 批量同步到飞书
            record_ids = await self.feishu_service.batch_sync_to_feishu(analysis_results)
            
            self.current_workflow["results"]["feishu_records"] = record_ids
            self.current_workflow["progress"]["synced_records"] = len(record_ids)
            self.current_workflow["progress"]["completed_steps"] += 1
            
            app_logger.info(f"飞书同步完成: 同步{len(record_ids)}条记录")
            
            await self._trigger_callback("on_step_complete", WorkflowStep.FEISHU_SYNC, self.current_workflow)
            
        except Exception as e:
            app_logger.error(f"飞书同步步骤失败: {str(e)}")
            raise
    
    async def _complete_workflow(self):
        """完成工作流"""
        try:
            self.current_workflow["current_step"] = WorkflowStep.COMPLETED
            self.current_workflow["status"] = WorkflowStatus.COMPLETED
            self.current_workflow["end_time"] = datetime.now()
            self.current_workflow["progress"]["completed_steps"] = self.current_workflow["progress"]["total_steps"]
            
            # 计算统计信息
            duration = (self.current_workflow["end_time"] - self.current_workflow["start_time"]).total_seconds()
            
            summary = {
                "workflow_id": self.current_workflow["id"],
                "job_title": self.current_workflow["job"].title,
                "duration_seconds": duration,
                "collected_resumes": len(self.current_workflow["results"]["collected_resumes"]),
                "analyzed_resumes": len(self.current_workflow["results"]["analysis_results"]),
                "synced_records": len(self.current_workflow["results"]["feishu_records"]),
                "error_count": len(self.current_workflow["errors"]),
                "success_rate": self._calculate_success_rate()
            }
            
            self.current_workflow["summary"] = summary
            
            # 添加到历史记录
            self.workflow_history.append(self.current_workflow.copy())
            
            app_logger.info(
                f"工作流完成: {self.current_workflow['id']} - "
                f"收集{summary['collected_resumes']}份简历, "
                f"分析{summary['analyzed_resumes']}份, "
                f"同步{summary['synced_records']}条记录, "
                f"耗时{duration:.2f}秒"
            )
            
            await self._trigger_callback("on_workflow_complete", self.current_workflow)
            
        except Exception as e:
            app_logger.error(f"完成工作流失败: {str(e)}")
            raise
    
    async def _handle_workflow_error(self, error: Exception):
        """处理工作流错误"""
        try:
            self.current_workflow["status"] = WorkflowStatus.FAILED
            self.current_workflow["end_time"] = datetime.now()
            self.current_workflow["errors"].append(str(error))
            
            app_logger.error(f"工作流失败: {self.current_workflow['id']} - {str(error)}")
            
            await self._trigger_callback("on_error", error, self.current_workflow)
            
            # 添加到历史记录
            self.workflow_history.append(self.current_workflow.copy())
            
        except Exception as e:
            app_logger.error(f"处理工作流错误失败: {str(e)}")
    
    def _calculate_success_rate(self) -> float:
        """计算成功率"""
        try:
            collected = len(self.current_workflow["results"]["collected_resumes"])
            analyzed = len(self.current_workflow["results"]["analysis_results"])
            synced = len(self.current_workflow["results"]["feishu_records"])
            
            if collected == 0:
                return 0.0
            
            # 计算各步骤成功率的平均值
            analysis_rate = analyzed / collected if collected > 0 else 0
            sync_rate = synced / analyzed if analyzed > 0 else 0
            
            overall_rate = (analysis_rate + sync_rate) / 2
            
            return round(overall_rate * 100, 2)
            
        except Exception:
            return 0.0
    
    async def pause_workflow(self) -> bool:
        """暂停工作流"""
        try:
            if not self.current_workflow or self.current_workflow["status"] != WorkflowStatus.RUNNING:
                return False
            
            self.current_workflow["status"] = WorkflowStatus.PAUSED
            
            # 停止RPA控制器
            await self.rpa_controller.stop()
            
            app_logger.info(f"工作流已暂停: {self.current_workflow['id']}")
            
            return True
            
        except Exception as e:
            app_logger.error(f"暂停工作流失败: {str(e)}")
            return False
    
    async def cancel_workflow(self) -> bool:
        """取消工作流"""
        try:
            if not self.current_workflow:
                return False
            
            self.current_workflow["status"] = WorkflowStatus.CANCELLED
            self.current_workflow["end_time"] = datetime.now()
            
            # 停止RPA控制器
            await self.rpa_controller.stop()
            
            app_logger.info(f"工作流已取消: {self.current_workflow['id']}")
            
            # 添加到历史记录
            self.workflow_history.append(self.current_workflow.copy())
            
            return True
            
        except Exception as e:
            app_logger.error(f"取消工作流失败: {str(e)}")
            return False
    
    def get_workflow_status(self) -> Optional[Dict[str, Any]]:
        """获取当前工作流状态"""
        if not self.current_workflow:
            return None
        
        # 计算进度百分比
        progress = self.current_workflow["progress"]
        total_progress = (progress["completed_steps"] / progress["total_steps"]) * 100
        
        status = {
            "workflow_id": self.current_workflow["id"],
            "status": self.current_workflow["status"].value,
            "current_step": self.current_workflow["current_step"].value,
            "progress_percentage": round(total_progress, 2),
            "progress_details": progress,
            "start_time": self.current_workflow["start_time"].isoformat(),
            "job_title": self.current_workflow["job"].title,
            "error_count": len(self.current_workflow["errors"])
        }
        
        if self.current_workflow.get("end_time"):
            status["end_time"] = self.current_workflow["end_time"].isoformat()
            status["duration_seconds"] = (
                self.current_workflow["end_time"] - self.current_workflow["start_time"]
            ).total_seconds()
        
        if self.current_workflow.get("summary"):
            status["summary"] = self.current_workflow["summary"]
        
        return status
    
    def get_workflow_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取工作流历史记录"""
        # 返回最近的工作流记录
        recent_workflows = self.workflow_history[-limit:] if self.workflow_history else []
        
        history = []
        for workflow in reversed(recent_workflows):
            history_item = {
                "workflow_id": workflow["id"],
                "job_title": workflow["job"].title,
                "status": workflow["status"].value,
                "start_time": workflow["start_time"].isoformat(),
                "collected_resumes": len(workflow["results"]["collected_resumes"]),
                "analyzed_resumes": len(workflow["results"]["analysis_results"]),
                "synced_records": len(workflow["results"]["feishu_records"]),
                "error_count": len(workflow["errors"])
            }
            
            if workflow.get("end_time"):
                history_item["end_time"] = workflow["end_time"].isoformat()
                history_item["duration_seconds"] = (
                    workflow["end_time"] - workflow["start_time"]
                ).total_seconds()
            
            if workflow.get("summary"):
                history_item["success_rate"] = workflow["summary"]["success_rate"]
            
            history.append(history_item)
        
        return history
    
    async def get_workflow_statistics(self) -> Dict[str, Any]:
        """获取工作流统计信息"""
        try:
            total_workflows = len(self.workflow_history)
            
            if total_workflows == 0:
                return {
                    "total_workflows": 0,
                    "success_rate": 0,
                    "average_duration": 0,
                    "total_resumes_collected": 0,
                    "total_resumes_analyzed": 0,
                    "total_records_synced": 0
                }
            
            # 统计各种指标
            successful_workflows = [w for w in self.workflow_history if w["status"] == WorkflowStatus.COMPLETED]
            failed_workflows = [w for w in self.workflow_history if w["status"] == WorkflowStatus.FAILED]
            
            total_resumes_collected = sum(len(w["results"]["collected_resumes"]) for w in self.workflow_history)
            total_resumes_analyzed = sum(len(w["results"]["analysis_results"]) for w in self.workflow_history)
            total_records_synced = sum(len(w["results"]["feishu_records"]) for w in self.workflow_history)
            
            # 计算平均持续时间
            completed_workflows = [w for w in self.workflow_history if w.get("end_time")]
            if completed_workflows:
                total_duration = sum(
                    (w["end_time"] - w["start_time"]).total_seconds() 
                    for w in completed_workflows
                )
                average_duration = total_duration / len(completed_workflows)
            else:
                average_duration = 0
            
            stats = {
                "total_workflows": total_workflows,
                "successful_workflows": len(successful_workflows),
                "failed_workflows": len(failed_workflows),
                "success_rate": round(len(successful_workflows) / total_workflows * 100, 2),
                "average_duration": round(average_duration, 2),
                "total_resumes_collected": total_resumes_collected,
                "total_resumes_analyzed": total_resumes_analyzed,
                "total_records_synced": total_records_synced,
                "last_updated": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            app_logger.error(f"获取工作流统计失败: {str(e)}")
            return {}


# 全局服务实例
_workflow_service_instance = None


def get_workflow_service() -> WorkflowService:
    """获取工作流服务实例"""
    global _workflow_service_instance
    if _workflow_service_instance is None:
        _workflow_service_instance = WorkflowService()
    return _workflow_service_instance