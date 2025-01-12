FROM python:3

COPY src/ ./src
COPY pyproject.toml ./
COPY pdm.lock ./

RUN pip install --no-cache-dir pdm
RUN pdm install --no-lock --no-editable

EXPOSE 5000
ENTRYPOINT ["pdm", "run", "flask"]
CMD ["-A", "doujia.server", "run", "--host", "0.0.0.0"]
