#!/usr/bin/env sh
set -eu

# モデルインポートをスキップ
echo "Starting BentoML service in simple mode..."

# # モデル検証
# python -u scripts/import_volume_spike_model.py

# BentoML サービスを起動
# Cloud Run の環境変数 PORT を使って、0.0.0.0 にバインド
# 一時的にMLFlowへの依存なしのサービスを起動
exec bentoml serve services.simple_service:SimpleService \
  --reload \
  --host 0.0.0.0 \
  --port "${PORT:-3000}"