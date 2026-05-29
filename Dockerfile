FROM python:3.13-slim

WORKDIR /app

COPY . .

RUN pip install uv
RUN uv sync

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 5000

CMD ["ddtrace-run", "python", "run.py"]
