FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# Koyeb 会注入 $PORT 环境变量，gunicorn 监听该端口
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-8000}
