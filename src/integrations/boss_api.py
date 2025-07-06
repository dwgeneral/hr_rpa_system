"""BOSS直聘API集成模块"""

import asyncio
import random
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from ..utils.config import get_settings
from ..utils.logger import rpa_logger
from ..utils.helpers import clean_text, extract_email, extract_phone, extract_name_from_filename
from ..models.resume import ResumeSource

settings = get_settings()


class BossRPAError(Exception):
    """BOSS直聘RPA异常"""
    pass


class BossRPA:
    """BOSS直聘RPA客户端"""
    
    def __init__(self):
        self.username = settings.boss.username
        self.password = settings.boss.password
        self.login_url = settings.boss.login_url
        self.search_url = settings.boss.search_url
        
        self.driver = None
        self.wait = None
        self.is_logged_in = False
        
        # 反爬虫配置
        self.min_delay = 2
        self.max_delay = 5
        self.page_load_timeout = settings.rpa.page_load_timeout
        self.implicit_wait = settings.rpa.implicit_wait
    
    async def __aenter__(self):
        await self.init_driver()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def init_driver(self):
        """初始化浏览器驱动"""
        try:
            chrome_options = Options()
            
            if settings.rpa.headless_browser:
                chrome_options.add_argument('--headless')
            
            # 反检测配置
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 设置User-Agent
            chrome_options.add_argument(f'--user-agent={settings.rpa.user_agent}')
            
            # 禁用图片加载以提高速度
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # 自动下载ChromeDriver
            service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 执行反检测脚本
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.driver.implicitly_wait(self.implicit_wait)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            
            self.wait = WebDriverWait(self.driver, 10)
            
            rpa_logger.info("浏览器驱动初始化成功")
            
        except Exception as e:
            rpa_logger.error(f"初始化浏览器驱动失败: {str(e)}")
            raise BossRPAError(f"初始化浏览器失败: {str(e)}")
    
    async def _random_delay(self, min_seconds: float = None, max_seconds: float = None):
        """随机延时"""
        min_delay = min_seconds or self.min_delay
        max_delay = max_seconds or self.max_delay
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    async def _simulate_human_behavior(self):
        """模拟人类行为"""
        # 随机滚动页面
        scroll_height = random.randint(200, 800)
        self.driver.execute_script(f"window.scrollBy(0, {scroll_height});")
        await self._random_delay(0.5, 1.5)
        
        # 随机鼠标移动
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)
            actions.move_by_offset(random.randint(-100, 100), random.randint(-100, 100))
            actions.perform()
        except:
            pass
    
    async def login(self) -> bool:
        """登录BOSS直聘"""
        try:
            rpa_logger.info("开始登录BOSS直聘")
            
            self.driver.get(self.login_url)
            await self._random_delay()
            
            # 等待登录页面加载
            try:
                # 尝试找到用户名输入框
                username_input = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[name='username'], input[placeholder*='手机'], input[placeholder*='邮箱']"))
                )
                
                # 模拟人类输入
                username_input.clear()
                for char in self.username:
                    username_input.send_keys(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                
                await self._random_delay(0.5, 1.0)
                
                # 找到密码输入框
                password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
                password_input.clear()
                for char in self.password:
                    password_input.send_keys(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                
                await self._random_delay(1.0, 2.0)
                
                # 点击登录按钮
                login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .btn-login, .login-btn")
                login_button.click()
                
                await self._random_delay(3.0, 5.0)
                
                # 检查是否需要验证码
                if "验证码" in self.driver.page_source or "captcha" in self.driver.page_source.lower():
                    rpa_logger.warning("检测到验证码，需要人工处理")
                    # 等待用户手动处理验证码
                    input("请手动完成验证码验证，然后按回车继续...")
                
                # 检查登录是否成功
                await self._random_delay(2.0, 3.0)
                
                if "个人中心" in self.driver.page_source or "我的简历" in self.driver.page_source:
                    self.is_logged_in = True
                    rpa_logger.info("BOSS直聘登录成功")
                    return True
                else:
                    rpa_logger.error("BOSS直聘登录失败")
                    return False
                    
            except TimeoutException:
                rpa_logger.error("登录页面加载超时")
                return False
                
        except Exception as e:
            rpa_logger.error(f"登录过程中发生错误: {str(e)}")
            return False
    
    async def search_resumes(self, keywords: str, location: str = "", experience: str = "", education: str = "", page_limit: int = 5) -> List[Dict[str, Any]]:
        """搜索简历"""
        try:
            if not self.is_logged_in:
                if not await self.login():
                    raise BossRPAError("登录失败，无法搜索简历")
            
            rpa_logger.info(f"开始搜索简历: {keywords}")
            
            # 构建搜索URL
            search_params = {
                "query": keywords,
                "city": location,
                "experience": experience,
                "degree": education
            }
            
            # 过滤空参数
            search_params = {k: v for k, v in search_params.items() if v}
            
            # 访问搜索页面
            self.driver.get(self.search_url)
            await self._random_delay()
            
            # 输入搜索关键词
            try:
                search_input = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='搜索'], .search-input, input[name='query']"))
                )
                search_input.clear()
                search_input.send_keys(keywords)
                
                # 点击搜索按钮
                search_button = self.driver.find_element(By.CSS_SELECTOR, ".search-btn, button[type='submit'], .btn-search")
                search_button.click()
                
                await self._random_delay(2.0, 4.0)
                
            except (TimeoutException, NoSuchElementException):
                rpa_logger.warning("未找到搜索框，尝试直接解析页面")
            
            all_resumes = []
            
            # 遍历搜索结果页面
            for page in range(1, page_limit + 1):
                rpa_logger.info(f"正在抓取第{page}页简历")
                
                # 解析当前页面的简历列表
                resumes = await self._parse_resume_list()
                all_resumes.extend(resumes)
                
                # 模拟人类行为
                await self._simulate_human_behavior()
                
                # 尝试翻页
                if page < page_limit:
                    if not await self._go_to_next_page():
                        rpa_logger.info("已到达最后一页或翻页失败")
                        break
                
                await self._random_delay(3.0, 6.0)
            
            rpa_logger.info(f"简历搜索完成，共找到{len(all_resumes)}份简历")
            
            return all_resumes
            
        except Exception as e:
            rpa_logger.error(f"搜索简历失败: {str(e)}")
            raise
    
    async def _parse_resume_list(self) -> List[Dict[str, Any]]:
        """解析简历列表页面"""
        try:
            resumes = []
            
            # 等待页面加载
            await self._random_delay(1.0, 2.0)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 查找简历卡片（需要根据实际页面结构调整选择器）
            resume_cards = soup.find_all(['div', 'li'], class_=lambda x: x and any(keyword in x.lower() for keyword in ['resume', 'geek', 'talent', 'card']))
            
            for card in resume_cards:
                try:
                    resume_data = await self._extract_resume_from_card(card)
                    if resume_data:
                        resumes.append(resume_data)
                except Exception as e:
                    rpa_logger.warning(f"解析简历卡片失败: {str(e)}")
                    continue
            
            return resumes
            
        except Exception as e:
            rpa_logger.error(f"解析简历列表失败: {str(e)}")
            return []
    
    async def _extract_resume_from_card(self, card) -> Optional[Dict[str, Any]]:
        """从简历卡片中提取信息"""
        try:
            resume_data = {
                "source": ResumeSource.BOSS.value,
                "source_url": self.driver.current_url,
                "raw_text": clean_text(card.get_text()),
                "extracted_at": datetime.now().isoformat()
            }
            
            # 提取姓名
            name_elem = card.find(['h3', 'h4', 'span'], class_=lambda x: x and 'name' in x.lower())
            if name_elem:
                resume_data["name"] = clean_text(name_elem.get_text())
            
            # 提取职位
            position_elem = card.find(['div', 'span'], class_=lambda x: x and any(keyword in x.lower() for keyword in ['position', 'title', 'job']))
            if position_elem:
                resume_data["current_position"] = clean_text(position_elem.get_text())
            
            # 提取公司
            company_elem = card.find(['div', 'span'], class_=lambda x: x and 'company' in x.lower())
            if company_elem:
                resume_data["current_company"] = clean_text(company_elem.get_text())
            
            # 提取工作年限
            experience_elem = card.find(['div', 'span'], text=lambda x: x and '年' in x and '经验' in x)
            if experience_elem:
                exp_text = experience_elem.get_text()
                # 提取数字
                import re
                years = re.findall(r'(\d+)年', exp_text)
                if years:
                    resume_data["years_of_experience"] = int(years[0])
            
            # 提取学历
            education_elem = card.find(['div', 'span'], text=lambda x: x and any(edu in x for edu in ['本科', '硕士', '博士', '专科']))
            if education_elem:
                resume_data["education_level"] = clean_text(education_elem.get_text())
            
            # 提取联系方式（如果可见）
            contact_text = resume_data["raw_text"]
            email = extract_email(contact_text)
            phone = extract_phone(contact_text)
            
            if email or phone:
                resume_data["contact_info"] = {
                    "email": email,
                    "phone": phone
                }
            
            # 提取详情页链接
            detail_link = card.find('a', href=True)
            if detail_link:
                href = detail_link['href']
                if href.startswith('/'):
                    href = 'https://www.zhipin.com' + href
                resume_data["detail_url"] = href
            
            # 验证必要字段
            if not resume_data.get("name") and not resume_data.get("current_position"):
                return None
            
            return resume_data
            
        except Exception as e:
            rpa_logger.warning(f"提取简历信息失败: {str(e)}")
            return None
    
    async def _go_to_next_page(self) -> bool:
        """翻到下一页"""
        try:
            # 查找下一页按钮
            next_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".next, .page-next, a[title*='下一页'], button[title*='下一页']")
            
            for button in next_buttons:
                if button.is_enabled() and button.is_displayed():
                    # 滚动到按钮位置
                    self.driver.execute_script("arguments[0].scrollIntoView();", button)
                    await self._random_delay(0.5, 1.0)
                    
                    button.click()
                    await self._random_delay(2.0, 4.0)
                    
                    return True
            
            # 尝试通过页码翻页
            page_numbers = self.driver.find_elements(By.CSS_SELECTOR, ".page-num a, .pagination a")
            current_page = None
            
            for page_elem in page_numbers:
                if 'current' in page_elem.get_attribute('class') or 'active' in page_elem.get_attribute('class'):
                    try:
                        current_page = int(page_elem.text)
                        break
                    except ValueError:
                        continue
            
            if current_page:
                next_page = current_page + 1
                for page_elem in page_numbers:
                    if page_elem.text == str(next_page):
                        page_elem.click()
                        await self._random_delay(2.0, 4.0)
                        return True
            
            return False
            
        except Exception as e:
            rpa_logger.warning(f"翻页失败: {str(e)}")
            return False
    
    async def get_resume_detail(self, detail_url: str) -> Optional[Dict[str, Any]]:
        """获取简历详情"""
        try:
            rpa_logger.info(f"获取简历详情: {detail_url}")
            
            self.driver.get(detail_url)
            await self._random_delay(2.0, 4.0)
            
            # 模拟人类行为
            await self._simulate_human_behavior()
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 提取详细信息
            detail_data = {
                "source_url": detail_url,
                "raw_text": clean_text(soup.get_text()),
                "extracted_at": datetime.now().isoformat()
            }
            
            # 提取更详细的信息（需要根据实际页面结构调整）
            # 这里只是示例，实际需要根据BOSS直聘的页面结构来调整
            
            return detail_data
            
        except Exception as e:
            rpa_logger.error(f"获取简历详情失败: {str(e)}")
            return None
    
    async def close(self):
        """关闭浏览器"""
        try:
            if self.driver:
                self.driver.quit()
                rpa_logger.info("浏览器已关闭")
        except Exception as e:
            rpa_logger.error(f"关闭浏览器失败: {str(e)}")


# 全局RPA实例
_boss_rpa_instance = None


async def get_boss_rpa() -> BossRPA:
    """获取BOSS RPA实例"""
    global _boss_rpa_instance
    if _boss_rpa_instance is None:
        _boss_rpa_instance = BossRPA()
    return _boss_rpa_instance


async def close_boss_rpa():
    """关闭BOSS RPA实例"""
    global _boss_rpa_instance
    if _boss_rpa_instance:
        await _boss_rpa_instance.close()
        _boss_rpa_instance = None