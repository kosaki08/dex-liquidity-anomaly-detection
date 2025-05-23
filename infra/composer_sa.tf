# Composer 専用 SA を用意
resource "google_service_account" "composer" {
  account_id   = "composer-${local.env_suffix}"
  display_name = "Composer SA (${local.env_suffix})"
}

# Composer Worker 権限を付与
resource "google_project_iam_member" "composer_sa_worker_role" {
  project = local.project_id
  role    = "roles/composer.worker"
  member  = "serviceAccount:${google_service_account.composer.email}"
}
