# ---------- 1. builder stage ----------
FROM python:3.11-slim AS builder

WORKDIR /build

# ビルドに必要なツールをインストール
RUN apt-get update && \
  apt-get install -y --no-install-recommends build-essential && \
  rm -rf /var/lib/apt/lists/*

# requirements をコピー
COPY docker/streamlit/requirements.txt ./requirements.txt

# wheel をまとめて作成
RUN pip wheel --no-cache-dir -r requirements.txt -w /wheels

# ---------- 2. runtime stage ----------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
  STREAMLIT_SERVER_HEADLESS=true \
  STREAMLIT_SERVER_PORT=8501 \
  STREAMLIT_SERVER_ADDRESS=0.0.0.0

WORKDIR /app

# wheel だけコピーして展開
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# アプリ本体のみコピー（ビルドキャッシュ効率のため最後にコピー）
COPY app /app

EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py"]
