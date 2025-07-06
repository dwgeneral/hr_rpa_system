"""SiliconFlow API集成模块"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.config import get_settings
from ..utils.logger import ai_logger
from ..models.analysis import (
    ScoreDetail, ScoreDimension, MatchAnalysis, RiskAssessment,
    InterviewSuggestions, RecommendationLevel
)

settings = get_settings()


class SiliconFlowAPIError(Exception):
    """SiliconFlow API异常"""
    pass


class SiliconFlowAPI:
    """SiliconFlow API客户端"""
    
    def __init__(self):
        self.api_key = settings.siliconflow.api_key
        self.base_url = settings.siliconflow.base_url
        self.model = settings.siliconflow.model
        self.timeout = settings.siliconflow.timeout
        self.max_retries = settings.siliconflow.max_retries
        
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """发送API请求"""
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.1),
                "max_tokens": kwargs.get("max_tokens", 4000),
                "top_p": kwargs.get("top_p", 0.9),
                "stream": False
            }
            
            ai_logger.info(f"发送SiliconFlow API请求: {self.model}")
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            response.raise_for_status()
            result = response.json()
            
            ai_logger.info(f"SiliconFlow API响应成功, tokens: {result.get('usage', {})}")
            
            return result
            
        except httpx.HTTPStatusError as e:
            ai_logger.error(f"SiliconFlow API HTTP错误: {e.response.status_code} - {e.response.text}")
            raise SiliconFlowAPIError(f"API请求失败: {e.response.status_code}")
        except httpx.RequestError as e:
            ai_logger.error(f"SiliconFlow API请求错误: {str(e)}")
            raise SiliconFlowAPIError(f"网络请求失败: {str(e)}")
        except Exception as e:
            ai_logger.error(f"SiliconFlow API未知错误: {str(e)}")
            raise SiliconFlowAPIError(f"未知错误: {str(e)}")
    
    def _build_analysis_prompt(self, resume_text: str, job_description: str) -> str:
        """构建分析提示词"""
        prompt = f"""
你是一个专业的HR简历分析专家。请根据以下岗位描述(JD)和候选人简历，进行详细的匹配度分析。

## 岗位描述(JD):
{job_description}

## 候选人简历:
{resume_text}

## 分析要求:
请从以下10个维度进行评分分析(每个维度0-10分):

1. **技能匹配度** (权重25%): 核心技能与JD要求的匹配程度
2. **经验相关性** (权重20%): 工作经验与岗位的相关度
3. **教育背景** (权重15%): 学历和专业匹配度
4. **项目经验** (权重15%): 相关项目经验的质量
5. **工作稳定性** (权重10%): 工作连续性和稳定性
6. **薪资期望** (权重5%): 薪资期望的合理性
7. **地理位置** (权重3%): 工作地点匹配度
8. **语言能力** (权重3%): 语言要求匹配度
9. **证书资质** (权重2%): 相关证书和资质
10. **其他加分项** (权重2%): 特殊技能或经验

## 输出格式:
请严格按照以下JSON格式输出分析结果:

```json
{{
  "overall_score": 8.5,
  "recommendation_level": "highly_recommended",
  "score_details": [
    {{
      "dimension": "skill_match",
      "score": 9.0,
      "weight": 0.25,
      "explanation": "候选人掌握的技能与岗位要求高度匹配",
      "evidence": ["精通Python", "熟悉机器学习"],
      "suggestions": ["可以进一步了解深度学习"]
    }}
    // ... 其他9个维度
  ],
  "match_analysis": {{
    "matched_skills": ["Python", "机器学习"],
    "missing_skills": ["深度学习"],
    "extra_skills": ["数据可视化"],
    "skill_match_rate": 0.85,
    "experience_match": true,
    "experience_gap": null,
    "education_match": true,
    "education_gap": null,
    "location_match": true,
    "location_note": null
  }},
  "risk_assessment": {{
    "overall_risk": "low",
    "risk_factors": [],
    "job_hopping_risk": 0.2,
    "salary_risk": 0.1,
    "skill_gap_risk": 0.3,
    "culture_fit_risk": 0.2,
    "mitigation_strategies": ["提供技能培训"]
  }},
  "interview_suggestions": {{
    "recommended_questions": ["请介绍一下您的Python项目经验"],
    "focus_areas": ["技术深度", "项目管理能力"],
    "technical_assessment": ["编程测试"],
    "behavioral_assessment": ["团队协作能力"],
    "red_flags": []
  }},
  "summary": "候选人整体匹配度较高，技能和经验都符合要求",
  "strengths": ["技术能力强", "项目经验丰富"],
  "weaknesses": ["缺少深度学习经验"],
  "recommendations": ["建议进入面试流程"]
}}
```

## 注意事项:
1. recommendation_level只能是: "highly_recommended", "recommended", "not_recommended", "needs_review"
2. dimension只能是: "skill_match", "experience_relevance", "education_background", "project_experience", "work_stability", "salary_expectation", "location_match", "language_ability", "certifications", "bonus_points"
3. overall_risk只能是: "low", "medium", "high"
4. 所有评分都是0-10分，权重是0-1之间的小数
5. 请确保JSON格式正确，可以被解析

