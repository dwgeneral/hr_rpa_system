"""候选人数据模型"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class CandidateStatus(str, Enum):
    """候选人状态枚举"""
    NEW = "new"  # 新候选人
    SCREENING = "screening"  # 简历筛选中
    PHONE_INTERVIEW = "phone_interview"  # 电话面试
    TECHNICAL_INTERVIEW = "technical_interview"  # 技术面试
    FINAL_INTERVIEW = "final_interview"  # 终面
    OFFER_SENT = "offer_sent"  # 已发offer
    OFFER_ACCEPTED = "offer_accepted"  # 接受offer
    OFFER_REJECTED = "offer_rejected"  # 拒绝offer
    HIRED = "hired"  # 已入职
    REJECTED = "rejected"  # 已拒绝
    WITHDRAWN = "withdrawn"  # 主动退出
    ON_HOLD = "on_hold"  # 暂缓


class InterviewType(str, Enum):
    """面试类型枚举"""
    PHONE = "phone"  # 电话面试
    VIDEO = "video"  # 视频面试
    ONSITE = "onsite"  # 现场面试
    TECHNICAL = "technical"  # 技术面试
    HR = "hr"  # HR面试
    FINAL = "final"  # 终面


class InterviewResult(str, Enum):
    """面试结果枚举"""
    PASS = "pass"  # 通过
    FAIL = "fail"  # 不通过
    PENDING = "pending"  # 待定
    NO_SHOW = "no_show"  # 未出席


class CommunicationRecord(BaseModel):
    """沟通记录模型"""
    type: str = Field(..., description="沟通类型(email/phone/message)")
    content: str = Field(..., description="沟通内容")
    direction: str = Field(..., description="方向(inbound/outbound)")
    timestamp: datetime = Field(..., description="沟通时间")
    created_by: Optional[str] = Field(None, description="记录人")
    attachments: List[str] = Field(default_factory=list, description="附件")


class InterviewRecord(BaseModel):
    """面试记录模型"""
    type: InterviewType = Field(..., description="面试类型")
    scheduled_time: datetime = Field(..., description="预定时间")
    actual_time: Optional[datetime] = Field(None, description="实际时间")
    duration_minutes: Optional[int] = Field(None, description="面试时长(分钟)")
    interviewer: str = Field(..., description="面试官")
    location: Optional[str] = Field(None, description="面试地点")
    result: InterviewResult = Field(InterviewResult.PENDING, description="面试结果")
    score: Optional[float] = Field(None, description="面试评分")
    feedback: Optional[str] = Field(None, description="面试反馈")
    notes: Optional[str] = Field(None, description="备注")
    next_steps: Optional[str] = Field(None, description="下一步安排")


class OfferDetails(BaseModel):
    """Offer详情模型"""
    position: str = Field(..., description="职位")
    salary: int = Field(..., description="薪资")
    currency: str = Field("CNY", description="货币")
    benefits: List[str] = Field(default_factory=list, description="福利")
    start_date: Optional[datetime] = Field(None, description="入职日期")
    probation_period: Optional[int] = Field(None, description="试用期(月)")
    offer_sent_date: datetime = Field(..., description="发送日期")
    response_deadline: Optional[datetime] = Field(None, description="回复截止日期")
    accepted_date: Optional[datetime] = Field(None, description="接受日期")
    rejected_date: Optional[datetime] = Field(None, description="拒绝日期")
    rejection_reason: Optional[str] = Field(None, description="拒绝原因")


class CandidateBase(BaseModel):
    """候选人基础模型"""
    name: str = Field(..., description="姓名")
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号")
    location: Optional[str] = Field(None, description="所在地")
    
    # 关联信息
    resume_id: int = Field(..., description="简历ID")
    job_id: int = Field(..., description="应聘岗位ID")
    
    # 来源信息
    source: str = Field(..., description="候选人来源")
    source_url: Optional[str] = Field(None, description="来源链接")
    referrer: Optional[str] = Field(None, description="推荐人")
    
    # 基本信息
    current_company: Optional[str] = Field(None, description="当前公司")
    current_position: Optional[str] = Field(None, description="当前职位")
    years_of_experience: Optional[int] = Field(None, description="工作年限")
    education_level: Optional[str] = Field(None, description="学历")
    
    # 期望信息
    expected_salary: Optional[int] = Field(None, description="期望薪资")
    available_date: Optional[datetime] = Field(None, description="可入职日期")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('姓名不能为空且长度至少为2个字符')
        return v.strip()
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('邮箱格式不正确')
        return v


class CandidateCreate(CandidateBase):
    """创建候选人模型"""
    pass


class CandidateUpdate(BaseModel):
    """更新候选人模型"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    referrer: Optional[str] = None
    current_company: Optional[str] = None
    current_position: Optional[str] = None
    years_of_experience: Optional[int] = None
    education_level: Optional[str] = None
    expected_salary: Optional[int] = None
    available_date: Optional[datetime] = None
    status: Optional[CandidateStatus] = None
    notes: Optional[str] = None


class Candidate(CandidateBase):
    """完整候选人模型"""
    id: int = Field(..., description="候选人ID")
    status: CandidateStatus = Field(CandidateStatus.NEW, description="候选人状态")
    
    # 流程信息
    current_stage: Optional[str] = Field(None, description="当前阶段")
    priority: int = Field(3, description="优先级(1-5)")
    tags: List[str] = Field(default_factory=list, description="标签")
    notes: Optional[str] = Field(None, description="备注")
    
    # 评估信息
    overall_score: Optional[float] = Field(None, description="综合评分")
    technical_score: Optional[float] = Field(None, description="技术评分")
    culture_fit_score: Optional[float] = Field(None, description="文化匹配度")
    
    # 沟通记录
    communications: List[CommunicationRecord] = Field(default_factory=list, description="沟通记录")
    
    # 面试记录
    interviews: List[InterviewRecord] = Field(default_factory=list, description="面试记录")
    
    # Offer信息
    offer: Optional[OfferDetails] = Field(None, description="Offer详情")
    
    # 负责人
    recruiter: Optional[str] = Field(None, description="招聘负责人")
    hiring_manager: Optional[str] = Field(None, description="用人经理")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    last_contact_at: Optional[datetime] = Field(None, description="最后联系时间")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CandidateSearchParams(BaseModel):
    """候选人搜索参数"""
    keyword: Optional[str] = Field(None, description="关键词搜索")
    job_id: Optional[int] = Field(None, description="岗位ID")
    status: Optional[CandidateStatus] = Field(None, description="候选人状态")
    source: Optional[str] = Field(None, description="来源")
    recruiter: Optional[str] = Field(None, description="招聘负责人")
    min_score: Optional[float] = Field(None, description="最低评分")
    max_score: Optional[float] = Field(None, description="最高评分")
    priority: Optional[int] = Field(None, description="优先级")
    tags: Optional[List[str]] = Field(None, description="标签")
    
    # 时间范围
    created_after: Optional[datetime] = Field(None, description="创建时间起")
    created_before: Optional[datetime] = Field(None, description="创建时间止")
    
    # 分页参数
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    
    # 排序参数
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", regex="^(asc|desc)$", description="排序方向")


class CandidateStatusUpdate(BaseModel):
    """候选人状态更新模型"""
    candidate_id: int = Field(..., description="候选人ID")
    new_status: CandidateStatus = Field(..., description="新状态")
    reason: Optional[str] = Field(None, description="状态变更原因")
    notes: Optional[str] = Field(None, description="备注")
    next_action: Optional[str] = Field(None, description="下一步行动")
    scheduled_time: Optional[datetime] = Field(None, description="计划时间")