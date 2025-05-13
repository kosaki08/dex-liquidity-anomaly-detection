output "url" {
  description = "Cloud Run の URL"
  value       = google_cloud_run_v2_service.default.uri
}
