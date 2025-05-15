variable "tf_service_account_email" {
  type        = string
  description = "TF サービスアカウントのメールアドレス"
}

variable "image_tag" {
  description = "Cloud Build でビルドされたコンテナイメージのタグ"
  type        = string
}
