# HR RPA系统使用指南

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件，配置必要的API密钥：

```bash
# SiliconFlow API配置（必需）
SILICONFLOW_API_KEY=your_siliconflow_api_key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL=deepseek-chat

# 飞书API配置（必需）
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
FEISHU_TABLE_APP_TOKEN=your_table_app_token
FEISHU_TABLE_ID=your_table_id

# BOSS直聘配置（可选，用于RPA）
BOSS_USERNAME=your_boss_username
BOSS_PASSWORD=your_boss_password
```

### 3. 初始化数据库

```bash
python init_db.py
```

### 4. 测试系统

```bash
python test_system.py
```

### 5. 启动系统

```bash
# 启动API服务器
python run.py server

# 或者直接启动简历筛选工作流
python run.py workflow --job-id 1
```

## 主要功能

### 1. 岗位管理

#### 创建岗位

```bash
# 通过命令行创建岗位
python run.py create-job \
  --title "AI工程师" \
  --company "科技公司" \
  --location "北京" \
  --description "负责AI算法开发"
```

#### API方式创建岗位

```bash
curl -X POST "http://localhost:8000/api/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI工程师",
    "company": "科技公司",
    "location": "北京",
    "job_type": "full_time",
    "description": "负责AI算法开发和优化",
    "responsibilities": [
      "开发机器学习算法",
      "优化模型性能"
    ],
    "requirements": {
      "experience_level": "mid_level",
      "education": "bachelor",
      "required_skills": ["Python", "机器学习", "深度学习"],
      "preferred_skills": ["TensorFlow", "PyTorch"]
    },
    "created_by": "HR部门"
  }'
```

### 2. 简历筛选工作流

#### 启动完整工作流

```bash
# 启动简历筛选工作流
curl -X POST "http://localhost:8000/api/workflow/start" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 1,
    "search_keywords": "AI工程师 机器学习",
    "max_resumes": 50,
    "filters": {
      "experience_years": "3-8",
      "education": "本科及以上",
      "location": "北京"
    }
  }'
```

#### 查看工作流状态

```bash
curl "http://localhost:8000/api/workflow/status"
```

### 3. 手动简历分析

#### 上传简历并分析

```bash
# 创建简历
curl -X POST "http://localhost:8000/api/resumes" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三",
    "contact_info": {
      "email": "zhangsan@example.com",
      "phone": "13800138000",
      "location": "北京市"
    },
    "summary": "5年AI开发经验",
    "skills": ["Python", "TensorFlow", "机器学习"],
    "years_of_experience": 5,
    "source": "manual"
  }'

# 分析简历与岗位匹配度
curl -X POST "http://localhost:8000/api/resumes/1/analyze" \
  -H "Content-Type: application/json" \
  -d '{"job_id": 1}'
```

### 4. 飞书集成

#### 同步分析结果到飞书

```bash
curl -X POST "http://localhost:8000/api/feishu/sync/1"
```

#### 批量同步

```bash
curl -X POST "http://localhost:8000/api/feishu/batch-sync" \
  -H "Content-Type: application/json" \
  -d '{"analysis_ids": [1, 2, 3]}'
```

## API文档

### 核心端点

- `GET /` - 健康检查
- `GET /api/health` - 系统状态

### 岗位管理

- `POST /api/jobs` - 创建岗位
- `GET /api/jobs/{job_id}` - 获取岗位详情
- `PUT /api/jobs/{job_id}` - 更新岗位
- `GET /api/jobs` - 搜索岗位

### 简历管理

- `POST /api/resumes` - 创建简历
- `GET /api/resumes/{resume_id}` - 获取简历详情
- `PUT /api/resumes/{resume_id}` - 更新简历
- `GET /api/resumes` - 搜索简历
- `POST /api/resumes/{resume_id}/analyze` - 分析简历
- `POST /api/resumes/batch-analyze` - 批量分析

### 工作流管理

- `POST /api/workflow/start` - 启动工作流
- `GET /api/workflow/status` - 获取工作流状态
- `POST /api/workflow/pause` - 暂停工作流
- `POST /api/workflow/cancel` - 取消工作流
- `GET /api/workflow/history` - 获取工作流历史

