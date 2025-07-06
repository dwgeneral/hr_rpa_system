"""飞书API集成模块"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.config import get_settings
from ..utils.logger import api_logger
from ..models.candidate import Candidate
from ..models.analysis import AnalysisResult

settings = get_settings()


class FeishuAPIError(Exception):
    """飞书API异常"""
    pass


class FeishuAPI:
    """飞书API客户端"""
    
    def __init__(self):
        self.app_id = settings.feishu.app_id
        self.app_secret = settings.feishu.app_secret
        self.table_token = settings.feishu.table_token
        self.table_id = settings.feishu.table_id
        self.base_url = settings.feishu.base_url
        
        self.access_token = None
        self.token_expires_at = 0
        
        self.client = httpx.AsyncClient(
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
    
    async def __aenter__(self):
        await self._ensure_access_token()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def _get_access_token(self) -> str:
        """获取访问令牌"""
        try:
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            response = await self.client.post(
                f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal",
                json=payload
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                raise FeishuAPIError(f"获取访问令牌失败: {result.get('msg')}")
            
            token = result["tenant_access_token"]
            expires_in = result.get("expire", 7200)  # 默认2小时
            
            self.access_token = token
            self.token_expires_at = time.time() + expires_in - 300  # 提前5分钟刷新
            
            api_logger.info("飞书访问令牌获取成功")
            
            return token
            
        except Exception as e:
            api_logger.error(f"获取飞书访问令牌失败: {str(e)}")
            raise FeishuAPIError(f"获取访问令牌失败: {str(e)}")
    
    async def _ensure_access_token(self):
        """确保访问令牌有效"""
        if not self.access_token or time.time() >= self.token_expires_at:
            await self._get_access_token()
            # 更新请求头
            self.client.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """发送API请求"""
        await self._ensure_access_token()
        
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("code") != 0:
                error_msg = result.get("msg", "未知错误")
                api_logger.error(f"飞书API业务错误: {error_msg}")
                raise FeishuAPIError(f"API业务错误: {error_msg}")
            
            return result
            
        except httpx.HTTPStatusError as e:
            api_logger.error(f"飞书API HTTP错误: {e.response.status_code} - {e.response.text}")
            raise FeishuAPIError(f"HTTP错误: {e.response.status_code}")
        except httpx.RequestError as e:
            api_logger.error(f"飞书API请求错误: {str(e)}")
            raise FeishuAPIError(f"网络请求失败: {str(e)}")
    
    def _format_candidate_record(self, candidate: Candidate, analysis: Optional[AnalysisResult] = None) -> Dict[str, Any]:
        """格式化候选人记录"""
        # 基本信息
        record = {
            "姓名": candidate.name,
            "邮箱": candidate.email or "",
            "手机号": candidate.phone or "",
            "所在地": candidate.location or "",
            "简历来源": candidate.source,
            "当前公司": candidate.current_company or "",
            "当前职位": candidate.current_position or "",
            "工作年限": candidate.years_of_experience or 0,
            "学历": candidate.education_level or "",
            "期望薪资": candidate.expected_salary or 0,
            "候选人状态": candidate.status.value,
            "优先级": candidate.priority,
            "标签": ",".join(candidate.tags) if candidate.tags else "",
            "备注": candidate.notes or "",
            "招聘负责人": candidate.recruiter or "",
            "创建时间": candidate.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "更新时间": candidate.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 分析结果
        if analysis:
            record.update({
                "AI总分": analysis.overall_score,
                "推荐等级": analysis.recommendation_level.value,
                "技能匹配度": self._get_dimension_score(analysis, "skill_match"),
                "经验相关性": self._get_dimension_score(analysis, "experience_relevance"),
                "教育背景": self._get_dimension_score(analysis, "education_background"),
                "项目经验": self._get_dimension_score(analysis, "project_experience"),
                "工作稳定性": self._get_dimension_score(analysis, "work_stability"),
                "审查报告": analysis.summary,
                "优势": ",".join(analysis.strengths) if analysis.strengths else "",
                "劣势": ",".join(analysis.weaknesses) if analysis.weaknesses else "",
                "建议": ",".join(analysis.recommendations) if analysis.recommendations else "",
                "风险等级": analysis.risk_assessment.overall_risk,
                "分析时间": analysis.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return record
    
    def _get_dimension_score(self, analysis: AnalysisResult, dimension: str) -> float:
        """获取指定维度的评分"""
        for detail in analysis.score_details:
            if detail.dimension.value == dimension:
                return detail.score
        return 0.0
    
    async def create_record(self, candidate: Candidate, analysis: Optional[AnalysisResult] = None) -> str:
        """创建记录"""
        try:
            record_data = self._format_candidate_record(candidate, analysis)
            
            payload = {
                "fields": record_data
            }
            
            url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.table_token}/tables/{self.table_id}/records"
            
            result = await self._make_request("POST", url, json=payload)
            
            record_id = result["data"]["record"]["record_id"]
            
            api_logger.info(f"飞书记录创建成功: {candidate.name} - {record_id}")
            
            return record_id
            
        except Exception as e:
            api_logger.error(f"创建飞书记录失败: {str(e)}")
            raise
    
    async def update_record(self, record_id: str, candidate: Candidate, analysis: Optional[AnalysisResult] = None) -> bool:
        """更新记录"""
        try:
            record_data = self._format_candidate_record(candidate, analysis)
            
            payload = {
                "fields": record_data
            }
            
            url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.table_token}/tables/{self.table_id}/records/{record_id}"
            
            await self._make_request("PUT", url, json=payload)
            
            api_logger.info(f"飞书记录更新成功: {candidate.name} - {record_id}")
            
            return True
            
        except Exception as e:
            api_logger.error(f"更新飞书记录失败: {str(e)}")
            raise
    
    async def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取记录"""
        try:
            url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.table_token}/tables/{self.table_id}/records/{record_id}"
            
            result = await self._make_request("GET", url)
            
            return result["data"]["record"]
            
        except Exception as e:
            api_logger.error(f"获取飞书记录失败: {str(e)}")
            return None
    
    async def search_records(self, filter_condition: Optional[str] = None, page_size: int = 100) -> List[Dict[str, Any]]:
        """搜索记录"""
        try:
            params = {
                "page_size": page_size
            }
            
            if filter_condition:
                params["filter"] = filter_condition
            
            url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.table_token}/tables/{self.table_id}/records"
            
            result = await self._make_request("GET", url, params=params)
            
            records = result["data"]["items"]
            
            api_logger.info(f"飞书记录搜索完成，找到{len(records)}条记录")
            
            return records
            
        except Exception as e:
            api_logger.error(f"搜索飞书记录失败: {str(e)}")
            return []
    
    async def delete_record(self, record_id: str) -> bool:
        """删除记录"""
        try:
            url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.table_token}/tables/{self.table_id}/records/{record_id}"
            
            await self._make_request("DELETE", url)
            
            api_logger.info(f"飞书记录删除成功: {record_id}")
            
            return True
            
        except Exception as e:
            api_logger.error(f"删除飞书记录失败: {str(e)}")
            return False
    
    async def batch_create_records(self, candidates_with_analysis: List[tuple[Candidate, Optional[AnalysisResult]]]) -> List[str]:
        """批量创建记录"""
        try:
            records_data = []
            for candidate, analysis in candidates_with_analysis:
                record_data = self._format_candidate_record(candidate, analysis)
                records_data.append({"fields": record_data})
            
            # 飞书API限制每次最多500条记录
            batch_size = 500
            all_record_ids = []
            
            for i in range(0, len(records_data), batch_size):
                batch = records_data[i:i + batch_size]
                
                payload = {
                    "records": batch
                }
                
                url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.table_token}/tables/{self.table_id}/records/batch_create"
                
                result = await self._make_request("POST", url, json=payload)
                
                batch_record_ids = [record["record_id"] for record in result["data"]["records"]]
                all_record_ids.extend(batch_record_ids)
            
            api_logger.info(f"飞书批量记录创建成功，共{len(all_record_ids)}条")
            
            return all_record_ids
            
        except Exception as e:
            api_logger.error(f"批量创建飞书记录失败: {str(e)}")
            raise
    
    async def get_table_fields(self) -> List[Dict[str, Any]]:
        """获取表格字段信息"""
        try:
            url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.table_token}/tables/{self.table_id}/fields"
            
            result = await self._make_request("GET", url)
            
            fields = result["data"]["items"]
            
            api_logger.info(f"获取飞书表格字段成功，共{len(fields)}个字段")
            
            return fields
            
        except Exception as e:
            api_logger.error(f"获取飞书表格字段失败: {str(e)}")
            return []
    
    async def sync_candidate_status(self, candidate_id: int, new_status: str, notes: Optional[str] = None) -> bool:
        """同步候选人状态到飞书"""
        try:
            # 根据候选人ID查找对应的飞书记录
            filter_condition = f'CurrentValue.[候选人ID] = "{candidate_id}"'
            records = await self.search_records(filter_condition)
            
            if not records:
                api_logger.warning(f"未找到候选人ID为{candidate_id}的飞书记录")
                return False
            
            record_id = records[0]["record_id"]
            
            # 更新状态
            update_data = {
                "候选人状态": new_status,
                "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if notes:
                update_data["备注"] = notes
            
            payload = {
                "fields": update_data
            }
            
            url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.table_token}/tables/{self.table_id}/records/{record_id}"
            
            await self._make_request("PUT", url, json=payload)
            
            api_logger.info(f"候选人状态同步成功: {candidate_id} -> {new_status}")
            
            return True
            
        except Exception as e:
            api_logger.error(f"同步候选人状态失败: {str(e)}")
            return False
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 全局API实例
_feishu_api_instance = None


async def get_feishu_api() -> FeishuAPI:
    """获取飞书API实例"""
    global _feishu_api_instance
    if _feishu_api_instance is None:
        _feishu_api_instance = FeishuAPI()
    return _feishu_api_instance


async def close_feishu_api():
    """关闭飞书API实例"""
    global _feishu_api_instance
    if _feishu_api_instance:
        await _feishu_api_instance.close()
        _feishu_api_instance = None