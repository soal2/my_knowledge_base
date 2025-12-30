# Makefile for Knowledge Base Docker Deployment
.PHONY: help build up down restart logs ps clean backup restore

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## 显示帮助信息
	@echo "$(CYAN)========================================$(NC)"
	@echo "$(CYAN)  知识库系统 Docker 管理命令$(NC)"
	@echo "$(CYAN)========================================$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

setup: ## 初始化环境（首次部署必须执行）
	@echo "$(CYAN)初始化部署环境...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.docker .env; \
		echo "$(GREEN)✓ 已创建 .env 文件$(NC)"; \
		echo "$(YELLOW)⚠️  请编辑 .env 文件并设置密钥！$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  .env 文件已存在$(NC)"; \
	fi
	@mkdir -p data/mysql data/backend data/uploads
	@chmod -R 755 data/
	@echo "$(GREEN)✓ 数据目录已创建$(NC)"
	@echo ""
	@echo "$(YELLOW)下一步：$(NC)"
	@echo "1. 编辑 .env 文件设置安全密钥"
	@echo "2. 运行 'make build' 构建镜像"
	@echo "3. 运行 'make up' 启动服务"

build: ## 构建所有Docker镜像
	@echo "$(CYAN)构建Docker镜像...$(NC)"
	docker-compose build
	@echo "$(GREEN)✓ 镜像构建完成$(NC)"

build-no-cache: ## 无缓存构建（强制重新构建）
	@echo "$(CYAN)无缓存构建Docker镜像...$(NC)"
	docker-compose build --no-cache
	@echo "$(GREEN)✓ 镜像构建完成$(NC)"

up: ## 启动所有服务
	@echo "$(CYAN)启动服务...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ 服务已启动$(NC)"
	@make ps

down: ## 停止并删除所有容器
	@echo "$(CYAN)停止服务...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ 服务已停止$(NC)"

stop: ## 停止所有服务（不删除容器）
	@echo "$(CYAN)停止服务...$(NC)"
	docker-compose stop
	@echo "$(GREEN)✓ 服务已停止$(NC)"

start: ## 启动已存在的服务
	@echo "$(CYAN)启动服务...$(NC)"
	docker-compose start
	@echo "$(GREEN)✓ 服务已启动$(NC)"

restart: ## 重启所有服务
	@echo "$(CYAN)重启服务...$(NC)"
	docker-compose restart
	@echo "$(GREEN)✓ 服务已重启$(NC)"

restart-backend: ## 重启后端服务
	@echo "$(CYAN)重启后端服务...$(NC)"
	docker-compose restart backend
	@echo "$(GREEN)✓ 后端服务已重启$(NC)"

restart-frontend: ## 重启前端服务
	@echo "$(CYAN)重启前端服务...$(NC)"
	docker-compose restart frontend
	@echo "$(GREEN)✓ 前端服务已重启$(NC)"

logs: ## 查看所有服务日志
	docker-compose logs -f

logs-backend: ## 查看后端日志
	docker-compose logs -f backend

logs-frontend: ## 查看前端日志
	docker-compose logs -f frontend

logs-mysql: ## 查看MySQL日志
	docker-compose logs -f mysql

ps: ## 显示服务状态
	@echo "$(CYAN)服务状态：$(NC)"
	@docker-compose ps
	@echo ""
	@echo "$(CYAN)健康检查：$(NC)"
	@docker-compose ps --format json | jq -r '.[] | "\(.Name): \(.Health)"' 2>/dev/null || docker-compose ps

health: ## 检查服务健康状态
	@echo "$(CYAN)检查服务健康状态...$(NC)"
	@echo ""
	@echo "$(CYAN)MySQL:$(NC)"
	@docker-compose exec mysql mysqladmin ping -h localhost -u root -p$$(grep MYSQL_ROOT_PASSWORD .env | cut -d '=' -f2) 2>/dev/null && echo "$(GREEN)✓ MySQL 健康$(NC)" || echo "$(RED)✗ MySQL 异常$(NC)"
	@echo ""
	@echo "$(CYAN)Backend:$(NC)"
	@curl -sf http://localhost:5000/api/health > /dev/null && echo "$(GREEN)✓ Backend 健康$(NC)" || echo "$(RED)✗ Backend 异常$(NC)"
	@echo ""
	@echo "$(CYAN)Frontend:$(NC)"
	@curl -sf http://localhost/health > /dev/null && echo "$(GREEN)✓ Frontend 健康$(NC)" || echo "$(RED)✗ Frontend 异常$(NC)"

exec-backend: ## 进入后端容器
	docker-compose exec backend bash

