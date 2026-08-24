FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MONGO_URI="mongodb://localhost:3039/" \
    MONGO_DB_NAME="food_preorder"

# Patch OS packages (fixes the util-linux CVEs: CVE-2026-53612/53613/53614/53615)
RUN apt-get update && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --only-binary :all: --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --only-binary :all: -r ./backend/requirements.txt && \
    pip install --no-cache-dir --only-binary :all: --upgrade "setuptools>=78.1.1" "msgpack>=1.2.1" && \
    pip show setuptools msgpack | grep -E "Name|Version"

COPY backend ./backend
COPY frontend ./frontend

EXPOSE 5000

CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "5000"]