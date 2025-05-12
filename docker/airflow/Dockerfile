FROM apache/airflow:3.0.0-python3.11

# ---------- libgomp1 をインストール ----------
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends libgomp1 \
  && rm -rf /var/lib/apt/lists/*
USER airflow

# ---------- 依存パッケージをインストール ----------
ARG AIRFLOW_VERSION=3.0.0
ARG PYTHON_VERSION=3.11
ARG CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

# requirements をコピー
COPY docker/airflow/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --upgrade pip==25.1.1 \
  && pip install --no-cache-dir -r requirements.txt