请开始分析:
"""
        return prompt
    
    async def analyze_resume(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """分析简历匹配度"""
        try:
            prompt = self._build_analysis_prompt(resume_text, job_description)
            
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的HR简历分析专家，擅长根据岗位要求分析候选人简历的匹配度。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await self._make_request(messages, temperature=0.1)
            
            # 提取AI回复内容
            content = response["choices"][0]["message"]["content"]
            
            # 尝试解析JSON
            try:
                # 提取JSON部分
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                
                if json_start == -1 or json_end == 0:
                    raise ValueError("未找到JSON格式的分析结果")
                
                json_content = content[json_start:json_end]
                analysis_result = json.loads(json_content)
                
                # 验证必要字段
                required_fields = [
                    'overall_score', 'recommendation_level', 'score_details',
                    'match_analysis', 'risk_assessment', 'interview_suggestions',
                    'summary', 'strengths', 'weaknesses', 'recommendations'
                ]
                
                for field in required_fields:
                    if field not in analysis_result:
                        raise ValueError(f"分析结果缺少必要字段: {field}")
                
                ai_logger.info(f"简历分析完成，综合得分: {analysis_result['overall_score']}")
                
                return analysis_result
                
            except json.JSONDecodeError as e:
                ai_logger.error(f"解析AI分析结果JSON失败: {str(e)}")
                ai_logger.error(f"原始内容: {content}")
                raise SiliconFlowAPIError(f"AI返回的分析结果格式错误: {str(e)}")
            
        except Exception as e:
            ai_logger.error(f"简历分析失败: {str(e)}")
            raise
    
    async def extract_resume_info(self, resume_text: str) -> Dict[str, Any]:
        """提取简历结构化信息"""
        try:
            prompt = f"""
请从以下简历文本中提取结构化信息:

{resume_text}

请按照以下JSON格式输出:

```json
{{
  "name": "张三",
  "contact_info": {{
    "email": "zhangsan@example.com",
    "phone": "13800138000",
    "location": "北京市"
  }},
  "summary": "5年Python开发经验...",
  "work_experiences": [
    {{
      "company": "ABC公司",
      "position": "高级工程师",
      "start_date": "2020-01",
      "end_date": "2023-12",
      "description": "负责后端开发...",
      "responsibilities": ["开发API", "数据库设计"],
      "achievements": ["提升性能30%"]
    }}
  ],
  "education": [
    {{
      "school": "清华大学",
      "major": "计算机科学",
      "degree": "本科",
      "start_date": "2016-09",
      "end_date": "2020-06"
    }}
  ],
  "skills": ["Python", "Django", "MySQL"],
  "years_of_experience": 5,
  "keywords": ["Python", "后端开发", "API"]
}}
```

注意:
1. 如果某些信息无法提取，请设置为null或空数组
2. 确保JSON格式正确
3. 工作年限请根据工作经历计算
"""
            
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的简历信息提取专家，擅长从简历文本中提取结构化信息。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await self._make_request(messages, temperature=0.1)
            content = response["choices"][0]["message"]["content"]
            
            # 解析JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("未找到JSON格式的提取结果")
            
            json_content = content[json_start:json_end]
            extracted_info = json.loads(json_content)
            
            ai_logger.info(f"简历信息提取完成: {extracted_info.get('name', 'Unknown')}")
            
            return extracted_info
            
        except Exception as e:
            ai_logger.error(f"简历信息提取失败: {str(e)}")
            raise
    
    async def generate_interview_questions(self, resume_text: str, job_description: str, focus_areas: List[str] = None) -> List[str]:
        """生成面试问题"""
        try:
            focus_text = ""
            if focus_areas:
                focus_text = f"\n重点关注领域: {', '.join(focus_areas)}"
            
            prompt = f"""
根据以下岗位描述和候选人简历，生成10个有针对性的面试问题:

## 岗位描述:
{job_description}

## 候选人简历:
{resume_text}{focus_text}

请生成包含以下类型的问题:
1. 技术能力相关问题 (3-4个)
2. 项目经验相关问题 (2-3个)
3. 行为面试问题 (2-3个)
4. 情景假设问题 (1-2个)

请按照以下JSON格式输出:

```json
{{
  "questions": [
    "请详细介绍一下您在XX项目中的技术架构设计",
    "遇到技术难题时，您是如何解决的？请举个具体例子",
    "..."
  ]
}}
```
"""
            
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的面试官，擅长根据岗位要求和候选人背景设计有针对性的面试问题。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await self._make_request(messages, temperature=0.3)
            content = response["choices"][0]["message"]["content"]
            
            # 解析JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("未找到JSON格式的问题列表")
            
            json_content = content[json_start:json_end]
            result = json.loads(json_content)
            
            questions = result.get('questions', [])
            
            ai_logger.info(f"生成面试问题完成，共{len(questions)}个问题")
            
            return questions
            
        except Exception as e:
            ai_logger.error(f"生成面试问题失败: {str(e)}")
            raise
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 全局API实例
_api_instance = None


async def get_siliconflow_api() -> SiliconFlowAPI:
    """获取SiliconFlow API实例"""
    global _api_instance
    if _api_instance is None:
        _api_instance = SiliconFlowAPI()
    return _api_instance


async def close_siliconflow_api():
    """关闭API实例"""
    global _api_instance
    if _api_instance:
        await _api_instance.close()
        _api_instance = None