exec-mysql: ## 进入MySQL容器
	docker-compose exec mysql bash

exec-frontend: ## 进入前端容器
	docker-compose exec frontend sh

mysql-cli: ## 连接到MySQL命令行
	@docker-compose exec mysql mysql -u root -p$$(grep MYSQL_ROOT_PASSWORD .env | cut -d '=' -f2) knowledge_base_db

clean: ## 删除所有容器、网络（保留数据卷）
	@echo "$(YELLOW)⚠️  这将删除所有容器和网络$(NC)"
	@read -p "确认继续? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down; \
		echo "$(GREEN)✓ 清理完成$(NC)"; \
	else \
		echo "$(YELLOW)取消操作$(NC)"; \
	fi

clean-all: ## 删除所有容器、网络和数据卷（危险！）
	@echo "$(RED)⚠️  警告：这将删除所有数据！$(NC)"
	@read -p "确认继续? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		rm -rf data/*; \
		echo "$(GREEN)✓ 所有数据已清理$(NC)"; \
	else \
		echo "$(YELLOW)取消操作$(NC)"; \
	fi

backup: ## 备份数据库和数据卷
	@echo "$(CYAN)备份数据...$(NC)"
	@mkdir -p backups
	@BACKUP_FILE=backups/kb_backup_$$(date +%Y%m%d_%H%M%S); \
	docker-compose exec -T mysql mysqldump \
		-u root -p$$(grep MYSQL_ROOT_PASSWORD .env | cut -d '=' -f2) \
		knowledge_base_db > $$BACKUP_FILE.sql; \
	tar -czf $$BACKUP_FILE.tar.gz data/; \
	echo "$(GREEN)✓ 备份完成: $$BACKUP_FILE.sql, $$BACKUP_FILE.tar.gz$(NC)"

restore: ## 恢复数据库（需要指定备份文件：make restore FILE=backups/kb_backup.sql）
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)错误: 请指定备份文件$(NC)"; \
		echo "用法: make restore FILE=backups/kb_backup_20231230.sql"; \
		exit 1; \
	fi
	@echo "$(CYAN)恢复数据库...$(NC)"
	@docker-compose exec -T mysql mysql \
		-u root -p$$(grep MYSQL_ROOT_PASSWORD .env | cut -d '=' -f2) \
		knowledge_base_db < $(FILE)
	@echo "$(GREEN)✓ 数据库恢复完成$(NC)"

update: ## 更新应用（拉取代码、重新构建、重启）
	@echo "$(CYAN)更新应用...$(NC)"
	git pull origin main
	docker-compose build
	docker-compose up -d
	@echo "$(GREEN)✓ 更新完成$(NC)"

stats: ## 显示资源使用情况
	docker stats --no-stream kb-mysql kb-backend kb-frontend

prune: ## 清理未使用的Docker资源
	@echo "$(CYAN)清理Docker资源...$(NC)"
	docker system prune -f
	@echo "$(GREEN)✓ 清理完成$(NC)"

test: ## 测试部署（检查所有服务是否正常）
	@echo "$(CYAN)测试部署...$(NC)"
	@echo ""
	@make health
	@echo ""
	@echo "$(CYAN)测试前端访问：$(NC)"
	@curl -sf http://localhost > /dev/null && echo "$(GREEN)✓ 前端可访问$(NC)" || echo "$(RED)✗ 前端无法访问$(NC)"
	@echo ""
	@echo "$(CYAN)测试API访问：$(NC)"
	@curl -sf http://localhost/api/health > /dev/null && echo "$(GREEN)✓ API可访问$(NC)" || echo "$(RED)✗ API无法访问$(NC)"

dev: ## 开发模式（启动服务并查看日志）
	docker-compose up

prod: ## 生产模式部署
	@echo "$(CYAN)生产模式部署...$(NC)"
	docker-compose -f docker-compose.yml up -d
	@echo "$(GREEN)✓ 生产环境已启动$(NC)"

# 一键部署（首次使用）
deploy: setup build up ## 一键完整部署（首次使用）
	@echo ""
	@echo "$(GREEN)========================================$(NC)"
	@echo "$(GREEN)  部署完成！$(NC)"
	@echo "$(GREEN)========================================$(NC)"
	@echo ""
	@echo "$(CYAN)访问地址：$(NC)"
	@echo "  前端: http://localhost"
	@echo "  API: http://localhost/api"
	@echo ""
	@echo "$(CYAN)查看状态：$(NC) make ps"
	@echo "$(CYAN)查看日志：$(NC) make logs"
	@echo "$(CYAN)查看帮助：$(NC) make help"
