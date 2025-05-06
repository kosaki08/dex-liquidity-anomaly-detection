# DEX Liquidity Anomaly Detection Pipeline

分散型取引所（DEX）の流動性データを毎時収集し、特徴量を生成した上で LightGBM モデルによる異常スパイク検知を行うパイプラインです。
Uniswap V3 と Sushiswap から hourly データを抽出し、週次で LightGBM モデルを再学習 (retrain_lightgbm)、毎時間 predict_volume_spike で最新データをスコアリング・Slack 通知します。

## 📊 アーキテクチャ

```
┌──────────────┐
│  GitHub      │      CI : GitHub Actions
└──────┬───────┘
       │              (lint / unit-test / dbt build)
       ▼
┌──────────────┐  Airflow  ┌───────────┐
│ The Graph API│──DAG──────▶ Snowflake │  (raw / stg / mart)
│  ├ Uniswap V3│           └──────┬────┘
│  └ Sushiswap │                  │ dbt run
└──────────────┘                  ▼
                           ┌──────────────┐
                           │ retrain_lgbm │  @weekly retrain  ← train_lightgbm.py
                           └──────┬───────┘
                                 │ model: volume_spike_lgbm (Production)
                                 ▼
                           ┌───────────────────────┐
                           │ predict_volume_spike  │  @hourly predict + Slack alert
                           └──────┬────────────────┘
                                 │ score API (BentoML)
                                 ▼
                           ┌────────────┐
                           │  BentoML   │  /score
                           └────────────┘
                                  │
                           ┌─────────────┐
                           │ BentoML API │  /score   ← Cloud Run
                           └──────┬──────┘
                                  │
                           ┌────────────┐
                           │ Streamlit  │  GitHub Pages
                           └────────────┘
```

## 🛠 技術スタック

### データパイプライン

- **ETL**: Apache Airflow
- **データ収集**: The Graph API (GraphQL)
- **データウェアハウス**: Snowflake (PoC), BigQuery (運用)
- **データ変換**: dbt Core

### 機械学習 & API

- **初期学習 & 週次再学習**: LightGBM (LGBMClassifier) + MLflow
- **実験管理**: MLflow
- **モデル配信**: BentoML + FastAPI (LightGBM)
- **デプロイ**: Cloud Run

### 可視化 & モニタリング

- **ダッシュボード**: Streamlit (GitHub Pages)
- **EDA**: DuckDB
- **CI/CD**: GitHub Actions

## 🚀 環境構築

### 利用バージョン等

- Docker & Docker Compose
- Python 3.11+
- The Graph API key
- Snowflake アカウント

### セットアップ

1. リポジトリをクローン

```bash
git clone https://github.com/yourusername/dex-liquidity-anomaly-detection.git
cd dex-liquidity-anomaly-detection
```

2. 環境変数を設定

```bash
cp .env.example .env
# 以下の値を設定
# THE_GRAPH_API_KEY
# THE_GRAPH_UNISWAP_SUBGRAPH_ID
# THE_GRAPH_SUSHISWAP_SUBGRAPH_ID
# SNOWFLAKE_USER
# SNOWFLAKE_PASSWORD
# SNOWFLAKE_ACCOUNT
# SNOWFLAKE_DATABASE
# SNOWFLAKE_SCHEMA
# SNOWFLAKE_WAREHOUSE
# SNOWFLAKE_ROLE
```

3. 基盤セットアップ

```bash
# Snowflake セットアップ
make setup-snowflake

# Airflow & データパイプライン起動
docker-compose up -d

# パイプラインを手動トリガー（初回データロード）
docker-compose exec airflow airflow dags trigger dex_liquidity_raw
```

4. dbt による変換

```bash
# dbt モデルをビルド
dbt build
```

5. Airflow DAG の実行

- 初回／週次再学習

```bash
docker-compose exec airflow airflow dags trigger retrain_lightgbm
```

- 毎時推論＆Slack 通知

```bash
docker-compose exec airflow airflow dags trigger predict_volume_spike
```

6. API サーバー起動

```bash
# ローカルで実行
bentoml serve service:svc

# または Cloud Run にデプロイ
make deploy-to-cloud-run
```

7. Streamlit ダッシュボード確認

```bash
streamlit run app/streamlit_app.py
```

## 📂 プロジェクト構造

