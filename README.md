# [WIP] DEX Liquidity Anomaly Detection Pipeline

分散型取引所（DEX）の流動性データを毎時収集し、Isolation Forest による異常スパイク検知を行うパイプラインです。

- Uniswap V3 / Sushiswap で流動性プールの異常スパイクを検知
- 毎時間ロックされたトークンの時価総額（TVL）と取引量を The Graph API で取得
- 週次で Isolation Forest モデルを再学習し、MLflow で管理・BentoML 経由で推論 API 化
- 毎時間スコアリング

## デモ URL (dev)

- Streamlit Dashboard
  <https://streamlit-dev-6tqknz3neq-an.a.run.app/>
- BentoML API
  <https://bento-api-dev-6tqknz3neq-an.a.run.app/predict>

## 開発ステータス

**✅ 完了済み**

- データ収集（The Graph → JSONL）
- Snowflake RAW/COPY
- dbt Staging / Mart モデル
- Isolation Forest 初回学習 & MLflow 登録
- 週次再学習 DAG（`retrain_isolation_forest`）
- 毎時推論 DAG（`predict_pool_iforest`）
- BentoML API & Streamlit ダッシュボード
- CI/CD（GitHub Actions）ワークフロー
- Terraform でのベースインフラ（Cloud Run / Secret Manager / VPC）

**🚧 開発中**

- Cloud Composer 3（dev 環境）への Airflow DAG デプロイ
- 権限制御 (IAM 最小権限ポリシー) の細分化
- EDA Notebook の整備＆リポジトリへの追加

**⏳ 実装予定**

- Cloud Logging / Error Reporting 連携
- リトライ／エラーハンドリング強化
- Streamlit 上で１ヶ月分の時系列データと予測スコアを並べて表示
- Precision\@10／Recall\@10 推移グラフの実装
- Snowflake から BigQuery への外部テーブル移行
- シークレット管理強化（Vault）

## アーキテクチャ

```
┌──────────────┐
│  GitHub      │      CI : GitHub Actions
└──────┬───────┘
       │              (lint / unit-test / dbt build)
       ▼
┌───────────────┐  Airflow  ┌───────────┐
│ The Graph API │──DAG──────▶ Snowflake │  (raw / stg / mart)
│  ├ Uniswap V3 │           └─────┬─────┘
│  └ Sushiswap  │                 │ dbt run
└───────────────┘                 ▼
                           ┌──────────────────────────┐
                           │ retrain_isolation_forest │  @weekly retrain  ← train_isolation_forest.py
                           └──────┬───────────────────┘
                                  │ model: volume_spike_iforest (Production)
                                  ▼
                           ┌──────────────────────┐
                           │ predict_pool_iforest │  @hourly predict + Slack alert
                           └──────┬───────────────┘
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
                           │ Streamlit  │  Cloud Run
                           └────────────┘
```

## 技術スタック

### データパイプライン

- ETL: Apache Airflow
- データ収集: The Graph API (GraphQL)
- データウェアハウス: Snowflake (PoC), BigQuery (運用)
- データ変換: dbt Core

### 機械学習 & API

- 初期学習 & 週次再学習: Isolation Forest + MLflow
- 実験管理: MLflow
- モデル配信: BentoML + FastAPI (Isolation Forest)
- デプロイ: Cloud Run

### 可視化 & モニタリング

- ダッシュボード: Streamlit (GitHub Pages)
- EDA: DuckDB
- CI/CD: GitHub Actions

## 環境構築

### 利用サービス等

- gcloud CLI
- Cloud Build API／Artifact Registry API／Secret Manager API
- Docker & Docker Compose
- Python 3.11+
- The Graph API
- Snowflake

### セットアップ

1. リポジトリをクローン

```bash
git clone https://github.com/yourusername/dex-liquidity-anomaly-detection.git
cd dex-liquidity-anomaly-detection
```

2. 環境変数を設定

```bash
cp .env.example .env
# それぞれの値を設定
```

3. 基盤セットアップ

```bash
# Snowflake セットアップ
make setup-snowflake

# Airflow & データパイプライン起動
docker compose up -d

# パイプラインを手動トリガー（初回データロード）
docker compose exec airflow airflow dags trigger dex_liquidity_raw
```

4. dbt による変換

```bash
# dbt モデルをビルド
dbt build
```

5. Airflow DAG の実行

- 初回／週次再学習

```bash
docker compose exec airflow airflow dags trigger retrain_isolation_forest
```

- 毎時推論

```bash
docker compose exec airflow airflow dags trigger predict_pool_iforest
```

6. API サーバー起動

```bash
# ローカルで実行
bentoml serve services.volume_spike_service:PoolIForestService

# または Cloud Run にデプロイ
make deploy-to-cloud-run
```

7. BentoML サービス起動

```bash
bentoml serve bentofile.yaml
# または
bentoml serve services.volume_spike_service:PoolIForestService
```

8. Streamlit ダッシュボード確認

```bash
streamlit run app/streamlit_app.py
```

## 📂 プロジェクト構造（抜粋）

```
.
├── dags/                          # Airflow DAG 本体
│   ├── dex_pipeline.py            # メイン ETL（Graph → Snowflake）
│   ├── predict_pool_iforest.py    # 毎時推論 & Slack 通知
│   ├── retrain_isolation_forest.py         # 週次再学習
│   └── check_snowflake_connection.py
│
├── scripts/                       # Python ユーティリティ
│   ├── fetcher/                   # The Graph 取得ロジック
│   │   ├── base.py / uniswap.py / sushiswap.py
│   │   └── queries/               # GraphQL クエリ定義
│   ├── model/                     # 学習・推論スクリプト
│   │   ├── train_iforest.py
│   │   └── predict.py
│   └── import_volume_spike_model.py
│
├── models/                        # dbt モデル
│   ├── staging/                   # RAW → STG
│   │   └── (Uniswap / Sushiswap)
│   ├── mart/                      # 特徴量 & ラベル
│   └── sources/                   # source.yml
│
├── macros/                        # dbt 共通マクロ
│   └── json_extract.sql / pool_hourly_base.sql
│
├── services/                      # BentoML Service
│   └── volume_spike_service.py
│
├── sql/                           # Snowflake 初期化 SQL
│   └── 01_create_infra.sql など
│
├── app/                           # Streamlit ダッシュボード
│
├── infra/                         # Terraform インフラ
│   ├── envs/                      # Dev / Prod 環境ごとの Terraform ファイル
│   └── modules/                   # Terraform モジュール
│
├── docker-compose.yml
├── Dockerfile.airflow / Dockerfile.bento
├── dbt_project.yml
├── pyproject.toml / poetry.lock
└── README.md
```

## データフロー

1. データ収集
   The Graph API から Uniswap V3／Sushiswap の hourly プールデータを取得
2. ロード
   Airflow DAG (`dex_liquidity_raw`) で Snowflake RAW レイヤへ `COPY INTO`
3. 変換
   dbt で Staging → Mart（`mart_pool_features_labeled`）モデルをビルド
4. モデル学習
   - 初期学習: `train_iforest.py` による直近 30 日バッチ学習
   - 週次再学習: Airflow DAG (`retrain_isolation_forest`) で最新データを再学習・MLflow へログ
5. 異常検知
   Airflow DAG (`predict_pool_iforest`) で毎時最新データを Isolation Forest モデルでスコアリングし、閾値超過時は Slack へ通知
6. 配信 & 可視化
   - API: BentoML + FastAPI で `/score` エンドポイント提供
   - ダッシュボード: Streamlit でリアルタイムにスコア・Precision\@10 推移を表示

## 主な機能

### 異常検知

- 教師なし二値分類: Isolation Forest による volume-spike 検出
- ラベル生成: Mart モデル内でプールごとの 90th percentile を閾値とした教師ラベル (`y`) を自動生成
- 毎時推論: 最新データをスコアリングし、スコア ≥ 閾値 のプールを Slack へ通知

### モニタリング & 管理

- MLflow トラッキング: 学習／再学習の run, metrics (PR-AUC, Precision\@10, Recall\@10), パラメータを一元管理
- モデルレジストリ: `volume_spike_iforest` を Production ステージに登録

### 配信 & 可視化

- BentoML API: `/predict` エンドポイントでリアルタイムスコア取得可能
- Streamlit ダッシュボード:
  - スコア上位 N プール一覧
  - スコア閾値スライダー
  - Precision\@10／Recall\@10 推移グラフ

### 動作確認フロー（開発用）

1. **DBT プロファイル解決の確認**

   ```bash
   dbt debug   # profiles/ が正しく読めているか
   ```

2. **staging モデル確認**

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

5. **Snowflake で staging → mart**

   ```bash
   dbt run -s "mart_pool_features_labeled" --target sf --full-refresh
   ```

6. **Isolation Forest モデル初期学習**

   ```bash
   airflow dags trigger retrain_isolation_forest
   ```

7. **毎時推論**

   ```bash
   airflow dags trigger predict_pool_iforest
   ```

## ライセンス

MIT License
