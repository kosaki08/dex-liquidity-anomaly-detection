variable "image_tag" {
  type        = string
  description = "Cloud Build でビルドされたコンテナイメージのタグ"
}

variable "composer_version" {
  type        = string
  description = "Composer のバージョン"
  default     = "composer-3-airflow-2.10.5-build.3"
}

# dev / prod を CLI から渡すために設定
variable "env_suffix" {
  description = "環境識別子 (dev / prod)。未指定なら terraform.workspace を使う"
  type        = string
  default     = ""
}
