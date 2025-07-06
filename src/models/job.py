"""岗位数据模型"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class JobStatus(str, Enum):
    """岗位状态枚举"""
    ACTIVE = "active"  # 活跃招聘
    PAUSED = "paused"  # 暂停招聘
    CLOSED = "closed"  # 关闭招聘
    DRAFT = "draft"  # 草稿


class JobType(str, Enum):
    """岗位类型枚举"""
    FULL_TIME = "full_time"  # 全职
    PART_TIME = "part_time"  # 兼职
    CONTRACT = "contract"  # 合同工
    INTERNSHIP = "internship"  # 实习
    REMOTE = "remote"  # 远程


class ExperienceLevel(str, Enum):
    """经验要求枚举"""
    ENTRY = "entry"  # 应届生
    JUNIOR = "junior"  # 1-3年
    MID = "mid"  # 3-5年
    SENIOR = "senior"  # 5-10年
    EXPERT = "expert"  # 10年以上


class EducationRequirement(str, Enum):
    """学历要求枚举"""
    HIGH_SCHOOL = "high_school"  # 高中
    COLLEGE = "college"  # 专科
    BACHELOR = "bachelor"  # 本科
    MASTER = "master"  # 硕士
    PHD = "phd"  # 博士
    NO_REQUIREMENT = "no_requirement"  # 不限


class SalaryRange(BaseModel):
    """薪资范围模型"""
    min_salary: Optional[int] = Field(None, description="最低薪资")
    max_salary: Optional[int] = Field(None, description="最高薪资")
    currency: str = Field("CNY", description="货币单位")
    unit: str = Field("monthly", description="薪资单位(monthly/yearly)")
    negotiable: bool = Field(False, description="是否面议")


class JobRequirement(BaseModel):
    """岗位要求模型"""
    # 基本要求
    experience_level: ExperienceLevel = Field(..., description="经验要求")
    min_years: Optional[int] = Field(None, description="最少工作年限")
    max_years: Optional[int] = Field(None, description="最多工作年限")
    education: EducationRequirement = Field(..., description="学历要求")
    
    # 技能要求
    required_skills: List[str] = Field(default_factory=list, description="必需技能")
    preferred_skills: List[str] = Field(default_factory=list, description="优选技能")
    
    # 语言要求
    languages: List[str] = Field(default_factory=list, description="语言要求")
    
    # 其他要求
    certifications: List[str] = Field(default_factory=list, description="证书要求")
    location_requirement: Optional[str] = Field(None, description="地点要求")
    travel_requirement: Optional[str] = Field(None, description="出差要求")
    
    # 加分项
    bonus_points: List[str] = Field(default_factory=list, description="加分项")


class JobBase(BaseModel):
    """岗位基础模型"""
    title: str = Field(..., description="岗位名称")
    department: Optional[str] = Field(None, description="部门")
    company: str = Field(..., description="公司名称")
    location: str = Field(..., description="工作地点")
    job_type: JobType = Field(JobType.FULL_TIME, description="岗位类型")
    
    # 岗位描述
    description: str = Field(..., description="岗位描述")
    responsibilities: List[str] = Field(default_factory=list, description="工作职责")
    
    # 岗位要求
    requirements: JobRequirement = Field(..., description="岗位要求")
    
    # 薪资福利
    salary_range: Optional[SalaryRange] = Field(None, description="薪资范围")
    benefits: List[str] = Field(default_factory=list, description="福利待遇")
    
    # 其他信息
    team_size: Optional[int] = Field(None, description="团队规模")
    reporting_to: Optional[str] = Field(None, description="汇报对象")
    
    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('岗位名称不能为空且长度至少为2个字符')
        return v.strip()
    
    @validator('company')
    def validate_company(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('公司名称不能为空且长度至少为2个字符')
        return v.strip()


class JobCreate(JobBase):
    """创建岗位模型"""
    pass


class JobUpdate(BaseModel):
    """更新岗位模型"""
    title: Optional[str] = None
    department: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[JobType] = None
    description: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    requirements: Optional[JobRequirement] = None
    salary_range: Optional[SalaryRange] = None
    benefits: Optional[List[str]] = None
    team_size: Optional[int] = None
    reporting_to: Optional[str] = None
    status: Optional[JobStatus] = None


class Job(JobBase):
    """完整岗位模型"""
    id: int = Field(..., description="岗位ID")
    status: JobStatus = Field(JobStatus.DRAFT, description="岗位状态")
    
    # 统计信息
    view_count: int = Field(0, description="浏览次数")
    application_count: int = Field(0, description="申请人数")
    
    # 创建者信息
    created_by: Optional[str] = Field(None, description="创建者")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    published_at: Optional[datetime] = Field(None, description="发布时间")
    closed_at: Optional[datetime] = Field(None, description="关闭时间")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobSearchParams(BaseModel):
    """岗位搜索参数"""
    keyword: Optional[str] = Field(None, description="关键词搜索")
    company: Optional[str] = Field(None, description="公司名称")
    location: Optional[str] = Field(None, description="工作地点")
    job_type: Optional[JobType] = Field(None, description="岗位类型")
    status: Optional[JobStatus] = Field(None, description="岗位状态")
    experience_level: Optional[ExperienceLevel] = Field(None, description="经验要求")
    education: Optional[EducationRequirement] = Field(None, description="学历要求")
    skills: Optional[List[str]] = Field(None, description="技能要求")
    
    # 薪资范围
    min_salary: Optional[int] = Field(None, description="最低薪资")
    max_salary: Optional[int] = Field(None, description="最高薪资")
    
    # 分页参数
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    
    # 排序参数
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", regex="^(asc|desc)$", description="排序方向")


class JobAnalysisRequest(BaseModel):
    """岗位分析请求模型"""
    job_id: int = Field(..., description="岗位ID")
    resume_ids: List[int] = Field(..., description="简历ID列表")
    analysis_type: str = Field("standard", description="分析类型")
    custom_weights: Optional[Dict[str, float]] = Field(None, description="自定义权重")