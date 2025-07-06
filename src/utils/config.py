"""配置管理模块"""

import os
from typing import Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class SiliconFlowConfig(BaseSettings):
    """SiliconFlow API配置"""
    api_key: str = Field(..., env="SILICONFLOW_API_KEY")
    base_url: str = Field("https://api.siliconflow.cn/v1", env="SILICONFLOW_BASE_URL")
    model: str = Field("deepseek-chat", env="SILICONFLOW_MODEL")
    timeout: int = Field(30, env="SILICONFLOW_TIMEOUT")
    max_retries: int = Field(3, env="SILICONFLOW_MAX_RETRIES")


class FeishuConfig(BaseSettings):
    """飞书API配置"""
    app_id: str = Field(..., env="FEISHU_APP_ID")
    app_secret: str = Field(..., env="FEISHU_APP_SECRET")
    table_token: str = Field(..., env="FEISHU_TABLE_TOKEN")
    table_id: str = Field(..., env="FEISHU_TABLE_ID")
    base_url: str = Field("https://open.feishu.cn", env="FEISHU_BASE_URL")


class BossConfig(BaseSettings):
    """BOSS直聘配置"""
    username: str = Field(..., env="BOSS_USERNAME")
    password: str = Field(..., env="BOSS_PASSWORD")
    login_url: str = Field("https://login.zhipin.com/", env="BOSS_LOGIN_URL")
    search_url: str = Field("https://www.zhipin.com/web/geek/", env="BOSS_SEARCH_URL")


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    url: str = Field("sqlite:///./hr_system.db", env="DATABASE_URL")
    echo: bool = Field(False, env="DATABASE_ECHO")


class RedisConfig(BaseSettings):
    """Redis配置"""
    url: str = Field("redis://localhost:6379/0", env="REDIS_URL")


class RPAConfig(BaseSettings):
    """RPA配置"""
    headless_browser: bool = Field(True, env="HEADLESS_BROWSER")
    browser_timeout: int = Field(30, env="BROWSER_TIMEOUT")
    page_load_timeout: int = Field(10, env="PAGE_LOAD_TIMEOUT")
    implicit_wait: int = Field(5, env="IMPLICIT_WAIT")
    user_agent: str = Field(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        env="USER_AGENT"
    )


class ResumeConfig(BaseSettings):
    """简历处理配置"""
    max_size_mb: int = Field(10, env="MAX_RESUME_SIZE_MB")
    supported_formats: str = Field("pdf,doc,docx,html", env="SUPPORTED_FORMATS")
    batch_size: int = Field(10, env="BATCH_SIZE")
    process_interval_seconds: int = Field(5, env="PROCESS_INTERVAL_SECONDS")
    
    @property
    def supported_formats_list(self) -> list[str]:
        return [fmt.strip() for fmt in self.supported_formats.split(",")]


class AppConfig(BaseSettings):
    """应用配置"""
    name: str = Field("HR RPA System", env="APP_NAME")
    version: str = Field("1.0.0", env="APP_VERSION")
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    secret_key: str = Field(..., env="SECRET_KEY")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")


class Settings:
    """全局配置类"""
    
    def __init__(self):
        self.app = AppConfig()
        self.siliconflow = SiliconFlowConfig()
        self.feishu = FeishuConfig()
        self.boss = BossConfig()
        self.database = DatabaseConfig()
        self.redis = RedisConfig()
        self.rpa = RPAConfig()
        self.resume = ResumeConfig()


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings