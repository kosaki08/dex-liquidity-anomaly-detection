# DEX Liquidity Anomaly Detection Pipeline

分散型取引所（DEX）の流動性データをリアルタイムで収集・異常検知するパイプラインです。Uniswap V3, Sushiswap から hourly データを抽出し、River による 1 時間ごとのオンライン学習によって異常な流動性パターンを検知します。

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
                           ┌─────────────┐
                           │  River OL   │  hourly partial_fit
                           └──────┬──────┘
                                  │ metrics
                           ┌───────────┐
                           │   MLflow  │  experiment tracking
                           └──────┬────┘
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

- **オンライン学習**: River (IsolationForest)
- **実験管理**: MLflow
- **モデル配信**: BentoML + FastAPI
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

5. River オンライン学習の起動

```bash
# 初期モデルを訓練
docker-compose exec airflow airflow dags trigger train_initial_model

# オンライン学習スケジュールを開始
docker-compose exec airflow airflow dags trigger update_model_hourly
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

1. **データ収集**: The Graph API から hourly プールデータを取得
2. **ロード**: Snowflake RAW レイヤに COPY INTO
3. **変換**: dbt でステージング～マートモデル作成
4. **モデル学習**: 初期バッチ学習＋継続的なオンライン学習
5. **異常検知**: 新規データに対して 1 時間ごとに予測
6. **可視化**: Streamlit ダッシュボードでリアルタイム表示

## 💡 主な機能

### 異常検知

- IsolationForest による非教師あり学習
- 流動性・ボリューム・価格の時系列異常を検知
- データドリフト検知と自動再学習

### モニタリング

- MLflow による実験管理
- メトリクス（F1, Precision）トラッキング
- ダッシュボードでの TOP N 異常可視化

### 動作確認フロー（開発用）

1. **プロファイル解決の確認**

   ```bash
   dbt debug   # profiles/ が取れているか確認
   ```

2. **モデル一覧**

   ```bash
   dbt ls -s "stg_*"  # モデル一覧
   ```

3. **構文チェックのみ**

   ```bash
   dbt parse   # 実 DB 接続なし
   ```

4. **DuckDB (ローカル) で実行**

   ```bash
   dbt run -s "stg_*"  # RAW → STG の変換ビューが作成
   ```

5. **Snowflake で実行**

   ```bash
   dbt run -s "stg_*" --target sf
   ```

## 🚧 ローンチ後のタスク

- [ ] Snowflake trial 終了後 BigQuery External Table へ移行
- [ ] データドリフト検知の強化

## 📝 ライセンス

MIT License
