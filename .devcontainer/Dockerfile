FROM mcr.microsoft.com/devcontainers/python:1-3.11

# ---------- OS レイヤ ----------
USER root
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  build-essential curl && \
  rm -rf /var/lib/apt/lists/*

# ---------- Python パッケージ ----------
RUN pip install --no-cache-dir poetry "apache-airflow-providers-snowflake>=5.3.1,<6.0.0"

# プロジェクトルートに移動し、先に lock／toml をコピー
WORKDIR /workspaces/${localWorkspaceFolderBasename}
COPY pyproject.toml poetry.lock ./

# 仮想環境は作らずコンテナ全体にインストール
RUN poetry config virtualenvs.create false \
  && poetry install --no-root --no-interaction --no-ansi

# ---------- SnowSQL インストール ----------
RUN curl -O https://sfc-repo.snowflakecomputing.com/snowsql/bootstrap/1.2/linux_x86_64/snowsql-1.2.26-linux_x86_64.bash && \
  chmod 755 snowsql-1.2.26-linux_x86_64.bash && \
  SNOWSQL_DEST=/usr/local/bin SNOWSQL_LOGIN_SHELL=/dev/null bash snowsql-1.2.26-linux_x86_64.bash -batch || true && \
  rm snowsql-1.2.26-linux_x86_64.bash

# ---------- vscode ユーザーに切り替え ----------
USER vscode