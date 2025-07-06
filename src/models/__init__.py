"""数据模型模块"""

from .resume import Resume, ResumeCreate, ResumeUpdate
from .job import Job, JobCreate, JobUpdate, JobRequirement
from .candidate import Candidate, CandidateCreate, CandidateUpdate
from .analysis import AnalysisResult, ScoreDetail, RecommendationLevel

__all__ = [
    "Resume",
    "ResumeCreate", 
    "ResumeUpdate",
    "Job",
    "JobCreate",
    "JobUpdate",
    "JobRequirement",
    "Candidate",
    "CandidateCreate",
    "CandidateUpdate",
    "AnalysisResult",
    "ScoreDetail",
    "RecommendationLevel",
]