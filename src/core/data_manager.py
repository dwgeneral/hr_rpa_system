"""数据管理器核心模块"""

import sqlite3
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager

from ..models.resume import Resume, ResumeCreate, ResumeUpdate, ResumeStatus, ResumeSource
from ..models.job import Job, JobCreate, JobUpdate, JobStatus
from ..models.candidate import Candidate, CandidateCreate, CandidateUpdate, CandidateStatus
from ..models.analysis import AnalysisResult, AnalysisResultCreate, AnalysisResultUpdate
from ..utils.logger import app_logger
from ..utils.config import get_config
from ..utils.helpers import generate_hash


class DataManager:
    """数据管理器"""
    
    def __init__(self, db_path: Optional[str] = None):
        config = get_config()
        self.db_path = db_path or config.database.url.replace("sqlite:///", "")
        self.connection_pool = {}
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        try:
            # 确保数据库目录存在
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                self._create_tables(conn)
                app_logger.info(f"数据库初始化完成: {self.db_path}")
        except Exception as e:
            app_logger.error(f"数据库初始化失败: {str(e)}")
            raise
    
    def _create_tables(self, conn: sqlite3.Connection):
        """创建数据表"""
        # 岗位表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                department TEXT,
                location TEXT NOT NULL,
                job_type TEXT NOT NULL,
                description TEXT NOT NULL,
                responsibilities TEXT,  -- JSON array
                requirements TEXT NOT NULL,  -- JSON object
                salary_range TEXT,  -- JSON object
                benefits TEXT,  -- JSON array
                status TEXT NOT NULL DEFAULT 'active',
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 简历表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact_info TEXT NOT NULL,  -- JSON object
                summary TEXT,
                work_experiences TEXT,  -- JSON array
                education TEXT,  -- JSON array
                project_experiences TEXT,  -- JSON array
                skills TEXT,  -- JSON array
                languages TEXT,  -- JSON array
                certifications TEXT,  -- JSON array
                years_of_experience INTEGER,
                current_position TEXT,
                current_company TEXT,
                current_salary TEXT,
                salary_expectation TEXT,
                job_status TEXT,
                availability TEXT,
                source TEXT NOT NULL,
                source_url TEXT,
                source_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                file_path TEXT,
                file_hash TEXT,
                raw_data TEXT,  -- JSON object
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, source_id)
            )
        """)
        
        # 候选人表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                current_stage TEXT NOT NULL DEFAULT 'initial_screening',
                status TEXT NOT NULL DEFAULT 'active',
                priority TEXT NOT NULL DEFAULT 'medium',
                source_channel TEXT,
                referrer TEXT,
                notes TEXT,
                tags TEXT,  -- JSON array
                communication_records TEXT,  -- JSON array
                interview_records TEXT,  -- JSON array
                offer_details TEXT,  -- JSON object
                rejection_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes (id),
                FOREIGN KEY (job_id) REFERENCES jobs (id),
                UNIQUE(resume_id, job_id)
            )
        """)
        
        # 分析结果表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                overall_score REAL NOT NULL,
                recommendation_level TEXT NOT NULL,
                score_details TEXT NOT NULL,  -- JSON array
                match_analysis TEXT NOT NULL,  -- JSON object
                risk_assessment TEXT NOT NULL,  -- JSON object
                interview_suggestions TEXT NOT NULL,  -- JSON object
                summary TEXT NOT NULL,
                strengths TEXT,  -- JSON array
                weaknesses TEXT,  -- JSON array
                recommendations TEXT,  -- JSON array
                analysis_version TEXT,
                model_used TEXT,
                analysis_duration REAL,
                raw_analysis_data TEXT,  -- JSON object
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes (id),
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
        """)
        
        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_resumes_status ON resumes(status)",
            "CREATE INDEX IF NOT EXISTS idx_resumes_source ON resumes(source)",
            "CREATE INDEX IF NOT EXISTS idx_resumes_created_at ON resumes(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status)",
            "CREATE INDEX IF NOT EXISTS idx_candidates_stage ON candidates(current_stage)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_score ON analysis_results(overall_score)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_recommendation ON analysis_results(recommendation_level)"
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
        
        conn.commit()
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    # ==================== 岗位管理 ====================
    
    async def create_job(self, job_data: JobCreate) -> Job:
        """创建岗位"""
        try:
            async with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO jobs (
                        title, company, department, location, job_type,
                        description, responsibilities, requirements,
                        salary_range, benefits, status, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_data.title,
                    job_data.company,
                    job_data.department,
                    job_data.location,
                    job_data.job_type.value,
                    job_data.description,
                    json.dumps(job_data.responsibilities, ensure_ascii=False),
                    json.dumps(job_data.requirements.dict(), ensure_ascii=False),
                    json.dumps(job_data.salary_range.dict() if job_data.salary_range else None, ensure_ascii=False),
                    json.dumps(job_data.benefits, ensure_ascii=False),
                    JobStatus.ACTIVE.value,
                    job_data.created_by
                ))
                
                job_id = cursor.lastrowid
                conn.commit()
                
                # 获取创建的岗位
                job = await self.get_job_by_id(job_id)
                app_logger.info(f"创建岗位成功: {job.title} (ID: {job_id})")
                
                return job
        except Exception as e:
            app_logger.error(f"创建岗位失败: {str(e)}")
            raise
    
    async def get_job_by_id(self, job_id: int) -> Optional[Job]:
        """根据ID获取岗位"""
        try:
            async with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM jobs WHERE id = ?", (job_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_job(row)
                return None
        except Exception as e:
            app_logger.error(f"获取岗位失败: {str(e)}")
            return None
    
    async def update_job(self, job_id: int, job_data: JobUpdate) -> Optional[Job]:
        """更新岗位"""
        try:
            update_fields = []
            values = []
            
            for field, value in job_data.dict(exclude_unset=True).items():
                if field == "requirements" and value:
                    update_fields.append("requirements = ?")
                    values.append(json.dumps(value.dict(), ensure_ascii=False))
                elif field == "salary_range" and value:
                    update_fields.append("salary_range = ?")
                    values.append(json.dumps(value.dict(), ensure_ascii=False))
                elif field in ["responsibilities", "benefits"] and value:
                    update_fields.append(f"{field} = ?")
                    values.append(json.dumps(value, ensure_ascii=False))
                elif field == "job_type" and value:
                    update_fields.append("job_type = ?")
                    values.append(value.value)
                elif field == "status" and value:
                    update_fields.append("status = ?")
                    values.append(value.value)
                elif value is not None:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
            
            if not update_fields:
                return await self.get_job_by_id(job_id)
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(job_id)
            
            async with self.get_connection() as conn:
                conn.execute(
                    f"UPDATE jobs SET {', '.join(update_fields)} WHERE id = ?",
                    values
                )
                conn.commit()
                
                return await self.get_job_by_id(job_id)
        except Exception as e:
            app_logger.error(f"更新岗位失败: {str(e)}")
            raise
    
    # ==================== 简历管理 ====================
    
    async def create_resume(self, resume_data: ResumeCreate) -> Resume:
        """创建简历"""
        try:
            async with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO resumes (
                        name, contact_info, summary, work_experiences, education,
                        project_experiences, skills, languages, certifications,
                        years_of_experience, current_position, current_company,
                        current_salary, salary_expectation, job_status, availability,
                        source, source_url, source_id, file_path, file_hash, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    resume_data.name,
                    json.dumps(resume_data.contact_info, ensure_ascii=False),
                    resume_data.summary,
                    json.dumps([exp.dict() for exp in resume_data.work_experiences], ensure_ascii=False),
                    json.dumps([edu.dict() for edu in resume_data.education], ensure_ascii=False),
                    json.dumps([proj.dict() for proj in resume_data.project_experiences], ensure_ascii=False),
                    json.dumps(resume_data.skills, ensure_ascii=False),
                    json.dumps(resume_data.languages, ensure_ascii=False),
                    json.dumps(resume_data.certifications, ensure_ascii=False),
                    resume_data.years_of_experience,
                    resume_data.current_position,
                    resume_data.current_company,
                    resume_data.current_salary,
                    resume_data.salary_expectation,
                    resume_data.job_status,
                    resume_data.availability,
                    resume_data.source.value,
                    resume_data.source_url,
                    resume_data.source_id,
                    resume_data.file_path,
                    resume_data.file_hash,
                    json.dumps(resume_data.raw_data, ensure_ascii=False) if resume_data.raw_data else None
                ))
                
                resume_id = cursor.lastrowid
                conn.commit()
                
                # 获取创建的简历
                resume = await self.get_resume_by_id(resume_id)
                app_logger.info(f"创建简历成功: {resume.name} (ID: {resume_id})")
                
                return resume
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                app_logger.warning(f"简历已存在: {resume_data.source.value} - {resume_data.source_id}")
                # 尝试获取已存在的简历
                existing = await self.get_resume_by_source(resume_data.source, resume_data.source_id)
                if existing:
                    return existing
            raise
        except Exception as e:
            app_logger.error(f"创建简历失败: {str(e)}")
            raise
    
    async def get_resume_by_id(self, resume_id: int) -> Optional[Resume]:
        """根据ID获取简历"""
        try:
            async with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM resumes WHERE id = ?", (resume_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_resume(row)
                return None
        except Exception as e:
            app_logger.error(f"获取简历失败: {str(e)}")
            return None
    
    async def get_resume_by_source(self, source: ResumeSource, source_id: str) -> Optional[Resume]:
        """根据来源获取简历"""
        try:
            async with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM resumes WHERE source = ? AND source_id = ?",
                    (source.value, source_id)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_resume(row)
                return None
        except Exception as e:
            app_logger.error(f"获取简历失败: {str(e)}")
            return None
    
    async def update_resume(self, resume_id: int, resume_data: ResumeUpdate) -> Optional[Resume]:
        """更新简历"""
        try:
            update_fields = []
            values = []
            
            for field, value in resume_data.dict(exclude_unset=True).items():
                if field == "contact_info" and value:
                    update_fields.append("contact_info = ?")
                    values.append(json.dumps(value, ensure_ascii=False))
                elif field == "work_experiences" and value:
                    update_fields.append("work_experiences = ?")
                    values.append(json.dumps([exp.dict() for exp in value], ensure_ascii=False))
                elif field == "education" and value:
                    update_fields.append("education = ?")
                    values.append(json.dumps([edu.dict() for edu in value], ensure_ascii=False))
                elif field == "project_experiences" and value:
                    update_fields.append("project_experiences = ?")
                    values.append(json.dumps([proj.dict() for proj in value], ensure_ascii=False))
                elif field in ["skills", "languages", "certifications"] and value:
                    update_fields.append(f"{field} = ?")
                    values.append(json.dumps(value, ensure_ascii=False))
                elif field == "status" and value:
                    update_fields.append("status = ?")
                    values.append(value.value)
                elif field == "source" and value:
                    update_fields.append("source = ?")
                    values.append(value.value)
                elif field == "raw_data" and value:
                    update_fields.append("raw_data = ?")
                    values.append(json.dumps(value, ensure_ascii=False))
                elif value is not None:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
            
            if not update_fields:
                return await self.get_resume_by_id(resume_id)
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(resume_id)
            
            async with self.get_connection() as conn:
                conn.execute(
                    f"UPDATE resumes SET {', '.join(update_fields)} WHERE id = ?",
                    values
                )
                conn.commit()
                
                return await self.get_resume_by_id(resume_id)
        except Exception as e:
            app_logger.error(f"更新简历失败: {str(e)}")
            raise
    
    async def search_resumes(self, filters: Dict[str, Any], limit: int = 50, offset: int = 0) -> Tuple[List[Resume], int]:
        """搜索简历"""
        try:
            where_conditions = []
            values = []
            
            # 构建查询条件
            if filters.get("status"):
                where_conditions.append("status = ?")
                values.append(filters["status"])
            
            if filters.get("source"):
                where_conditions.append("source = ?")
                values.append(filters["source"])
            
            if filters.get("name"):
                where_conditions.append("name LIKE ?")
                values.append(f"%{filters['name']}%")
            
            if filters.get("skills"):
                where_conditions.append("skills LIKE ?")
                values.append(f"%{filters['skills']}%")
            
            if filters.get("min_experience"):
                where_conditions.append("years_of_experience >= ?")
                values.append(filters["min_experience"])
            
            if filters.get("max_experience"):
                where_conditions.append("years_of_experience <= ?")
                values.append(filters["max_experience"])
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            async with self.get_connection() as conn:
                # 获取总数
                count_cursor = conn.execute(
                    f"SELECT COUNT(*) FROM resumes WHERE {where_clause}", values
                )
                total = count_cursor.fetchone()[0]
                
                # 获取数据
                cursor = conn.execute(
                    f"SELECT * FROM resumes WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    values + [limit, offset]
                )
                rows = cursor.fetchall()
                
                resumes = [self._row_to_resume(row) for row in rows]
                
                return resumes, total
        except Exception as e:
            app_logger.error(f"搜索简历失败: {str(e)}")
            return [], 0
    
    # ==================== 分析结果管理 ====================
    
    async def create_analysis_result(self, analysis_data: AnalysisResultCreate) -> AnalysisResult:
        """创建分析结果"""
        try:
            async with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO analysis_results (
                        resume_id, job_id, overall_score, recommendation_level,
                        score_details, match_analysis, risk_assessment,
                        interview_suggestions, summary, strengths, weaknesses,
                        recommendations, analysis_version, model_used,
                        analysis_duration, raw_analysis_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis_data.resume_id,
                    analysis_data.job_id,
                    analysis_data.overall_score,
                    analysis_data.recommendation_level.value,
                    json.dumps([detail.dict() for detail in analysis_data.score_details], ensure_ascii=False),
                    json.dumps(analysis_data.match_analysis.dict(), ensure_ascii=False),
                    json.dumps(analysis_data.risk_assessment.dict(), ensure_ascii=False),
                    json.dumps(analysis_data.interview_suggestions.dict(), ensure_ascii=False),
                    analysis_data.summary,
                    json.dumps(analysis_data.strengths, ensure_ascii=False),
                    json.dumps(analysis_data.weaknesses, ensure_ascii=False),
                    json.dumps(analysis_data.recommendations, ensure_ascii=False),
                    analysis_data.analysis_version,
                    analysis_data.model_used,
                    analysis_data.analysis_duration,
                    json.dumps(analysis_data.raw_analysis_data, ensure_ascii=False) if analysis_data.raw_analysis_data else None
                ))
                
                analysis_id = cursor.lastrowid
                conn.commit()
                
                # 获取创建的分析结果
                analysis = await self.get_analysis_result_by_id(analysis_id)
                app_logger.info(f"创建分析结果成功: Resume {analysis_data.resume_id} - Job {analysis_data.job_id} (ID: {analysis_id})")
                
                return analysis
        except Exception as e:
            app_logger.error(f"创建分析结果失败: {str(e)}")
            raise
    
    async def get_analysis_result_by_id(self, analysis_id: int) -> Optional[AnalysisResult]:
        """根据ID获取分析结果"""
        try:
            async with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM analysis_results WHERE id = ?", (analysis_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_analysis_result(row)
                return None
        except Exception as e:
            app_logger.error(f"获取分析结果失败: {str(e)}")
            return None
    
    async def get_analysis_by_resume_job(self, resume_id: int, job_id: int) -> Optional[AnalysisResult]:
        """根据简历和岗位获取分析结果"""
        try:
            async with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM analysis_results WHERE resume_id = ? AND job_id = ? ORDER BY created_at DESC LIMIT 1",
                    (resume_id, job_id)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_analysis_result(row)
                return None
        except Exception as e:
            app_logger.error(f"获取分析结果失败: {str(e)}")
            return None
    
    # ==================== 数据转换方法 ====================
    
    def _row_to_job(self, row: sqlite3.Row) -> Job:
        """将数据库行转换为Job对象"""
        from ..models.job import JobType, JobRequirements, SalaryRange
        
        requirements_data = json.loads(row["requirements"])
        requirements = JobRequirements(**requirements_data)
        
        salary_range = None
        if row["salary_range"]:
            salary_data = json.loads(row["salary_range"])
            salary_range = SalaryRange(**salary_data)
        
        return Job(
            id=row["id"],
            title=row["title"],
            company=row["company"],
            department=row["department"],
            location=row["location"],
            job_type=JobType(row["job_type"]),
            description=row["description"],
            responsibilities=json.loads(row["responsibilities"]) if row["responsibilities"] else [],
            requirements=requirements,
            salary_range=salary_range,
            benefits=json.loads(row["benefits"]) if row["benefits"] else [],
            status=JobStatus(row["status"]),
            created_by=row["created_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
    
    def _row_to_resume(self, row: sqlite3.Row) -> Resume:
        """将数据库行转换为Resume对象"""
        from ..models.resume import ContactInfo, WorkExperience, Education, ProjectExperience
        
        contact_info = ContactInfo(**json.loads(row["contact_info"]))
        
        work_experiences = []
        if row["work_experiences"]:
            for exp_data in json.loads(row["work_experiences"]):
                work_experiences.append(WorkExperience(**exp_data))
        
        education = []
        if row["education"]:
            for edu_data in json.loads(row["education"]):
                education.append(Education(**edu_data))
        
        project_experiences = []
        if row["project_experiences"]:
            for proj_data in json.loads(row["project_experiences"]):
                project_experiences.append(ProjectExperience(**proj_data))
        
        return Resume(
            id=row["id"],
            name=row["name"],
            contact_info=contact_info,
            summary=row["summary"],
            work_experiences=work_experiences,
            education=education,
            project_experiences=project_experiences,
            skills=json.loads(row["skills"]) if row["skills"] else [],
            languages=json.loads(row["languages"]) if row["languages"] else [],
            certifications=json.loads(row["certifications"]) if row["certifications"] else [],
            years_of_experience=row["years_of_experience"],
            current_position=row["current_position"],
            current_company=row["current_company"],
            current_salary=row["current_salary"],
            salary_expectation=row["salary_expectation"],
            job_status=row["job_status"],
            availability=row["availability"],
            source=ResumeSource(row["source"]),
            source_url=row["source_url"],
            source_id=row["source_id"],
            status=ResumeStatus(row["status"]),
            file_path=row["file_path"],
            file_hash=row["file_hash"],
            raw_data=json.loads(row["raw_data"]) if row["raw_data"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
    
    def _row_to_analysis_result(self, row: sqlite3.Row) -> AnalysisResult:
        """将数据库行转换为AnalysisResult对象"""
        from ..models.analysis import (
            ScoreDetail, MatchAnalysis, RiskAssessment, 
            InterviewSuggestions, RecommendationLevel
        )
        
        score_details = []
        for detail_data in json.loads(row["score_details"]):
            score_details.append(ScoreDetail(**detail_data))
        
        match_analysis = MatchAnalysis(**json.loads(row["match_analysis"]))
        risk_assessment = RiskAssessment(**json.loads(row["risk_assessment"]))
        interview_suggestions = InterviewSuggestions(**json.loads(row["interview_suggestions"]))
        
        return AnalysisResult(
            id=row["id"],
            resume_id=row["resume_id"],
            job_id=row["job_id"],
            overall_score=row["overall_score"],
            recommendation_level=RecommendationLevel(row["recommendation_level"]),
            score_details=score_details,
            match_analysis=match_analysis,
            risk_assessment=risk_assessment,
            interview_suggestions=interview_suggestions,
            summary=row["summary"],
            strengths=json.loads(row["strengths"]) if row["strengths"] else [],
            weaknesses=json.loads(row["weaknesses"]) if row["weaknesses"] else [],
            recommendations=json.loads(row["recommendations"]) if row["recommendations"] else [],
            analysis_version=row["analysis_version"],
            model_used=row["model_used"],
            analysis_duration=row["analysis_duration"],
            raw_analysis_data=json.loads(row["raw_analysis_data"]) if row["raw_analysis_data"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )


# 全局数据管理器实例
_data_manager_instance = None


def get_data_manager() -> DataManager:
    """获取数据管理器实例"""
    global _data_manager_instance
    if _data_manager_instance is None:
        _data_manager_instance = DataManager()
    return _data_manager_instance