### 飞书集成

- `POST /api/feishu/sync/{analysis_id}` - 同步单个分析结果
- `POST /api/feishu/batch-sync` - 批量同步
- `GET /api/feishu/records` - 获取飞书记录
- `GET /api/feishu/stats` - 获取同步统计

### 分析结果

- `GET /api/analysis/{analysis_id}` - 获取分析结果
- `GET /api/analysis` - 搜索分析结果
- `GET /api/analysis/stats` - 获取分析统计

## 配置说明

### SiliconFlow API配置

```bash
# API密钥（必需）
SILICONFLOW_API_KEY=sk-xxx

# API基础URL（可选）
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

# 使用的模型（可选）
SILICONFLOW_MODEL=deepseek-chat

# 请求超时时间（秒）
SILICONFLOW_TIMEOUT=30

# 最大重试次数
SILICONFLOW_MAX_RETRIES=3
```

### 飞书API配置

```bash
# 应用ID和密钥（必需）
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx

# 多维表格配置（必需）
FEISHU_TABLE_APP_TOKEN=xxx
FEISHU_TABLE_ID=xxx

# API基础URL（可选）
FEISHU_BASE_URL=https://open.feishu.cn
```

### BOSS直聘RPA配置

```bash
# 登录凭据（可选）
BOSS_USERNAME=your_username
BOSS_PASSWORD=your_password

# 浏览器配置
BOSS_HEADLESS=true
BOSS_BROWSER_TIMEOUT=30
BOSS_PAGE_TIMEOUT=10

# 反爬虫配置
BOSS_MIN_DELAY=2
BOSS_MAX_DELAY=5
BOSS_MAX_RETRIES=3
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查数据库文件权限
   ls -la data/hr_rpa.db
   
   # 重新初始化数据库
   rm data/hr_rpa.db
   python init_db.py
   ```

2. **API密钥配置错误**
   ```bash
   # 检查环境变量
   python -c "from src.utils.config import get_config; print(get_config().siliconflow.api_key)"
   ```

3. **RPA浏览器启动失败**
   ```bash
   # 安装Chrome浏览器
   # macOS: brew install --cask google-chrome
   # Ubuntu: sudo apt-get install google-chrome-stable
   
   # 检查ChromeDriver
   chromedriver --version
   ```

4. **飞书API调用失败**
   ```bash
   # 检查飞书应用权限
   # 确保应用有多维表格的读写权限
   ```

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log

# 查看RPA日志
tail -f logs/rpa.log

# 查看AI分析日志
tail -f logs/ai_analysis.log
```

### 性能优化

1. **数据库优化**
   - 定期清理旧数据
   - 添加适当的索引
   - 使用连接池

2. **API调用优化**
   - 启用请求缓存
   - 使用批量操作
   - 设置合理的超时时间

3. **RPA优化**
   - 调整等待时间
   - 使用无头浏览器
   - 限制并发数量

## 开发指南

### 项目结构

```
src/
├── core/           # 核心组件
│   ├── ai_analyzer.py      # AI分析器
│   ├── rpa_controller.py   # RPA控制器
│   └── data_manager.py     # 数据管理器
├── integrations/   # 第三方集成
│   ├── siliconflow_api.py  # SiliconFlow API
│   ├── feishu_api.py       # 飞书API
│   └── boss_api.py         # BOSS直聘RPA
├── services/       # 业务服务
│   ├── resume_service.py   # 简历服务
│   ├── feishu_service.py   # 飞书服务
│   └── workflow_service.py # 工作流服务
├── models/         # 数据模型
├── utils/          # 工具函数
└── main.py         # 主入口
```

### 扩展开发

1. **添加新的AI模型**
   - 修改 `src/integrations/siliconflow_api.py`
   - 更新模型配置

2. **添加新的数据源**
   - 在 `src/integrations/` 下创建新的API客户端
   - 更新 `src/core/rpa_controller.py`

3. **自定义分析逻辑**
   - 修改 `src/core/ai_analyzer.py`
   - 添加新的评分维度

4. **扩展飞书功能**
   - 修改 `src/services/feishu_service.py`
   - 添加新的同步逻辑

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。