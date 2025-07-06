"""简历处理服务"""

import asyncio
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from ..core.data_manager import get_data_manager
from ..core.ai_analyzer import get_ai_analyzer
from ..models.resume import Resume, ResumeCreate, ResumeUpdate, ResumeStatus, ResumeSource, ResumeSearchParams
from ..models.job import Job
from ..models.analysis import AnalysisResult, AnalysisResultCreate
from ..utils.logger import app_logger
from ..utils.helpers import generate_hash, validate_file_type, get_file_size


class ResumeService:
    """简历处理服务"""
    
    def __init__(self):
        self.data_manager = get_data_manager()
        self.ai_analyzer = get_ai_analyzer()
    
    async def create_resume(self, resume_data: ResumeCreate) -> Resume:
        """创建简历"""
        try:
            # 验证数据
            await self._validate_resume_data(resume_data)
            
            # 生成文件哈希（如果有文件路径）
            if resume_data.file_path:
                resume_data.file_hash = await self._generate_file_hash(resume_data.file_path)
            
            # 创建简历
            resume = await self.data_manager.create_resume(resume_data)
            
            app_logger.info(f"简历创建成功: {resume.name} (ID: {resume.id})")
            
            return resume
            
        except Exception as e:
            app_logger.error(f"创建简历失败: {str(e)}")
            raise
    
    async def get_resume_by_id(self, resume_id: int) -> Optional[Resume]:
        """根据ID获取简历"""
        return await self.data_manager.get_resume_by_id(resume_id)
    
    async def get_resume_by_source(self, source: ResumeSource, source_id: str) -> Optional[Resume]:
        """根据来源获取简历"""
        return await self.data_manager.get_resume_by_source(source, source_id)
    
    async def update_resume(self, resume_id: int, resume_data: ResumeUpdate) -> Optional[Resume]:
        """更新简历"""
        try:
            # 验证简历是否存在
            existing_resume = await self.get_resume_by_id(resume_id)
            if not existing_resume:
                raise ValueError(f"简历不存在: {resume_id}")
            
            # 更新简历
            updated_resume = await self.data_manager.update_resume(resume_id, resume_data)
            
            if updated_resume:
                app_logger.info(f"简历更新成功: {updated_resume.name} (ID: {resume_id})")
            
            return updated_resume
            
        except Exception as e:
            app_logger.error(f"更新简历失败: {str(e)}")
            raise
    
    async def search_resumes(self, search_params: ResumeSearchParams) -> Tuple[List[Resume], int]:
        """搜索简历"""
        try:
            filters = {}
            
            if search_params.status:
                filters["status"] = search_params.status.value
            
            if search_params.source:
                filters["source"] = search_params.source.value
            
            if search_params.name:
                filters["name"] = search_params.name
            
            if search_params.skills:
                filters["skills"] = search_params.skills
            
            if search_params.min_experience is not None:
                filters["min_experience"] = search_params.min_experience
            
            if search_params.max_experience is not None:
                filters["max_experience"] = search_params.max_experience
            
            resumes, total = await self.data_manager.search_resumes(
                filters, search_params.limit, search_params.offset
            )
            
            app_logger.info(f"简历搜索完成: 找到{total}份简历，返回{len(resumes)}份")
            
            return resumes, total
            
        except Exception as e:
            app_logger.error(f"搜索简历失败: {str(e)}")
            raise
    
    async def analyze_resume(self, resume_id: int, job_id: int, custom_weights: Optional[Dict] = None) -> AnalysisResult:
        """分析简历匹配度"""
        try:
            # 获取简历和岗位信息
            resume = await self.get_resume_by_id(resume_id)
            if not resume:
                raise ValueError(f"简历不存在: {resume_id}")
            
            job = await self.data_manager.get_job_by_id(job_id)
            if not job:
                raise ValueError(f"岗位不存在: {job_id}")
            
            # 检查是否已有分析结果
            existing_analysis = await self.data_manager.get_analysis_by_resume_job(resume_id, job_id)
            if existing_analysis:
                app_logger.info(f"使用已有分析结果: Resume {resume_id} - Job {job_id}")
                return existing_analysis
            
            # 进行AI分析
            analysis_result = await self.ai_analyzer.analyze_resume(resume, job, custom_weights)
            
            # 保存分析结果
            analysis_create = AnalysisResultCreate(
                resume_id=resume_id,
                job_id=job_id,
                overall_score=analysis_result.overall_score,
                recommendation_level=analysis_result.recommendation_level,
                score_details=analysis_result.score_details,
                match_analysis=analysis_result.match_analysis,
                risk_assessment=analysis_result.risk_assessment,
                interview_suggestions=analysis_result.interview_suggestions,
                summary=analysis_result.summary,
                strengths=analysis_result.strengths,
                weaknesses=analysis_result.weaknesses,
                recommendations=analysis_result.recommendations,
                analysis_version=analysis_result.analysis_version,
                model_used=analysis_result.model_used,
                analysis_duration=analysis_result.analysis_duration,
                raw_analysis_data=analysis_result.raw_analysis_data
            )
            
            saved_analysis = await self.data_manager.create_analysis_result(analysis_create)
            
            app_logger.info(
                f"简历分析完成: {resume.name} 应聘 {job.title} - "
                f"得分: {saved_analysis.overall_score} - "
                f"推荐等级: {saved_analysis.recommendation_level.value}"
            )
            
            return saved_analysis
            
        except Exception as e:
            app_logger.error(f"分析简历失败: {str(e)}")
            raise
    
    async def batch_analyze_resumes(self, resume_ids: List[int], job_id: int, custom_weights: Optional[Dict] = None) -> List[AnalysisResult]:
        """批量分析简历"""
        try:
            app_logger.info(f"开始批量分析{len(resume_ids)}份简历")
            
            # 获取岗位信息
            job = await self.data_manager.get_job_by_id(job_id)
            if not job:
                raise ValueError(f"岗位不存在: {job_id}")
            
            # 获取所有简历
            resumes = []
            for resume_id in resume_ids:
                resume = await self.get_resume_by_id(resume_id)
                if resume:
                    resumes.append(resume)
                else:
                    app_logger.warning(f"简历不存在，跳过: {resume_id}")
            
            if not resumes:
                return []
            
            # 批量AI分析
            analysis_results = await self.ai_analyzer.batch_analyze_resumes(resumes, job, custom_weights)
            
            # 保存分析结果
            saved_results = []
            for analysis_result in analysis_results:
                try:
                    # 检查是否已有分析结果
                    existing = await self.data_manager.get_analysis_by_resume_job(
                        analysis_result.resume_id, analysis_result.job_id
                    )
                    
                    if existing:
                        saved_results.append(existing)
                        continue
                    
                    # 创建新的分析结果
                    analysis_create = AnalysisResultCreate(
                        resume_id=analysis_result.resume_id,
                        job_id=analysis_result.job_id,
                        overall_score=analysis_result.overall_score,
                        recommendation_level=analysis_result.recommendation_level,
                        score_details=analysis_result.score_details,
                        match_analysis=analysis_result.match_analysis,
                        risk_assessment=analysis_result.risk_assessment,
                        interview_suggestions=analysis_result.interview_suggestions,
                        summary=analysis_result.summary,
                        strengths=analysis_result.strengths,
                        weaknesses=analysis_result.weaknesses,
                        recommendations=analysis_result.recommendations,
                        analysis_version=analysis_result.analysis_version,
                        model_used=analysis_result.model_used,
                        analysis_duration=analysis_result.analysis_duration,
                        raw_analysis_data=analysis_result.raw_analysis_data
                    )
                    
                    saved_analysis = await self.data_manager.create_analysis_result(analysis_create)
                    saved_results.append(saved_analysis)
                    
                except Exception as e:
                    app_logger.error(f"保存分析结果失败: Resume {analysis_result.resume_id} - {str(e)}")
            
            app_logger.info(f"批量分析完成: 成功分析{len(saved_results)}份简历")
            
            return saved_results
            
        except Exception as e:
            app_logger.error(f"批量分析简历失败: {str(e)}")
            raise
    
    async def update_resume_status(self, resume_id: int, status: ResumeStatus) -> Optional[Resume]:
        """更新简历状态"""
        try:
            resume_update = ResumeUpdate(status=status)
            updated_resume = await self.update_resume(resume_id, resume_update)
            
            if updated_resume:
                app_logger.info(f"简历状态更新: {updated_resume.name} -> {status.value}")
            
            return updated_resume
            
        except Exception as e:
            app_logger.error(f"更新简历状态失败: {str(e)}")
            raise
    
    async def get_resume_statistics(self) -> Dict[str, Any]:
        """获取简历统计信息"""
        try:
            # 按状态统计
            status_stats = {}
            for status in ResumeStatus:
                resumes, total = await self.data_manager.search_resumes(
                    {"status": status.value}, limit=1, offset=0
                )
                status_stats[status.value] = total
            
            # 按来源统计
            source_stats = {}
            for source in ResumeSource:
                resumes, total = await self.data_manager.search_resumes(
                    {"source": source.value}, limit=1, offset=0
                )
                source_stats[source.value] = total
            
            # 总数统计
            all_resumes, total_count = await self.data_manager.search_resumes({}, limit=1, offset=0)
            
            stats = {
                "total_count": total_count,
                "by_status": status_stats,
                "by_source": source_stats,
                "last_updated": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            app_logger.error(f"获取简历统计失败: {str(e)}")
            return {}
    
    async def _validate_resume_data(self, resume_data: ResumeCreate):
        """验证简历数据"""
        # 验证必填字段
        if not resume_data.name or not resume_data.name.strip():
            raise ValueError("简历姓名不能为空")
        
        # 验证联系信息
        if not resume_data.contact_info:
            raise ValueError("联系信息不能为空")
        
        # 验证文件（如果有）
        if resume_data.file_path:
            file_path = Path(resume_data.file_path)
            if not file_path.exists():
                raise ValueError(f"简历文件不存在: {resume_data.file_path}")
            
            # 验证文件类型
            if not validate_file_type(resume_data.file_path, ['.pdf', '.doc', '.docx']):
                raise ValueError("不支持的文件类型，仅支持 PDF、DOC、DOCX")
            
            # 验证文件大小（最大10MB）
            file_size = get_file_size(resume_data.file_path)
            if file_size > 10 * 1024 * 1024:  # 10MB
                raise ValueError("文件大小超过限制（最大10MB）")
        
        # 验证来源信息
        if resume_data.source and resume_data.source != ResumeSource.MANUAL:
            if not resume_data.source_id:
                raise ValueError("外部来源简历必须提供source_id")
    
    async def _generate_file_hash(self, file_path: str) -> str:
        """生成文件哈希"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return generate_hash(content)
        except Exception as e:
            app_logger.error(f"生成文件哈希失败: {str(e)}")
            return ""


# 全局服务实例
_resume_service_instance = None


def get_resume_service() -> ResumeService:
    """获取简历服务实例"""
    global _resume_service_instance
    if _resume_service_instance is None:
        _resume_service_instance = ResumeService()
    return _resume_service_instance