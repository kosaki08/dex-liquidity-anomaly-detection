# [WIP] DEX Pool Reliability Evaluation Pipeline

分散型取引所（DEX）の流動性データを毎時収集し、各プールの TVL／流動性の欠損・負値発生頻度や変動幅をもとに「信頼性スコア」を算出し、安定的に流動性を維持できているプールを可視化・モニタリングするパイプラインです。

- Uniswap V3 / Sushiswap の各プールを対象に「信頼性スコア」を算出
- 毎時間、The Graph API から TVL・流動性・取引量データを取得
- 週次で LightGBM ベースの Reliability Score モデルを再学習し、MLflow で実験管理・BentoML で推論 API 化
- 毎時間最新の信頼性スコアを算出し、しきい値以下のプールを Slack へ自動通知

## 開発ステータス

**✅ 完了済み**

- データ収集（The Graph → JSONL）
- Snowflake RAW/COPY
- dbt Staging / Mart モデル
- LightGBM 初回学習 & MLflow 登録
- 週次再学習 DAG（`retrain_lightgbm`）
- 毎時推論 DAG（`predict_volume_spike`）
- BentoML API & Streamlit ダッシュボード

**🚧 開発中**

- 特徴量エンジニアリングと信頼性スコアリングモデルのパイプライン統合
- 各プールの Reliability Score ダッシュボード整備 (Streamlit)
- EDA Notebook の整備＆リポジトリへの追加
- 特徴量エンジニアリングと異常検知モデルのパイプライン統合

**⏳ 実装予定**

- Terraform による環境構築
- リトライ／エラーハンドリング強化
- Streamlit 上で１ヶ月分の時系列データと予測スコアを並べて表示
- Precision\@10／Recall\@10 推移グラフの実装
- BigQuery 外部テーブル移行
- CI/CD（GitHub Actions）ワークフロー
- シークレット管理強化（Vault など）
- BentoML モデルロード最適化
- Slack で通知

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

## 技術スタック

### データパイプライン

- ETL: Apache Airflow
- データ収集: The Graph API (GraphQL)
- データウェアハウス: Snowflake (PoC), BigQuery (運用)
- データ変換: dbt Core

### 機械学習 & API

- 初期学習 & 週次再学習: LightGBM (LGBMClassifier) + MLflow
- 実験管理: MLflow
- モデル配信: BentoML + FastAPI (LightGBM)
- デプロイ: Cloud Run

### 可視化 & モニタリング

- ダッシュボード: Streamlit (GitHub Pages)
- EDA: DuckDB
- CI/CD: GitHub Actions

## 環境構築

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
# それぞれの値を設定
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

7. BentoML サービス起動

```bash
bentoml serve bentofile.yaml
# または
bentoml serve services.volume_spike_service:VolumeSpikeService
```

8. Streamlit ダッシュボード確認

```bash
streamlit run app/streamlit_app.py
```

## 📂 プロジェクト構造（抜粋）

```
.
├── dags/                           # Airflow DAG 本体
│   ├── dex\_pipeline.py            # メイン ETL（Graph → Snowflake）
│   ├── predict\_volume\_spike.py   # 毎時推論 & Slack 通知
│   ├── retrain\_lightgbm.py        # 週次再学習
│   └── check\_snowflake\_connection.py
│
├── scripts/                       # Python ユーティリティ
│   ├── fetcher/                   # The Graph 取得ロジック
│   │   ├── base.py / uniswap.py / sushiswap.py
│   │   └── queries/               # GraphQL クエリ定義
│   ├── model/                     # 学習・推論スクリプト
│   │   ├── train\_lightgbm.py
│   │   └── predict.py
│   └── import\_volume\_spike\_model.py
│
├── models/                        # dbt モデル
│   ├── staging/                   # RAW → STG
│   │   └── (Uniswap / Sushiswap)
│   ├── mart/                      # 特徴量 & ラベル
│   └── sources/                   # source.yml
│
├── macros/                        # dbt 共通マクロ
│   └── json\_extract.sql / pool\_hourly\_base.sql
│
├── services/                      # BentoML Service
│   └── volume\_spike\_service.py
│
├── sql/                           # Snowflake 初期化 SQL
│   └── 01\_create\_infra.sql など
│
├── app/                           # Streamlit ダッシュボード
│
├── docker-compose.yml
├── Dockerfile.airflow / Dockerfile.bento
├── dbt\_project.yml
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
   - 初期学習: `train_lightgbm.py` による直近 30 日バッチ学習
   - 週次再学習: Airflow DAG (`retrain_lightgbm`) で最新データを再学習・MLflow へログ
5. 異常検知
   Airflow DAG (`predict_volume_spike`) で毎時最新データを LightGBM モデルでスコアリングし、閾値超過時は Slack へ通知
6. 配信 & 可視化
   - API: BentoML + FastAPI で `/score` エンドポイント提供
   - ダッシュボード: Streamlit でリアルタイムにスコア・Precision\@10 推移を表示

## 主な機能

### 信頼性評価

- 流動性の欠損率・負値率・変動統計量を集約してスコアリング
- 各プールごとに「Reliability Score」を算出 (0–1 正規化)
- スコア閾値を下回るプールを Slack へアラート

### モニタリング & 管理

- MLflow トラッキング: 学習／再学習の run, metrics (PR-AUC, Precision\@10, Recall\@10), パラメータを一元管理
- モデルレジストリ: `volume_spike_lgbm` を Production ステージに登録
- Slack アラート: `predict_volume_spike` DAG から `SlackWebhookOperator` でアラート配信

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

6. **LightGBM モデル初期学習**

   ```bash
   airflow dags trigger retrain_lightgbm
   ```

7. **毎時推論＆Slack 通知**

   ```bash
   airflow dags trigger predict_volume_spike
   ```

## ライセンス

MIT License
