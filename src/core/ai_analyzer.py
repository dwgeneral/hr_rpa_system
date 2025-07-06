"""AI分析器核心模块"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..integrations.siliconflow_api import get_siliconflow_api, SiliconFlowAPIError
from ..models.resume import Resume
from ..models.job import Job
from ..models.analysis import (
    AnalysisResult, AnalysisResultCreate, ScoreDetail, ScoreDimension,
    MatchAnalysis, RiskAssessment, InterviewSuggestions, RecommendationLevel
)
from ..utils.logger import ai_logger
from ..utils.helpers import calculate_text_similarity, extract_keywords


class AIAnalyzer:
    """AI分析器"""
    
    def __init__(self):
        self.default_weights = {
            ScoreDimension.SKILL_MATCH: 0.25,
            ScoreDimension.EXPERIENCE_RELEVANCE: 0.20,
            ScoreDimension.EDUCATION_BACKGROUND: 0.15,
            ScoreDimension.PROJECT_EXPERIENCE: 0.15,
            ScoreDimension.WORK_STABILITY: 0.10,
            ScoreDimension.SALARY_EXPECTATION: 0.05,
            ScoreDimension.LOCATION_MATCH: 0.03,
            ScoreDimension.LANGUAGE_ABILITY: 0.03,
            ScoreDimension.CERTIFICATIONS: 0.02,
            ScoreDimension.BONUS_POINTS: 0.02
        }
    
    async def analyze_resume(self, resume: Resume, job: Job, custom_weights: Optional[Dict[ScoreDimension, float]] = None) -> AnalysisResult:
        """分析简历匹配度"""
        try:
            ai_logger.info(f"开始分析简历: {resume.name} 应聘 {job.title}")
            
            start_time = datetime.now()
            
            # 准备分析数据
            resume_text = self._prepare_resume_text(resume)
            job_description = self._prepare_job_description(job)
            
            # 使用AI进行分析
            async with await get_siliconflow_api() as api:
                ai_result = await api.analyze_resume(resume_text, job_description)
            
            # 处理分析结果
            analysis_result = await self._process_ai_result(
                ai_result, resume, job, custom_weights
            )
            
            # 计算分析耗时
            duration = (datetime.now() - start_time).total_seconds()
            analysis_result.analysis_duration = duration
            
            ai_logger.info(
                f"简历分析完成: {resume.name} - 得分: {analysis_result.overall_score} - "
                f"推荐等级: {analysis_result.recommendation_level.value} - 耗时: {duration:.2f}秒"
            )
            
            return analysis_result
            
        except Exception as e:
            ai_logger.error(f"分析简历失败: {str(e)}")
            raise
    
    async def batch_analyze_resumes(self, resumes: List[Resume], job: Job, custom_weights: Optional[Dict[ScoreDimension, float]] = None) -> List[AnalysisResult]:
        """批量分析简历"""
        try:
            ai_logger.info(f"开始批量分析{len(resumes)}份简历")
            
            results = []
            
            # 并发分析（限制并发数避免API限流）
            semaphore = asyncio.Semaphore(3)  # 最多3个并发请求
            
            async def analyze_single(resume: Resume) -> AnalysisResult:
                async with semaphore:
                    return await self.analyze_resume(resume, job, custom_weights)
            
            # 创建任务
            tasks = [analyze_single(resume) for resume in resumes]
            
            # 执行批量分析
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            successful_results = []
            failed_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    ai_logger.error(f"分析简历失败: {resumes[i].name} - {str(result)}")
                    failed_count += 1
                else:
                    successful_results.append(result)
            
            ai_logger.info(
                f"批量分析完成: 成功{len(successful_results)}份，失败{failed_count}份"
            )
            
            return successful_results
            
        except Exception as e:
            ai_logger.error(f"批量分析失败: {str(e)}")
            raise
    
    def _prepare_resume_text(self, resume: Resume) -> str:
        """准备简历文本"""
        text_parts = []
        
        # 基本信息
        text_parts.append(f"姓名: {resume.name}")
        
        if resume.contact_info.email:
            text_parts.append(f"邮箱: {resume.contact_info.email}")
        
        if resume.contact_info.phone:
            text_parts.append(f"电话: {resume.contact_info.phone}")
        
        if resume.contact_info.location:
            text_parts.append(f"所在地: {resume.contact_info.location}")
        
        # 个人简介
        if resume.summary:
            text_parts.append(f"个人简介: {resume.summary}")
        
        # 工作经历
        if resume.work_experiences:
            text_parts.append("\n工作经历:")
            for exp in resume.work_experiences:
                exp_text = f"- {exp.company} | {exp.position}"
                if exp.start_date and exp.end_date:
                    exp_text += f" | {exp.start_date} - {exp.end_date}"
                if exp.description:
                    exp_text += f"\n  {exp.description}"
                if exp.responsibilities:
                    exp_text += f"\n  主要职责: {'; '.join(exp.responsibilities)}"
                if exp.achievements:
                    exp_text += f"\n  主要成就: {'; '.join(exp.achievements)}"
                text_parts.append(exp_text)
        
        # 教育背景
        if resume.education:
            text_parts.append("\n教育背景:")
            for edu in resume.education:
                edu_text = f"- {edu.school} | {edu.major} | {edu.degree}"
                if edu.start_date and edu.end_date:
                    edu_text += f" | {edu.start_date} - {edu.end_date}"
                text_parts.append(edu_text)
        
        # 项目经验
        if resume.project_experiences:
            text_parts.append("\n项目经验:")
            for proj in resume.project_experiences:
                proj_text = f"- {proj.name}"
                if proj.role:
                    proj_text += f" | {proj.role}"
                if proj.description:
                    proj_text += f"\n  {proj.description}"
                if proj.technologies:
                    proj_text += f"\n  技术栈: {'; '.join(proj.technologies)}"
                text_parts.append(proj_text)
        
        # 技能
        if resume.skills:
            text_parts.append(f"\n技能: {'; '.join(resume.skills)}")
        
        # 语言能力
        if resume.languages:
            text_parts.append(f"\n语言能力: {'; '.join(resume.languages)}")
        
        # 证书资质
        if resume.certifications:
            text_parts.append(f"\n证书资质: {'; '.join(resume.certifications)}")
        
        # 工作年限
        if resume.years_of_experience:
            text_parts.append(f"\n工作年限: {resume.years_of_experience}年")
        
        # 薪资期望
        if resume.salary_expectation:
            text_parts.append(f"\n薪资期望: {resume.salary_expectation}")
        
        return "\n".join(text_parts)
    
    def _prepare_job_description(self, job: Job) -> str:
        """准备岗位描述文本"""
        text_parts = []
        
        # 基本信息
        text_parts.append(f"岗位名称: {job.title}")
        text_parts.append(f"公司: {job.company}")
        text_parts.append(f"工作地点: {job.location}")
        text_parts.append(f"岗位类型: {job.job_type.value}")
        
        if job.department:
            text_parts.append(f"部门: {job.department}")
        
        # 岗位描述
        text_parts.append(f"\n岗位描述: {job.description}")
        
        # 工作职责
        if job.responsibilities:
            text_parts.append(f"\n工作职责: {'; '.join(job.responsibilities)}")
        
        # 岗位要求
        req = job.requirements
        text_parts.append("\n岗位要求:")
        text_parts.append(f"- 经验要求: {req.experience_level.value}")
        
        if req.min_years or req.max_years:
            years_text = "- 工作年限: "
            if req.min_years and req.max_years:
                years_text += f"{req.min_years}-{req.max_years}年"
            elif req.min_years:
                years_text += f"{req.min_years}年以上"
            elif req.max_years:
                years_text += f"{req.max_years}年以下"
            text_parts.append(years_text)
        
        text_parts.append(f"- 学历要求: {req.education.value}")
        
        if req.required_skills:
            text_parts.append(f"- 必需技能: {'; '.join(req.required_skills)}")
        
        if req.preferred_skills:
            text_parts.append(f"- 优选技能: {'; '.join(req.preferred_skills)}")
        
        if req.languages:
            text_parts.append(f"- 语言要求: {'; '.join(req.languages)}")
        
        if req.certifications:
            text_parts.append(f"- 证书要求: {'; '.join(req.certifications)}")
        
        if req.bonus_points:
            text_parts.append(f"- 加分项: {'; '.join(req.bonus_points)}")
        
        # 薪资福利
        if job.salary_range:
            salary = job.salary_range
            if salary.min_salary and salary.max_salary:
                text_parts.append(f"\n薪资范围: {salary.min_salary}-{salary.max_salary} {salary.currency}/{salary.unit}")
            elif salary.negotiable:
                text_parts.append("\n薪资: 面议")
        
        if job.benefits:
            text_parts.append(f"\n福利待遇: {'; '.join(job.benefits)}")
        
        return "\n".join(text_parts)
    
    async def _process_ai_result(self, ai_result: Dict[str, Any], resume: Resume, job: Job, custom_weights: Optional[Dict[ScoreDimension, float]] = None) -> AnalysisResult:
        """处理AI分析结果"""
        try:
            # 使用自定义权重或默认权重
            weights = custom_weights or self.default_weights
            
            # 处理评分详情
            score_details = []
            for detail_data in ai_result["score_details"]:
                dimension = ScoreDimension(detail_data["dimension"])
                weight = weights.get(dimension, detail_data["weight"])
                
                score_detail = ScoreDetail(
                    dimension=dimension,
                    score=detail_data["score"],
                    weight=weight,
                    weighted_score=detail_data["score"] * weight,
                    explanation=detail_data["explanation"],
                    evidence=detail_data.get("evidence", []),
                    suggestions=detail_data.get("suggestions", [])
                )
                score_details.append(score_detail)
            
            # 重新计算总分
            overall_score = sum(detail.weighted_score for detail in score_details)
            
            # 处理匹配分析
            match_data = ai_result["match_analysis"]
            match_analysis = MatchAnalysis(
                matched_skills=match_data["matched_skills"],
                missing_skills=match_data["missing_skills"],
                extra_skills=match_data["extra_skills"],
                skill_match_rate=match_data["skill_match_rate"],
                experience_match=match_data["experience_match"],
                experience_gap=match_data.get("experience_gap"),
                education_match=match_data["education_match"],
                education_gap=match_data.get("education_gap"),
                location_match=match_data["location_match"],
                location_note=match_data.get("location_note")
            )
            
            # 处理风险评估
            risk_data = ai_result["risk_assessment"]
            risk_assessment = RiskAssessment(
                overall_risk=risk_data["overall_risk"],
                risk_factors=risk_data["risk_factors"],
                job_hopping_risk=risk_data["job_hopping_risk"],
                salary_risk=risk_data["salary_risk"],
                skill_gap_risk=risk_data["skill_gap_risk"],
                culture_fit_risk=risk_data["culture_fit_risk"],
                mitigation_strategies=risk_data["mitigation_strategies"]
            )
            
            # 处理面试建议
            interview_data = ai_result["interview_suggestions"]
            interview_suggestions = InterviewSuggestions(
                recommended_questions=interview_data["recommended_questions"],
                focus_areas=interview_data["focus_areas"],
                technical_assessment=interview_data["technical_assessment"],
                behavioral_assessment=interview_data["behavioral_assessment"],
                red_flags=interview_data["red_flags"]
            )
            
            # 确定推荐等级
            recommendation_level = RecommendationLevel(ai_result["recommendation_level"])
            
            # 创建分析结果
            analysis_result = AnalysisResult(
                id=0,  # 将在数据库保存时设置
                resume_id=resume.id,
                job_id=job.id,
                overall_score=round(overall_score, 2),
                recommendation_level=recommendation_level,
                score_details=score_details,
                match_analysis=match_analysis,
                risk_assessment=risk_assessment,
                interview_suggestions=interview_suggestions,
                summary=ai_result["summary"],
                strengths=ai_result["strengths"],
                weaknesses=ai_result["weaknesses"],
                recommendations=ai_result["recommendations"],
                analysis_version="1.0",
                model_used="deepseek-chat",
                raw_analysis_data=ai_result,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            return analysis_result
            
        except Exception as e:
            ai_logger.error(f"处理AI分析结果失败: {str(e)}")
            raise
    
    def calculate_similarity_score(self, resume: Resume, job: Job) -> float:
        """计算简历与岗位的文本相似度"""
        try:
            resume_text = self._prepare_resume_text(resume)
            job_text = self._prepare_job_description(job)
            
            # 提取关键词
            resume_keywords = extract_keywords(resume_text)
            job_keywords = extract_keywords(job_text)
            
            # 计算关键词重叠度
            resume_set = set(resume_keywords)
            job_set = set(job_keywords)
            
            if not job_set:
                return 0.0
            
            intersection = resume_set.intersection(job_set)
            similarity = len(intersection) / len(job_set)
            
            return round(similarity, 3)
            
        except Exception as e:
            ai_logger.error(f"计算相似度失败: {str(e)}")
            return 0.0
    
    async def generate_interview_questions(self, resume: Resume, job: Job, focus_areas: Optional[List[str]] = None) -> List[str]:
        """生成面试问题"""
        try:
            resume_text = self._prepare_resume_text(resume)
            job_description = self._prepare_job_description(job)
            
            async with await get_siliconflow_api() as api:
                questions = await api.generate_interview_questions(
                    resume_text, job_description, focus_areas
                )
            
            ai_logger.info(f"为{resume.name}生成了{len(questions)}个面试问题")
            
            return questions
            
        except Exception as e:
            ai_logger.error(f"生成面试问题失败: {str(e)}")
            return []


# 全局分析器实例
_analyzer_instance = None


def get_ai_analyzer() -> AIAnalyzer:
    """获取AI分析器实例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = AIAnalyzer()
    return _analyzer_instance