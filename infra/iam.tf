# Cloud Run の invoker ロールを付与
resource "google_project_iam_member" "composer_run_invoker" {
  project = local.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:service-${data.google_project.project.number}@cloudcomposer-accounts.iam.gserviceaccount.com"
}
