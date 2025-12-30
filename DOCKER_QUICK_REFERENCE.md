# Docker部署快速参考手册

## 🚀 快速开始

### 方式1：使用 Makefile（推荐）
```bash
# 一键部署
make deploy

# 查看服务状态
make ps

# 查看日志
make logs
```

### 方式2：使用 docker-compose
```bash
# 1. 配置环境
cp .env.docker .env
nano .env  # 编辑密钥

# 2. 创建数据目录
mkdir -p data/{mysql,backend,uploads}

# 3. 启动服务
docker-compose up -d

# 4. 查看状态
docker-compose ps
```

---

## 📋 常用命令

### Makefile 命令

| 命令 | 说明 |
|------|------|
| `make help` | 显示所有可用命令 |
| `make deploy` | 一键完整部署（首次使用） |
| `make setup` | 初始化环境 |
| `make build` | 构建镜像 |
| `make up` | 启动服务 |
| `make down` | 停止服务 |
| `make restart` | 重启服务 |
| `make logs` | 查看日志 |
| `make ps` | 查看状态 |
| `make health` | 健康检查 |
| `make backup` | 备份数据 |
| `make test` | 测试部署 |

### Docker Compose 命令

```bash
# 服务管理
docker-compose up -d          # 启动
docker-compose down           # 停止
docker-compose restart        # 重启
docker-compose ps             # 状态
docker-compose logs -f        # 日志

# 单独操作某个服务
docker-compose restart backend
docker-compose logs -f frontend

# 进入容器
docker-compose exec backend bash
docker-compose exec mysql bash

# 资源清理
docker-compose down -v        # 删除所有（包括数据卷）
```

---

## 🔧 故障排查

### 检查服务健康
```bash
make health
# 或
docker-compose ps
```

### 查看错误日志
```bash
# 所有服务
make logs

# 特定服务
make logs-backend
make logs-mysql
make logs-frontend
```

### 常见问题

**1. 容器启动失败**
```bash
# 查看详细错误
docker-compose logs [service_name]

# 检查端口占用
lsof -i :80
lsof -i :5000
```

**2. 数据库连接失败**
```bash
# 检查MySQL状态
docker-compose exec mysql mysqladmin ping -h localhost -u root -p

# 等待MySQL完全启动（约30秒）
```

**3. 前端无法访问**
```bash
# 检查Nginx配置
docker-compose exec frontend cat /etc/nginx/conf.d/nginx.conf

# 测试网络连接
docker-compose exec frontend ping backend
```

---

## 📊 监控和维护

### 资源使用
```bash
make stats
# 或
docker stats
```

### 备份
```bash
# 自动备份
make backup

# 恢复
make restore FILE=backups/kb_backup_20231230.sql
```

### 更新应用
```bash
make update
# 或手动：
git pull
docker-compose build
docker-compose up -d
```

---

## 🔐 安全检查清单

- [ ] 修改默认密码（.env 文件）
- [ ] 生成安全密钥（SECRET_KEY, JWT_SECRET_KEY）
- [ ] 限制MySQL端口（只监听127.0.0.1）
- [ ] 配置防火墙规则
- [ ] 启用HTTPS（生产环境）
- [ ] 定期备份数据
- [ ] 更新Docker镜像

---

## 📍 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost | Web界面 |
| API | http://localhost/api | 后端API |
| MySQL | localhost:3306 | 数据库（仅本地） |

---

## 📞 获取帮助

```bash
# 查看Makefile帮助
make help

# 查看详细文档
cat DOCKER_DEPLOYMENT.md

# 检查服务健康
make health

# 测试部署
make test
```

---

## ⚡ 快速操作

```bash
# 完整部署流程
make deploy

# 日常操作
make restart          # 重启
make logs            # 查看日志
make backup          # 备份

# 开发调试
make dev             # 前台运行
make exec-backend    # 进入后端容器
make mysql-cli       # MySQL命令行

# 清理
make clean           # 清理容器
make prune           # 清理Docker资源
```
