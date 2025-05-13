variable "project_id" {
  type        = string
  description = "GCP プロジェクト ID"
}

variable "name" {
  type        = string
  description = "Cloud Run サービス名"
}

variable "location" {
  type        = string
  description = "デプロイ先リージョン"
}

variable "image" {
  type        = string
  description = "コンテナイメージ URL"
}

variable "vpc_connector" {
  type        = string
  description = "VPC コネクタのリソース ID"
  default     = null
}

variable "concurrency" {
  type        = number
  description = "同時実行数"
  default     = 80
}

variable "memory" {
  type        = string
  description = "メモリサイズ"
  default     = "512Mi"
}

variable "env_vars" {
  type        = map(string)
  description = "環境変数マップ"
  default     = {}
}

variable "container_port" {
  type        = number
  description = "コンテナ内アプリが LISTEN するポート番号"
  default     = 3000
}
