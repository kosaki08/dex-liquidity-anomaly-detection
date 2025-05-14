# ---------- 1. builder stage ----------
FROM --platform=linux/amd64 python:3.11-slim AS builder

WORKDIR /build

# ビルドに必要なツールをインストール
RUN apt-get update && \
  apt-get install -y --no-install-recommends build-essential && \
  rm -rf /var/lib/apt/lists/*

# requirements をコピー
COPY docker/mlflow/requirements.txt ./requirements.txt

# wheel をまとめて作成
RUN pip wheel --no-cache-dir -r requirements.txt -w /wheels

# ---------- 2. runtime stage ----------
FROM --platform=linux/amd64 python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# wheel だけコピーして展開
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# スクリプトやモデルを配置
COPY scripts/model /app/scripts/model

# mlruns ディレクトリを作成しておく
RUN mkdir -p /app/mlruns/db /app/mlruns/artifacts

EXPOSE 5000
CMD ["mlflow", "server", \
  "--backend-store-uri", "sqlite:////app/mlruns/db/mlflow.db", \
  "--default-artifact-root", "file:///app/mlruns/artifacts", \
  "--host", "0.0.0.0", "--port", "5000"]
