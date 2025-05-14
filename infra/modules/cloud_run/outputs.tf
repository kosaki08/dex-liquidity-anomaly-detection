output "url" {
  description = "Cloud Run の URL"
  value       = google_cloud_run_v2_service.default.uri
}

output "service_account_email" {
  description = "Cloud Run リビジョンにアタッチされたサービスアカウント（nullになることがあります→デフォルト）"
  value       = google_cloud_run_v2_service.default.template[0].service_account
}
