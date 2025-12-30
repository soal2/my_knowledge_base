# Frontend Dockerfile with Multi-Stage Build
# Stage 1: Build the Vue application
FROM node:18-alpine AS builder

WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# Stage 2: Nginx服务器
FROM nginx:1.25-alpine

# 删除默认的Nginx配置
RUN rm /etc/nginx/conf.d/default.conf

# 复制自定义Nginx配置
COPY nginx.conf /etc/nginx/conf.d/

# 从构建阶段复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

# 启动Nginx
CMD ["nginx", "-g", "daemon off;"]
