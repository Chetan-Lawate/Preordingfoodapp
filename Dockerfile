FROM python:3.11-alpine AS builder

RUN addgroup -S nonroot \
    && adduser -S -G nonroot nonroot

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MONGO_URI="mongodb://localhost:3039/" \
    MONGO_DB_NAME="food_preorder"

RUN apk upgrade --no-cache

COPY backend/requirements.txt ./backend/requirements.txt

RUN pip install --no-cache-dir \
        pip==26.2.1 \
        setuptools==78.1.1 \
        wheel==0.48.0 \
    && pip install --no-cache-dir \
        -r ./backend/requirements.txt \
    && python -m pip uninstall -y pip setuptools wheel

COPY backend ./backend
COPY frontend ./frontend

RUN chown -R nonroot:nonroot /app

FROM alpine:3.24

RUN addgroup -S nonroot \
    && adduser -S -G nonroot nonroot

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MONGO_URI="mongodb://localhost:3039/" \
    MONGO_DB_NAME="food_preorder"

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app/backend ./backend
COPY --from=builder /app/frontend ./frontend

RUN rm -rf /usr/local/lib/python3.11/site-packages/pip* \
    /usr/local/lib/python3.11/site-packages/setuptools* \
    /usr/local/lib/python3.11/site-packages/wheel* \
    /usr/local/bin/pip* \
    && chown -R nonroot:nonroot /app

USER nonroot

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3)"

CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "5000"]