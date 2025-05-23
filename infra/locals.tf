locals {
  # env_suffix が渡されていれば優先、無ければ workspace
  env_suffix = var.env_suffix != "" ? var.env_suffix : terraform.workspace

  # GCP プロジェクト ID
  project_id = local.env_suffix == "prod" ? "portfolio-dex-prod-460122" : "portfolio-dex-dev"

  # デプロイ先リージョン
  region = "asia-northeast1"

  # MLflow のアーティファクトを置く GCS バケット名
  artifacts_bucket = local.env_suffix == "prod" ? "portfolio-dex-mlflow-artifacts-prod" : "portfolio-dex-mlflow-artifacts"
}
