#!/usr/bin/env sh
set -eu

# モデル検証
python -u scripts/import_volume_spike_model.py

# BentoML サービスを起動
exec bentoml serve services.volume_spike_service:VolumeSpikeService
