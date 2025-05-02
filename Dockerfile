FROM python:3

COPY src/ ./src
COPY pyproject.toml ./
COPY uv.lock ./

# 安装 uv
RUN pip install --no-cache-dir uv

# 使用 uv 安装依赖
RUN uv sync --all-extras
RUN uv pip install .

EXPOSE 5000
ENTRYPOINT ["uv", "run", "flask"]
CMD ["-A", "doujia.server", "run", "--host", "0.0.0.0"]
