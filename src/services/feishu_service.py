"""飞书集成服务"""

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from ..integrations.feishu_api import get_feishu_api, FeishuAPIError
from ..core.data_manager import get_data_manager
from ..models.resume import Resume
from ..models.job import Job
from ..models.analysis import AnalysisResult
from ..models.candidate import Candidate, CandidateCreate, CandidateStatus, CandidateStage
from ..utils.logger import app_logger
from ..utils.config import get_config


class FeishuService:
    """飞书集成服务"""
    
    def __init__(self):
        self.data_manager = get_data_manager()
        self.config = get_config()
        self.table_id = self.config.feishu.table_id
    
    async def sync_analysis_to_feishu(self, analysis: AnalysisResult) -> Optional[str]:
        """将分析结果同步到飞书多维表格"""
        try:
            # 获取相关数据
            resume = await self.data_manager.get_resume_by_id(analysis.resume_id)
            job = await self.data_manager.get_job_by_id(analysis.job_id)
            
            if not resume or not job:
                raise ValueError(f"无法找到相关数据: Resume {analysis.resume_id}, Job {analysis.job_id}")
            
            # 准备飞书记录数据
            record_data = await self._prepare_feishu_record(analysis, resume, job)
            
            # 检查是否已存在记录
            existing_record = await self._find_existing_record(resume.id, job.id)
            
            async with await get_feishu_api() as feishu:
                if existing_record:
                    # 更新现有记录
                    record_id = await feishu.update_record(self.table_id, existing_record["record_id"], record_data)
                    app_logger.info(f"更新飞书记录: {resume.name} - {job.title} (Record ID: {record_id})")
                else:
                    # 创建新记录
                    record_id = await feishu.create_record(self.table_id, record_data)
                    app_logger.info(f"创建飞书记录: {resume.name} - {job.title} (Record ID: {record_id})")
                
                return record_id
                
        except Exception as e:
            app_logger.error(f"同步到飞书失败: {str(e)}")
            raise
    
    async def batch_sync_to_feishu(self, analysis_results: List[AnalysisResult]) -> List[str]:
        """批量同步分析结果到飞书"""
        try:
            app_logger.info(f"开始批量同步{len(analysis_results)}条分析结果到飞书")
            
            # 准备批量数据
            records_data = []
            for analysis in analysis_results:
                try:
                    resume = await self.data_manager.get_resume_by_id(analysis.resume_id)
                    job = await self.data_manager.get_job_by_id(analysis.job_id)
                    
                    if resume and job:
                        record_data = await self._prepare_feishu_record(analysis, resume, job)
                        records_data.append(record_data)
                    else:
                        app_logger.warning(f"跳过无效分析结果: Resume {analysis.resume_id}, Job {analysis.job_id}")
                        
                except Exception as e:
                    app_logger.error(f"准备飞书记录数据失败: {str(e)}")
            
            if not records_data:
                return []
            
            # 批量创建记录
            async with await get_feishu_api() as feishu:
                record_ids = await feishu.batch_create_records(self.table_id, records_data)
                
                app_logger.info(f"批量同步完成: 成功创建{len(record_ids)}条飞书记录")
                
                return record_ids
                
        except Exception as e:
            app_logger.error(f"批量同步到飞书失败: {str(e)}")
            raise
    
    async def create_candidate_record(self, resume: Resume, job: Job, analysis: Optional[AnalysisResult] = None) -> Optional[str]:
        """创建候选人记录"""
        try:
            # 准备候选人数据
            record_data = await self._prepare_candidate_record(resume, job, analysis)
            
            async with await get_feishu_api() as feishu:
                record_id = await feishu.create_record(self.table_id, record_data)
                
                app_logger.info(f"创建候选人记录: {resume.name} - {job.title} (Record ID: {record_id})")
                
                return record_id
                
        except Exception as e:
            app_logger.error(f"创建候选人记录失败: {str(e)}")
            raise
    
    async def update_candidate_status(self, resume_id: int, job_id: int, status: CandidateStatus, stage: Optional[CandidateStage] = None, notes: Optional[str] = None) -> bool:
        """更新候选人状态"""
        try:
            # 查找现有记录
            existing_record = await self._find_existing_record(resume_id, job_id)
            
            if not existing_record:
                app_logger.warning(f"未找到候选人记录: Resume {resume_id}, Job {job_id}")
                return False
            
            # 准备更新数据
            update_data = {
                "候选人状态": status.value,
                "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if stage:
                update_data["当前阶段"] = stage.value
            
            if notes:
                update_data["备注"] = notes
            
            async with await get_feishu_api() as feishu:
                await feishu.update_record(self.table_id, existing_record["record_id"], update_data)
                
                app_logger.info(f"更新候选人状态: Resume {resume_id}, Job {job_id} -> {status.value}")
                
                return True
                
        except Exception as e:
            app_logger.error(f"更新候选人状态失败: {str(e)}")
            return False
    
    async def get_feishu_records(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """获取飞书记录"""
        try:
            async with await get_feishu_api() as feishu:
                records = await feishu.search_records(self.table_id, filters or {})
                
                app_logger.info(f"获取飞书记录: {len(records)}条")
                
                return records
                
        except Exception as e:
            app_logger.error(f"获取飞书记录失败: {str(e)}")
            return []
    
    async def sync_feishu_updates(self) -> int:
        """同步飞书更新到本地数据库"""
        try:
            # 获取最近更新的飞书记录
            recent_time = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            filters = {
                "更新时间": f">={recent_time}"
            }
            
            records = await self.get_feishu_records(filters)
            
            updated_count = 0
            
            for record in records:
                try:
                    # 解析记录数据
                    resume_id = record.get("简历ID")
                    job_id = record.get("岗位ID")
                    status = record.get("候选人状态")
                    stage = record.get("当前阶段")
                    
                    if resume_id and job_id and status:
                        # 更新本地候选人状态
                        # 这里可以扩展为更新本地数据库中的候选人记录
                        app_logger.info(f"同步飞书更新: Resume {resume_id}, Job {job_id} -> {status}")
                        updated_count += 1
                        
                except Exception as e:
                    app_logger.error(f"处理飞书记录失败: {str(e)}")
            
            app_logger.info(f"同步飞书更新完成: {updated_count}条记录")
            
            return updated_count
            
        except Exception as e:
            app_logger.error(f"同步飞书更新失败: {str(e)}")
            return 0
    
    async def _prepare_feishu_record(self, analysis: AnalysisResult, resume: Resume, job: Job) -> Dict[str, Any]:
        """准备飞书记录数据"""
        # 格式化技能列表
        skills_text = ", ".join(resume.skills) if resume.skills else "无"
        
        # 格式化工作经历
        work_exp_text = ""
        if resume.work_experiences:
            work_exp_list = []
            for exp in resume.work_experiences[:3]:  # 只显示前3个工作经历
                exp_text = f"{exp.company} - {exp.position}"
                if exp.start_date and exp.end_date:
                    exp_text += f" ({exp.start_date} ~ {exp.end_date})"
                work_exp_list.append(exp_text)
            work_exp_text = "\n".join(work_exp_list)
        
        # 格式化教育背景
        education_text = ""
        if resume.education:
            edu_list = []
            for edu in resume.education:
                edu_text = f"{edu.school} - {edu.major} - {edu.degree}"
                if edu.start_date and edu.end_date:
                    edu_text += f" ({edu.start_date} ~ {edu.end_date})"
                edu_list.append(edu_text)
            education_text = "\n".join(edu_list)
        
        # 格式化匹配分析
        match_summary = f"技能匹配度: {analysis.match_analysis.skill_match_rate:.1%}\n"
        match_summary += f"经验匹配: {analysis.match_analysis.experience_match}\n"
        match_summary += f"学历匹配: {analysis.match_analysis.education_match}"
        
        # 格式化优势和劣势
        strengths_text = "\n".join([f"• {s}" for s in analysis.strengths]) if analysis.strengths else "无"
        weaknesses_text = "\n".join([f"• {w}" for w in analysis.weaknesses]) if analysis.weaknesses else "无"
        
        # 格式化推荐问题
        interview_questions = "\n".join([
            f"{i+1}. {q}" for i, q in enumerate(analysis.interview_suggestions.recommended_questions[:5])
        ]) if analysis.interview_suggestions.recommended_questions else "无"
        
        record_data = {
            # 基本信息
            "简历ID": resume.id,
            "岗位ID": job.id,
            "候选人姓名": resume.name,
            "岗位名称": job.title,
            "公司名称": job.company,
            "部门": job.department or "",
            
            # 联系信息
            "邮箱": resume.contact_info.email or "",
            "电话": resume.contact_info.phone or "",
            "所在地": resume.contact_info.location or "",
            
            # 基本情况
            "当前职位": resume.current_position or "",
            "当前公司": resume.current_company or "",
            "工作年限": resume.years_of_experience or 0,
            "薪资期望": resume.salary_expectation or "",
            "求职状态": resume.job_status or "",
            
            # 技能和经历
            "技能标签": skills_text,
            "工作经历": work_exp_text,
            "教育背景": education_text,
            "语言能力": ", ".join(resume.languages) if resume.languages else "",
            "证书资质": ", ".join(resume.certifications) if resume.certifications else "",
            
            # AI分析结果
            "综合得分": analysis.overall_score,
            "推荐等级": analysis.recommendation_level.value,
            "匹配分析": match_summary,
            "分析总结": analysis.summary,
            "候选人优势": strengths_text,
            "候选人劣势": weaknesses_text,
            "面试建议": interview_questions,
            
            # 风险评估
            "整体风险": analysis.risk_assessment.overall_risk.value,
            "跳槽风险": analysis.risk_assessment.job_hopping_risk.value,
            "薪资风险": analysis.risk_assessment.salary_risk.value,
            "技能差距风险": analysis.risk_assessment.skill_gap_risk.value,
            
            # 状态和时间
            "候选人状态": CandidateStatus.ACTIVE.value,
            "当前阶段": CandidateStage.INITIAL_SCREENING.value,
            "简历来源": resume.source.value,
            "创建时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            
            # 其他信息
            "分析模型": analysis.model_used or "deepseek-chat",
            "分析版本": analysis.analysis_version or "1.0",
            "备注": ""
        }
        
        return record_data
    
    async def _prepare_candidate_record(self, resume: Resume, job: Job, analysis: Optional[AnalysisResult] = None) -> Dict[str, Any]:
        """准备候选人记录数据"""
        if analysis:
            return await self._prepare_feishu_record(analysis, resume, job)
        
        # 没有分析结果时的基础记录
        record_data = {
            "简历ID": resume.id,
            "岗位ID": job.id,
            "候选人姓名": resume.name,
            "岗位名称": job.title,
            "公司名称": job.company,
            "邮箱": resume.contact_info.email or "",
            "电话": resume.contact_info.phone or "",
            "所在地": resume.contact_info.location or "",
            "当前职位": resume.current_position or "",
            "当前公司": resume.current_company or "",
            "工作年限": resume.years_of_experience or 0,
            "薪资期望": resume.salary_expectation or "",
            "候选人状态": CandidateStatus.ACTIVE.value,
            "当前阶段": CandidateStage.INITIAL_SCREENING.value,
            "简历来源": resume.source.value,
            "创建时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "备注": "待AI分析"
        }
        
        return record_data
    
    async def _find_existing_record(self, resume_id: int, job_id: int) -> Optional[Dict[str, Any]]:
        """查找已存在的记录"""
        try:
            filters = {
                "简历ID": resume_id,
                "岗位ID": job_id
            }
            
            records = await self.get_feishu_records(filters)
            
            if records:
                return records[0]  # 返回第一个匹配的记录
            
            return None
            
        except Exception as e:
            app_logger.error(f"查找已存在记录失败: {str(e)}")
            return None
    
    async def get_sync_statistics(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        try:
            # 获取飞书记录总数
            all_records = await self.get_feishu_records()
            total_records = len(all_records)
            
            # 按状态统计
            status_stats = {}
            for status in CandidateStatus:
                status_records = [r for r in all_records if r.get("候选人状态") == status.value]
                status_stats[status.value] = len(status_records)
            
            # 按阶段统计
            stage_stats = {}
            for stage in CandidateStage:
                stage_records = [r for r in all_records if r.get("当前阶段") == stage.value]
                stage_stats[stage.value] = len(stage_records)
            
            # 最近同步时间
            recent_records = sorted(all_records, key=lambda x: x.get("更新时间", ""), reverse=True)
            last_sync_time = recent_records[0].get("更新时间") if recent_records else None
            
            stats = {
                "total_records": total_records,
                "by_status": status_stats,
                "by_stage": stage_stats,
                "last_sync_time": last_sync_time,
                "table_id": self.table_id,
                "updated_at": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            app_logger.error(f"获取同步统计失败: {str(e)}")
            return {}


# 全局服务实例
_feishu_service_instance = None


def get_feishu_service() -> FeishuService:
    """获取飞书服务实例"""
    global _feishu_service_instance
    if _feishu_service_instance is None:
        _feishu_service_instance = FeishuService()
    return _feishu_service_instance