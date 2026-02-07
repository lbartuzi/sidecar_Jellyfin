FROM python:3.12-slim

# Best practices: minimal image, non-root user, no cache
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# data dir (will be mounted)
RUN mkdir -p /data && chown -R appuser:appuser /data /app

USER appuser

EXPOSE 8088
CMD ["python", "main.py"]
