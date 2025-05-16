variable "project_id" {
  type        = string
  description = "GCP プロジェクト ID"
}

variable "sa_names" {
  type        = list(string)
  description = "作成するサービスアカウント名"
}

# terraform.workspace を呼び出し側から渡す
variable "env" {
  type        = string
  description = "環境名 (dev / prod)"
}
