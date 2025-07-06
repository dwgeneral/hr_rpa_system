"""辅助函数模块"""

import re
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import mimetypes


def generate_hash(text: str) -> str:
    """生成文本的MD5哈希值"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def clean_text(text: str) -> str:
    """清理文本，移除多余的空白字符"""
    if not text:
        return ""
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text.strip())
    # 移除特殊字符
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    return text


def extract_email(text: str) -> Optional[str]:
    """从文本中提取邮箱地址"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    return matches[0] if matches else None


def extract_phone(text: str) -> Optional[str]:
    """从文本中提取手机号码"""
    # 中国手机号码模式
    phone_patterns = [
        r'1[3-9]\d{9}',  # 11位手机号
        r'\+86[\s-]?1[3-9]\d{9}',  # 带国际区号
        r'86[\s-]?1[3-9]\d{9}',   # 带区号
    ]
    
    for pattern in phone_patterns:
        matches = re.findall(pattern, text.replace(' ', '').replace('-', ''))
        if matches:
            return matches[0]
    
    return None


def extract_name_from_filename(filename: str) -> str:
    """从文件名中提取可能的姓名"""
    # 移除文件扩展名
    name = Path(filename).stem
    
    # 移除常见的简历关键词
    keywords_to_remove = ['简历', 'resume', 'cv', '个人简历', '求职简历']
    for keyword in keywords_to_remove:
        name = re.sub(keyword, '', name, flags=re.IGNORECASE)
    
    # 清理特殊字符
    name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z\s]', '', name)
    name = clean_text(name)
    
    return name if len(name) > 1 else ""


def validate_file_type(file_path: str, allowed_types: List[str]) -> bool:
    """验证文件类型"""
    file_ext = Path(file_path).suffix.lower().lstrip('.')
    return file_ext in [ext.lower() for ext in allowed_types]


def get_file_size_mb(file_path: str) -> float:
    """获取文件大小（MB）"""
    try:
        size_bytes = Path(file_path).stat().st_size
        return size_bytes / (1024 * 1024)
    except FileNotFoundError:
        return 0.0


def get_mime_type(file_path: str) -> str:
    """获取文件MIME类型"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'


def format_datetime(dt: datetime = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间"""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime(format_str)


def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """解析日期时间字符串"""
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        return None


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """安全的JSON解析"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """安全的JSON序列化"""
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return default


def extract_years_of_experience(text: str) -> Optional[int]:
    """从文本中提取工作年限"""
    patterns = [
        r'(\d+)年.*?经验',
        r'经验.*?(\d+)年',
        r'工作.*?(\d+)年',
        r'(\d+)年.*?工作',
        r'从业.*?(\d+)年',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                return int(matches[0])
            except ValueError:
                continue
    
    return None


def extract_education_level(text: str) -> Optional[str]:
    """从文本中提取学历信息"""
    education_levels = {
        '博士': ['博士', 'PhD', 'Ph.D', '博士学位'],
        '硕士': ['硕士', '研究生', 'Master', '硕士学位'],
        '本科': ['本科', '学士', 'Bachelor', '大学本科', '学士学位'],
        '专科': ['专科', '大专', '高职', '专科学历'],
        '高中': ['高中', '中专', '技校', '职高']
    }
    
    for level, keywords in education_levels.items():
        for keyword in keywords:
            if keyword in text:
                return level
    
    return None


def extract_salary_expectation(text: str) -> Optional[Dict[str, Union[int, str]]]:
    """从文本中提取薪资期望"""
    # 匹配薪资范围模式
    patterns = [
        r'(\d+)[kK万]?[-~至到](\d+)[kK万]?',
        r'薪资.*?(\d+)[kK万]?[-~至到](\d+)[kK万]?',
        r'期望.*?(\d+)[kK万]?[-~至到](\d+)[kK万]?',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                min_salary, max_salary = matches[0]
                return {
                    'min': int(min_salary),
                    'max': int(max_salary),
                    'unit': 'k' if 'k' in text.lower() or 'K' in text else '万'
                }
            except ValueError:
                continue
    
    return None


def normalize_skill_name(skill: str) -> str:
    """标准化技能名称"""
    # 技能名称映射
    skill_mapping = {
        'js': 'JavaScript',
        'ts': 'TypeScript',
        'py': 'Python',
        'golang': 'Go',
        'reactjs': 'React',
        'vuejs': 'Vue.js',
        'nodejs': 'Node.js',
    }
    
    skill_lower = skill.lower().strip()
    return skill_mapping.get(skill_lower, skill.strip())


def calculate_text_similarity(text1: str, text2: str) -> float:
    """计算两个文本的相似度（简单的词汇重叠度）"""
    if not text1 or not text2:
        return 0.0
    
    # 分词（简单按空格分割）
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    # 计算交集和并集
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    if not union:
        return 0.0
    
    return len(intersection) / len(union)


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """截断文本到指定长度"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def is_valid_chinese_name(name: str) -> bool:
    """验证是否为有效的中文姓名"""
    if not name or len(name) < 2 or len(name) > 4:
        return False
    
    # 检查是否包含中文字符
    chinese_pattern = r'[\u4e00-\u9fa5]'
    return bool(re.search(chinese_pattern, name))


def extract_keywords(text: str, min_length: int = 2) -> List[str]:
    """从文本中提取关键词"""
    # 移除标点符号和特殊字符
    cleaned_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)
    
    # 分词
    words = cleaned_text.split()
    
    # 过滤长度和常见停用词
    stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
    
    keywords = []
    for word in words:
        if len(word) >= min_length and word.lower() not in stop_words:
            keywords.append(word)
    
    return list(set(keywords))  # 去重