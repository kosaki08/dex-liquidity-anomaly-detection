resource "google_service_account" "streamlit" {
  account_id   = "run-streamlit-${local.env}"
  display_name = "Streamlit Cloud Run SA (${local.env})"
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
