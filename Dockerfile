# 使用官方 Python 运行时作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY app.py .
COPY config.py .
COPY logger.py .
COPY utils.py .
COPY .env.example .env

# 创建必要的目录
RUN mkdir -p logs webhooks_data

# 暴露端口
EXPOSE 8000

# 使用 gunicorn 运行应用(生产环境)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "app:app"]