```
.
├── dags/                          # Airflow DAGs
│   ├── check_snowflake_connection.py
│   ├── dex_pipeline.py           # メイン ETL パイプライン
│   └── scripts/
│       └── fetcher/              # The Graph データフェッチ
│           ├── base.py
│           ├── uniswap.py
│           ├── sushiswap.py
│           └── queries/          # GraphQL クエリ
├── models/                        # dbt モデル
│   ├── staging/                  # Raw → ステージング変換
│   └── mart/                     # マート層（特徴量）
├── sql/                          # Snowflake セットアップ SQL
├── services/                      # BentoML サービス定義
├── app/                          # Streamlit アプリ
├── docker-compose.yml
├── Dockerfile.airflow
├── dbt_project.yml
└── pyproject.toml
```

## 🔄 データフロー

1. **データ収集**
   The Graph API から Uniswap V3／Sushiswap の hourly プールデータを取得
2. **ロード**
   Airflow DAG (`dex_liquidity_raw`) で Snowflake RAW レイヤへ `COPY INTO`
3. **変換**
   dbt で Staging → Mart（`mart_pool_features_labeled`）モデルをビルド
4. **モデル学習**
   - **初期学習**: `train_lightgbm.py` による直近 30 日バッチ学習
   - **週次再学習**: Airflow DAG (`retrain_lightgbm`) で最新データを再学習・MLflow へログ
5. **異常検知**
   Airflow DAG (`predict_volume_spike`) で毎時最新データを LightGBM モデルでスコアリングし、閾値超過時は Slack へ通知
6. **配信 & 可視化**
   - **API**: BentoML + FastAPI で `/score` エンドポイント提供
   - **ダッシュボード**: Streamlit でリアルタイムにスコア・Precision\@10 推移を表示

## 💡 主な機能

### 異常検知

- **教師あり二値分類**: LightGBM (LGBMClassifier) による volume-spike 検出
- **ラベル生成**: Mart モデル内でプールごとの 90th percentile を閾値とした教師ラベル (`y`) を自動生成
- **毎時推論**: 最新データをスコアリングし、スコア ≥ 閾値 のプールを Slack へ通知

### モニタリング & 管理

- **MLflow トラッキング**: 学習／再学習の run, metrics (PR-AUC, Precision\@10, Recall\@10), パラメータを一元管理
- **モデルレジストリ**: `volume_spike_lgbm` を Production ステージに登録
- **Slack アラート**: `predict_volume_spike` DAG から `SlackWebhookOperator` でアラート配信

### 配信 & 可視化

- **BentoML API**: `/score` エンドポイントで外部システムからリアルタイムスコア取得可能
- **Streamlit ダッシュボード**:
  - スコア上位 N プール一覧
  - スコア閾値スライダー
  - Precision\@10／Recall\@10 推移グラフ

### 動作確認フロー（開発用）

1. **DBT プロファイル解決の確認**

   ```bash
   dbt debug   # profiles/ が正しく読めているか
   ```

2. **ステージングモデル確認**

   ```bash
   dbt ls -s "stg_*"   # Staging ビュー一覧をチェック
   ```

3. **構文チェック**

   ```bash
   dbt parse   # DuckDB なしで SQL 構文のみ検証
   ```

4. **ローカル DuckDB で変換ビュー作成**

   ```bash
   dbt run -s "stg_*"   # RAW → STG ビューをローカルで生成
   ```

5. **Snowflake でステージング → マート**

   ```bash
   dbt run -s "mart_pool_features_labeled" --target sf --full-refresh
   ```

6. **LightGBM モデル初期学習**

   ```bash
   airflow dags trigger retrain_lightgbm
   ```

7. **毎時推論＆Slack 通知**

   ```bash
   airflow dags trigger predict_volume_spike
   ```

## 🚧 今後のタスク

- [ ] Snowflake 無償クレジット切れ後に **BigQuery 外部テーブル** 移行
- [ ] データドリフト検知用に **再学習頻度 or 特徴量検知** ロジック強化
- [ ] Slack 通知の **閾値チューニング** とアラート最適化
- [ ] BentoML API の **スケーリング／監視** 設計
- [ ] Streamlit ダッシュボードを **運用環境へデプロイ** (GitHub Pages など)

## 📝 ライセンス

MIT License
