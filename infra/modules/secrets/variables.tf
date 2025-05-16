variable "project_id" {
  type        = string
  description = "GCP プロジェクト ID"
}

# Secret ID の付与先となる SA メールアドレスのマップ
variable "accessors" {
  type        = map(list(string))
  description = "Secret に対して accessor 権限を付与する SA のメールリスト"
}
