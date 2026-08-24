FROM python:3.11-slim

RUN addgroup --system nonroot \
    && adduser --system --ingroup nonroot nonroot

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MONGO_URI="mongodb://localhost:3039/" \
    MONGO_DB_NAME="food_preorder"

RUN apt-get update && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt

RUN pip install --no-cache-dir \
        pip==26.2.1 \
        setuptools==78.1.1 \
        wheel==0.48.0 \
    && pip install --no-cache-dir \
        -r ./backend/requirements.txt \
    && pip install --no-cache-dir \
        setuptools==78.1.1 \
        msgpack==1.2.1 \
    && pip show setuptools msgpack | grep -E "Name|Version"

COPY backend ./backend
COPY frontend ./frontend

RUN chown -R nonroot:nonroot /app

USER nonroot

EXPOSE 5000

CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "5000"]