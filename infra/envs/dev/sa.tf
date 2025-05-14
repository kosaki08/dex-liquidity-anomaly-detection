resource "google_service_account" "streamlit" {
  account_id   = "run-streamlit-${var.env}"
  display_name = "Streamlit Cloud Run SA (${var.env})"
}

# Secret Manager Accessor 付与
resource "google_secret_manager_secret_iam_member" "streamlit_sa_access" {
  for_each = toset([
    "snowflake-pass",
    "snowflake-user",
  ])

  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.streamlit.email}"
}
