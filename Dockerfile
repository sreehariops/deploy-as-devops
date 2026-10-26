FROM python:3.12-slim

WORKDIR /opt/app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd --system --no-create-home appuser

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER appuser

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=10s \
    --start-interval=5s \
    --retries=3 \
    CMD python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3); exit(0 if r.status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]