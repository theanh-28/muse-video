FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    ANISTUDIO_HOME=/app \
    ANISTUDIO_HOST=0.0.0.0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml AGENTS.md ./
COPY docs/ ./docs/
COPY config/ ./config/
COPY src/ ./src/
COPY .agents/skills/anistudio-story-continuity/ ./.agents/skills/anistudio-story-continuity/

RUN pip install --no-cache-dir '.[http,web]'

EXPOSE 8765

CMD ["python", "-m", "animation_studio.cli.main", "web", "--port", "8765"]
