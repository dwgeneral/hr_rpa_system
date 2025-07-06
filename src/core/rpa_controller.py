"""RPA控制器核心模块"""

import asyncio
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime, timedelta
import time
import random

from ..integrations.boss_api import get_boss_rpa, BossRPAError
from ..models.resume import Resume, ResumeCreate, ResumeSource, ResumeStatus
from ..models.job import Job
from ..utils.logger import rpa_logger
from ..utils.helpers import extract_email, extract_phone, extract_name, clean_text


class RPAController:
    """RPA控制器"""
    
    def __init__(self):
        self.is_running = False
        self.current_session = None
        self.stats = {
            "total_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "start_time": None,
            "last_activity": None
        }
        self.callbacks = {
            "on_resume_found": [],
            "on_extraction_complete": [],
            "on_error": [],
            "on_session_complete": []
        }
    
    def add_callback(self, event: str, callback: Callable):
        """添加回调函数"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def remove_callback(self, event: str, callback: Callable):
        """移除回调函数"""
        if event in self.callbacks and callback in self.callbacks[event]:
            self.callbacks[event].remove(callback)
    
    async def _trigger_callback(self, event: str, *args, **kwargs):
        """触发回调函数"""
        for callback in self.callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                rpa_logger.error(f"回调函数执行失败: {event} - {str(e)}")
    
    async def start_resume_collection(self, job: Job, search_params: Dict[str, Any], max_resumes: int = 100) -> List[Resume]:
        """开始简历收集"""
        try:
            if self.is_running:
                raise ValueError("RPA控制器已在运行中")
            
            self.is_running = True
            self.stats["start_time"] = datetime.now()
            self.stats["total_processed"] = 0
            self.stats["successful_extractions"] = 0
            self.stats["failed_extractions"] = 0
            
            rpa_logger.info(f"开始收集简历: {job.title} - 最大数量: {max_resumes}")
            
            collected_resumes = []
            
            async with await get_boss_rpa() as rpa:
                # 登录
                await rpa.login()
                rpa_logger.info("BOSS直聘登录成功")
                
                # 搜索简历
                await rpa.search_resumes(search_params)
                rpa_logger.info(f"开始搜索简历: {search_params}")
                
                page = 1
                consecutive_failures = 0
                max_consecutive_failures = 3
                
                while len(collected_resumes) < max_resumes and consecutive_failures < max_consecutive_failures:
                    try:
                        rpa_logger.info(f"处理第{page}页简历列表")
                        
                        # 获取当前页简历列表
                        resume_list = await rpa.get_resume_list()
                        
                        if not resume_list:
                            rpa_logger.warning(f"第{page}页没有找到简历")
                            consecutive_failures += 1
                            break
                        
                        # 处理每个简历
                        page_resumes = await self._process_resume_list(
                            rpa, resume_list, job, max_resumes - len(collected_resumes)
                        )
                        
                        collected_resumes.extend(page_resumes)
                        consecutive_failures = 0  # 重置失败计数
                        
                        rpa_logger.info(
                            f"第{page}页处理完成: 获取{len(page_resumes)}份简历, "
                            f"总计{len(collected_resumes)}份"
                        )
                        
                        # 检查是否达到目标数量
                        if len(collected_resumes) >= max_resumes:
                            break
                        
                        # 尝试翻页
                        if await rpa.go_to_next_page():
                            page += 1
                            # 随机等待，避免被检测
                            await asyncio.sleep(random.uniform(2, 5))
                        else:
                            rpa_logger.info("已到达最后一页")
                            break
                            
                    except Exception as e:
                        rpa_logger.error(f"处理第{page}页时出错: {str(e)}")
                        consecutive_failures += 1
                        await self._trigger_callback("on_error", e, page)
                        
                        # 等待后重试
                        await asyncio.sleep(random.uniform(5, 10))
            
            # 更新统计信息
            self.stats["last_activity"] = datetime.now()
            duration = (self.stats["last_activity"] - self.stats["start_time"]).total_seconds()
            
            rpa_logger.info(
                f"简历收集完成: 总计{len(collected_resumes)}份简历, "
                f"成功{self.stats['successful_extractions']}份, "
                f"失败{self.stats['failed_extractions']}份, "
                f"耗时{duration:.2f}秒"
            )
            
            await self._trigger_callback("on_session_complete", collected_resumes, self.stats)
            
            return collected_resumes
            
        except Exception as e:
            rpa_logger.error(f"简历收集失败: {str(e)}")
            await self._trigger_callback("on_error", e)
            raise
        finally:
            self.is_running = False
    
    async def _process_resume_list(self, rpa, resume_list: List[Dict[str, Any]], job: Job, max_count: int) -> List[Resume]:
        """处理简历列表"""
        processed_resumes = []
        
        for i, resume_item in enumerate(resume_list[:max_count]):
            try:
                self.stats["total_processed"] += 1
                
                rpa_logger.info(f"处理简历 {i+1}/{len(resume_list)}: {resume_item.get('name', 'Unknown')}")
                
                # 点击进入简历详情页
                await rpa.click_resume_item(resume_item)
                
                # 等待页面加载
                await asyncio.sleep(random.uniform(1, 3))
                
                # 提取简历详情
                resume_detail = await rpa.extract_resume_detail()
                
                if resume_detail:
                    # 转换为Resume对象
                    resume = await self._convert_to_resume(resume_detail, job)
                    
                    if resume:
                        processed_resumes.append(resume)
                        self.stats["successful_extractions"] += 1
                        
                        await self._trigger_callback("on_resume_found", resume)
                        
                        rpa_logger.info(f"成功提取简历: {resume.name}")
                    else:
                        self.stats["failed_extractions"] += 1
                        rpa_logger.warning(f"简历数据转换失败: {resume_item.get('name')}")
                else:
                    self.stats["failed_extractions"] += 1
                    rpa_logger.warning(f"简历详情提取失败: {resume_item.get('name')}")
                
                # 返回列表页
                await rpa.go_back_to_list()
                
                # 随机等待
                await asyncio.sleep(random.uniform(1, 3))
                
                await self._trigger_callback("on_extraction_complete", resume_item, len(processed_resumes))
                
            except Exception as e:
                self.stats["failed_extractions"] += 1
                rpa_logger.error(f"处理简历失败: {resume_item.get('name', 'Unknown')} - {str(e)}")
                await self._trigger_callback("on_error", e, resume_item)
                
                # 尝试恢复到列表页
                try:
                    await rpa.go_back_to_list()
                except:
                    pass
                
                # 等待后继续
                await asyncio.sleep(random.uniform(2, 5))
        
        return processed_resumes
    
    async def _convert_to_resume(self, resume_detail: Dict[str, Any], job: Job) -> Optional[Resume]:
        """将RPA提取的数据转换为Resume对象"""
        try:
            # 提取基本信息
            name = resume_detail.get("name") or "Unknown"
            
            # 提取联系信息
            contact_info = {
                "email": extract_email(resume_detail.get("contact", "")),
                "phone": extract_phone(resume_detail.get("contact", "")),
                "location": resume_detail.get("location"),
                "address": resume_detail.get("address")
            }
            
            # 处理工作经历
            work_experiences = []
            for exp in resume_detail.get("work_experiences", []):
                work_exp = {
                    "company": exp.get("company"),
                    "position": exp.get("position"),
                    "start_date": exp.get("start_date"),
                    "end_date": exp.get("end_date"),
                    "description": clean_text(exp.get("description", "")),
                    "responsibilities": exp.get("responsibilities", []),
                    "achievements": exp.get("achievements", []),
                    "industry": exp.get("industry"),
                    "company_size": exp.get("company_size")
                }
                work_experiences.append(work_exp)
            
            # 处理教育背景
            education = []
            for edu in resume_detail.get("education", []):
                education_item = {
                    "school": edu.get("school"),
                    "major": edu.get("major"),
                    "degree": edu.get("degree"),
                    "start_date": edu.get("start_date"),
                    "end_date": edu.get("end_date"),
                    "gpa": edu.get("gpa"),
                    "honors": edu.get("honors", [])
                }
                education.append(education_item)
            
            # 处理项目经验
            project_experiences = []
            for proj in resume_detail.get("projects", []):
                project = {
                    "name": proj.get("name"),
                    "role": proj.get("role"),
                    "start_date": proj.get("start_date"),
                    "end_date": proj.get("end_date"),
                    "description": clean_text(proj.get("description", "")),
                    "technologies": proj.get("technologies", []),
                    "achievements": proj.get("achievements", []),
                    "url": proj.get("url")
                }
                project_experiences.append(project)
            
            # 创建Resume对象
            resume_create = ResumeCreate(
                name=name,
                contact_info=contact_info,
                summary=clean_text(resume_detail.get("summary", "")),
                work_experiences=work_experiences,
                education=education,
                project_experiences=project_experiences,
                skills=resume_detail.get("skills", []),
                languages=resume_detail.get("languages", []),
                certifications=resume_detail.get("certifications", []),
                years_of_experience=resume_detail.get("years_of_experience"),
                current_position=resume_detail.get("current_position"),
                current_company=resume_detail.get("current_company"),
                current_salary=resume_detail.get("current_salary"),
                salary_expectation=resume_detail.get("salary_expectation"),
                job_status=resume_detail.get("job_status"),
                availability=resume_detail.get("availability"),
                source=ResumeSource.BOSS_ZHIPIN,
                source_url=resume_detail.get("source_url"),
                source_id=resume_detail.get("source_id"),
                raw_data=resume_detail
            )
            
            # 转换为Resume对象（添加默认字段）
            resume = Resume(
                id=0,  # 将在数据库保存时设置
                status=ResumeStatus.PENDING,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                **resume_create.dict()
            )
            
            return resume
            
        except Exception as e:
            rpa_logger.error(f"转换简历数据失败: {str(e)}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        
        if stats["start_time"]:
            if self.is_running:
                stats["duration"] = (datetime.now() - stats["start_time"]).total_seconds()
            elif stats["last_activity"]:
                stats["duration"] = (stats["last_activity"] - stats["start_time"]).total_seconds()
            
            # 计算效率指标
            if stats.get("duration", 0) > 0:
                stats["resumes_per_minute"] = round(stats["total_processed"] / (stats["duration"] / 60), 2)
                stats["success_rate"] = round(stats["successful_extractions"] / max(stats["total_processed"], 1) * 100, 2)
        
        stats["is_running"] = self.is_running
        
        return stats
    
    async def stop(self):
        """停止RPA控制器"""
        if self.is_running:
            rpa_logger.info("正在停止RPA控制器...")
            self.is_running = False
            
            # 等待当前操作完成
            await asyncio.sleep(1)
            
            rpa_logger.info("RPA控制器已停止")
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "start_time": None,
            "last_activity": None
        }
        rpa_logger.info("统计信息已重置")


# 全局控制器实例
_controller_instance = None


def get_rpa_controller() -> RPAController:
    """获取RPA控制器实例"""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = RPAController()
    return _controller_instance