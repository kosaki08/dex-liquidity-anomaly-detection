variable "image_tag" {
  type        = string
  description = "Cloud Build でビルドされたコンテナイメージのタグ"
}

variable "composer_version" {
  type        = string
  description = "Composer のバージョン"
  default     = "composer-3-airflow-2.10.5-build.3"
}
