variable "tf_service_account_email" {
  type        = string
  description = "TF サービスアカウントのメールアドレス"
}

variable "image_tag" {
  type        = string
  description = "Cloud Build でビルドされたコンテナイメージのタグ"
}
