.PHONY: help install init test server workflow clean

# 默认目标
help:
	@echo "HR RPA系统 - 可用命令:"
	@echo "  make install    - 安装依赖"
	@echo "  make init       - 初始化数据库"
	@echo "  make test       - 运行系统测试"
	@echo "  make server     - 启动API服务器"
	@echo "  make workflow   - 启动简历筛选工作流"
	@echo "  make clean      - 清理临时文件"
	@echo "  make setup      - 完整设置（安装+初始化+测试）"

# 安装依赖
install:
	@echo "📦 安装Python依赖..."
	pip install -r requirements.txt
	@echo "✅ 依赖安装完成"

# 初始化数据库
init:
	@echo "🗄️ 初始化数据库..."
	python init_db.py
	@echo "✅ 数据库初始化完成"

# 运行测试
test:
	@echo "🧪 运行系统测试..."
	python test_system.py
	@echo "✅ 测试完成"

# 启动API服务器
server:
	@echo "🚀 启动API服务器..."
	python run.py server

# 启动工作流（需要指定岗位ID）
workflow:
	@echo "⚡ 启动简历筛选工作流..."
	@echo "请使用: python run.py workflow --job-id <JOB_ID>"

# 清理临时文件
clean:
	@echo "🧹 清理临时文件..."
	rm -rf __pycache__/
	rm -rf src/__pycache__/
	rm -rf src/*/__pycache__/
	rm -rf src/*/*/__pycache__/
	rm -rf .pytest_cache/
	rm -rf *.pyc
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	@echo "✅ 清理完成"

# 完整设置
setup: install init test
	@echo "🎉 系统设置完成！"
	@echo "💡 下一步:"
	@echo "   1. 编辑 .env 文件配置API密钥"
	@echo "   2. 运行 'make server' 启动API服务器"
	@echo "   3. 或运行 'python run.py workflow --job-id 1' 启动工作流"

# 开发环境设置
dev-setup: install
	@echo "🔧 设置开发环境..."
	pip install black flake8 pytest pytest-asyncio
	@echo "✅ 开发环境设置完成"

# 代码格式化
format:
	@echo "🎨 格式化代码..."
	black src/ --line-length 100
	@echo "✅ 代码格式化完成"

# 代码检查
lint:
	@echo "🔍 检查代码质量..."
	flake8 src/ --max-line-length=100 --ignore=E203,W503
	@echo "✅ 代码检查完成"

# 运行单元测试
unittest:
	@echo "🧪 运行单元测试..."
	pytest tests/ -v
	@echo "✅ 单元测试完成"

# 查看日志
logs:
	@echo "📋 查看应用日志..."
	tail -f logs/app.log

# 查看错误日志
error-logs:
	@echo "❌ 查看错误日志..."
	tail -f logs/error.log

# 备份数据库
backup:
	@echo "💾 备份数据库..."
	mkdir -p backups
	cp data/hr_rpa.db backups/hr_rpa_$(shell date +%Y%m%d_%H%M%S).db
	@echo "✅ 数据库备份完成"

# 恢复数据库（需要指定备份文件）
restore:
	@echo "🔄 恢复数据库..."
	@echo "请使用: cp backups/<backup_file> data/hr_rpa.db"