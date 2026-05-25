FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY alert_ai/ alert_ai/
RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "alert_ai"]
