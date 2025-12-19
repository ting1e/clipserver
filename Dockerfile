FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/webdav_data/history /app/webdav_data/file

# 暴露端口
EXPOSE 8000

# 环境变量
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DATA_DIR=/app/webdav_data

# 启动命令
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
