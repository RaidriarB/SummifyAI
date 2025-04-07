# 使用Python 3.10作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_ENV production

# 先复制 requirements.txt 并安装依赖
# 这样可以利用 Docker 的缓存层，避免每次代码更改都重新安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN apt update && apt install -y ffmpeg

# 复制项目文件
COPY . .
RUN chmod +x start_server.sh

# 暴露端口
EXPOSE 15000

# 启动命令
CMD ["./start_server.sh"]