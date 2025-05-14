variable "project_id" {
  description = "GCP プロジェクト ID"
  type        = string
}

variable "region" {
  type    = string
  default = "asia-northeast1"
}

variable "tf_service_account_email" {
  type        = string
  description = "TF サービスアカウントのメールアドレス"
}

variable "env" {
  type        = string
  description = "環境識別子 (dev|prod)"
}

variable "image_tag" {
  description = "Cloud Build でビルドされたコンテナイメージのタグ"
  type        = string
}

variable "artifacts_bucket" {
  description = "MLflow のアーティファクトを置く GCS バケット名"
  type        = string
}
