locals {
  # GCP プロジェクト ID
  project_id = terraform.workspace == "prod" ? "portfolio-dex-prod-460122" : "portfolio-dex-dev"

  # デプロイ先リージョン
  region = "asia-northeast1"

  # MLflow のアーティファクトを置く GCS バケット名
  artifacts_bucket = terraform.workspace == "prod" ? "portfolio-dex-mlflow-artifacts-prod" : "portfolio-dex-mlflow-artifacts"
}
