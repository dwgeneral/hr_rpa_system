"""简历数据模型"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ResumeStatus(str, Enum):
    """简历状态枚举"""
    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    ANALYZED = "analyzed"  # 已分析
    APPROVED = "approved"  # 通过
    REJECTED = "rejected"  # 拒绝
    ERROR = "error"  # 错误


class ResumeSource(str, Enum):
    """简历来源枚举"""
    BOSS = "boss"  # BOSS直聘
    LAGOU = "lagou"  # 拉勾网
    ZHILIAN = "zhilian"  # 智联招聘
    MANUAL = "manual"  # 手动上传
    OTHER = "other"  # 其他


class WorkExperience(BaseModel):
    """工作经历模型"""
    company: str = Field(..., description="公司名称")
    position: str = Field(..., description="职位名称")
    start_date: Optional[str] = Field(None, description="开始时间")
    end_date: Optional[str] = Field(None, description="结束时间")
    duration: Optional[str] = Field(None, description="工作时长")
    description: Optional[str] = Field(None, description="工作描述")
    responsibilities: List[str] = Field(default_factory=list, description="主要职责")
    achievements: List[str] = Field(default_factory=list, description="主要成就")


class Education(BaseModel):
    """教育经历模型"""
    school: str = Field(..., description="学校名称")
    major: str = Field(..., description="专业")
    degree: str = Field(..., description="学历")
    start_date: Optional[str] = Field(None, description="开始时间")
    end_date: Optional[str] = Field(None, description="结束时间")
    gpa: Optional[str] = Field(None, description="GPA")
    description: Optional[str] = Field(None, description="描述")


class ProjectExperience(BaseModel):
    """项目经历模型"""
    name: str = Field(..., description="项目名称")
    role: Optional[str] = Field(None, description="担任角色")
    start_date: Optional[str] = Field(None, description="开始时间")
    end_date: Optional[str] = Field(None, description="结束时间")
    description: Optional[str] = Field(None, description="项目描述")
    technologies: List[str] = Field(default_factory=list, description="使用技术")
    achievements: List[str] = Field(default_factory=list, description="项目成果")


class ContactInfo(BaseModel):
    """联系信息模型"""
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号")
    wechat: Optional[str] = Field(None, description="微信")
    location: Optional[str] = Field(None, description="所在地")
    address: Optional[str] = Field(None, description="详细地址")


class ResumeBase(BaseModel):
    """简历基础模型"""
    name: str = Field(..., description="姓名")
    source: ResumeSource = Field(ResumeSource.MANUAL, description="简历来源")
    source_url: Optional[str] = Field(None, description="来源链接")
    file_path: Optional[str] = Field(None, description="文件路径")
    raw_text: Optional[str] = Field(None, description="原始文本")
    
    # 基本信息
    contact_info: ContactInfo = Field(default_factory=ContactInfo, description="联系信息")
    summary: Optional[str] = Field(None, description="个人简介")
    
    # 经历信息
    work_experiences: List[WorkExperience] = Field(default_factory=list, description="工作经历")
    education: List[Education] = Field(default_factory=list, description="教育经历")
    project_experiences: List[ProjectExperience] = Field(default_factory=list, description="项目经历")
    
    # 技能信息
    skills: List[str] = Field(default_factory=list, description="技能列表")
    languages: List[str] = Field(default_factory=list, description="语言能力")
    certifications: List[str] = Field(default_factory=list, description="证书资质")
    
    # 其他信息
    salary_expectation: Optional[Dict[str, Any]] = Field(None, description="薪资期望")
    years_of_experience: Optional[int] = Field(None, description="工作年限")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('姓名不能为空且长度至少为2个字符')
        return v.strip()
    
    @validator('contact_info')
    def validate_contact_info(cls, v):
        if not v.email and not v.phone:
            raise ValueError('邮箱和手机号至少需要提供一个')
        return v


class ResumeCreate(ResumeBase):
    """创建简历模型"""
    pass


class ResumeUpdate(BaseModel):
    """更新简历模型"""
    name: Optional[str] = None
    source: Optional[ResumeSource] = None
    source_url: Optional[str] = None
    file_path: Optional[str] = None
    raw_text: Optional[str] = None
    contact_info: Optional[ContactInfo] = None
    summary: Optional[str] = None
    work_experiences: Optional[List[WorkExperience]] = None
    education: Optional[List[Education]] = None
    project_experiences: Optional[List[ProjectExperience]] = None
    skills: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    salary_expectation: Optional[Dict[str, Any]] = None
    years_of_experience: Optional[int] = None
    keywords: Optional[List[str]] = None
    status: Optional[ResumeStatus] = None


class Resume(ResumeBase):
    """完整简历模型"""
    id: int = Field(..., description="简历ID")
    status: ResumeStatus = Field(ResumeStatus.PENDING, description="处理状态")
    hash_value: Optional[str] = Field(None, description="内容哈希值")
    file_size: Optional[float] = Field(None, description="文件大小(MB)")
    mime_type: Optional[str] = Field(None, description="文件类型")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    processed_at: Optional[datetime] = Field(None, description="处理时间")
    
    # 分析结果关联
    analysis_id: Optional[int] = Field(None, description="分析结果ID")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ResumeSearchParams(BaseModel):
    """简历搜索参数"""
    keyword: Optional[str] = Field(None, description="关键词搜索")
    source: Optional[ResumeSource] = Field(None, description="简历来源")
    status: Optional[ResumeStatus] = Field(None, description="处理状态")
    min_experience: Optional[int] = Field(None, description="最少工作年限")
    max_experience: Optional[int] = Field(None, description="最多工作年限")
    education_level: Optional[str] = Field(None, description="学历要求")
    skills: Optional[List[str]] = Field(None, description="技能要求")
    location: Optional[str] = Field(None, description="工作地点")
    
    # 分页参数
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    
    # 排序参数
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", regex="^(asc|desc)$", description="排序方向")