FROM mcr.microsoft.com/devcontainers/python:1-3.11

# ---------- OS レイヤ ----------
USER root
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  build-essential curl && \
  rm -rf /var/lib/apt/lists/*

# ---------- Python パッケージ ----------
ARG AIRFLOW_VERSION=2.9.1
ARG PYTHON_VERSION=3.11
ARG CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

RUN pip install --no-cache-dir \
  "apache-airflow==${AIRFLOW_VERSION}" \
  --constraint "${CONSTRAINT_URL}" \
  && pip install --no-cache-dir \
  dbt-duckdb \
  dbt-bigquery \
  mlflow \
  river \
  bentoML \
  optuna \
  lightgbm \
  jupyterlab

# ---------- Node.js ----------
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y nodejs

# ---------- ユーザ戻し ----------
USER vscode
