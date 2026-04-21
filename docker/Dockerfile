FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY apps ./apps
COPY main.py .
COPY config.py .
COPY init_agent.py .
COPY dashboard.py .
COPY cli ./cli

ENV AGENT_LOG_DIR=/app/.logs
ENV AGENT_WATCH_DIR=/app
ENV AGENT_DEBUG=false

EXPOSE 8000

CMD ["python", "-m", "main"]
