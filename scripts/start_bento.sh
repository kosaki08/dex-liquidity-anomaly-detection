#!/usr/bin/env sh
set -eu

# モデル検証
python -u scripts/import_volume_spike_model.py || {
  echo "Warning: model import failed, starting server anyway" >&2
}

# BentoML サービスを起動
exec bentoml serve services.volume_spike_service:PoolIForestService \
  --reload \
  --host 0.0.0.0 \
  --port "${PORT:-3000}"
