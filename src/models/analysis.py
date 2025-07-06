"""分析结果数据模型"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class RecommendationLevel(str, Enum):
    """推荐等级枚举"""
    HIGHLY_RECOMMENDED = "highly_recommended"  # 强烈推荐 (绿灯)
    RECOMMENDED = "recommended"  # 推荐 (黄灯)
    NOT_RECOMMENDED = "not_recommended"  # 不推荐 (红灯)
    NEEDS_REVIEW = "needs_review"  # 需要人工审核


class ScoreDimension(str, Enum):
    """评分维度枚举"""
    SKILL_MATCH = "skill_match"  # 技能匹配度
    EXPERIENCE_RELEVANCE = "experience_relevance"  # 经验相关性
    EDUCATION_BACKGROUND = "education_background"  # 教育背景
    PROJECT_EXPERIENCE = "project_experience"  # 项目经验
    WORK_STABILITY = "work_stability"  # 工作稳定性
    SALARY_EXPECTATION = "salary_expectation"  # 薪资期望
    LOCATION_MATCH = "location_match"  # 地理位置
    LANGUAGE_ABILITY = "language_ability"  # 语言能力
    CERTIFICATIONS = "certifications"  # 证书资质
    BONUS_POINTS = "bonus_points"  # 其他加分项


class ScoreDetail(BaseModel):
    """评分详情模型"""
    dimension: ScoreDimension = Field(..., description="评分维度")
    score: float = Field(..., ge=0, le=10, description="得分(0-10)")
    weight: float = Field(..., ge=0, le=1, description="权重(0-1)")
    weighted_score: float = Field(..., description="加权得分")
    explanation: str = Field(..., description="评分说明")
    evidence: List[str] = Field(default_factory=list, description="支撑证据")
    suggestions: List[str] = Field(default_factory=list, description="改进建议")
    
    @validator('weighted_score')
    def calculate_weighted_score(cls, v, values):
        if 'score' in values and 'weight' in values:
            return values['score'] * values['weight']
        return v


class MatchAnalysis(BaseModel):
    """匹配分析模型"""
    matched_skills: List[str] = Field(default_factory=list, description="匹配的技能")
    missing_skills: List[str] = Field(default_factory=list, description="缺失的技能")
    extra_skills: List[str] = Field(default_factory=list, description="额外的技能")
    skill_match_rate: float = Field(..., ge=0, le=1, description="技能匹配率")
    
    experience_match: bool = Field(..., description="经验是否匹配")
    experience_gap: Optional[str] = Field(None, description="经验差距")
    
    education_match: bool = Field(..., description="学历是否匹配")
    education_gap: Optional[str] = Field(None, description="学历差距")
    
    location_match: bool = Field(..., description="地点是否匹配")
    location_note: Optional[str] = Field(None, description="地点备注")


class RiskAssessment(BaseModel):
    """风险评估模型"""
    overall_risk: str = Field(..., description="整体风险等级(low/medium/high)")
    risk_factors: List[str] = Field(default_factory=list, description="风险因素")
    
    # 具体风险项
    job_hopping_risk: float = Field(..., ge=0, le=1, description="跳槽风险")
    salary_risk: float = Field(..., ge=0, le=1, description="薪资风险")
    skill_gap_risk: float = Field(..., ge=0, le=1, description="技能差距风险")
    culture_fit_risk: float = Field(..., ge=0, le=1, description="文化适应风险")
    
    mitigation_strategies: List[str] = Field(default_factory=list, description="风险缓解策略")


class InterviewSuggestions(BaseModel):
    """面试建议模型"""
    recommended_questions: List[str] = Field(default_factory=list, description="推荐问题")
    focus_areas: List[str] = Field(default_factory=list, description="重点关注领域")
    technical_assessment: List[str] = Field(default_factory=list, description="技术评估建议")
    behavioral_assessment: List[str] = Field(default_factory=list, description="行为评估建议")
    red_flags: List[str] = Field(default_factory=list, description="需要注意的红旗")


class AnalysisResultBase(BaseModel):
    """分析结果基础模型"""
    resume_id: int = Field(..., description="简历ID")
    job_id: int = Field(..., description="岗位ID")
    
    # 总体评分
    overall_score: float = Field(..., ge=0, le=10, description="综合得分(0-10)")
    recommendation_level: RecommendationLevel = Field(..., description="推荐等级")
    
    # 详细评分
    score_details: List[ScoreDetail] = Field(..., description="各维度评分详情")
    
    # 分析结果
    match_analysis: MatchAnalysis = Field(..., description="匹配分析")
    risk_assessment: RiskAssessment = Field(..., description="风险评估")
    
    # 建议
    interview_suggestions: InterviewSuggestions = Field(..., description="面试建议")
    
    # 总结
    summary: str = Field(..., description="分析总结")
    strengths: List[str] = Field(default_factory=list, description="优势")
    weaknesses: List[str] = Field(default_factory=list, description="劣势")
    recommendations: List[str] = Field(default_factory=list, description="建议")
    
    @validator('overall_score')
    def calculate_overall_score(cls, v, values):
        if 'score_details' in values:
            total_weighted_score = sum(detail.weighted_score for detail in values['score_details'])
            return round(total_weighted_score, 2)
        return v


class AnalysisResultCreate(AnalysisResultBase):
    """创建分析结果模型"""
    pass


class AnalysisResultUpdate(BaseModel):
    """更新分析结果模型"""
    overall_score: Optional[float] = None
    recommendation_level: Optional[RecommendationLevel] = None
    score_details: Optional[List[ScoreDetail]] = None
    match_analysis: Optional[MatchAnalysis] = None
    risk_assessment: Optional[RiskAssessment] = None
    interview_suggestions: Optional[InterviewSuggestions] = None
    summary: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    human_review_notes: Optional[str] = None
    is_reviewed: Optional[bool] = None


class AnalysisResult(AnalysisResultBase):
    """完整分析结果模型"""
    id: int = Field(..., description="分析结果ID")
    
    # 分析元信息
    analysis_version: str = Field(..., description="分析版本")
    model_used: str = Field(..., description="使用的AI模型")
    analysis_duration: Optional[float] = Field(None, description="分析耗时(秒)")
    
    # 人工审核
    is_reviewed: bool = Field(False, description="是否已人工审核")
    human_review_notes: Optional[str] = Field(None, description="人工审核备注")
    reviewed_by: Optional[str] = Field(None, description="审核人")
    reviewed_at: Optional[datetime] = Field(None, description="审核时间")
    
    # 原始数据
    raw_analysis_data: Optional[Dict[str, Any]] = Field(None, description="原始分析数据")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnalysisRequest(BaseModel):
    """分析请求模型"""
    resume_id: int = Field(..., description="简历ID")
    job_id: int = Field(..., description="岗位ID")
    analysis_type: str = Field("standard", description="分析类型")
    custom_weights: Optional[Dict[ScoreDimension, float]] = Field(None, description="自定义权重")
    force_reanalysis: bool = Field(False, description="是否强制重新分析")


class BatchAnalysisRequest(BaseModel):
    """批量分析请求模型"""
    job_id: int = Field(..., description="岗位ID")
    resume_ids: List[int] = Field(..., description="简历ID列表")
    analysis_type: str = Field("standard", description="分析类型")
    custom_weights: Optional[Dict[ScoreDimension, float]] = Field(None, description="自定义权重")
    force_reanalysis: bool = Field(False, description="是否强制重新分析")
    
    @validator('resume_ids')
    def validate_resume_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError('简历ID列表不能为空')
        if len(v) > 100:
            raise ValueError('单次批量分析不能超过100份简历')
        return v


class AnalysisSearchParams(BaseModel):
    """分析结果搜索参数"""
    job_id: Optional[int] = Field(None, description="岗位ID")
    resume_id: Optional[int] = Field(None, description="简历ID")
    recommendation_level: Optional[RecommendationLevel] = Field(None, description="推荐等级")
    min_score: Optional[float] = Field(None, ge=0, le=10, description="最低得分")
    max_score: Optional[float] = Field(None, ge=0, le=10, description="最高得分")
    is_reviewed: Optional[bool] = Field(None, description="是否已审核")
    
    # 时间范围
    created_after: Optional[datetime] = Field(None, description="创建时间起")
    created_before: Optional[datetime] = Field(None, description="创建时间止")
    
    # 分页参数
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    
    # 排序参数
    sort_by: str = Field("overall_score", description="排序字段")
    sort_order: str = Field("desc", regex="^(asc|desc)$", description="排序方向")


class AnalysisStatistics(BaseModel):
    """分析统计模型"""
    total_analyses: int = Field(..., description="总分析数")
    highly_recommended: int = Field(..., description="强烈推荐数")
    recommended: int = Field(..., description="推荐数")
    not_recommended: int = Field(..., description="不推荐数")
    needs_review: int = Field(..., description="需要审核数")
    
    average_score: float = Field(..., description="平均得分")
    score_distribution: Dict[str, int] = Field(..., description="得分分布")
    
    top_skills: List[Dict[str, Any]] = Field(..., description="热门技能")
    common_weaknesses: List[Dict[str, Any]] = Field(..., description="常见不足")